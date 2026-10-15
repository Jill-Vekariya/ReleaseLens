"""Verify the authenticated Compose interface in isolated installed Edge.

Reads local .env only in memory; never outputs or stores token values.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run():
    line = next(
        line
        for line in (ROOT / ".env").read_text().splitlines()
        if line.startswith("RELEASELENS_TOKENS=")
    )
    credentials = json.loads(line.split("=", 1)[1].strip("'"))
    tokens = {identity["role"]: token for token, identity in credentials.items()}
    errors, checks = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8080", wait_until="networkidle")
        expect(page.locator("#error")).to_contain_text("Bearer authentication required")
        expect(page.locator("#role")).to_be_disabled()

        def identity(token):
            if page.locator("#auth-panel").is_hidden():
                page.locator("#auth-toggle").click()
            page.locator("#token").fill(token)
            page.locator("#auth-apply").click()

        identity(tokens["admin"])
        expect(page.locator("#project")).to_have_value("pydantic")
        page.locator("#ask-form button[type=submit]").click()
        expect(page.locator("#answer-result .source-card").first).to_be_attached()
        checks.append(
            "bearer-authenticated PostgreSQL question renders immutable evidence through Nginx"
        )
        page.locator('[data-view="compare"]').click()
        page.locator("#compare-form button[type=submit]").click()
        expect(page.locator("#comparison .result")).to_have_count(2)
        checks.append("authenticated version comparison renders both releases")
        page.locator('[data-view="security"]').click()
        expect(page.locator("#documents")).to_contain_text("restricted-canary")
        with page.expect_response(lambda response: response.url.endswith("/api/ask")) as response:
            page.locator("#security-probe").click()
        private = response.value.json()
        expect(page.locator("#security-result")).to_contain_text("CANARY-ORCHID-7814")
        identity(tokens["reader"])
        expect(page.locator("#security-result")).to_be_empty()
        expect(page.locator("#documents")).not_to_contain_text("restricted-canary")
        page.locator("#security-probe").click()
        expect(page.locator("#security-result .abstention")).to_be_visible()
        for path in (
            "/api/evidence/" + private["passages"][0]["passage_id"],
            "/api/answers/" + private["saved_answer_id"],
            "/api/answers/" + private["saved_answer_id"] + "/history",
        ):
            assert (
                page.request.get(
                    "http://127.0.0.1:8080" + path,
                    headers={"Authorization": "Bearer " + tokens["reader"]},
                ).status
                == 404
            )
        checks.append("reader cannot retrieve admin canary, saved answer, citation or history")
        identity("invalid-auth-token-for-negative-test")
        expect(page.locator("#error")).to_contain_text("Invalid credentials")
        expect(page.locator("#auth-apply")).to_be_enabled()
        identity(tokens["reader"])
        expect(page.locator("#error")).to_be_hidden()
        checks.append(
            "invalid token error, loading control recovery and successful reauthentication"
        )
        assert not errors, errors
        browser.close()
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "checks": checks,
        "javascript_errors": errors,
        "transport": "real loopback Nginx/FastAPI/PostgreSQL",
        "profile": "fresh isolated Edge; credentials used only in memory",
    }
    (ROOT / "evaluation/browser-docker-verification.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    run()
