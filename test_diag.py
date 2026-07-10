"""Diagnostic Playwright test."""

import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:8051"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = context.new_page()

    page.goto(URL, wait_until="networkidle")
    time.sleep(4)

    # List all selectbox-like elements
    for sel in ["select", 'div[data-testid="stSelectbox"]', 'div[role="combobox"]']:
        els = page.locator(sel)
        n = els.count()
        print("Selector '%s': %d" % (sel, n))
        for i in range(n):
            vis = els.nth(i).is_visible()
            txt = els.nth(i).inner_text()[:80]
            print("  [%d] visible=%s text=%s" % (i, vis, repr(txt)))

    # Sidebar
    sb = page.locator('[data-testid="stSidebar"]')
    if sb.count():
        print("\nSIDEBAR:\n" + sb.inner_text()[:500])

    # Main content
    mc = page.locator('[data-testid="stAppViewContainer"]').first
    if mc.count():
        print("\nMAIN:\n" + mc.inner_text()[:500])

    # Errors
    er = page.locator('[data-testid="stException"], .stAlert')
    print("\nERRORS: %d" % er.count())
    if er.count():
        print(er.inner_text()[:500])

    # Navigate
    sb = page.locator('div[data-testid="stSelectbox"]').first
    if sb.count():
        sb.click()
        time.sleep(0.5)
        opt = page.locator('li[role="option"]', has_text="Forecast Viewer")
        if opt.count():
            opt.click()
            time.sleep(4)
            print("\n=== AFTER NAV ===")
            mc2 = page.locator('[data-testid="stAppViewContainer"]').first
            print("MAIN:\n" + mc2.inner_text()[:300])
            sb2 = page.locator('div[data-testid="stSelectbox"]')
            print("Selectboxes: %d" % sb2.count())
            er2 = page.locator('[data-testid="stException"], .stAlert')
            print("Errors: %d" % er2.count())
            if er2.count():
                print(er2.inner_text()[:300])
        else:
            print("Option not found")
    else:
        print("No selectbox")

    browser.close()
