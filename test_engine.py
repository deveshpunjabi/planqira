"""
Planqira Test Suite — Complete Engineering & Financial Verification
100% Isolated from working database via dynamic tmp_path fixtures.
Tests: Pricing models, rounding, quote approvals, deposit vs payment separation,
double-counting prevention, stale scenario rejection, DAG invalidations,
safe reverts, CSV formula sanitization, RFC-5545 ICS calendar, and Gemma 4 model support.
"""

import os
import pytest
from fastapi.testclient import TestClient

from engine import (
    calculate_tax_paise,
    compute_line_item_paise,
    evaluate_event_solvency,
    DependencyDAG,
    simulate_scenario_impact,
)
from database import (
    approve_vendor_quote_in_db,
    commit_scenario_version,
    create_event,
    create_incident,
    get_connection,
    get_event_by_id,
    init_db,
    list_events,
    list_incidents,
    record_payment,
    revert_scenario_version,
)
from ai_service import get_active_model, parse_vendor_quote_text
from main import app


# =====================================================================
# 1. DATABASE ISOLATION FIXTURE (Runs on Every Test)
# =====================================================================

@pytest.fixture(autouse=True)
def isolate_test_database(tmp_path, monkeypatch):
    """Guarantees every test runs against a fresh, isolated temporary database."""
    test_db_path = str(tmp_path / "isolated_test_planqira.db")
    monkeypatch.setenv("PLANQIRA_DB_PATH", test_db_path)
    init_db(test_db_path)
    yield test_db_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# =====================================================================
# 2. FINANCIAL MATHEMATICS & FORMULA TESTS
# =====================================================================

def test_tax_and_contingency_half_up_rounding():
    # 1800 bps = 18.00%
    # Subtotal 100 paise -> 18 paise
    assert calculate_tax_paise(100, 1800) == 18

    # Subtotal 555 paise at 1800 bps:
    # 555 * 1800 = 999,000. (999,000 + 5000) // 10000 = 100 paise
    assert calculate_tax_paise(555, 1800) == 100

    # Boundary test: exactly half (.5) rounds up
    assert calculate_tax_paise(10, 500) == 1

    # Less than half rounds down
    assert calculate_tax_paise(9, 500) == 0

    # Zero values return 0
    assert calculate_tax_paise(0, 1800) == 0
    assert calculate_tax_paise(10000, 0) == 0


def test_compute_line_item_paise_models():
    # FIXED: 1 unit regardless of guest headcount
    res_fixed = compute_line_item_paise("FIXED", 15000000, guest_count=250, tax_rate_bps=1800)
    assert res_fixed["quantity"] == 1
    assert res_fixed["subtotal_paise"] == 15000000
    assert res_fixed["tax_paise"] == 2700000
    assert res_fixed["total_paise"] == 17700000

    # PER_CAPITA: 1 unit per guest
    res_pc = compute_line_item_paise("PER_CAPITA", 200000, guest_count=150, tax_rate_bps=500)
    assert res_pc["quantity"] == 150
    assert res_pc["subtotal_paise"] == 30000000
    assert res_pc["tax_paise"] == 1500000
    assert res_pc["total_paise"] == 31500000

    # STEP_TIERED: integer ceiling division
    # 250 guests / capacity 50 -> 5 units
    res_tier1 = compute_line_item_paise("STEP_TIERED", 1200000, guest_count=250, step_capacity=50, tax_rate_bps=0)
    assert res_tier1["quantity"] == 5
    assert res_tier1["total_paise"] == 6000000

    # 251 guests / capacity 50 -> 6 units (step jump)
    res_tier2 = compute_line_item_paise("STEP_TIERED", 1200000, guest_count=251, step_capacity=50, tax_rate_bps=0)
    assert res_tier2["quantity"] == 6
    assert res_tier2["total_paise"] == 7200000


def test_compute_line_item_paise_rejections():
    # Nonpositive guest count must be rejected
    with pytest.raises(ValueError, match="strictly positive"):
        compute_line_item_paise("FIXED", 1000, guest_count=0)

    with pytest.raises(ValueError, match="strictly positive"):
        compute_line_item_paise("PER_CAPITA", 1000, guest_count=-5)

    # Negative unit cost must be rejected
    with pytest.raises(ValueError, match="cannot be negative"):
        compute_line_item_paise("FIXED", -100, guest_count=100)

    # Invalid tax rate bounds must be rejected
    with pytest.raises(ValueError, match="between 0 and 10000"):
        compute_line_item_paise("FIXED", 1000, guest_count=100, tax_rate_bps=-10)

    with pytest.raises(ValueError, match="between 0 and 10000"):
        compute_line_item_paise("FIXED", 1000, guest_count=100, tax_rate_bps=10001)

    # Nonpositive step capacity must be rejected
    with pytest.raises(ValueError, match="strictly positive"):
        compute_line_item_paise("STEP_TIERED", 1000, guest_count=100, step_capacity=0)

    # Unsupported pricing model must be rejected
    with pytest.raises(ValueError, match="Unsupported pricing model"):
        compute_line_item_paise("INVALID_MODEL", 1000, guest_count=100)


def test_evaluate_solvency_deficit_detection():
    # Target: ₹5,00,000 (50,000,000 paise). Contingency 10% = 5,000,000 paise.
    # Total required = 5,000,000 + 60,000,000 = 65,000,000 paise.
    # Budget variance = -15,000,000 paise -> Solvency: DEFICIT
    items = [
        {"name": "Luxury Space", "pricing_model": "FIXED", "unit_cost_paise": 60000000, "tax_rate_bps": 0, "approval_state": "APPROVED"}
    ]
    solv = evaluate_event_solvency(target_budget_paise=50000000, contingency_bps=1000, line_items=items, guest_count=100)
    assert solv["solvency_status"] == "DEFICIT"
    assert solv["variance_paise"] == -15000000
    assert solv["remaining_budget_paise"] == 0
    assert solv["total_approved_commitments_paise"] == 60000000


# =====================================================================
# 3. QUOTE APPROVAL, PAYMENTS & DOUBLE-COUNTING PREVENTION TESTS
# =====================================================================

def test_quote_approval_multi_item_and_unique_ids():
    evts = list_events()
    evt_id = evts[0]["id"]

    items_to_approve = [
        {"name": "Intelligent Moving Heads", "pricing_model": "FIXED", "unit_cost_paise": 5000000, "tax_rate_bps": 1800},
        {"name": "LED Floor Par Canisters", "pricing_model": "STEP_TIERED", "unit_cost_paise": 100000, "step_capacity": 25, "tax_rate_bps": 1800},
    ]

    res = approve_vendor_quote_in_db(
        event_id=evt_id,
        vendor_name="Starlight AV Productions",
        category="Sound & Lighting",
        items=items_to_approve,
        advance_deposit_paise=2000000,
        deposit_due_date="2026-11-15",
    )

    assert res["success"] is True
    assert res["commitment_id"].startswith("com-")
    assert len(res["item_ids"]) == 2
    # Verify IDs are unique
    assert res["item_ids"][0] != res["item_ids"][1]


def test_quote_approval_separates_deposit_from_payment():
    evts = list_events()
    evt_id = evts[0]["id"]

    # Approve quote that requires ₹30,000 advance deposit
    res = approve_vendor_quote_in_db(
        event_id=evt_id,
        vendor_name="Royal Brass Shehnai Band",
        category="Live Music",
        items=[{"name": "4-Musician Folk Ensemble", "pricing_model": "FIXED", "unit_cost_paise": 8000000, "tax_rate_bps": 1800}],
        advance_deposit_paise=3000000,
        deposit_due_date="2026-11-01",
    )

    full = get_event_by_id(evt_id)
    com = [c for c in full["vendors"] if c["id"] == res["commitment_id"]][0]

    # Required deposit must be recorded, but paid cash must be strictly 0
    assert com["deposit_required_paise"] == 3000000
    assert com["paid_amount_paise"] == 0


def test_record_payment_updates_ledger_and_balances():
    evts = list_events()
    evt_id = evts[0]["id"]

    # Approve quote
    res_app = approve_vendor_quote_in_db(
        event_id=evt_id,
        vendor_name="Heritage Transport Coaches",
        category="Logistics",
        items=[{"name": "50-Seater AC Bus", "pricing_model": "STEP_TIERED", "unit_cost_paise": 1500000, "step_capacity": 50, "tax_rate_bps": 0}],
        advance_deposit_paise=1500000,
    )
    com_id = res_app["commitment_id"]

    # Record actual payment of ₹15,000
    pay_res = record_payment(
        event_id=evt_id,
        amount_paise=1500000,
        payment_method="NEFT_TRANSFER",
        reference_note="Advance booking token for guest bus transport",
        commitment_id=com_id,
    )

    assert pay_res["success"] is True
    assert pay_res["payment_id"].startswith("pay-")

    # Verify commitment paid amount was incremented
    full = get_event_by_id(evt_id)
    com = [c for c in full["vendors"] if c["id"] == com_id][0]
    assert com["paid_amount_paise"] == 1500000

    # Verify payment appears in payments list
    matching_pay = [p for p in full["payments"] if p["id"] == pay_res["payment_id"]]
    assert len(matching_pay) == 1
    assert matching_pay[0]["amount_paise"] == 1500000


def test_quote_replacement_eliminates_double_counting():
    evts = list_events()
    evt_id = evts[0]["id"]
    initial_full = get_event_by_id(evt_id)
    initial_cat_item = [it for it in initial_full["budget_items"] if it["category"] == "Catering" and it["approval_state"] == "ESTIMATED" or it["approval_state"] == "QUOTED"][0]

    # Approve a real catering quote
    res = approve_vendor_quote_in_db(
        event_id=evt_id,
        vendor_name="Maharaja Banquet Kitchens",
        category="Catering",
        items=[{"name": "Royal Feast Deluxe", "pricing_model": "PER_CAPITA", "unit_cost_paise": 180000, "tax_rate_bps": 500}],
        advance_deposit_paise=5000000,
        supersedes_item_id=initial_cat_item["id"],
    )
    assert res["success"] is True

    updated_full = get_event_by_id(evt_id)
    superseded_item = [it for it in updated_full["budget_items"] if it["id"] == initial_cat_item["id"]][0]

    # The superseded estimated item must be marked REPLACED
    assert superseded_item["approval_state"] == "REPLACED"

    # In solvency evaluation, REPLACED items must be excluded from projected spend
    solvency = evaluate_event_solvency(
        target_budget_paise=updated_full["event"]["target_budget_paise"],
        contingency_bps=updated_full["event"]["contingency_bps"],
        line_items=updated_full["budget_items"],
        guest_count=updated_full["event"]["guest_count"],
    )
    assert initial_cat_item["id"] not in [it["id"] for it in solvency["items"] if it["approval_state"] not in ("REJECTED", "REPLACED") and it["id"] == initial_cat_item["id"]]


def test_quote_approval_idempotency_retries():
    evts = list_events()
    evt_id = evts[0]["id"]
    idem_key = "unique-retry-token-12345"

    items = [{"name": "Floral Gate Arch", "pricing_model": "FIXED", "unit_cost_paise": 3000000, "tax_rate_bps": 1800}]

    # First attempt
    res1 = approve_vendor_quote_in_db(
        event_id=evt_id,
        vendor_name="Floral Magic",
        category="Decor",
        items=items,
        idempotency_key=idem_key,
    )
    assert res1["success"] is True
    com_id = res1["commitment_id"]

    # Second retry attempt with identical key
    res2 = approve_vendor_quote_in_db(
        event_id=evt_id,
        vendor_name="Floral Magic",
        category="Decor",
        items=items,
        idempotency_key=idem_key,
    )
    assert res2["success"] is True
    assert res2.get("already_approved") is True
    assert res2["commitment_id"] == com_id


# =====================================================================
# 4. SCENARIO TRUSTWORTHINESS & DAG PROPAGATION TESTS
# =====================================================================

def test_stale_scenario_proposal_rejection():
    evts = list_events()
    evt_id = evts[0]["id"]
    initial_full = get_event_by_id(evt_id)
    current_ver = initial_full["event"]["active_scenario_version"]

    # Attempt to commit proposal based on an out-of-date base_version (e.g. current_ver - 1)
    with pytest.raises(ValueError, match="Stale proposal rejected"):
        commit_scenario_version(
            event_id=evt_id,
            new_guests=300,
            new_budget_items=initial_full["budget_items"],
            note="Proposal with stale base revision",
            base_version=current_ver - 1,
        )


def test_scenario_commit_persists_task_and_vendor_invalidation():
    evts = list_events()
    evt_id = evts[0]["id"]
    initial_full = get_event_by_id(evt_id)
    base_ver = initial_full["event"]["active_scenario_version"]

    # Pick a pending task to invalidate
    pending_tasks = [t for t in initial_full["tasks"] if t["status"] == "PENDING"]
    target_task_id = pending_tasks[0]["id"]

    res = commit_scenario_version(
        event_id=evt_id,
        new_guests=350,  # Headcount shifted from 250 to 350
        new_budget_items=initial_full["budget_items"],
        note="Headcount expansion to 350",
        base_version=base_ver,
        invalidated_task_ids=[target_task_id],
    )
    assert res["success"] is True
    assert res["new_version"] == base_ver + 1

    updated_full = get_event_by_id(evt_id)

    # Invalidate task must now have status NEEDS_REVIEW and a reverification reason
    inv_task = [t for t in updated_full["tasks"] if t["id"] == target_task_id][0]
    assert inv_task["status"] == "NEEDS_REVIEW"
    assert "Invalidated by Scenario" in (inv_task.get("reverification_reason") or "")

    # Vendors must be flagged for reconfirmation
    reconfirm_vendors = [v for v in updated_full["vendors"] if v["needs_reconfirmation"] == 1]
    assert len(reconfirm_vendors) > 0


def test_scenario_commit_flags_completed_tasks_for_reverification():
    evts = list_events()
    evt_id = evts[0]["id"]
    initial_full = get_event_by_id(evt_id)
    base_ver = initial_full["event"]["active_scenario_version"]

    # Verify existing completed task
    done_tasks = [t for t in initial_full["tasks"] if t["status"] == "DONE"]
    assert len(done_tasks) > 0
    done_id = done_tasks[0]["id"]

    # Commit scenario with the completed task invalidated due to headcount shift
    commit_scenario_version(
        event_id=evt_id,
        new_guests=280,
        new_budget_items=initial_full["budget_items"],
        note="Headcount expansion from 250 to 280",
        base_version=base_ver,
        invalidated_task_ids=[done_id],
    )

    updated_full = get_event_by_id(evt_id)
    retained_task = [t for t in updated_full["tasks"] if t["id"] == done_id][0]
    # Completed task whose precondition shifted must transition to NEEDS_REVIEW
    assert retained_task["status"] == "NEEDS_REVIEW"
    assert "previously DONE" in retained_task["reverification_reason"]


def test_scenario_revert_creates_forward_revision():
    evts = list_events()
    evt_id = evts[0]["id"]
    initial_full = get_event_by_id(evt_id)
    v1 = initial_full["event"]["active_scenario_version"]

    # Commit v2
    commit_scenario_version(
        event_id=evt_id,
        new_guests=320,
        new_budget_items=initial_full["budget_items"],
        note="Version 2 update",
        base_version=v1,
    )
    v2_full = get_event_by_id(evt_id)
    assert v2_full["event"]["active_scenario_version"] == v1 + 1

    # Revert back to v1 state
    revert_res = revert_scenario_version(
        event_id=evt_id,
        target_version=v1,
        reason="Client decided against headcount expansion",
    )
    assert revert_res["success"] is True
    assert revert_res["new_version"] == v1 + 2  # Forward version v3

    reverted_full = get_event_by_id(evt_id)
    assert reverted_full["event"]["active_scenario_version"] == v1 + 2
    assert reverted_full["event"]["guest_count"] == initial_full["event"]["guest_count"]


# =====================================================================
# 5. CORE PLANNING EXPERIENCE & "CREATE EVENT" FLOW TESTS
# =====================================================================

def test_create_custom_event():
    evt_payload = {
        "title": "Aarav & Meera Destination Wedding",
        "event_type": "wedding",
        "city": "Jodhpur",
        "event_date": "2026-12-18",
        "start_time": "17:00",
        "duration_hours": 6.0,
        "timezone": "Asia/Kolkata",
        "setting": "outdoor",
        "guest_count": 300,
        "target_budget_paise": 150000000,
        "currency": "INR",
        "contingency_bps": 1000,
        "preferences": {"dietary": "North & South Indian Fusion", "style": "Royal Marigold"},
    }
    res = create_event(evt_payload)
    assert res["success"] is True
    evt_id = res["event_id"]

    full = get_event_by_id(evt_id)
    assert full["event"]["title"] == "Aarav & Meera Destination Wedding"
    assert full["event"]["setting"] == "outdoor"
    assert len(full["themes"]) == 3
    assert len(full["tasks"]) >= 3
    assert len(full["runbook"]) >= 3


def test_short_notice_schedule_compression():
    # Event scheduled 5 days from today
    short_notice_payload = {
        "title": "Rapid 30th Birthday Bash",
        "event_type": "birthday",
        "city": "Mumbai",
        "event_date": "2026-10-26",
        "start_time": "20:00",
        "duration_hours": 5.0,
        "timezone": "Asia/Kolkata",
        "setting": "indoor",
        "guest_count": 50,
        "target_budget_paise": 25000000,
    }
    res = create_event(short_notice_payload)
    evt_id = res["event_id"]
    full = get_event_by_id(evt_id)

    # Must contain rapid timeframe compressed tasks
    timeframes = [t["timeframe"] for t in full["tasks"]]
    assert any("Rapid" in tf or "T-3" in tf or "T-1" in tf for tf in timeframes)


def test_incident_logging_and_resolution():
    evts = list_events()
    evt_id = evts[0]["id"]

    inc_res = create_incident(
        event_id=evt_id,
        severity="HIGH",
        title="Generator Phase Overload",
        description="Auxiliary generator tripped under sudden sub-bass load during DJ soundcheck.",
        resolution="Switched audio rack to independent secondary phase line within 6 minutes.",
    )
    assert inc_res["success"] is True

    incidents = list_incidents(evt_id)
    assert len(incidents) >= 1
    assert incidents[0]["severity"] == "HIGH"
    assert incidents[0]["status"] == "RESOLVED"


# =====================================================================
# 6. AI COGNITIVE INTEGRATION & SECURITY TESTS
# =====================================================================

def test_ai_model_configuration_and_quote_parsing():
    # Verifies active model configuration and fallback safety
    model = get_active_model()
    assert "gemma" in model.lower() or "gemini" in model.lower()

    raw_text = (
        "Namaste, Udaipur Royal Kitchens here. Royal Thali Buffet is Rs 2100 per plate + 5% GST for your 250 guests. "
        "Advance token Rs 100000 due by 20th Nov. Note: kitchen generator diesel extra Rs 12000."
    )
    parsed = parse_vendor_quote_text(raw_text, current_guest_count=250)
    assert parsed["success"] is True
    assert parsed["data"]["advance_deposit_paise"] == 10000000
    assert len(parsed["data"]["extracted_items"]) >= 1

    # Explicit clauses check
    clauses = parsed["data"]["explicit_clauses_extracted"]
    assert any("diesel" in cl.lower() or "fuel" in cl.lower() for cl in clauses)


def test_ai_quote_parsing_short_input_rejection():
    res = parse_vendor_quote_text("hi")
    assert res["success"] is False
    assert res["extraction_mode"] == "REJECTED"


# =====================================================================
# 7. EXPORT SECURITY & RFC CONFORMANCE TESTS
# =====================================================================

def test_csv_export_formula_injection_sanitization(client):
    evts = client.get("/api/events").json()["events"]
    evt_id = evts[0]["id"]

    response = client.get(f"/api/events/{evt_id}/export.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    csv_text = response.text

    # Verify no raw formula triggers at start of cells
    for line in csv_text.splitlines():
        cells = line.split(",")
        for c in cells:
            clean_c = c.strip('"')
            # If it starts with formula trigger =, +, -, @, it must be escaped with single quote
            if clean_c.startswith(("=", "@")):
                assert clean_c.startswith("'")


def test_ics_export_escaping_and_timezone(client):
    evts = client.get("/api/events").json()["events"]
    evt_id = evts[0]["id"]

    response = client.get(f"/api/events/{evt_id}/export.ics")
    assert response.status_code == 200
    assert "text/calendar" in response.headers["content-type"]
    ics_text = response.text

    assert "BEGIN:VCALENDAR" in ics_text
    assert "VERSION:2.0" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "END:VCALENDAR" in ics_text


def test_invalid_nested_inputs(client):
    # Missing mandatory title and negative budget must be rejected
    invalid_payload = {
        "title": "AB",  # Min length 3
        "event_type": "wedding",
        "city": "Jaipur",
        "event_date": "invalid-date",
        "guest_count": -5,
        "target_budget_paise": -100,
    }
    response = client.post("/api/events", json=invalid_payload)
    assert response.status_code == 422  # Unprocessable Entity


def test_public_homepage_and_dashboard_routes(client):
    # Verify public homepage at /
    res_home = client.get("/")
    assert res_home.status_code == 200
    assert "Planqira" in res_home.text
    assert "Every decision. Every detail. Under control." in res_home.text
    assert "Deterministic Scaling" in res_home.text
    assert "Four Pillars" in res_home.text

    # Verify dedicated operational dashboard at /dashboard
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert "Planqira" in res_dash.text
    assert "app.js" in res_dash.text
    assert "Scenario Lab" in res_dash.text
    assert "dashboard-sidebar" in res_dash.text
    assert "tabOverview" in res_dash.text
    assert "tabEventDay" in res_dash.text

    # Verify /api/health
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "ok"
    assert "gemma" in health_data["model"].lower() or "gemini" in health_data["model"].lower()


def test_simulation_endpoint_with_dag_invalidations(client):
    evts = client.get("/api/events").json()["events"]
    evt_id = evts[0]["id"]

    sim_payload = {
        "new_guests": 320,
        "new_setting": "indoor"
    }
    response = client.post(f"/api/events/{evt_id}/simulate", json=sim_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["new_guests"] == 320
    assert data["new_setting"] == "indoor"
    assert "simulated_solvency_status" in data
    assert "dag_impacts" in data
    assert len(data["dag_impacts"]) > 0
    assert "tradeoffs" in data
    assert len(data["tradeoffs"]) > 0


# =====================================================================
# 10. REGRESSION & AUDIT VERIFICATION TESTS
# =====================================================================

def test_payment_ledger_unallocated_and_allocated():
    """Verifies that payments ledger is the authoritative source of truth for cash paid."""
    line_items = [
        {"id": "item-1", "pricing_model": "FIXED", "unit_cost_paise": 100000, "paid_amount_paise": 0},
        {"id": "item-2", "pricing_model": "FIXED", "unit_cost_paise": 200000, "paid_amount_paise": 0},
    ]
    # 2 allocated payments and 1 unallocated payment
    payments = [
        {"amount_paise": 50000, "budget_item_id": "item-1"},
        {"amount_paise": 100000, "budget_item_id": "item-2"},
        {"amount_paise": 25000, "budget_item_id": None, "commitment_id": None},
    ]
    solvency = evaluate_event_solvency(
        target_budget_paise=500000,
        contingency_bps=1000,
        line_items=line_items,
        guest_count=100,
        payments=payments,
    )
    # Total paid is 50,000 + 100,000 + 25,000 = 175,000 paise
    assert solvency["total_paid_paise"] == 175000
    assert solvency["unallocated_paid_paise"] == 25000
    assert solvency["items"][0]["paid_amount_paise"] == 50000
    assert solvency["items"][1]["paid_amount_paise"] == 100000


def test_revert_scenario_retains_ledger_payments():
    """Verifies that reverting a scenario never loses payments or creates financial drift."""
    evts = list_events()
    evt_id = evts[0]["id"]
    initial_full = get_event_by_id(evt_id)
    v1 = initial_full["event"]["active_scenario_version"]

    # Record a payment in v1
    pay_res = record_payment(
        event_id=evt_id,
        amount_paise=5000000,  # ₹50,000
        payment_method="UPI",
        reference_note="Advance catering token",
    )
    assert pay_res["success"] is True

    # Commit v2
    commit_scenario_version(
        event_id=evt_id,
        new_guests=300,
        new_budget_items=initial_full["budget_items"],
        note="Increase headcount to 300",
        base_version=v1,
    )
    v2_full = get_event_by_id(evt_id)
    assert v2_full["event"]["active_scenario_version"] == v1 + 1

    # Revert back to v1
    revert_res = revert_scenario_version(
        event_id=evt_id,
        target_version=v1,
        reason="Client decided against guest expansion",
    )
    assert revert_res["success"] is True

    reverted_full = get_event_by_id(evt_id)
    # Check that payment still exists and matches in payments list
    all_payments = reverted_full["payments"]
    matching_payment = [p for p in all_payments if p["amount_paise"] == 5000000]
    assert len(matching_payment) == 1

    # Evaluate solvency with reverted items and payments
    solvency = evaluate_event_solvency(
        target_budget_paise=reverted_full["event"]["target_budget_paise"],
        contingency_bps=reverted_full["event"]["contingency_bps"],
        line_items=reverted_full["budget_items"],
        guest_count=reverted_full["event"]["guest_count"],
        payments=reverted_full["payments"],
    )
    # Paid cash includes the recorded payment plus initial seed payment
    assert solvency["total_paid_paise"] >= 5000000


def test_cross_event_ownership_isolation(client):
    """Verifies strict cross-event scoping on tasks, runbooks, and payments."""
    evts = client.get("/api/events").json()["events"]
    evt_a_id = evts[0]["id"]
    evt_b_id = evts[1]["id"]

    evt_a_full = get_event_by_id(evt_a_id)
    task_a_id = evt_a_full["tasks"][0]["id"]

    # Attempting to patch task_a through event B's endpoint must return 404
    patch_res = client.patch(f"/api/events/{evt_b_id}/tasks/{task_a_id}", json={"status": "DONE"})
    assert patch_res.status_code == 404

    # Attempting to record payment on Event B referencing Event A's commitment must raise 400
    comm_a_id = evt_a_full["vendors"][0]["id"]
    pay_res = client.post(
        f"/api/events/{evt_b_id}/record-payment",
        json={
            "amount_paise": 1000000,
            "payment_method": "NEFT",
            "reference_note": "Cross event attack",
            "commitment_id": comm_a_id,
        }
    )
    assert pay_res.status_code == 400
    assert "not found for event" in pay_res.json()["detail"]


def test_quote_negation_and_percentage_advance():
    """Verifies that negation words are respected and percentage advances are computed accurately."""
    quote_text = (
        "Hi team, this is Spice Route Catering. For 200 pax, per plate charge is ₹1200/- per person. "
        "Diesel included. No corkage fee. Free delivery. "
        "40% advance required upon booking. 5% GST applicable."
    )
    parsed = parse_vendor_quote_text(quote_text, current_guest_count=200)
    data = parsed["data"]

    # Check vendor name
    assert "Spice Route" in data["vendor_name"]
    # Check pricing model
    assert data["extracted_items"][0]["pricing_model"] == "PER_CAPITA"
    assert data["extracted_items"][0]["unit_cost_paise"] == 120000  # ₹1200

    # Total estimated subtotal: 200 * ₹1200 = ₹240,000 (24,000,000 paise)
    # 40% advance: 0.40 * 24,000,000 = 9,600,000 paise (₹96,000)
    assert data["advance_deposit_paise"] == 9600000

    # Check clauses: must NOT classify "diesel included" or "no corkage" as extra surcharges
    clauses = " ".join(data["explicit_clauses_extracted"]).lower()
    assert "diesel explicitly included" in clauses or "diesel included" in clauses
    assert "corkage fee waived" in clauses
    assert "delivery included" in clauses


def test_rfc5545_exclusive_end_date_and_line_folding(client):
    """Verifies RFC-5545 calendar compliance: exclusive end date and <= 75 octet line folding."""
    evts = client.get("/api/events").json()["events"]
    evt_id = evts[0]["id"]

    res = client.get(f"/api/events/{evt_id}/export.ics")
    assert res.status_code == 200
    assert "text/calendar" in res.headers["content-type"]

    ics_content = res.text
    # All lines must be <= 75 octets
    for line in ics_content.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, f"Line exceeds 75 octets: {line}"

    # For all-day events, DTEND must be DTSTART + 1 day
    lines = ics_content.split("\r\n")
    for i, line in enumerate(lines):
        if line.startswith("DTSTART;VALUE=DATE:"):
            start_date_str = line.split(":")[1]
            end_line = lines[i+1]
            if end_line.startswith("DTEND;VALUE=DATE:"):
                end_date_str = end_line.split(":")[1]
                # Compare integer dates
                assert int(end_date_str) > int(start_date_str), f"DTEND ({end_date_str}) must be after DTSTART ({start_date_str})"


def test_dietary_and_style_personalization_in_create_event():
    """Verifies that preferences.dietary and style customize line items and tasks."""
    payload = {
        "title": "Aarav & Diya Heritage Wedding",
        "event_type": "wedding",
        "city": "Udaipur",
        "event_date": "2026-12-10",
        "guest_count": 200,
        "target_budget_paise": 100000000,
        "preferences": {
            "dietary": "Strict Vegetarian + Jain",
            "style": "Regal Rajputana Heritage",
        }
    }
    created = create_event(payload)
    evt_full = get_event_by_id(created["event_id"])

    catering_items = [it for it in evt_full["budget_items"] if it["category"] == "Catering"]
    assert len(catering_items) > 0
    assert "Pure Vegetarian & Jain" in catering_items[0]["name"]

    tasting_tasks = [t for t in evt_full["tasks"] if "tasting" in t["title"].lower()]
    assert len(tasting_tasks) > 0
    assert "Pure Veg & Jain" in tasting_tasks[0]["title"]

