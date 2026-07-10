import contextlib
import json
import sys
import time

from playwright.sync_api import TimeoutError, sync_playwright

BASE_URL = "http://localhost:8051"
GATEWAY_URL = "http://localhost:8000"
SERVICE_URLS = {
    "twin-state-mgr": "http://localhost:8001/health",
    "scenario-engine": "http://localhost:8002/health",
    "risk-engine": "http://localhost:8003/health",
    "rag-service": "http://localhost:8004/health",
    "copilot-agent": "http://localhost:8005/health",
    "forecast-engine": "http://localhost:8006/health",
    "report-service": "http://localhost:8007/health",
    "gateway": "http://localhost:8000/health",
}

results = {"passed": 0, "failed": 0, "checks": []}


def check(name, ok, detail=""):
    results["checks"].append({"name": name, "ok": ok, "detail": detail})
    if ok:
        results["passed"] += 1
        print(f"  PASS  {name}")
    else:
        results["failed"] += 1
        print(f"  FAIL  {name}  -- {detail}")


def test_services():
    import urllib.request

    for name, url in SERVICE_URLS.items():
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            data = json.loads(resp.read())
            ok = data.get("status") == "healthy" or resp.getcode() == 200
            check(
                f"Service {name} returns 200/healthy", ok, str(data.get("status", resp.getcode()))
            )
        except Exception as e:
            check(f"Service {name} reachable", False, str(e))


def test_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            check("Dashboard loads (200)", True, f"Title: {page.title()}")
        except Exception as e:
            check("Dashboard loads", False, str(e))
            browser.close()
            return

        with contextlib.suppress(TimeoutError):
            page.wait_for_selector("#root", state="attached", timeout=10000)

        time.sleep(5)
        page.screenshot(path="dashboard_test.png", full_page=True)
        check("Screenshot saved", True, "dashboard_test.png")

        body_text = page.locator("body").inner_text(timeout=10000)
        body_lower = body_text.lower()

        expected = ["Climate Twin", "Karnataka", "Bengaluru", "Overview"]
        for term in expected:
            found = term.lower() in body_lower
            check(f"Page contains '{term}'", found, f"found={found}")

        try:
            sidebar = page.locator('[data-testid="stSidebar"]')
            sidebar.wait_for(state="visible", timeout=8000)
            check("Sidebar is visible", sidebar.is_visible())
        except TimeoutError:
            check("Sidebar is visible", False, "not visible within 8s timeout")

        nav_items = [
            "Climate Overview",
            "Forecast Viewer",
            "Twin State",
            "Climate Risk",
            "Reports",
            "Copilot Chat",
            "Feedback",
        ]
        for item in nav_items:
            found = item.lower() in body_lower
            check(f"Nav item '{item}' present", found)

        try:
            metric = page.locator('[data-testid="stMetric"]').first
            metric.wait_for(state="attached", timeout=10000)
            check("Metric elements found", True)
        except TimeoutError:
            check("Metric elements found", False, "no stMetric elements")

        try:
            selectbox = page.locator('[data-testid="stSelectbox"]').first
            selectbox.wait_for(state="visible", timeout=5000)
            check("Selectboxes visible", True)
        except TimeoutError:
            check("Selectboxes visible", False, "no stSelectbox found")

        try:
            tabs = page.locator('[data-baseweb="tab"]')
            tab_count = tabs.count()
            check(f"Tabs present ({tab_count})", tab_count > 0, f"found {tab_count} tabs")
        except Exception as e:
            check("Tabs present", False, str(e))

        browser.close()


print("=== Service Health Checks ===")
test_services()

print("\n=== Dashboard Browser Tests ===")
test_dashboard()

print(f"\n{'=' * 40}")
print(
    f"Results: {results['passed']} passed, {results['failed']} failed out of {len(results['checks'])} checks"
)
if results["failed"] > 0:
    print("\nFailed checks:")
    for c in results["checks"]:
        if not c["ok"]:
            print(f"  - {c['name']}: {c['detail']}")
sys.exit(0 if results["failed"] == 0 else 1)
