"""Playwright test: verify all dashboard pages render visible content."""

import socket
import sys
import time

import pytest
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://localhost:8501"


def _server_is_running(host="localhost", port=8501) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


PAGES = [
    ("Climate Overview", True),  # already loaded as home
    ("Forecast Viewer", False),
    ("Digital Twin State", False),
    ("Scenario Simulator", False),
    ("Climate Risk", False),
    ("Reports & Insights", False),
    ("AI Copilot", False),
    ("Knowledge Base", False),
    ("Spatial Grid", False),
    ("Feedback", False),
]
MIN_VISIBLE = 100
NAV_SB_SEL = '.st-key-nav_select [data-testid="stSelectbox"]'


def log(msg):
    print(msg, flush=True)


def navigate_to(page, title):
    """Navigate to a page using the Navigate selectbox."""
    nav_sb = page.locator(NAV_SB_SEL)
    nav_sb.click(timeout=5000)
    page.wait_for_selector('div[role="option"]', timeout=5000)
    time.sleep(0.3)

    opt = page.locator('div[role="option"]', has_text=title).first
    opt.wait_for(timeout=3000)
    opt.click()
    time.sleep(2)


@pytest.mark.skipif(
    not _server_is_running(), reason="Dashboard server not running on localhost:8501"
)
def test_all_pages():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        results = []

        log("Loading dashboard...")
        page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector(NAV_SB_SEL, timeout=15000)
        time.sleep(3)
        log("Home page loaded")

        for title, skip_nav in PAGES:
            log(f"\n  --- {title} ---")
            try:
                if not skip_nav:
                    navigate_to(page, title)

                exc = page.locator('[data-testid="stException"]')
                exc_count = exc.count()
                body_text = page.inner_text("body")
                content_len = len(body_text.strip())

                status = "PASS"
                if exc_count > 0:
                    status = "ERRORS"
                elif content_len < MIN_VISIBLE:
                    status = "BLANK"
                log(f"  {status} ({content_len} chars, {exc_count} exc)")
                results.append((title, content_len, status))

            except Exception as e:
                log(f"  FAIL: {e}")
                results.append((title, 0, "FAIL"))

        browser.close()

        log("")
        log("=" * 40)
        passed = sum(1 for _, _, s in results if s == "PASS")
        blank = sum(1 for _, _, s in results if s == "BLANK")
        errors = sum(1 for _, _, s in results if s == "ERRORS")
        failed = sum(1 for _, _, s in results if s == "FAIL")
        log(f"PASS: {passed}  BLANK: {blank}  ERRORS: {errors}  FAIL: {failed}")
        for name, length, status in results:
            log(f"  [{status}] {name} ({length} chars)")
        if blank + errors + failed > 0:
            sys.exit(1)


if __name__ == "__main__":
    test_all_pages()
