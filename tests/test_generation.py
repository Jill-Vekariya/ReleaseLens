import json

import httpx
import pytest

from releaselens.generation import CompatibleGenerator, GenerationFailure
from releaselens.models import Passage


def test_provider_receives_only_supplied_evidence_and_returns_usage():
    def respond(request):
        data = json.loads(request.content)
        assert "CANARY" not in str(data)
        evidence = json.loads(data["messages"][1]["content"])["evidence"]
        assert evidence == [{"passage_id": "p1", "text": "An authorized extract"}]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "extracts": [
                                        {"passage_id": "p1", "text": "An authorized extract"}
                                    ]
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 30, "completion_tokens": 15},
            },
        )

    provider = CompatibleGenerator(
        "https://provider.invalid/v1", "test", transport=httpx.MockTransport(respond)
    )
    selections, metadata = provider.select(
        "a question", [Passage(id="p1", text="An authorized extract")]
    )
    assert selections[0]["passage_id"] == "p1"
    assert metadata["provider_cost_usd"] is None
    assert metadata["usage"]["prompt_tokens"] == 30
    malformed = CompatibleGenerator(
        "https://provider.invalid/v1",
        "test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "not valid JSON"}}],
                    "usage": {"prompt_tokens": 90},
                },
            )
        ),
    )
    with pytest.raises(GenerationFailure) as failure:
        malformed.select("a question", [Passage(id="p1", text="An authorized extract")])
    assert failure.value.metadata["usage"]["prompt_tokens"] == 90
    assert failure.value.metadata["provider_cost_usd"] is None


@pytest.mark.parametrize(
    "url",
    [
        "http://external.invalid",
        "https://user:password@provider.invalid",
        "https://provider.invalid?key=secret",
    ],
)
def test_provider_endpoint_constraints(url):
    with pytest.raises(ValueError):
        CompatibleGenerator(url, "test")


def test_fabricated_provider_extract_abstains(client, admin):
    from releaselens.schemas import AskRequest
    from releaselens.security import Principal
    from releaselens.service import ask

    def respond(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "extracts": [
                                        {"passage_id": "made-up-id", "text": "Use a secret setting"}
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    generator = CompatibleGenerator(
        "https://provider.invalid/v1", "test", transport=httpx.MockTransport(respond)
    )
    with client.app.state.factory.begin() as session:
        session.info["generator"] = generator
        result = ask(
            session,
            Principal("demo-admin", "admin"),
            AskRequest(project="demo", release="1.0", question="request_timeout", k=1),
            client.app.state.embedder,
        )
        assert not result.claims
        assert result.abstention_reason


def test_unauthorized_evidence_never_reaches_generator(client):
    from releaselens.schemas import AskRequest
    from releaselens.security import Principal
    from releaselens.service import ask

    class Spy:
        name = "boundary-spy"
        calls = 0

        def select(self, question, passages):
            self.calls += 1
            assert all("CANARY-ORCHID" not in passage.text for passage in passages)
            return [{"text": p.text, "passage_id": p.id} for p in passages], {
                "provider_cost_usd": 0
            }

    spy = Spy()
    with client.app.state.factory.begin() as session:
        session.info["generator"] = spy
        result = ask(
            session,
            Principal("reader", "reader"),
            AskRequest(project="demo", release="1.0", question="CANARY-ORCHID-7814", save=False),
            client.app.state.embedder,
        )
        assert result.abstention_reason
        assert spy.calls == 0
        result = ask(
            session,
            Principal("reader", "reader"),
            AskRequest(project="demo", release="1.0", question="request_timeout", save=False),
            client.app.state.embedder,
        )
        assert spy.calls == 1


def test_compatible_keyless_loopback_endpoint_uses_real_http_without_empty_bearer(monkeypatch):
    """MockTransport accepts an empty Bearer header that the actual h11 wire rejects."""
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from types import SimpleNamespace

    monkeypatch.setenv("ALL_PROXY", "socks5://127.0.0.1:1")
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            seen.append(self.headers.get("Authorization"))
            self.rfile.read(int(self.headers["Content-Length"]))
            data = json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"extracts": [{"text": "Exact quote", "passage_id": "p"}]}
                                )
                            }
                        }
                    ]
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        generator = CompatibleGenerator(f"http://127.0.0.1:{server.server_port}/v1", "local")
        extracts, _ = generator.select("Question?", [SimpleNamespace(id="p", text="Exact quote")])
        assert extracts == [{"text": "Exact quote", "passage_id": "p"}]
        assert seen == [None]
    finally:
        server.shutdown()
        server.server_close()
