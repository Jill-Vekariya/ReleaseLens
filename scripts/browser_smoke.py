"""Exercise the running local sandbox with a fresh headless Edge profile.

Requires optional playwright; uses installed Microsoft Edge, not a downloaded browser.
No personal browser profile, external website, or provider account is opened.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("RELEASELENS_TEST_BASE_URL", "http://127.0.0.1:8000")
if BASE_URL not in ("http://127.0.0.1:8000", "http://127.0.0.1:8001"):
    raise ValueError("Browser smoke must use an explicit loopback verification port")


def run():
    checks, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE_URL, wait_until="networkidle")
        expect(page.locator("#health")).to_contain_text("connected")
        page.locator("#ask-form button[type=submit]").click()
        expect(page.locator("#answer-result .result")).to_be_visible()
        expect(page.locator("#answer-result")).to_contain_text("1.10.15")
        assert page.locator("#answer-result .source-card").count() > 0
        checks.append("version-specific query renders cited evidence")
        page.locator('[data-view="compare"]').click()
        page.locator("#compare-form button[type=submit]").click()
        expect(page.locator("#comparison .result")).to_have_count(2)
        expect(page.locator("#comparison")).to_contain_text("2.10.4")
        checks.append("cross-version comparison renders two independent results")
        page.locator('[data-view="security"]').click()
        page.locator("#security-probe").click()
        expect(page.locator("#security-result .abstention")).to_be_visible()
        page.locator("#role").select_option("admin")
        expect(page.locator("#documents")).to_contain_text("restricted-canary")
        page.locator("#security-probe").click()
        expect(page.locator("#security-result .answer-text")).to_contain_text("CANARY-ORCHID-7814")
        page.locator("#role").select_option("reader")
        expect(page.locator("#security-result")).to_be_empty()
        checks.append(
            "role switching enforces evidence boundaries and clears rendered private results"
        )
        page.locator("#role").select_option("admin")
        page.locator('[data-view="changes"]').click()
        page.locator("#demo-save").click()
        expect(page.locator("#change-output .result")).to_be_visible()
        page.locator("#demo-technical").click()
        expect(page.locator("#change-output")).to_contain_text("technical review needed")
        pending = page.locator("#saved-answers .saved-row").filter(has_text="revalidation pending")
        expect(pending.first).to_be_visible()
        pending.first.locator("[data-review]").click()
        expect(page.locator("#review-output h2").first).to_have_text("confirmed stale")
        expect(page.locator("#review-output")).to_contain_text(
            "Original answer and evidence preserved"
        )
        page.locator("#demo-save").click()
        page.locator("#demo-format").click()
        expect(page.locator("#change-output")).to_contain_text("formatting only")
        checks.append("source update, pending review, correction and formatting-only workflow")
        page.locator('[data-view="evaluation"]').click()
        expect(page.locator("#evaluation-output table")).to_be_visible()
        checks.append("actual evaluation artifact renders")
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[data-view="ask"]').click()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Mobile page overflows horizontally"
        )
        expect(page.locator("#question")).to_be_visible()
        checks.append("390px mobile viewport has no horizontal page overflow")
        # Internal QA only: not a deliverable or a Library upload.
        screenshot = Path(tempfile.gettempdir()) / "releaselens-mobile-qa.png"
        page.screenshot(path=str(screenshot), full_page=True)
        assert not errors, errors
        version = browser.version
        browser.close()
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "browser": "installed Microsoft Edge",
        "browser_version": version,
        "base_url": BASE_URL,
        "checks": checks,
        "javascript_errors": errors,
        "profile": "fresh isolated context; no personal browser data",
    }
    (ROOT / "evaluation" / "browser-verification.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    run()
