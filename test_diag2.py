"""Diagnostic Playwright test."""

import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:8051", wait_until="networkidle")
    time.sleep(5)

    with open("test_diag_output.txt", "w", encoding="utf-8") as f:
        f.write("title: " + page.title() + "\n")
        sb = page.locator('div[data-testid="stSelectbox"]')
        f.write("selectboxes: " + str(sb.count()) + "\n")
        sd = page.locator('[data-testid="stSidebar"]')
        f.write("sidebar: " + str(sd.count()) + "\n")
        mc = page.locator('[data-testid="stAppViewContainer"]')
        f.write("main: " + str(mc.count()) + "\n")
        er = page.locator('[data-testid="stException"]')
        f.write("errors: " + str(er.count()) + "\n")
        al = page.locator(".stAlert")
        f.write("alerts: " + str(al.count()) + "\n")
        f.write("--- body ---\n")
        f.write(page.inner_text("body"))
        f.write("\n--- end body ---\n")

        # Navigate
        sel = page.locator('div[data-testid="stSelectbox"]').first
        f.write("selectbox visible: " + str(sel.is_visible()) + "\n")
        sel.click()
        time.sleep(0.5)

        opts = page.locator('li[role="option"]')
        f.write("options: " + str(opts.count()) + "\n")
        for i in range(opts.count()):
            f.write("  [" + str(i) + "] " + opts.nth(i).inner_text()[:60] + "\n")

        # Click first non-default option
        viewer = page.locator('li[role="option"]', has_text="Forecast Viewer")
        f.write("Forecast option: " + str(viewer.count()) + "\n")
        if viewer.count():
            viewer.click()
            time.sleep(4)
            f.write("--- after nav ---\n")
            f.write(
                "selectboxes: " + str(page.locator('div[data-testid="stSelectbox"]').count()) + "\n"
            )
            f.write("errors: " + str(page.locator('[data-testid="stException"]').count()) + "\n")
            mc2 = page.locator('[data-testid="stAppViewContainer"]').first
            f.write("main: " + mc2.inner_text()[:500] + "\n")

    browser.close()
print("Done - check test_diag_output.txt")
