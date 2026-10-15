"""Regress identity races against the running loopback demo using installed Edge.

Run with the optional Playwright dependency; no browser download is needed. A fresh
headless context never opens a personal profile. Real server responses are held
*after JSON parsing* so AbortController alone cannot make this regression pass.
The admin probe may save a synthetic answer, as the ordinary demo probe does.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8000"
CANARY = "CANARY-ORCHID-7814"

HOLD_RESPONSE = r"""
(() => {
  const originalFetch = window.fetch.bind(window);
  const state = window.identityRaceTest = {
    armed: false, held: false, released: false, hasCanary: false,
    signalAborted: false, watch: false, leaked: false, unhandled: []
  };
  window.addEventListener('unhandledrejection', event => {
    state.unhandled.push(String(event.reason));
  });
  new MutationObserver(records => {
    if (!state.watch) return;
    for (const record of records) {
      const target = record.target.nodeType === Node.ELEMENT_NODE
        ? record.target : record.target.parentElement;
      if (!target?.closest('#security-result')) continue;
      const text = [target.textContent,
        ...Array.from(record.addedNodes, node => node.textContent)].join(' ');
      if (text.includes('CANARY-ORCHID-7814')) state.leaked = true;
    }
  }).observe(document, {subtree: true, childList: true, characterData: true});
  window.fetch = async (input, init) => {
    const response = await originalFetch(input, init);
    if (input !== '/api/ask' || !state.armed) return response;
    state.armed = false;
    const readJSON = response.json.bind(response);
    response.json = async () => {
      const data = await readJSON();
      state.hasCanary = JSON.stringify(data).includes('CANARY-ORCHID-7814');
      state.held = true;
      await new Promise(resolve => {state.release = resolve;});
      state.signalAborted = init.signal.aborted;
      state.released = true;
      return data;
    };
    return response;
  };
})();
"""


def wait_for_race_flag(page, flag, timeout_seconds=10):
    """Poll through direct function evaluation; Playwright's poller uses CSP-blocked eval."""
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        if page.evaluate("flag => window.identityRaceTest[flag]", flag):
            return
        sleep(0.05)
    raise AssertionError(f"Timed out waiting for identity race flag: {flag}")


def hold_admin_probe(page):
    """Capture actual authorized evidence, rather than fabricated response data."""
    page.evaluate(
        """() => Object.assign(window.identityRaceTest, {
          armed:true, held:false, released:false, hasCanary:false,
          signalAborted:false, watch:false, leaked:false
        })"""
    )
    page.locator("#security-probe").click()
    wait_for_race_flag(page, "held")
    assert page.evaluate("() => window.identityRaceTest.hasCanary"), (
        "The held admin response must really contain the restricted canary"
    )
    expect(page.locator("#security-probe")).to_be_disabled()
    expect(page.locator("#security-probe")).to_have_attribute("aria-busy", "true")
    page.evaluate("() => window.identityRaceTest.watch = true")


def release_obsolete_probe(page):
    page.evaluate("() => window.identityRaceTest.release()")
    wait_for_race_flag(page, "released")
    # Drain handler continuations and mutation observers without a timing sleep.
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )
    assert page.evaluate("() => window.identityRaceTest.signalAborted"), (
        "Changing identity must abort the old request scope"
    )
    assert not page.evaluate("() => window.identityRaceTest.leaked"), (
        "Restricted evidence appeared in the DOM after the identity boundary"
    )
    expect(page.locator("#security-result")).to_be_empty()
    expect(page.locator("#security-probe")).to_be_enabled()
    assert page.locator("#security-probe").get_attribute("aria-busy") is None
    assert not page.evaluate("() => window.identityRaceTest.unhandled")


def run():
    checks, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script(HOLD_RESPONSE)
            page.goto(BASE_URL, wait_until="networkidle")
            expect(page.locator("#health")).to_contain_text("connected")
            expect(page.locator("#project option").first).to_be_attached()
            expect(page.locator("#role")).to_be_enabled()
            page.locator('[data-view="security"]').click()
            page.locator("#role").select_option("admin")
            expect(page.locator("#documents")).to_contain_text("restricted-canary")

            hold_admin_probe(page)
            page.locator("#role").select_option("reader")
            expect(page.locator("#documents table")).to_be_visible()
            expect(page.locator("#documents")).not_to_contain_text("restricted-canary")
            expect(page.locator("#security-probe")).to_be_enabled()
            release_obsolete_probe(page)
            expect(page.locator("#error")).to_be_hidden()
            checks.append("delayed real admin response never renders after reader downgrade")
            page.evaluate("() => window.identityRaceTest.watch = false")
            page.locator("#security-probe").click()
            expect(page.locator("#security-result .abstention")).to_be_visible()
            expect(page.locator("#security-result")).not_to_contain_text(CANARY)
            checks.append("reader probe still abstains after aborted admin request")

            page.locator("#role").select_option("admin")
            expect(page.locator("#documents")).to_contain_text("restricted-canary")
            hold_admin_probe(page)
            page.locator("#auth-toggle").click()
            # Deliberately invalid test input, never an actual user credential.
            page.locator("#token").fill("invalid-browser-security-test-token")
            page.locator("#auth-apply").click()
            expect(page.locator("#error")).to_have_text("Invalid credentials")
            expect(page.locator("#token")).to_have_value("")
            expect(page.locator("#documents")).to_be_empty()
            release_obsolete_probe(page)
            expect(page.locator("#error")).to_have_text("Invalid credentials")
            expect(page.locator("#auth-apply")).to_be_enabled()
            checks.append("token change cancels old evidence and preserves current auth error")

            page.evaluate("() => window.identityRaceTest.watch = false")
            page.locator("#auth-apply").click()  # Empty token restores native demo identity.
            expect(page.locator("#auth-panel")).to_be_hidden()
            expect(page.locator("#documents")).to_contain_text("restricted-canary")
            expect(page.locator("#error")).to_be_hidden()
            page.locator("#security-probe").click()
            expect(page.locator("#security-result .answer-text")).to_contain_text(CANARY)
            expect(page.locator("#security-probe")).to_be_enabled()
            checks.append("controls recover and native demo remains usable after auth failure")
            assert not errors, errors
            version = browser.version
        finally:
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
        "race": "real admin canary JSON held across identity change after transport completed",
    }
    (ROOT / "evaluation" / "browser-security-verification.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    run()
