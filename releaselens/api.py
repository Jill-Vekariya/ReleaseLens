import json
import logging
import os
import secrets
from asyncio import Lock
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from releaselens.db import create_local_schema, database
from releaselens.fixtures import seed
from releaselens.generation import configured_generator
from releaselens.ingestion import RevisionConflict, ingest
from releaselens.middleware import BodyLimitMiddleware
from releaselens.models import Answer, Change, Document, Review
from releaselens.relevance import configured_gate
from releaselens.retrieval import configured_embedder
from releaselens.schemas import AnswerPayload, AskRequest, CompareRequest, IngestRequest
from releaselens.security import ROLE_LEVELS, Forbidden, NotFound, Principal, authorized_document
from releaselens.service import ask, owned_answer, revalidate

log = logging.getLogger("releaselens")
ROOT = Path(__file__).resolve().parents[1]


def create_app(database_url=None, demo=None, tokens=None):
    demo = demo if demo is not None else os.getenv("RELEASELENS_DEMO", "false").lower() == "true"
    credentials = (
        tokens if tokens is not None else json.loads(os.getenv("RELEASELENS_TOKENS", "{}"))
    )
    if not demo and not credentials:
        raise RuntimeError(
            "Set RELEASELENS_TOKENS or explicitly enable loopback-only RELEASELENS_DEMO"
        )
    for token, identity in credentials.items():
        if len(token) < 24 or identity.get("role") not in ROLE_LEVELS or not identity.get("user"):
            raise RuntimeError(
                "Invalid token configuration; use random tokens of at least 24 characters"
            )
    engine, factory = database(database_url)
    embedder = configured_embedder()
    generator = configured_generator()
    relevance_gate = configured_gate()
    if relevance_gate is not None:
        policy = json.loads(Path(os.environ["ANSWERABILITY_POLICY"]).read_text(encoding="utf-8"))
        if policy.get("embedding") != embedder.name or policy.get("backend") != engine.dialect.name:
            raise ValueError(
                "Answerability policy requires its measured encoder and database backend"
            )
    prose_candidates = os.getenv("ENABLE_PROSE_REVIEW_CANDIDATES", "false").lower() == "true"
    # Sync generator dependencies may enter/exit on different worker threads.
    # Serialize transactions in an async dependency so no thread-owned lock crosses them.
    lock = Lock()

    @asynccontextmanager
    async def lifespan(app):
        if engine.dialect.name == "sqlite":
            create_local_schema(engine)
        if demo:
            with factory.begin() as session:
                seed(session, embedder)
        yield
        engine.dispose()

    app = FastAPI(
        title="ReleaseLens", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    app.state.factory = factory
    app.state.engine = engine
    app.state.embedder = embedder
    app.add_middleware(BodyLimitMiddleware, max_bytes=2_000_000)

    @app.middleware("http")
    async def telemetry(request: Request, call_next):
        request_id, start = str(uuid4()), perf_counter()
        # Demo role selection is deliberately restricted to loopback/test clients.
        if (
            demo
            and request.client
            and request.client.host not in ("127.0.0.1", "::1", "testclient")
        ):
            return JSONResponse({"detail": "Demo is loopback-only"}, status_code=403)
        if (
            request.headers.get("content-length", "0").isdigit()
            and int(request.headers.get("content-length", "0")) > 2_000_000
        ):
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        response = await call_next(request)
        elapsed = round((perf_counter() - start) * 1000, 3)
        response.headers["X-Request-ID"] = request_id
        response.headers["Server-Timing"] = f"app;dur={elapsed}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        # No question, passage, authorization token, or raw URL is logged.
        route = request.scope.get("route")
        log.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "route": route.path if route else "unmatched",
                    "status": response.status_code,
                    "latency_ms": elapsed,
                }
            )
        )
        return response

    def principal(
        authorization: str | None = Header(default=None),
        x_demo_role: str = Header(default="reader"),
    ):
        if authorization and authorization.startswith("Bearer "):
            supplied = authorization[7:]
            for token, identity in credentials.items():
                if secrets.compare_digest(supplied.encode(), token.encode()):
                    return Principal(identity["user"], identity["role"])
            raise HTTPException(401, "Invalid credentials")
        if demo and x_demo_role in ROLE_LEVELS:
            return Principal("demo-" + x_demo_role, x_demo_role)
        raise HTTPException(401, "Bearer authentication required")

    async def session_dep():
        async with lock:
            with factory.begin() as session:
                session.info["embedder"] = embedder
                session.info["generator"] = generator
                session.info["relevance_gate"] = relevance_gate
                session.info["prose_review_candidates"] = prose_candidates
                yield session

    for exception, code in ((NotFound, 404), (Forbidden, 403), (RevisionConflict, 409)):

        async def handler(request, exc, status=code):
            return JSONResponse({"detail": str(exc)}, status_code=status)

        app.add_exception_handler(exception, handler)

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(
            {"detail": "Concurrent or conflicting write; retry with current revision"},
            status_code=409,
        )

    @app.get("/health")
    def health(session=Depends(session_dep, scope="function")):
        session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": engine.dialect.name,
            "demo": demo,
            "embedding": embedder.name,
            "generator": generator.name,
            "answerability_policy": relevance_gate.policy_id if relevance_gate else None,
            "prose_review_candidates": prose_candidates,
        }

    @app.get("/api/projects")
    def projects(p=Depends(principal), session=Depends(session_dep, scope="function")):
        docs = session.scalars(
            select(Document).where(Document.classification.in_(p.classifications))
        )
        result = {}
        for doc in docs:
            result.setdefault(doc.project, set()).add(doc.release)
        return {key: sorted(values) for key, values in result.items()}

    @app.post("/api/ingest")
    def ingest_route(
        body: IngestRequest, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        return ingest(session, p, body, embedder)

    @app.post("/api/ask", response_model=AnswerPayload)
    def ask_route(
        body: AskRequest, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        if relevance_gate is not None and (body.mode != "version" or body.k != 4):
            raise HTTPException(
                422, "Experimental answerability policy requires version mode and k=4"
            )
        return ask(session, p, body, embedder)

    @app.post("/api/compare")
    def compare(
        body: CompareRequest, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        answers = [
            ask(
                session,
                p,
                AskRequest(project=body.project, release=v, question=body.question),
                embedder,
            )
            for v in (body.left, body.right)
        ]
        return {
            "left": answers[0],
            "right": answers[1],
            "comparison": "Inspect the cited extracts side by side; no inferred migration advice.",
        }

    @app.get("/api/evidence/{passage_id}")
    def evidence(
        passage_id: str, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        from releaselens.models import Passage
        from releaselens.service import citation

        passage = session.get(Passage, passage_id)
        if passage is None:
            raise NotFound("Resource unavailable")
        document = authorized_document(session, passage.document_id, p)
        if passage.quarantined:
            raise NotFound("Resource unavailable")
        return citation(session, passage, document)

    @app.get("/api/answers")
    def answers(p=Depends(principal), session=Depends(session_dep, scope="function")):
        result = []
        for answer in session.scalars(
            select(Answer).where(Answer.owner == p.user).order_by(Answer.created_at.desc())
        ):
            try:
                owned_answer(session, p, answer.id)
            except NotFound:
                continue
            result.append(
                {
                    "id": answer.id,
                    "question": answer.question,
                    "status": answer.status,
                    "project": answer.project,
                    "release": answer.release,
                }
            )
        return result

    @app.get("/api/answers/{answer_id}")
    def answer_detail(
        answer_id: str, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        answer, dependencies = owned_answer(session, p, answer_id)
        return {
            "id": answer.id,
            "status": answer.status,
            "payload": answer.payload,
            "dependencies": [item.id for item in dependencies],
        }

    @app.post("/api/answers/{answer_id}/revalidate")
    def revalidate_route(
        answer_id: str, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        # Lock this owner's answer before generating audit/correction rows.
        session.scalar(
            select(Answer).where(Answer.id == answer_id, Answer.owner == p.user).with_for_update()
        )
        return revalidate(session, p, answer_id)

    @app.get("/api/answers/{answer_id}/history")
    def history(
        answer_id: str, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        owned_answer(session, p, answer_id)
        reviews = session.scalars(
            select(Review).where(Review.answer_id == answer_id).order_by(Review.created_at)
        )
        return [
            {
                "id": r.id,
                "status": r.status,
                "assessment": r.assessment,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ]

    @app.get("/api/documents")
    def documents(p=Depends(principal), session=Depends(session_dep, scope="function")):
        docs = session.scalars(
            select(Document).where(Document.classification.in_(p.classifications))
        )
        return [
            {
                "id": d.id,
                "project": d.project,
                "release": d.release,
                "key": d.key,
                "revision_id": d.current_revision,
                "classification": d.classification,
            }
            for d in docs
        ]

    @app.get("/api/documents/{document_id}/changes")
    def changes(
        document_id: str, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        authorized_document(session, document_id, p)
        return [
            {
                "id": c.id,
                "kind": c.kind,
                "delta": c.delta,
                "old_revision": c.old_revision,
                "new_revision": c.new_revision,
            }
            for c in session.scalars(select(Change).where(Change.document_id == document_id))
        ]

    @app.get("/api/documents/{document_id}")
    def document_detail(
        document_id: str, p=Depends(principal), session=Depends(session_dep, scope="function")
    ):
        from releaselens.models import Passage
        from releaselens.service import citation

        document = authorized_document(session, document_id, p)
        passages = session.scalars(
            select(Passage).where(
                Passage.revision_id == document.current_revision, Passage.quarantined.is_(False)
            )
        )
        return {
            "id": document.id,
            "revision_id": document.current_revision,
            "passages": [citation(session, item, document) for item in passages],
        }

    @app.get("/api/evaluation")
    def evaluation(p=Depends(principal)):
        path = ROOT / "evaluation" / "results.json"
        return json.loads(path.read_text()) if path.exists() else {"status": "not_run"}

    @app.get("/")
    def index():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/docs", include_in_schema=False)
    def api_docs():
        from html import escape

        from fastapi.responses import HTMLResponse

        rows = "".join(
            f"<tr><td>{escape(method.upper())}</td><td>{escape(path)}</td><td>{escape(operation.get('summary', ''))}</td></tr>"
            for path, methods in app.openapi()["paths"].items()
            for method, operation in methods.items()
        )
        return HTMLResponse(
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ReleaseLens API</title>'
            '<link rel="stylesheet" href="/style.css"></head><body><h1>ReleaseLens API</h1>'
            '<p><a href="/openapi.json">OpenAPI 3.1 schema</a> · <a href="/">Workbench</a></p>'
            "<p>Bearer credentials required outside the explicit local demo. Errors: 401 authentication, "
            "403 forbidden operation, 404 missing or unauthorized resource, 409 revision conflict, 422 invalid body.</p>"
            "<table><tr><th>Method</th><th>Path</th><th>Operation</th></tr>"
            + rows
            + "</table></body></html>"
        )

    @app.get("/app.js")
    def javascript():
        return FileResponse(ROOT / "web" / "app.js", media_type="text/javascript")

    @app.get("/style.css")
    def styles():
        return FileResponse(ROOT / "web" / "style.css", media_type="text/css")

    return app
