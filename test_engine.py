"""
Planqira Test Suite — Deterministic Financial Solver, DAG Propagation,
ACID SQLite Persistence, AI Quoting, and REST API Exporters.
"""

import os
import sqlite3
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
    init_db,
    get_connection,
    get_event_by_id,
    list_events,
    commit_scenario_version,
)
from ai_service import parse_vendor_quote_text
from main import app


# =====================================================================
# 1. FINANCIAL MATHEMATICS & INTEGER-PAISE SOLVER TESTS
# =====================================================================

def test_calculate_tax_paise_exact_half_up_rounding():
    # 1800 bps = 18.00%
    # Subtotal: 100 paise -> 18 paise
    assert calculate_tax_paise(100, 1800) == 18

    # Subtotal: 555 paise at 1800 bps:
    # 555 * 1800 = 999,000. (999,000 + 5000) // 10000 = 1,004,000 // 10000 = 100 paise.
    assert calculate_tax_paise(555, 1800) == 100

    # Boundary test: exactly half rounds up
    # subtotal * bps = 5000 -> (5000 + 5000) // 10000 = 1
    # subtotal = 10, bps = 500 (5.00%) -> 10 * 500 = 5000 -> +5000 = 10000 -> 1 paise
    assert calculate_tax_paise(10, 500) == 1

    # Below half rounds down:
    # subtotal = 9, bps = 500 -> 4500 + 5000 = 9500 -> // 10000 = 0 paise
    assert calculate_tax_paise(9, 500) == 0

    # Zero or negative inputs return 0
    assert calculate_tax_paise(0, 1800) == 0
    assert calculate_tax_paise(10000, 0) == 0
    assert calculate_tax_paise(-500, 1800) == 0


def test_compute_line_item_paise_fixed():
    # FIXED: exactly 1 unit regardless of guest count
    res = compute_line_item_paise(
        pricing_model="FIXED",
        unit_cost_paise=15000000,  # ₹150,000
        guest_count=250,
        tax_rate_bps=1800,         # 18% GST
    )
    assert res["quantity"] == 1
    assert res["subtotal_paise"] == 15000000
    assert res["tax_paise"] == 2700000  # ₹27,000
    assert res["total_paise"] == 17700000


def test_compute_line_item_paise_per_capita():
    # PER_CAPITA: 1 unit per guest
    res = compute_line_item_paise(
        pricing_model="PER_CAPITA",
        unit_cost_paise=280000,    # ₹2,800 / plate
        guest_count=150,
        tax_rate_bps=500,          # 5% GST
    )
    assert res["quantity"] == 150
    assert res["subtotal_paise"] == 42000000  # ₹420,000
    assert res["tax_paise"] == 2100000        # ₹21,000
    assert res["total_paise"] == 44100000


def test_compute_line_item_paise_step_tiered():
    # STEP_TIERED: math.ceil(guests / step_capacity)
    # 250 guests with bus capacity of 50 -> 5 buses
    res = compute_line_item_paise(
        pricing_model="STEP_TIERED",
        unit_cost_paise=1200000,   # ₹12,000 / bus
        guest_count=250,
        step_capacity=50,
        tax_rate_bps=0,
    )
    assert res["quantity"] == 5
    assert res["total_paise"] == 6000000

    # 251 guests with bus capacity of 50 -> 6 buses (math.ceil step jump)
    res_jump = compute_line_item_paise(
        pricing_model="STEP_TIERED",
        unit_cost_paise=1200000,
        guest_count=251,
        step_capacity=50,
        tax_rate_bps=0,
    )
    assert res_jump["quantity"] == 6
    assert res_jump["total_paise"] == 7200000


def test_evaluate_event_solvency_and_approval_separation():
    items = [
        {
            "name": "Heritage Palace Lawn",
            "pricing_model": "FIXED",
            "unit_cost_paise": 50000000,  # ₹5,00,000
            "tax_rate_bps": 1800,
            "approval_state": "APPROVED",
            "paid_amount_paise": 20000000, # Partial paid
        },
        {
            "name": "Royal Feast Catering",
            "pricing_model": "PER_CAPITA",
            "unit_cost_paise": 200000,    # ₹2,000 / guest
            "tax_rate_bps": 500,
            "approval_state": "QUOTED",
            "paid_amount_paise": 0,
        },
        {
            "name": "Excessive Fireworks",
            "pricing_model": "FIXED",
            "unit_cost_paise": 30000000,
            "tax_rate_bps": 1800,
            "approval_state": "REJECTED",  # REJECTED should NOT count towards projected spend
            "paid_amount_paise": 0,
        },
    ]

    # Target: ₹15,00,000 (150,000,000 paise). 10% contingency (1000 bps) = 15,000,000 paise.
    # Lawn (APPROVED): 50,000,000 + 18% (9,000,000) = 59,000,000 paise
    # Catering (QUOTED for 200 guests): 200 * 200,000 = 40,000,000 + 5% (2,000,000) = 42,000,000 paise
    # Fireworks (REJECTED): excluded!
    # Total Projected: 59,000,000 + 42,000,000 = 101,000,000 paise
    # Total Required: 15,000,000 (contingency) + 101,000,000 = 116,000,000 paise
    # Target Budget: 150,000,000 paise
    # Variance: 150,000,000 - 116,000,000 = +34,000,000 paise (SOLVENT)

    solvency = evaluate_event_solvency(
        target_budget_paise=150000000,
        contingency_bps=1000,
        line_items=items,
        guest_count=200,
    )

    assert solvency["solvency_status"] == "SOLVENT"
    assert solvency["contingency_paise"] == 15000000
    assert solvency["total_projected_paise"] == 101000000
    assert solvency["total_required_paise"] == 116000000
    assert solvency["variance_paise"] == 34000000
    assert solvency["breakdown_by_approval_paise"]["APPROVED"] == 59000000
    assert solvency["breakdown_by_approval_paise"]["QUOTED"] == 42000000
    assert solvency["breakdown_by_approval_paise"]["REJECTED"] == 35400000

    # Payment tracking verification
    lawn_item = [it for it in solvency["items"] if it["name"] == "Heritage Palace Lawn"][0]
    assert lawn_item["calculated_payment_status"] == "PARTIAL"

    catering_item = [it for it in solvency["items"] if it["name"] == "Royal Feast Catering"][0]
    assert catering_item["calculated_payment_status"] == "UNPAID"


def test_evaluate_event_solvency_deficit_detection():
    # If target budget is lower than required spend, engine returns DEFICIT (never fakes affordability)
    items = [
        {
            "name": "Luxury Venue",
            "pricing_model": "FIXED",
            "unit_cost_paise": 100000000, # ₹10,00,000
            "tax_rate_bps": 0,
            "approval_state": "APPROVED",
        }
    ]
    # Target: ₹8,00,000 with 10% contingency (₹80,000). Total required = ₹10,80,000.
    solvency = evaluate_event_solvency(
        target_budget_paise=80000000,
        contingency_bps=1000,
        line_items=items,
        guest_count=100,
    )
    assert solvency["solvency_status"] == "DEFICIT"
    assert solvency["variance_paise"] < 0
    assert solvency["variance_paise"] == -28000000  # Deficit of ₹2,80,000


# =====================================================================
# 2. DIRECTED ACYCLIC GRAPH (DAG) & INVALIDATION TESTS
# =====================================================================

def test_dag_cycle_detection():
    dag = DependencyDAG()
    dag.add_node("A", "TASK", "Task A")
    dag.add_node("B", "TASK", "Task B", depends_on_ids=["A"])
    dag.add_node("C", "TASK", "Task C", depends_on_ids=["B"])

    # No cycle
    assert dag.detect_cycles() is False

    # Add cycle: A depends on C
    dag.add_node("A", "TASK", "Task A", depends_on_ids=["C"])
    assert dag.detect_cycles() is True


def test_dag_parameter_invalidation_propagation():
    dag = DependencyDAG()
    # Task A depends on guest headcount
    dag.add_node("T1", "TASK", "Finalize Catering Count", trigger_params=["guests"])
    # Task B depends on Task A
    dag.add_node("T2", "TASK", "Print Personalized Seating Cards", depends_on_ids=["T1"])
    # Task C depends on Task B
    dag.add_node("T3", "TASK", "Place Setting Distribution", depends_on_ids=["T2"])
    # Task D is independent (e.g., Book DJ)
    dag.add_node("T4", "TASK", "Soundcheck DJ Console")

    affected = dag.propagate_invalidation(["guests"])
    affected_ids = {item["id"] for item in affected}

    # T1, T2, and T3 must be invalidated in cascade
    assert "T1" in affected_ids
    assert "T2" in affected_ids
    assert "T3" in affected_ids
    # T4 is independent and must NOT be affected
    assert "T4" not in affected_ids


def test_simulate_scenario_impact():
    items = [
        {"id": "it-1", "name": "DJ", "category": "Sound", "pricing_model": "FIXED", "unit_cost_paise": 5000000, "tax_rate_bps": 0},
        {"id": "it-2", "name": "Buffet", "category": "Food", "pricing_model": "PER_CAPITA", "unit_cost_paise": 200000, "tax_rate_bps": 0},
        {"id": "it-3", "name": "Table Set", "category": "Furniture", "pricing_model": "STEP_TIERED", "unit_cost_paise": 500000, "step_capacity": 10, "tax_rate_bps": 0},
    ]

    dag = DependencyDAG()
    dag.add_node("t-food", "TASK", "Catering Final Headcount", trigger_params=["guests"])

    # Baseline: 100 guests -> DJ (₹50k) + Buffet (100 * ₹2k = ₹200k) + Table (10 sets * ₹5k = ₹50k) = ₹300k
    # New: 150 guests -> DJ (₹50k) + Buffet (150 * ₹2k = ₹300k) + Table (15 sets * ₹5k = ₹75k) = ₹425k
    # Projected Spend Delta: ₹425k - ₹300k = +₹125k (+12,500,000 paise)
    sim = simulate_scenario_impact(
        baseline_guests=100,
        new_guests=150,
        target_budget_paise=50000000,  # ₹5,00,000 target
        contingency_bps=1000,
        line_items=items,
        dag=dag,
    )

    assert sim["baseline_guests"] == 100
    assert sim["new_guests"] == 150
    assert sim["cost_delta_paise"] == 12500000
    assert len(sim["dag_impacts"]) == 1
    assert sim["dag_impacts"][0]["id"] == "t-food"


# =====================================================================
# 3. DATABASE PERSISTENCE & VERSIONING TESTS
# =====================================================================

def test_database_idempotent_init_and_seeding(tmp_path):
    test_db = str(tmp_path / "test_planqira.db")
    init_db(test_db)

    # Check that events exist
    evts = list_events(test_db)
    assert len(evts) >= 3

    # Check wedding event retrieval
    w_evt = [e for e in evts if "Wedding" in e["title"]][0]
    full_data = get_event_by_id(w_evt["id"], test_db)
    assert full_data is not None
    assert len(full_data["budget_items"]) > 0
    assert len(full_data["tasks"]) > 0
    assert len(full_data["runbook"]) > 0
    assert len(full_data["themes"]) == 3


def test_scenario_versioning_and_audit_logging(tmp_path):
    test_db = str(tmp_path / "test_planqira.db")
    init_db(test_db)

    evts = list_events(test_db)
    evt_id = evts[0]["id"]
    current_data = get_event_by_id(evt_id, test_db)
    base_version = current_data["event"]["active_scenario_version"]

    # Modify items and commit scenario v2
    new_items = current_data["budget_items"]
    res = commit_scenario_version(
        event_id=evt_id,
        new_guests=300,
        new_budget_items=new_items,
        note="Guest expansion to 300 with extra banquet tables",
        db_path=test_db,
    )

    assert res["success"] is True
    assert res["new_version"] == base_version + 1

    # Reload event
    updated_data = get_event_by_id(evt_id, test_db)
    assert updated_data["event"]["active_scenario_version"] == base_version + 1
    assert updated_data["event"]["guest_count"] == 300

    # Verify audit log recorded
    logs = updated_data["audit_logs"]
    assert any("Guest expansion to 300" in log["description"] for log in logs)


# =====================================================================
# 4. AI COGNITIVE SERVICE & HEURISTIC FALLBACK TESTS
# =====================================================================

def test_quote_parsing_fallback():
    raw_quote = (
        "Hello sir, this is Royal Caterers Udaipur. For your wedding we offer our signature thali "
        "at Rs 2400 per person + 5% GST. Minimum booking advance is 100000 rupees due by 15th Nov. "
        "Also note diesel generator charges are separate at 8000 per hour."
    )
    result = parse_vendor_quote_text(raw_quote, current_guest_count=200)
    assert result["success"] is True
    assert "data" in result
    extracted = result["data"]

    # In simulated/fallback mode, discloses transparently
    if result.get("is_simulated"):
        assert result["is_simulated"] is True
        assert extracted["vendor_name"] is not None
        assert extracted["advance_deposit_paise"] > 0
        assert len(extracted["flagged_clauses"]) > 0


# =====================================================================
# 5. FASTAPI REST API & FILE EXPORTER TESTS
# =====================================================================

@pytest.fixture
def client():
    # Uses default SQLite database (seeded on startup)
    init_db()
    with TestClient(app) as test_client:
        yield test_client


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "persistence" in data


def test_api_list_and_get_events(client):
    response = client.get("/api/events")
    assert response.status_code == 200
    evts = response.json()["events"]
    assert len(evts) >= 3

    event_id = evts[0]["id"]
    evt_resp = client.get(f"/api/events/{event_id}")
    assert evt_resp.status_code == 200
    evt_data = evt_resp.json()
    assert "solvency" in evt_data
    assert "budget_items" not in evt_data or len(evt_data["solvency"]["items"]) > 0
    assert len(evt_data["themes"]) == 3


def test_api_simulate_scenario(client):
    evts = client.get("/api/events").json()["events"]
    event_id = evts[0]["id"]

    sim_payload = {"new_guests": 320}
    response = client.post(f"/api/events/{event_id}/simulate", json=sim_payload)
    assert response.status_code == 200
    sim_data = response.json()
    assert sim_data["new_guests"] == 320
    assert "cost_delta_paise" in sim_data
    assert "item_diffs" in sim_data
    assert len(sim_data["item_diffs"]) > 0


def test_api_quote_parsing_and_approval(client):
    evts = client.get("/api/events").json()["events"]
    event_id = evts[0]["id"]

    raw_text = "DJ sound system and intelligent light truss for sangeet night is Rs 120000 + 18% GST. Advance Rs 30000."
    parse_resp = client.post(f"/api/events/{event_id}/parse-quote", json={"raw_quote_text": raw_text})
    assert parse_resp.status_code == 200
    parse_data = parse_resp.json()
    assert parse_data["success"] is True

    # Approve quote into ledger
    approve_payload = {
        "vendor_name": "SoundBlast Productions",
        "category": "Sound & Lighting",
        "items": [
            {
                "name": "Intelligent Lighting Truss",
                "pricing_model": "FIXED",
                "unit_cost_paise": 12000000,
                "tax_rate_bps": 1800,
            }
        ],
        "advance_deposit_paise": 3000000,
        "deposit_due_date": "2026-11-15",
        "notes": "Includes sound console and 2 techs",
    }
    appr_resp = client.post(f"/api/events/{event_id}/approve-quote", json=approve_payload)
    assert appr_resp.status_code == 200
    assert appr_resp.json()["success"] is True


def test_api_csv_export(client):
    evts = client.get("/api/events").json()["events"]
    event_id = evts[0]["id"]

    response = client.get(f"/api/events/{event_id}/export.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "PLANQIRA EVENT FINANCIAL LEDGER" in response.text
    assert "Category,Item Name" in response.text


def test_api_ics_export(client):
    evts = client.get("/api/events").json()["events"]
    event_id = evts[0]["id"]

    response = client.get(f"/api/events/{event_id}/export.ics")
    assert response.status_code == 200
    assert "text/calendar" in response.headers["content-type"]
    assert "BEGIN:VCALENDAR" in response.text
    assert "BEGIN:VEVENT" in response.text
    assert "END:VCALENDAR" in response.text
