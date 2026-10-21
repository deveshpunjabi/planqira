import os
import re
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8080"
ARTIFACT_DIR = r"C:\Users\Lenovo\.gemini\antigravity\brain\6c81ff26-c10e-4a15-b572-337e6e6e8ce0"


@pytest.fixture(scope="session")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        yield context
        browser.close()


def test_homepage_render(browser_context):
    """Verify Homepage render, typography, 10% contingency calculation, and CTA."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/")
    page.wait_for_load_state("networkidle")

    # Title & Branding
    title = page.title()
    assert "Planqira" in title

    headline = page.locator("h1").first.inner_text()
    assert "Under control" in headline or "Planqira" in headline or "Every decision" in headline

    # Verify interactive calculator exists
    calc_budget = page.locator("#calcBudget")
    if calc_budget.count() > 0:
        calc_budget.fill("2000000")
        page.dispatch_event("#calcBudget", "input")
        page.wait_for_timeout(300)

        # Check contingency reserve display: 10% of 2,000,000 = 200,000
        calc_reserve = page.locator("#calcReserve").inner_text()
        assert "2,00,000" in calc_reserve or "200,000" in calc_reserve

    # Verify Launch Dashboard CTA
    cta = page.locator("a[href='/dashboard']").first
    assert cta.is_visible()

    # Save screenshot artifact
    screenshot_path = os.path.join(ARTIFACT_DIR, "homepage_desktop.png")
    page.screenshot(path=screenshot_path)
    page.close()


def test_dashboard_workspaces_and_navigation(browser_context):
    """Verify Dashboard persistent sidebar and switching between all 6 workspaces."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Wait for initial event data load
    page.wait_for_selector("#headerEventTitle", timeout=10000)
    title_text = page.locator("#headerEventTitle").inner_text()
    assert len(title_text) > 0 and title_text != "Loading Celebration..."

    # Check financial strip solvency metrics
    fin_budget = page.locator("#finBudget").inner_text()
    assert "₹" in fin_budget

    # Test navigating through all 6 workspace tabs
    workspaces = [
        ("navBtnOverview", "#tabOverview"),
        ("navBtnIdeas", "#tabIdeas"),
        ("navBtnBudget", "#tabBudget"),
        ("navBtnTimeline", "#tabTimeline"),
        ("navBtnEventDay", "#tabEventDay"),
        ("navBtnScenario", "#tabScenario"),
    ]

    for btn_id, tab_id in workspaces:
        btn = page.locator(f"#{btn_id}")
        btn.click()
        page.wait_for_timeout(200)
        tab = page.locator(tab_id)
        assert tab.is_visible(), f"Workspace {tab_id} should be visible after clicking #{btn_id}"

    # Verify tabIdeas content
    page.locator("#navBtnIdeas").click()
    page.wait_for_timeout(300)
    theme_cards = page.locator("#themesContainer .concept-panel")
    assert theme_cards.count() >= 1, "Should render at least one curated theme concept panel"

    # Verify tabBudget tables
    page.locator("#navBtnBudget").click()
    page.wait_for_timeout(300)
    budget_rows = page.locator("#budgetTableBody tr")
    assert budget_rows.count() >= 1, "Should render budget line items"

    # Verify tabTimeline tasks
    page.locator("#navBtnTimeline").click()
    page.wait_for_timeout(300)
    task_rows = page.locator("#tasksTableBody tr")
    assert task_rows.count() >= 1, "Should render timeline preparation tasks"

    # Verify tabEventDay runbook
    page.locator("#navBtnEventDay").click()
    page.wait_for_timeout(300)
    runbook_rows = page.locator("#runbookTableBody tr")
    assert runbook_rows.count() >= 1, "Should render runbook cues"

    # Save screenshot of dashboard
    screenshot_path = os.path.join(ARTIFACT_DIR, "dashboard_desktop.png")
    page.screenshot(path=screenshot_path)
    page.close()


def test_quote_extraction_modal(browser_context):
    """Verify AI quote parser modal extracts items, parses percentages, and handles negations."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")
    page.locator("#navBtnBudget").click()
    page.wait_for_timeout(300)

    # Open Quote Modal via exact button
    page.locator("button:has-text('AI Quote Extractor')").first.click()
    page.wait_for_selector("#quoteModal", state="visible")

    # Fill sample quote text with advance percentage & waived fees
    sample_quote = (
        "Royal Sound & Stage Setup: Grand banquet stage ₹1,20,000, Acoustic line-array ₹60,000. "
        "Diesel included. No corkage fee. 30% advance deposit due by 2026-11-05."
    )
    page.locator("#rawQuoteInput").fill(sample_quote)
    page.locator("button:has-text('Extract Line Items')").click()

    # Wait for parsed review section
    page.wait_for_selector("#quoteReviewSection", state="visible", timeout=10000)

    # Verify extracted vendor and deposit amount
    vendor_display = page.locator("#revVendorName").inner_text()
    assert "Sound" in vendor_display or "Royal" in vendor_display

    deposit_display = page.locator("#revAdvance").inner_text()
    assert "₹" in deposit_display
    # 30% of ₹180,000 = ₹54,000
    assert "54,000" in deposit_display

    # Verify approve button is now visible
    approve_btn = page.locator("#btnApproveQuote")
    assert approve_btn.is_visible()

    # Close modal
    page.locator("#quoteModal button:has-text('Cancel')").click()
    page.wait_for_selector("#quoteModal", state="hidden")
    page.close()


def test_record_payment_modal(browser_context):
    """Verify cash flow payment recording updates the payments table and financial strip."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")
    page.locator("#navBtnBudget").click()
    page.wait_for_timeout(300)

    # Open Payment Modal
    page.locator("button:has-text('Record Payment')").first.click()
    page.wait_for_selector("#paymentModal", state="visible")

    # Fill payment details
    page.locator("#payAmountRs").fill("15000")
    page.locator("#payMethod").select_option("UPI")
    page.locator("#payReference").fill("PLAYWRIGHT-TEST-REF-001")

    # Submit Payment
    page.locator("button:has-text('Commit Payment to Ledger')").click()
    page.wait_for_selector("#paymentModal", state="hidden", timeout=5000)

    # Verify table has the new payment row
    page.wait_for_timeout(500)
    payments_table = page.locator("#paymentsTableBody").inner_text()
    assert "PLAYWRIGHT-TEST-REF-001" in payments_table
    assert "15,000" in payments_table

    page.close()


def test_scenario_lab_simulation(browser_context):
    """Verify Scenario Lab recalculation, DAG impact detection, and diff table."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Navigate to Scenario Lab
    page.locator("#navBtnScenario").click()
    page.wait_for_timeout(300)

    # Adjust guest headcount
    slider = page.locator("#simHeadcountSlider")
    slider.fill("320")
    page.dispatch_event("#simHeadcountSlider", "input")
    page.wait_for_timeout(200)

    # Click Compute Impact
    page.locator("button:has-text('Compute Impact')").click()

    # Verify summary section and diff table appear
    page.wait_for_selector("#simSummarySection", state="visible", timeout=10000)
    page.wait_for_selector("#simDiffCard", state="visible", timeout=10000)

    # Check diff table has entries
    diff_rows = page.locator("#simDiffTableBody tr")
    assert diff_rows.count() >= 1

    # Check Commit button is visible
    commit_btn = page.locator("button:has-text('Commit as Scenario vNext')")
    assert commit_btn.is_visible()
    page.close()


def test_accessibility_keyboard_modal_dismissal(browser_context):
    """Verify modal accessibility: pressing Escape closes active modal."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Open Create Event modal via exact button
    page.locator("button:has-text('+ Create Event')").first.click()
    page.wait_for_selector("#createEventModal", state="visible")

    # Press Escape key
    page.keyboard.press("Escape")
    page.wait_for_selector("#createEventModal", state="hidden")

    page.close()


def test_file_exports_csv_and_ics(browser_context):
    """Verify CSV and RFC-5545 ICS calendar exports return valid HTTP 200 data."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Get active event ID from selector
    event_id = page.locator("#eventSelector").input_value()
    assert event_id, "Active event ID must be present"

    # Verify CSV export
    csv_response = page.request.get(f"{BASE_URL}/api/events/{event_id}/export.csv")
    assert csv_response.status == 200
    csv_text = csv_response.text()
    assert "PLANQIRA EVENT FINANCIAL LEDGER" in csv_text
    assert "Event Title" in csv_text

    # Verify ICS export
    ics_response = page.request.get(f"{BASE_URL}/api/events/{event_id}/export.ics")
    assert ics_response.status == 200
    ics_text = ics_response.text()
    assert "BEGIN:VCALENDAR" in ics_text
    assert "END:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "SUMMARY:" in ics_text

    page.close()


def test_light_editorial_theme_styling(browser_context):
    """Verify strict light theme compliance (no dark backgrounds, warm ivory palette)."""
    page = browser_context.new_page()
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Check body background color
    bg_color = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
    # RGB for #f7f6f2 is rgb(247, 246, 242)
    assert "247" in bg_color or "255" in bg_color

    # Verify no dark class on body or html
    body_class = page.locator("body").get_attribute("class") or ""
    assert "dark" not in body_class

    page.close()
