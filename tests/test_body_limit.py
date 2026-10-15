import asyncio

import httpx

from releaselens.api import create_app


def test_chunked_body_limit_does_not_trust_content_length():
    async def scenario():
        app = create_app("sqlite:///:memory:", demo=True)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
                base_url="http://test",
            ) as client:

                async def chunks():
                    for _ in range(3):
                        yield b"x" * 800_000

                response = await client.post(
                    "/api/ask", content=chunks(), headers={"content-type": "application/json"}
                )
                assert response.status_code == 413
                response = await client.post(
                    "/api/ask",
                    content=chunks(),
                    headers={"content-length": "1", "content-type": "application/json"},
                )
                assert response.status_code == 413
                assert (await client.get("/health")).status_code == 200

    asyncio.run(scenario())
