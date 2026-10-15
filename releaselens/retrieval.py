"""Small-corpus retrieval. ACL and optional release filtering precede scoring."""

import hashlib
import math
import os
import re
from collections import Counter

from sqlalchemy import select, text

from releaselens.models import Document, Passage

STOP = set(
    "a an the is are was were to of for in on and or how what which can i use do does with my".split()
)
DIMENSIONS = 384


def tokens(value: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", value.lower()) if t not in STOP]


class HashEmbedder:
    """Deterministic feature-hashing test double. No learned semantics."""

    name = "hash-384-demo-not-semantic"

    def encode(self, value: str) -> list[float]:
        result = [0.0] * DIMENSIONS
        for token, count in Counter(tokens(value)).items():
            digest = hashlib.sha256(token.encode()).digest()
            result[int.from_bytes(digest[:4], "big") % DIMENSIONS] += count
        length = math.sqrt(sum(x * x for x in result)) or 1
        return [x / length for x in result]


class SentenceEmbedder:
    """Opt-in local learned encoder; pin the model commit in configuration."""

    def __init__(self, model: str, revision: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model, revision=revision, trust_remote_code=False)
        if self.model.get_sentence_embedding_dimension() != DIMENSIONS:
            raise ValueError("This schema requires a 384-dimensional model")
        self.name = f"{model}@{revision}"

    def encode(self, value: str) -> list[float]:
        return self.model.encode(value, normalize_embeddings=True).tolist()


def configured_embedder():
    model, revision = os.getenv("EMBEDDING_MODEL"), os.getenv("EMBEDDING_REVISION")
    if not model and not revision:
        return HashEmbedder()
    if not model or not revision or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Learned encoder requires a model and a 40-character commit revision")
    return SentenceEmbedder(model, revision)


def bm25(query: str, texts: list[str]) -> list[float]:
    corpus = [Counter(tokens(t)) for t in texts]
    lengths = [sum(c.values()) for c in corpus]
    average = sum(lengths) / max(len(corpus), 1) or 1
    scores = [0.0] * len(corpus)
    for term in set(tokens(query)):
        df = sum(term in c for c in corpus)
        idf = math.log(1 + (len(corpus) - df + 0.5) / (df + 0.5))
        for i, c in enumerate(corpus):
            frequency = c[term]
            scores[i] += (
                idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * lengths[i] / average))
            )
    return scores


def rank(session, principal, project, release, question, embedder, mode="version", k=5):
    if session.bind.dialect.name == "postgresql":
        return postgres_rank(session, principal, project, release, question, embedder, mode, k)
    query = (
        select(Passage, Document)
        .join(Document, Passage.document_id == Document.id)
        .where(
            Document.classification.in_(principal.classifications),
            Document.project == project,
            Passage.revision_id == Document.current_revision,
            Passage.quarantined.is_(False),
            Passage.embedding_model == embedder.name,
        )
    )
    # A/B/C intentionally omit release for ablations. Their outputs never bypass citation checks.
    if mode == "version":
        query = query.where(Document.release == release)
    rows = list(session.execute(query))
    if not rows:
        return []
    vectors = embedder.encode(question)
    dense = [sum(x * y for x, y in zip(vectors, p.embedding, strict=True)) for p, _ in rows]
    lexical = bm25(question, [p.section + " " + p.text for p, _ in rows])

    def stable_key(i):
        return (rows[i][1].release, rows[i][1].key, rows[i][0].logical_key)

    order_dense = sorted(range(len(rows)), key=lambda i: (-dense[i], stable_key(i)))
    order_lexical = sorted(range(len(rows)), key=lambda i: (-lexical[i], stable_key(i)))
    # Positive lexical overlap is a conservative demo abstention gate, not calibrated confidence.
    eligible = (
        set(range(len(rows)))
        if mode == "vector"
        else {i for i in range(len(rows)) if lexical[i] > 0}
    )
    if mode == "vector":
        ranked = order_dense
        scores = dense
    else:
        scores = [0.0] * len(rows)
        for order in (order_dense[:20], order_lexical[:20]):
            for position, i in enumerate(order):
                scores[i] += 1 / (60 + position + 1)
        ranked = sorted(range(len(rows)), key=lambda i: (-scores[i], stable_key(i)))
        if mode == "rerank":
            # Transparent heuristic experiment; not a learned cross-encoder.
            terms = set(tokens(question))
            ranked = sorted(
                ranked[:20],
                key=lambda i: (
                    -len(terms & set(tokens(rows[i][0].section))) / max(len(terms), 1),
                    -scores[i],
                    stable_key(i),
                ),
            )
    return [(rows[i][0], rows[i][1], scores[i]) for i in ranked if i in eligible][:k]


def pgvector_candidates(session, principal, project, release, vector, k=20):
    """Exact pgvector search with SQL authorization before ORDER/LIMIT; no ANN recall claims."""
    return session.execute(
        text("""
      SELECT p.id, p.dense_vector <=> CAST(:query AS vector) AS distance
      FROM passages p JOIN documents d ON p.document_id = d.id
      WHERE d.project = :project AND d.release = :release
        AND d.classification = ANY(CAST(:classes AS text[]))
        AND p.revision_id = d.current_revision AND NOT p.quarantined
      ORDER BY distance, p.id LIMIT :k
    """),
        {
            "query": str(vector),
            "project": project,
            "release": release,
            "classes": list(principal.classifications),
            "k": k,
        },
    ).all()


def postgres_rank(session, principal, project, release, question, embedder, mode, k):
    """SQL-filtered exact dense search + PostgreSQL lexical search and RRF.

    Uses PostgreSQL text ranking, not BM25. CI integration is required before claiming
    deployment validation; local SQLite experiments are not measurements of this path.
    """
    scope = """
      FROM passages p JOIN documents d ON p.document_id=d.id
      WHERE d.project=:project
        AND (CAST(:release AS text) IS NULL OR d.release=CAST(:release AS text))
        AND d.classification=ANY(CAST(:classes AS text[]))
        AND p.revision_id=d.current_revision AND NOT p.quarantined
        AND p.embedding_model=:embedding_model
    """
    params = {
        "project": project,
        "release": release if mode == "version" else None,
        "classes": list(principal.classifications),
        "embedding_model": embedder.name,
        "vector": str(embedder.encode(question)),
        "question": question,
    }
    dense_rows = session.execute(
        text(
            "SELECT p.id, p.dense_vector <=> CAST(:vector AS vector) AS distance "
            + scope
            + " ORDER BY distance, d.release, d.key, p.logical_key LIMIT 20"
        ),
        params,
    ).all()
    lexical_rows = session.execute(
        text(
            "SELECT p.id, ts_rank_cd(to_tsvector('english', p.section || ' ' || p.text), "
            "websearch_to_tsquery('english',:question)) AS score "
            + scope
            + " AND to_tsvector('english', p.section || ' ' || p.text) @@ websearch_to_tsquery('english',:question) "
            "ORDER BY score DESC, d.release, d.key, p.logical_key LIMIT 20"
        ),
        params,
    ).all()
    eligible = {row.id for row in (dense_rows if mode == "vector" else lexical_rows)}
    if not eligible:
        return []
    scores = {}
    if mode == "vector":
        scores = {row.id: 1 - row.distance for row in dense_rows if row.id in eligible}
    else:
        for group in (dense_rows, lexical_rows):
            for index, row in enumerate(group):
                scores[row.id] = scores.get(row.id, 0) + 1 / (61 + index)
        scores = {pid: score for pid, score in scores.items() if pid in eligible}
    rows = list(
        session.execute(
            select(Passage, Document)
            .join(Document, Passage.document_id == Document.id)
            .where(Passage.id.in_(scores))
        )
    )
    terms = set(tokens(question))
    rows.sort(key=lambda row: (-scores[row[0].id], row[1].release, row[1].key, row[0].logical_key))
    if mode == "rerank":
        rows.sort(
            key=lambda row: (
                -len(terms & set(tokens(row[0].section))) / max(len(terms), 1),
                -scores[row[0].id],
                row[1].release,
                row[1].key,
                row[0].logical_key,
            )
        )
    return [(p, d, scores[p.id]) for p, d in rows[:k]]
