"""Diagnostic: test navigation without the selectbox approach."""

import time
from playwright.sync_api import sync_playwright

URL = "http://localhost:8051"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720}, color_scheme="light")
    page = context.new_page()

    page.goto(URL, wait_until="networkidle")
    time.sleep(4)

    # Dump all selectbox-like elements
    print("=== ALL select/selectbox elements ===")
    for selector in [
        "select",
        'div[data-testid="stSelectbox"]',
        'div[role="combobox"]',
        '[data-baseweb="select"]',
    ]:
        els = page.locator(selector)
        count = els.count()
        print(f"  '{selector}': {count} found")
        if count > 0:
            for i in range(count):
                visible = els.nth(i).is_visible()
                text = els.nth(i).inner_text()[:100]
                html_preview = els.nth(i).inner_html()[:200]
                print(f"    [{i}] visible={visible} text='{text}'")
                print(f"         html={html_preview}")

    # Dump sidebar content
    sidebar = page.locator('[data-testid="stSidebar"]')
    if sidebar.count() > 0:
        print(f"\n=== SIDEBAR TEXT ===")
        print(sidebar.inner_text()[:500])
    else:
        print(f"\n=== NO SIDEBAR FOUND ===")

    # Dump main area
    main = page.locator('[data-testid="stAppViewContainer"], .main, .block-container').first
    if main.count() > 0:
        print(f"\n=== MAIN TEXT (first 300 chars) ===")
        print(main.inner_text()[:300])
    else:
        print(f"\n=== NO MAIN FOUND ===")

    # Check for error elements
    errors = page.locator('[data-testid="stException"], .stAlert, .stErrorMessage')
    print(f"\n=== ERRORS: {errors.count()} ===")
    if errors.count() > 0:
        print(errors.inner_text()[:500])

    # Take screenshot
    page.screenshot(path="test_screenshots/diag_initial.png")
    print(f"\nScreenshot saved: test_screenshots/diag_initial.png")

    # Now try to navigate by clicking the selectbox directly using JS
    print(f"\n{'=' * 60}")
    print("Attempting JS-based navigation")
    print(f"{'=' * 60}")

    # Get the selectbox widget
    try:
        sb = page.locator('div[data-testid="stSelectbox"]').first
        if sb.count() > 0:
            sb.click()
            time.sleep(1)

            # Click the "Forecast Viewer" option
            opt = page.locator("li[role='option']", has_text="Forecast Viewer")
            if opt.count() > 0:
                opt.click()
                time.sleep(4)

                # Check if page changed
                print(f"\n=== AFTER NAVIGATION ===")
                main_text = main.inner_text()[:500]
                print(f"Main text: {main_text[:300]}")
                print(f"Main length: {len(main_text)}")

                # Check selectbox still exists
                sb2 = page.locator('div[data-testid="stSelectbox"]')
                print(f"Selectboxes after nav: {sb2.count()}")
                page.screenshot(path="test_screenshots/diag_after_nav.png")
                print(f"Screenshot saved: test_screenshots/diag_after_nav.png")

                # Check for errors
                errors2 = page.locator('[data-testid="stException"], .stAlert')
                print(f"Errors after nav: {errors2.count()}")
                if errors2.count() > 0:
                    print(errors2.inner_text()[:500])

                # Now try navigating again
                sb3 = page.locator('div[data-testid="stSelectbox"]').first
                if sb3.count() > 0:
                    sb3.click()
                    time.sleep(0.5)
                    opt2 = page.locator("li[role='option']", has_text="Digital Twin State")
                    if opt2.count() > 0:
                        opt2.click()
                        time.sleep(4)
                        main_text3 = main.inner_text()[:500]
                        print(f"\n=== AFTER 2ND NAV ===")
                        print(f"Main text: {main_text3[:300]}")
                        print(
                            f"Selectboxes: {page.locator('div[data-testid="stSelectbox"]').count()}"
                        )
                        page.screenshot(path="test_screenshots/diag_after_nav2.png")
        else:
            print("No selectbox found initially")
    except Exception as e:
        print(f"Navigation error: {e}")

    browser.close()
