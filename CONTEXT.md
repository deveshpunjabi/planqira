# Planqira — Project Context & Engineering Architecture

## 1. Product Scope & Mission
- **Brand:** Planqira
- **Tagline:** Every decision. Every detail. Under control.
- **Purpose:** Autonomous event decision, commitment, and operations platform for weddings, milestone birthdays, and community festivals.
- **Two Complete Experiences:**
  1. **Public Homepage (`/`):** High-impact editorial showcase with asymmetric typography, 4-pillar breakdown, real-time client-side interactive solver demo, celebration profiles, quote parser spotlight, and engineering comparison matrix.
  2. **Operational Dashboard (`/dashboard`):** Structured planning control plane with real-time solvency strip, 4 tabbed workspaces, deficit alerts, quote approval modals, cash flow payment logging, runbook execution, and Kahn's DAG scenario simulation.

## 2. Core Operational Pillars
1. **Curated Creative Direction:** 3 sensory blueprints per event with color palettes, sensory hooks (scent, sound, warmth), signature reveal moments, and affordable DIY alternatives.
2. **Deterministic Financial Solver:** Integer-paise accounting (`₹1.00 = 100 paise`), half-up integer tax rounding, support for `FIXED`, `PER_CAPITA`, and `STEP_TIERED` formulas, and explicit Solvency Deficit detection (never fake 100% affordability).
3. **Operational Dependency DAG & Timelines:** Directed Acyclic Graph tracking task and vendor dependencies with Kahn's algorithm cycle detection and cascade BFS invalidation upon parameter shifts. Lead-time compressed preparation tasks (<14 days vs >30 days) and minute-by-minute dual-track day-of runbook.
4. **Commitments Hub & AI Quoting Intelligence:** Two-stage quote review pipeline, decoupling required deposit terms from actual recorded payments, hidden fee trap questions, and copyable negotiation scripts.
5. **Scenario Lab & Safe Reversion:** Side-by-side before/after preview, stale base-revision rejection (HTTP 409), server-side recomputation, persistence of invalidations as review tasks, and non-destructive revert via new forward revision.

## 3. Technical Stack & File Structure
- **Backend:** Python 3.12+ with FastAPI, Pydantic v2 schemas, and standard library SQLite.
- **Architecture Modules:**
  - `engine.py`: Financial math, pricing formulas, tax rounding, solvency evaluation, and `DependencyDAG`.
  - `database.py`: Relational SQLite persistence (`planqira.db`), foreign keys, transactional scenario snapshot versioning, and append-only audit trail logging.
  - `ai_service.py`: Google DeepMind Gemma 4 / Gemini API cognitive adapter, structured Pydantic extraction, and disclosed offline heuristic fallback.
  - `main.py`: REST endpoints, strict request/response validation, atomic operations, and RFC-compliant CSV/ICS exporters.
  - `test_engine.py`: Comprehensive automated test suite (23 tests) isolated from working user data.
- **Frontend Assets:**
  - `static/homepage.html`: Full public editorial homepage at `/`.
  - `static/dashboard.html`: Complete operational dashboard at `/dashboard`.
  - `static/styles.css`: Editorial light theme (warm ivory `#F7F6F2`, white `#FFFFFF`, charcoal `#242824`, soft neutral border `#DDE1D8`, deep olive accent `#435A46`, pale sage wash `#EDF2E9`).
  - `static/app.js`: Safe DOM rendering (zero unsafe innerHTML text interpolation), state management, and API client.
- **Deployment:**
  - Single git branch (`main`), repository footprint strictly under 1 MB.
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
- **Scenario Commits:**
  - Verifies `base_version` against the event's current active version (rejecting stale proposals with HTTP 409).
  - Flags affected tasks as `NEEDS_REVIEW` and affected vendors for reconfirmation.
  - Reverts create a new forward scenario revision rather than erasing history.

## 5. Verified Commands & Workflows
- **Test Suite (23/23 Passing):** `python -m pytest test_engine.py -v`
- **Development Server:** `python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload`
- **E2E Playwright Browser Test:** `python scratch/verify_e2e.py`
