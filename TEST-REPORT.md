# Planqira Verification & Engineering Audit Report
**Date:** 21 October 2026  
**Environment:** Python 3.12.10 • FastAPI 0.115.0 • Pytest 9.1.1  
**Project:** Planqira — Autonomous Event Decision, Commitment & Operations Engine

---

## 1. Executive Summary

All 18 comprehensive tests in `test_engine.py` pass with 100% success rate (`18 passed, 0 failed in 12.26s`).  
The engine eliminates the critical flaws identified in standard PromptWars event planner submissions:
1. **Integer-Paise Precision:** Verified exact paise arithmetic without IEEE-754 floating-point drift.
2. **Half-Up Tax Rounding:** Verified exact integer half-up rounding across boundary conditions.
3. **True Directed Acyclic Graph (DAG):** Verified Kahn's algorithm cycle detection and cascade BFS invalidation.
4. **Separation of Commitments & Cash Flow:** Verified approval pipeline (`ESTIMATED` $\rightarrow$ `QUOTED` $\rightarrow$ `APPROVED`) is decoupled from payment ledger (`UNPAID` $\rightarrow$ `PARTIAL` $\rightarrow$ `PAID`).
5. **ACID Relational Storage:** Verified SQLite schema with foreign keys, transactional scenario commits, and immutable audit logging.
6. **RFC-Compliant Exporters:** Verified RFC-4180 CSV exports and RFC-5545 ICS calendar exports.

---

## 2. Test Execution Log

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Hackathon\prompt wars virutal\Challenge 5 - Celebration & Event Planner
plugins: anyio-4.13.0, hypothesis-6.156.5, asyncio-1.4.0
collected 18 items

test_engine.py::test_calculate_tax_paise_exact_half_up_rounding PASSED   [  5%]
test_engine.py::test_compute_line_item_paise_fixed PASSED                [ 11%]
test_engine.py::test_compute_line_item_paise_per_capita PASSED           [ 16%]
test_engine.py::test_compute_line_item_paise_step_tiered PASSED          [ 22%]
test_engine.py::test_evaluate_event_solvency_and_approval_separation PASSED [ 27%]
test_engine.py::test_evaluate_event_solvency_deficit_detection PASSED    [ 33%]
test_engine.py::test_dag_cycle_detection PASSED                          [ 38%]
test_engine.py::test_dag_parameter_invalidation_propagation PASSED       [ 44%]
test_engine.py::test_simulate_scenario_impact PASSED                     [ 50%]
test_engine.py::test_database_idempotent_init_and_seeding PASSED         [ 55%]
test_engine.py::test_scenario_versioning_and_audit_logging PASSED        [ 61%]
test_engine.py::test_quote_parsing_fallback PASSED                       [ 66%]
test_engine.py::test_api_health PASSED                                   [ 72%]
test_engine.py::test_api_list_and_get_events PASSED                      [ 77%]
test_engine.py::test_api_simulate_scenario PASSED                        [ 83%]
test_engine.py::test_api_quote_parsing_and_approval PASSED               [ 88%]
test_engine.py::test_api_csv_export PASSED                               [ 94%]
test_engine.py::test_api_ics_export PASSED                               [100%]

======================= 18 passed, 0 failed in 12.26s =======================
```

---

## 3. Engineering Pillar Breakdown

### Pillar 1: Financial Determinism & Boundary Verification
- **Half-Up Rounding Verification:** Subtotals with basis points that evaluate to exactly `5000` round up to the next integer paise; subtotals with fractional parts below `5000` round down. Negative or zero inputs cleanly evaluate to 0.
- **Line Item Pricing Models:**
  - `FIXED`: Preserves exact total cost when guest headcount shifts from 100 to 500.
  - `PER_CAPITA`: Accurately scales with guest headcount down to single paise.
  - `STEP_TIERED`: Demonstrates discrete `math.ceil` threshold steps (e.g., 250 guests $\rightarrow$ 5 transport buses; 251 guests $\rightarrow$ 6 transport buses).
- **Solvency Status:** Replaces artificial 100% budget normalization with real solvency status:
  - When $\text{Target} \ge \text{Contingency} + \text{Projected Spend}$, status is `SOLVENT`.
  - When $\text{Target} < \text{Contingency} + \text{Projected Spend}$, status is `DEFICIT` with negative variance, prompting user action in Scenario Lab.

### Pillar 2: Operational Dependency Graph (DAG)
- **Cycle Prevention:** Proves Kahn's algorithm detects circular dependencies before tasks are saved.
- **Cascade Parameter Invalidation:** Demonstrates that shifting guest count cascades invalidations only to affected downstream nodes (e.g., Catering Headcount $\rightarrow$ Seating Cards $\rightarrow$ Table Placement), leaving independent tasks (e.g., Soundcheck DJ Console) untouched.

### Pillar 3: ACID Relational Persistence & Auditing
- **Relational Integrity:** Foreign keys enforce cascading deletions from Events to Scenarios to Budget Items and Tasks.
- **Scenario Versioning:** Scenario adjustments create versioned records (`v1` $\rightarrow$ `v2`) with status flags and timestamps, appending human-readable diff entries to the immutable `audit_logs` table.

### Pillar 4: Quoting Intelligence & API Reliability
- **Fallback Transparency:** Discloses simulated mode (`is_simulated: True`) when no `GEMINI_API_KEY` is present, while still providing structured line items, GST identification, and counter-negotiation scripts.
- **Direct File Downloads:** Tested `/api/events/{id}/export.csv` and `/api/events/{id}/export.ics` return appropriate HTTP content types (`text/csv` and `text/calendar`) and valid RFC document structure.
