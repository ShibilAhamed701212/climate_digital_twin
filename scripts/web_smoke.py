from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding="utf-8")

PAGES = [
    "Climate Overview",
    "Forecast Viewer",
    "Digital Twin State",
    "Scenario Simulator",
    "Climate Risk",
    "Reports & Insights",
    "AI Copilot",
    "Spatial Grid",
    "Knowledge Base",
    "Feedback",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:8501", wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(5_000)
    results = []
    for name in PAGES:
        page.get_by_text(name, exact=True).click()
        page.wait_for_timeout(2_000)
        body = page.locator("body").inner_text()
        bad = [x for x in ("Page '", "Traceback", "ValueError:", "ConnectionError:") if x in body]
        results.append((name, "FAIL" if bad else "PASS", bad, body[-1200:] if bad else ""))
    for result in results:
        print(result)
    browser.close()
    raise SystemExit(1 if any(r[1] == "FAIL" for r in results) else 0)
