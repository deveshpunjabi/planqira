# Planqira — Autonomous Event Decision & Operations Platform

Planqira is an autonomous event decision, commitment, and operations platform that replaces static checklists and fragile spreadsheets with deterministic integer-paise financial mathematics, Kahn's DAG dependency cascades, and Google DeepMind Gemma 4 cognitive quote parsing.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-37%20Passed-brightgreen.svg)](TEST-REPORT.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-deveshpunjabi%2Fplanqira-181717.svg?logo=github&logoColor=white)](https://github.com/deveshpunjabi/planqira)

---

## Features

- **Deterministic Integer-Paise Financial Math:** Computes all currency in integer paise ($1\text{ INR} = 100\text{ paise}$) with exact half-up tax rounding and zero IEEE-754 floating-point drift.
- **Solvency Deficit Detection:** Flags budget shortfalls with exact negative variance instead of artificially compressing market rates to fake affordability.
- **Topological DAG Dependency Cascades:** Models operational preparation as an acyclic graph (Kahn's algorithm) that automatically cascades parameter invalidations to downstream tasks.
- **Commitments & Cash Flow Decoupling:** Decouples contractual commitments (`ESTIMATED` $\rightarrow$ `QUOTED` $\rightarrow$ `APPROVED`) from the settled cash payments ledger.
- **Gemma 4 Cognitive Quote Extraction:** Extracts messy WhatsApp and email quotes into structured line items with context negation detection and percentage advance parsing.
- **Minute-by-Minute Runbook & Live Incident Logging:** Coordinates dual-track Front-of-House and Back-of-House operational cues with contingency failovers and live incident resolution.
- **Dual PostgreSQL / SQLite Relational Persistence:** Out-of-the-box local SQLite development with production-ready Supabase / Neon PostgreSQL support via `DATABASE_URL`.
- **RFC Standards Compliant Exporters:** Native RFC-4180 CSV export with formula injection defense and RFC-5545 ICS calendar scheduling.

---

## System Architecture & Workspaces

Planqira provides two synchronized interfaces built with an editorial Light Theme (Warm Ivory `#F7F6F2`, White `#FFFFFF`, Charcoal `#242824`, Deep Olive `#435A46`, Pale Sage `#EDF2E9`):

- **Public Homepage (`/`):** High-impact editorial showcase with an interactive client-side budget solver, celebration profiles, and an engineering philosophy matrix.
- **Operational Dashboard (`/dashboard`):** Real-time Solvency HUD with a persistent 235px sidebar spanning 6 dedicated workspaces:

| # | Workspace | Focus | Capabilities |
|---|---|---|---|
| **01** | **Overview & Solvency HUD** | Command Center | Solvency health card, KPI financial strip, quick action buttons, immutable audit log. |
| **02** | **Ideas & Creative Direction** | Sensory Blueprints | Multi-sensory blueprints (ambient lighting, scent notes, acoustic tempos), signature moments, DIY swaps. |
| **03** | **Financial Control & Commitments** | Ledger & Quotes | Integer-paise budget table, vendor commitments pipeline, WhatsApp inquiry generator, cash payments ledger, AI quote extractor. |
| **04** | **Timeline & Lead-Time Sequencing** | T-Minus Countdown | Lead-time compressed checklist (<14 days vs >30 days), topological sequencing, priority badges, reverification alerts. |
| **05** | **Event Day Operations** | Day-Of Execution | Dual-track minute-by-minute runbook (FOH vs BOH), failover contingency switchboards, live incident logger. |
| **06** | **Scenario Lab** | Decision Simulation | Headcount range slider (50–600 pax), venue setting selector, side-by-side cost differentials, DAG invalidation alerts, forward commits. |

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **pip** (Python package installer)
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/deveshpunjabi/planqira.git
cd planqira

# 2. Install application dependencies
pip install -r requirements.txt

# 3. Install Playwright browser binaries (for E2E verification)
playwright install chromium
```

---

## Usage

### Running the Application

```bash
# Start the local FastAPI server
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

- **Public Homepage:** Open [http://127.0.0.1:8080](http://127.0.0.1:8080)
- **Operational Dashboard:** Open [http://127.0.0.1:8080/dashboard](http://127.0.0.1:8080/dashboard)
- **API Health Check:** Open [http://127.0.0.1:8080/api/health](http://127.0.0.1:8080/api/health)

### Running the Test Suite

Planqira includes 37 automated tests across backend deterministic math and browser end-to-end interactions:

```bash
# 1. Run backend engine test suite (29 tests)
python -m pytest test_engine.py -v

# 2. Run Playwright browser E2E test suite (8 tests)
python -m pytest test_e2e_playwright.py -v
```

---

## 3-Minute Judge Evaluation Walkthrough

Judges can verify the core capabilities in under 3 minutes:

1. **Homepage & Simulator (`/`):** Test the interactive budget calculator. Changing budget to ₹20,00,000 updates the 10% contingency reserve instantly to ₹2,00,000.
2. **Dashboard (`/dashboard`):** Click "Launch Live Dashboard" to access the 6-workspace sidebar and Solvency HUD.
3. **AI Vendor Quote Extraction (Workspace 03):** Open *AI Quote Extractor* and paste:  
   `"Royal Sound & Stage Setup: Grand banquet stage ₹1,20,000, Acoustic line-array ₹60,000. Diesel included. No corkage fee. 30% advance deposit due by 2026-11-05."`  
   Click *Extract Line Items*. Observe that waived fees (diesel, corkage) are recognized as complimentary and the 30% advance (₹54,000) is accurately computed.
4. **Record Settled Cash Payment (Workspace 03):** Click *Record Payment*, enter ₹25,000 via UPI with reference `UPI-TEST-001`, and submit. Cash paid updates immediately in the HUD and logs to the settled payments ledger.
5. **Log Day-Of Incident (Workspace 05):** Navigate to *05. Event Day Operations*, click *Log Incident*, report an operational issue, and observe it log to the live incident ledger.
6. **Simulate Scenario Impact (Workspace 06):** In *06. Scenario Lab*, drag the headcount slider from 250 to 350 guests and click *Compute Impact*. Review the real-time cost diff, spend delta, and DAG task invalidation warnings.
7. **Export Files:** Download the sanitized financial ledger via **Export CSV** and the RFC-5545 schedule via **Export Calendar (.ics)**.

---

## Detailed Documentation

For comprehensive technical architecture, data flows, and specifications, refer to our dedicated documentation guides:

- **[DOCUMENTATION.md](DOCUMENTATION.md):** Complete architectural manual covering system topology flowcharts, sequence diagrams, integer-paise math proofs, Kahn's algorithm implementation, entity-relationship models, full REST API schemas, environment variables, and troubleshooting FAQs.
- **[TEST-REPORT.md](TEST-REPORT.md):** Detailed automated verification report documenting all 37 passing unit, regression, and Playwright browser tests.
- **[CONTEXT.md](CONTEXT.md):** Product scope, design invariants, and deployment architecture rules.

---

## Deployment

### Vercel Serverless
Planqira is configured out-of-the-box for serverless deployment on Vercel:
1. Import `deveshpunjabi/planqira` on [vercel.com/new](https://vercel.com/new).
2. Framework Preset: **Other** (detected via `vercel.json`).
3. Environment Variables (optional):
   - `GEMINI_API_KEY`: Google AI Studio key for live Gemma 4 quote extraction.
   - `DATABASE_URL`: PostgreSQL connection string (Supabase / Neon). If omitted, Planqira automatically operates via `/tmp/planqira.db`.
4. Click **Deploy**.

### Docker / Google Cloud Run
A production multi-stage Dockerfile is included:

```bash
docker build -t planqira .
docker run -p 8080:8080 -e PORT=8080 planqira
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository on GitHub.
2. Create a feature branch: `git checkout -b feat/your-feature-name`.
3. Commit your changes: `git commit -m "feat: add your feature description"`.
4. Verify all tests pass: `python -m pytest test_engine.py test_e2e_playwright.py`.
5. Push to your branch: `git push origin feat/your-feature-name`.
6. Open a Pull Request detailing your changes.

For major architectural proposals, please open an issue first to discuss the design.

---

## License

Distributed under the [MIT License](LICENSE) — Copyright (c) 2026 Devesh Punjabi.
