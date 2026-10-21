"""Browser regressions using a temporary database and an automatically managed server."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = Path(__file__).resolve().parent
    sandbox = tmp_path_factory.mktemp("browser-server")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, PLANQIRA_DB_PATH=str(sandbox / "events.db"), GEMINI_API_KEY="", GOOGLE_API_KEY="", DATABASE_URL="")
    with (sandbox / "server.log").open("w") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=root, env=env, stdout=log, stderr=log)
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail("Preview server exited; inspect temporary server.log")
                try:
                    with urllib.request.urlopen(base + "/api/health", timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                pytest.fail("Preview server did not become ready")
            yield base
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        options = {"headless": True}
        if os.getenv("PLAYWRIGHT_EXECUTABLE_PATH"):
            options["executable_path"] = os.environ["PLAYWRIGHT_EXECUTABLE_PATH"]
        instance = p.chromium.launch(**options)
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    context.close()
    assert not errors, f"Uncaught browser errors: {errors}"


def open_dashboard(page, server):
    page.goto(server + "/dashboard")
    expect(page.locator("#dashboardContent")).to_have_attribute("aria-busy", "false")
    expect(page.locator("#headerEventTitle")).not_to_contain_text("Loading")


def test_homepage_and_dashboard_routes(page, server):
    page.goto(server)
    expect(page).to_have_title(__import__('re').compile("Planqira"))
    expect(page.locator("a[href='/dashboard']").first).to_be_visible()
    open_dashboard(page, server)
    expect(page.locator("#upcomingTasks .task-preview")).to_have_count(3)
    expect(page.locator("#taskProgressCount")).to_contain_text("complete")


def test_navigation_and_context_survive_refresh(page, server):
    open_dashboard(page, server)
    for name in ["Ideas", "Budget", "Timeline", "EventDay", "Scenario", "Overview"]:
        page.locator("#navBtn" + name).click()
        expect(page.locator("#tab" + name)).to_be_visible()
        expect(page.locator("#navBtn" + name)).to_have_attribute("aria-current", "page")
    page.locator("#navBtnBudget").click()
    page.locator("#refreshButton").click()
    expect(page.locator("#refreshButton")).to_be_enabled()
    expect(page.locator("#tabBudget")).to_be_visible()
    page.reload()
    expect(page.locator("#tabBudget")).to_be_visible()
    page.locator("#sidebarToggle").click()
    expect(page.locator("#sidebarToggle")).to_have_attribute("aria-expanded", "false")
    page.reload()
    expect(page.locator("#sidebarToggle")).to_have_attribute("aria-expanded", "false")


def test_loading_error_retry_and_empty_states(page, server):
    page.route("**/api/events", lambda route: route.fulfill(status=503, content_type="application/json", body='{}'))
    page.goto(server + "/dashboard")
    expect(page.locator("#loadError")).to_be_visible()
    page.unroute("**/api/events")
    page.get_by_role("button", name="Try again", exact=True).click()
    expect(page.locator("#loadError")).to_be_hidden()
    expect(page.locator("#headerEventTitle")).to_be_visible()
    page.route("**/api/events", lambda route: route.fulfill(content_type="application/json", body='{"events":[]}'))
    page.reload()
    expect(page.locator("#emptyState")).to_be_visible()
    expect(page.locator("#workspaceMain")).to_be_hidden()


def test_skeleton_during_pending_request(page, server):
    page.route("**/api/events", lambda route: route.abort())
    page.goto(server + "/dashboard", wait_until="domcontentloaded")
    expect(page.locator("#loadError")).to_be_visible()
    # Hold a subsequent detail request until the test explicitly releases it.
    page.unroute("**/api/events")
    pending = []
    page.route("**/api/events/*", lambda route: pending.append(route))
    page.get_by_role("button", name="Try again", exact=True).click()
    expect(page.locator("#loadingState")).to_be_visible()
    expect(page.locator("#dashboardContent")).to_have_attribute("aria-busy", "true")
    expect(page.locator("#refreshButton")).to_be_disabled()
    page.wait_for_timeout(100)
    assert pending
    pending[0].continue_()
    expect(page.locator("#loadingState")).to_be_hidden()


def test_quote_review_and_modal_focus(page, server):
    open_dashboard(page, server)
    page.locator("#workspaceAction").click()
    modal = page.locator("#quoteModal")
    expect(modal).to_have_attribute("role", "dialog")
    page.locator("#rawQuoteInput").fill("Royal Sound & Stage Setup: Grand banquet stage ₹1,20,000, Acoustic line-array ₹60,000. Diesel included. No corkage fee. 30% advance deposit due by 2026-11-05.")
    page.get_by_role("button", name="Read quote", exact=True).click()
    expect(page.locator("#quoteReviewSection")).to_be_visible()
    expect(page.locator("#revAdvance")).to_contain_text("54,000")
    expect(page.locator("#aiParserStatus")).to_contain_text("Basic parser")
    expect(page.locator("#revClausesList")).not_to_contain_text("corkage fee required")
    page.locator("#btnApproveQuote").focus()
    page.keyboard.press("Tab")
    expect(modal.get_by_role("button", name="Close dialog")).to_be_focused()
    page.keyboard.press("Escape")
    expect(modal).to_be_hidden()
    expect(page.locator("#workspaceAction")).to_be_focused()


def test_payment_updates_cash_and_survives_refresh(page, server):
    open_dashboard(page, server)
    before = page.locator("#finPaid").inner_text()
    page.locator("#navBtnBudget").click()
    page.get_by_role("button", name="Record Payment", exact=True).click()
    page.locator("#payAmountRs").fill("100")
    page.locator("#payMethod").select_option("UPI")
    page.locator("#payReference").fill("ISOLATED-UI-TEST")
    page.get_by_role("button", name="Save payment", exact=True).click()
    expect(page.locator("#paymentModal")).to_be_hidden()
    expect(page.locator("#finPaid")).not_to_have_text(before)
    after = page.locator("#finPaid").inner_text()
    money = lambda text: float(text.replace('₹', '').replace(',', ''))
    assert money(after) - money(before) == 100
    page.reload()
    expect(page.locator("#finPaid")).to_have_text(after)
    expect(page.locator("#paymentsTableBody")).to_contain_text("ISOLATED-UI-TEST")


def test_payment_retry_after_lost_response_does_not_duplicate_cash(page, server):
    open_dashboard(page, server)
    money = lambda text: float(text.replace('₹', '').replace(',', ''))
    before = money(page.locator("#finPaid").inner_text())
    attempts = []
    def lose_first_response(route):
        attempts.append(route.request.post_data_json)
        if len(attempts) == 1:
            response = route.fetch()
            assert response.ok
            route.abort("failed")
        else:
            route.continue_()
    page.route("**/record-payment", lose_first_response)
    page.locator("#navBtnBudget").click()
    page.get_by_role("button", name="Record Payment", exact=True).click()
    page.locator("#payAmountRs").fill("123")
    page.locator("#payReference").fill("LOST-RESPONSE-RETRY")
    page.get_by_role("button", name="Save payment", exact=True).click()
    expect(page.get_by_text("Failed to fetch", exact=True)).to_be_visible()
    page.get_by_role("button", name="Save payment", exact=True).click()
    expect(page.locator("#paymentModal")).to_be_hidden()
    expect(page.locator("#paymentsTableBody")).to_contain_text("LOST-RESPONSE-RETRY")
    assert money(page.locator("#finPaid").inner_text()) - before == 123
    assert attempts[0]["idempotency_key"] == attempts[1]["idempotency_key"]


def test_quote_price_edit_and_explicit_replacement_persist(page, server):
    open_dashboard(page, server)
    event_id = page.evaluate("currentEventId")
    before = page.request.get(f"{server}/api/events/{event_id}").json()
    page.locator("#workspaceAction").click()
    page.locator("#rawQuoteInput").fill("Catering Rs 850 per plate including 5% GST. 40% advance.")
    page.get_by_role("button", name="Read quote", exact=True).click()
    expect(page.locator("#quoteReviewSection")).to_be_visible()
    page.locator("#revItemsTableBody input").first.fill("900")
    for checkbox in page.locator("#quoteReplacementChoices input").all():
        checkbox.uncheck()
    with page.expect_response(lambda response: response.url.endswith("/approve-quote")) as response:
        page.locator("#btnApproveQuote").click()
    assert response.value.ok
    expect(page.locator("#quoteModal")).to_be_hidden()
    after = page.request.get(f"{server}/api/events/{event_id}").json()
    assert after["solvency"]["total_projected_paise"] - before["solvency"]["total_projected_paise"] == 90000 * before["event"]["guest_count"]
    assert after["solvency"]["total_paid_paise"] == before["solvency"]["total_paid_paise"]


def test_scenario_preview_does_not_change_saved_guests(page, server):
    open_dashboard(page, server)
    before = page.locator("#metaGuests").inner_text()
    page.locator("#navBtnScenario").click()
    page.locator("#simHeadcountSlider").fill("320")
    page.locator("#simHeadcountSlider").dispatch_event("input")
    page.get_by_role("button", name="Preview changes", exact=True).click()
    expect(page.locator("#simSummarySection")).to_be_visible()
    assert page.locator("#simDiffTableBody tr").count() > 0
    expect(page.locator("#metaGuests")).to_have_text(before)
    expect(page.get_by_role("button", name="Save this version", exact=True)).to_be_visible()


@pytest.mark.parametrize("width", [390, 768, 1440])
def test_responsive_navigation_and_no_page_overflow(page, server, width):
    page.set_viewport_size({"width": width, "height": 900})
    open_dashboard(page, server)
    if width < 761:
        expect(page.locator("#sidebarToggle")).to_have_attribute("aria-expanded", "false")
        page.locator("#sidebarToggle").click()
        expect(page.locator("#sidebarBackdrop")).to_be_visible()
    page.locator("#navBtnBudget").click()
    expect(page.locator("#tabBudget")).to_be_visible()
    if width < 761:
        expect(page.locator("#sidebarBackdrop")).to_be_hidden()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Page overflows viewport"
    assert page.locator("#budgetTableBody tr").count() > 0
    for metric in page.locator('.fin-value:visible').all():
        assert metric.evaluate('e => e.clientHeight >= e.scrollHeight'), 'Financial value is clipped'
    if os.getenv("PLANQIRA_SCREENSHOT_DIR"):
        if width < 761:
            page.locator("#sidebarToggle").click()
        page.locator("#navBtnOverview").click()
        page.evaluate("window.scrollTo(0, 0)")
        page.emulate_media(reduced_motion="reduce")
        page.screenshot(path=str(Path(os.environ["PLANQIRA_SCREENSHOT_DIR"]) / f"planqira-dashboard-{width}.png"), full_page=False)


def test_guide_reduced_motion_and_exports(page, server):
    page.emulate_media(reduced_motion="reduce")
    open_dashboard(page, server)
    page.get_by_role("button", name="How to use Planqira", exact=True).click()
    expect(page.get_by_role("dialog", name="From first idea to event day")).to_be_visible()
    page.keyboard.press("Escape")
    assert page.locator("#tabOverview").evaluate("e => getComputedStyle(e).animationName") == "none"
    event = page.locator("#eventSelector").input_value()
    csv = page.request.get(server + f"/api/events/{event}/export.csv")
    assert csv.status == 200 and "Event Title" in csv.text()
    ics = page.request.get(server + f"/api/events/{event}/export.ics")
    assert ics.status == 200 and "BEGIN:VCALENDAR" in ics.text()
    assert page.locator("body").evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(247, 246, 242)"
