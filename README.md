# Planqira — Autonomous Event Decision & Operations Platform

> **Every decision. Every detail. Under control.**  
> *Google PromptWars Virtual [Challenge 5] Celebration & Event Planner*

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-37%20Passed-brightgreen.svg)](TEST-REPORT.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-deveshpunjabi%2Fplanqira-181717.svg?logo=github&logoColor=white)](https://github.com/deveshpunjabi/planqira)

---

## What is Planqira?

Most event planning software fails because it treats complex celebrations as static checklists or freeform AI prompts. In real life, circumstances change constantly: 50 extra guests RSVP, weather forces outdoor setups inside, curfews cut reception times, and vendor quotes hide generator fuel charges or overtime fees.

**Planqira** is an **autonomous event decision, commitment, and operations studio**. It replaces toy chatbots and fragile spreadsheets with:

- **Deterministic Integer-Paise Math:** Exact currency calculation ($1\text{ INR} = 100\text{ paise}$) with zero IEEE-754 floating-point drift and exact half-up tax rounding.
- **Solvency Deficit Detection:** Explicitly flags required budget overruns instead of artificially scaling down catering prices to fake affordability.
- **Topological DAG Dependency Cascades:** Evaluates task dependencies with Kahn's algorithm and automatically transitions affected tasks to `NEEDS_REVIEW` when parameters shift.
- **Contract Commitments vs. Cash Flow Separation:** Tracks contractual obligations independently from settled cash payments.
- **Gemma 4 Cognitive Quote Extraction:** Converts unstructured WhatsApp and email proposals into structured ledger items with negation-aware waived fee detection.
- **Minute-by-Minute Runbook & Incident Logger:** Coordinates Front-of-House and Back-of-House cues with failover switchboards and real-time incident tracking.
- **Dual PostgreSQL / SQLite Storage:** Connects to managed PostgreSQL in production (Supabase / Neon) via `DATABASE_URL` with auto-migration, while providing zero-config local SQLite for development.

> 📖 **Deep Technical Architecture:** For system flowcharts, sequence diagrams, mathematical proofs, and full REST API schemas, see [DOCUMENTATION.md](DOCUMENTATION.md).  
> 🧪 **Verification Evidence:** For the full automated test suite breakdown, see [TEST-REPORT.md](TEST-REPORT.md).

---

## System Overview

Planqira offers two synchronized experiences built with a strict **Light Editorial Design System** (Warm Ivory `#F7F6F2`, White `#FFFFFF`, Charcoal `#242824`, Soft Neutral Border `#DDE1D8`, Deep Olive `#435A46`, Pale Sage `#EDF2E9`):

1. **Public Homepage (`/`):** High-impact editorial value deck featuring an interactive real-time budget simulator, celebration showcase profiles, and an architectural comparison matrix.
2. **Operational Dashboard (`/dashboard`):** Unified planning control plane with a real-time Solvency HUD and a persistent 235px sidebar across 6 dedicated workspaces:

| # | Workspace | Focus | Core Capabilities |
|---|---|---|---|
| **01** | **Overview & Solvency HUD** | Command Center | Solvency health card, KPI metric strip, quick launch actions, immutable audit log table. |
| **02** | **Ideas & Creative Direction** | Sensory Blueprints | Multi-sensory blueprints (ambient lighting warmth, scent notes, acoustic tempos), signature reveal moments, contrast-rated swatches, and affordable DIY swaps. |
| **03** | **Financial Control & Commitments** | Ledger & Quotes | Deterministic integer-paise budget table, vendor commitments pipeline, WhatsApp inquiry generator, cash payments ledger, and AI quote extractor. |
| **04** | **Timeline & Lead-Time Sequencing** | T-Minus Countdown | Lead-time compressed countdown (<14 days vs >30 days), topological dependency sequencing, priority badges, and reverification warnings. |
| **05** | **Event Day Operations** | Day-Of Execution | Dual-track minute-by-minute runbook (FOH vs BOH), failover contingency switchboards (weather, power, curfew), and live incident logger. |
| **06** | **Scenario Lab** | Decision Simulation | Interactive guest headcount slider (50–600 pax), venue setting selector, side-by-side cost differentials, DAG invalidation alerts, and safe forward commits. |

---

## 3 Pre-Configured Celebration Profiles

Planqira includes three rich, pre-configured celebrations seeded out of the box:

- **Royal Rajputana Heritage Wedding (Jaipur):** 250 Guests • ₹12,00,000 Budget • Outdoor Haveli Lawn • Pure Vegetarian & Jain buffet, floral mandap, candid photography, shehnai ensemble, live Baraat runbook, and rain failover protocol.
- **Neo-Tokyo Cyberpunk 21st Birthday (Bengaluru):** 75 Guests • ₹3,50,000 Budget • Rooftop Glasshouse • Pan-Asian sliders, molecular mocktails, UV neon tunnel, synthwave DJ set, and 11 PM curfew transition protocol.
- **Sunlit Monsoon Community Harvest Festival (Pune):** 400 Attendees • ₹8,00,000 Budget • Botanical Amphitheatre • Solar acoustic stage, zero-waste composting, organic millet feast, and municipal permit clearance.

---

## 3-Minute Judge Evaluation Walkthrough

Judges can verify the platform's core capabilities in under 3 minutes:

1. **Inspect Homepage & Simulator (`http://127.0.0.1:8080/`):**  
   Observe the editorial typography. Scroll to the interactive budget simulator, change budget to ₹20,00,000, and verify the 10% contingency reserve updates instantly to ₹2,00,000.
2. **Launch Dashboard (`http://127.0.0.1:8080/dashboard`):**  
   Click "Launch Live Dashboard" to enter the operational workspace with the persistent sidebar.
3. **Parse a Messy Vendor Quote (Workspace 03):**  
   Navigate to *03. Financial Control & Commitments* and click **AI Quote Extractor**. Paste:  
   `"Royal Sound & Stage Setup: Grand banquet stage ₹1,20,000, Acoustic line-array ₹60,000. Diesel included. No corkage fee. 30% advance deposit due by 2026-11-05."`  
   Click *Extract Line Items*. Observe that waived fees (diesel, corkage) are tagged as complimentary and the 30% advance (₹54,000) is accurately computed.
4. **Record a Settled Cash Payment (Workspace 03):**  
   Click **Record Payment**, enter ₹25,000 via UPI with reference `UPI-TEST-001`, and submit. Observe that cash paid updates immediately in the HUD and logs to the settled payments ledger.
5. **Log a Day-Of Incident (Workspace 05):**  
   Navigate to *05. Event Day Operations*, click **Log Incident**, report a simulated weather delay, and verify it records to the live incident ledger.
6. **Simulate Headcount Surge in Scenario Lab (Workspace 06):**  
   Navigate to *06. Scenario Lab*, move the guest slider from 250 to 350, and click **Compute Impact**. Review the real-time cost diff, spend delta, and DAG task invalidation warnings.
7. **Export RFC-Compliant CSV & ICS:**  
   Click **Export CSV** in the sidebar to download the sanitized financial ledger, and **Export Calendar (.ics)** for the RFC-5545 schedule.

---

## Quickstart

### Prerequisites
- Python 3.12+
- `pip`

### Installation & Run

```bash
# 1. Clone repository
git clone https://github.com/deveshpunjabi/planqira.git
cd planqira

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Start development server
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

Open **[http://127.0.0.1:8080](http://127.0.0.1:8080)** for the Public Homepage, or **[http://127.0.0.1:8080/dashboard](http://127.0.0.1:8080/dashboard)** for the Operational Dashboard.

### Running the Automated Test Suite

Planqira includes 37 automated tests across backend logic and browser end-to-end flows:

```bash
# Backend engine suite (29 tests)
python -m pytest test_engine.py -v

# Playwright browser E2E suite (8 tests)
python -m pytest test_e2e_playwright.py -v
```

---

## Deployment

### Deploy to Vercel
Planqira is configured out-of-the-box for serverless deployment on Vercel:
1. Import `deveshpunjabi/planqira` on [vercel.com/new](https://vercel.com/new).
2. Framework Preset: **Other** (detected via `vercel.json`).
3. Root Directory: `./` (default).
4. Environment Variables (optional):
   - `GEMINI_API_KEY`: Google AI Studio key for live Gemma 4 quote extraction (falls back to transparent heuristic mode if omitted).
   - `DATABASE_URL`: PostgreSQL connection string (Supabase / Neon). If omitted, Planqira automatically operates via `/tmp/planqira.db`.
5. Click **Deploy**.

### Deploy with Docker / Google Cloud Run
A production multi-stage Dockerfile is included:

```bash
docker build -t planqira .
docker run -p 8080:8080 -e PORT=8080 planqira
```

---

## License

This project is licensed under the [MIT License](LICENSE) — Copyright (c) 2026 Devesh Punjabi.
