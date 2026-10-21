> Historical architecture notes: these describe intended behavior and include unverified claims. For current behavior and release limitations, use README.md and TEST-REPORT.md. In particular, PostgreSQL support and private tenant authorization are not implemented. The dashboard navigation and test harness have since changed.

# Planqira — Project Context & Engineering Architecture

## 1. Product Scope & Mission
- **Brand:** Planqira
- **Tagline:** Every decision. Every detail. Under control.
- **Purpose:** Autonomous event decision, commitment, and operations platform for weddings, milestone birthdays, and community festivals.
- **Two Complete Experiences:**
  1. **Public Homepage (`/`):** High-impact editorial showcase with asymmetric typography, interactive solver demo with exact 10% contingency calculation, celebration profiles, quote parser spotlight, and engineering comparison matrix.
  2. **Operational Dashboard (`/dashboard`):** Structured planning control plane with real-time solvency strip, 6 persistent workspaces in a 235px sidebar, deficit alerts, quote approval modals, cash flow payment logging, runbook execution, and Kahn's DAG scenario simulation.

## 2. The Six Dedicated Workspaces
1. **01. Overview & Solvency HUD:** Command Center with real-time solvency diagnostic, KPI counters (Target Budget, Deficit/Surplus, Approved Contracts, Settled Cash, Remaining Gap), quick action launch buttons, and immutable audit log table.
2. **02. Ideas & Creative Direction:** Multi-sensory blueprints (ambient lighting warmth, olfactory scent notes, acoustic tempos), signature ceremony moments, contrast-rated color swatches, and affordable DIY cost-saving alternatives.
3. **03. Financial Control & Commitments:** Deterministic integer-paise budget table (`FIXED`, `PER_CAPITA`, `STEP_TIERED`), vendor commitments pipeline, WhatsApp inquiry generator, cash flow payments ledger, and AI quote extractor modal.
4. **04. Timeline & Lead-Time Sequencing:** Lead-time compressed countdown checklist (<14 days vs >30 days), topological dependency sequencing, priority badges, and reverification warnings for invalidated tasks.
5. **05. Event Day Operations:** Minute-by-minute runbook cues (Front-of-House vs Back-of-House), failover contingency switchboards (weather, power, delay protocols), and live operational incident logger.
6. **06. Scenario Lab:** Headcount range slider (50–600 guests), venue setting selector, date picker, side-by-side cost differentials, DAG invalidation alerts, transactional "Commit as Scenario vNext" button, and non-destructive revert modal.

## 3. Technical Stack & File Structure
- **Backend:** Python 3.12+ with FastAPI, Pydantic v2 schemas, standard library SQLite, and optional psycopg2 for PostgreSQL.
- **Architecture Modules:**
  - `engine.py`: Financial math, pricing formulas, tax rounding, solvency evaluation, and `DependencyDAG`.
  - `database.py`: Dual relational persistence (PostgreSQL for Supabase/Neon production, SQLite `planqira.db` for local testing), foreign keys, transactional scenario snapshot versioning, and append-only audit trail logging.
  - `ai_service.py`: Google DeepMind Gemma 4 / Gemini API cognitive adapter, structured Pydantic extraction, negation context detection, percentage advance calculation, and disclosed offline heuristic fallback.
  - `main.py`: REST endpoints, strict request/response validation, atomic operations, tenant isolation enforcement, and RFC-compliant CSV/ICS exporters.
  - `test_engine.py`: Deterministic backend test suite (29 tests) isolated from working user data.
  - `test_e2e_playwright.py`: Comprehensive Playwright browser end-to-end test suite (8 tests).
- **Frontend Assets:**
  - `static/homepage.html`: Full public editorial homepage at `/`.
  - `static/dashboard.html`: Complete operational dashboard at `/dashboard`.
  - `static/styles.css`: Strict Light Editorial Theme (warm ivory `#F7F6F2`, white `#FFFFFF`, charcoal `#242824`, soft neutral border `#DDE1D8`, deep olive accent `#435A46`, pale sage wash `#EDF2E9`).
  - `static/app.js`: Safe DOM rendering (zero unsafe innerHTML text interpolation), state management, keyboard accessibility (Escape key dismiss listeners), and API client.
- **Deployment:**
  - Single git branch (`main`), repository footprint strictly under 1 MB (~720 KB).
  - `api/index.py` & `vercel.json` for Vercel Serverless ASGI support.
  - `Dockerfile` for containerized environments (Cloud Run / VPS).

## 4. Financial & Operational Invariants
- **Currency:** All financial calculations use integer minor units (paise for INR).
- **Tax Rounding Rule:** `(subtotal * tax_rate_bps + 5000) // 10000` (exact half-up rounding).
- **Contingency:** Default 10% (1000 bps) explicitly ringfenced in total required funds.
- **Quote Approval:**
  - Recomputes totals with line-item pricing formulas and taxes.
  - Generates secure unique identifiers.
  - Never marks funds as paid upon quote approval (deposit required $\ne$ deposit paid).
  - Supersedes matching estimated items to eliminate double-counting.
  - Idempotent against accidental retry submissions.
- **Tenant Isolation:**
  - Every mutation (`patch_task`, `patch_runbook`, `record_payment`, `approve_quote`, `commit_scenario`, `revert_scenario`) verifies `event_id` ownership before write operations.
- **Scenario Commits & Reverts:**
  - Verifies `base_version` against the event's current active version (rejecting stale proposals with HTTP 409).
  - Flags affected tasks as `NEEDS_REVIEW` (recording previous state in `reverification_reason`) and affected vendors for reconfirmation.
  - Reverts create a new forward scenario revision (`paid_amount_paise = 0` on forward items, deriving cash paid from the `payments` ledger) rather than erasing history.

## 5. Verified Commands & Workflows
- **Backend Test Suite (29/29 Passing):** `python -m pytest test_engine.py -v`
- **Playwright E2E Suite (8/8 Passing):** `python -m pytest test_e2e_playwright.py -v`
- **Total Test Matrix:** **37/37 Tests Passing**
- **Development Server:** `python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload`
- **Health Check:** `curl http://127.0.0.1:8080/api/health`
