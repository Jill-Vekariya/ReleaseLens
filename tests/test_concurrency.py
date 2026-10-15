import asyncio

import httpx

from releaselens.api import create_app


def test_concurrent_requests_complete_without_cross_thread_dependency_lock_errors():
    async def scenario():
        app = create_app("sqlite:///:memory:", demo=True)
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 1234))
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                replies = await asyncio.wait_for(
                    asyncio.gather(
                        *[
                            client.post(
                                "/api/ask",
                                json={
                                    "project": "demo",
                                    "release": "1.0",
                                    "question": "request_timeout",
                                    "k": 1,
                                },
                            )
                            for _ in range(50)
                        ]
                    ),
                    timeout=20,
                )
                assert all(r.status_code == 200 for r in replies)
                assert len({r.json()["saved_answer_id"] for r in replies}) == 50

    asyncio.run(scenario())
