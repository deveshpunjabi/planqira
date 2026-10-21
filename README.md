# Planqira — Event planning, clearly organised

Planqira helps an event organiser review budgets, vendor quotes, payments, preparation tasks, and the event-day schedule. It combines deterministic financial calculations with optional AI-assisted quote reading.

## Try the product

Run the app and open `/dashboard`. Choose a sample wedding, birthday, or community celebration from the sidebar, or create your own event.

1. **Overview:** see your budget position, next step, and upcoming tasks.
2. **Budget & vendors:** compare estimates, review a vendor quote, and record payments.
3. **Ideas & inspiration:** explore themes and practical details.
4. **Planning checklist:** track preparation and tasks that need review.
5. **Event-day schedule:** follow the runbook and record issues.
6. **Explore changes:** preview a new guest count, date, or setting before saving a new version.

For a short judge presentation: **Overview → Budget & vendors → Review a vendor quote → load an example → Explore changes → Preview changes**. Explain what changes in the estimate and which tasks need review. Approval records a commitment; recording a payment records actual cash. The sidebar includes a plain-language guide and spreadsheet/calendar exports.

The dashboard uses a light ivory/olive palette, collapsible desktop navigation, a mobile drawer, contextual actions, loading placeholders, refresh feedback, recoverable load errors, and reduced-motion support. Detailed budget calculations are available through **Show calculation details**.

## Run locally

Python 3.12 or newer is recommended.

```sh
git clone https://github.com/deveshpunjabi/planqira.git
cd planqira
python -m venv .venv
# Activate the virtual environment using your shell's activation command.
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```

Open [the homepage](http://127.0.0.1:8080) or [the dashboard](http://127.0.0.1:8080/dashboard).

Configuration:

- `PLANQIRA_DB_PATH`: SQLite file path; defaults to `planqira.db` locally.
- `GEMINI_API_KEY`: optional server-side key for quote extraction. Never commit credentials.
- Model configuration is defined in `ai_service.py` and `.env.example`. A configured key is not proof of a successful model request.

Without a provider key, quote reading uses a basic parser. Always review extracted prices, deposits, inclusions, and exclusions before approval. This fallback still needs the application server; it is not a fully offline web app.

## How it works

- `engine.py`: integer-paise pricing, tax rounding, budget calculations, and task dependencies.
- `database.py`: SQLite persistence, seeded examples, payments, event revisions, tasks, and audit records.
- `ai_service.py`: quote extraction and the basic-parser fallback.
- `main.py`: FastAPI routes and CSV/calendar exports.
- `static/`: homepage, dashboard, shared styles, and browser behavior.

Money calculations use integer paise. The default reserve is 10% of the target budget. Quote approval and cash payment are separate actions. Budget estimates are illustrative planning inputs, not verified vendor availability or market quotations. Cultural and dietary preferences need review by the organiser.

## Tests

```sh
pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest test_engine.py test_e2e_playwright.py
```

The test suite passes **51 backend tests and 13 browser checks (64 total)**. Browser tests start their own loopback server and use a temporary database; no manually running server is needed. They cover navigation, refresh, error recovery, loading/empty states, quote review, payment persistence, scenario previews, dialog focus, exports, and layouts at 390/768/1440 pixels. See [TEST-REPORT.md](TEST-REPORT.md) for scope and limitations.

For an existing compatible browser installation, tests accept `PLAYWRIGHT_EXECUTABLE_PATH`. Optional `PLANQIRA_SCREENSHOT_DIR` saves preview images outside the repository. GitHub Actions installs browser dependencies and runs both suites.

## Verified Remediations

- **Server-Owned Scenario Computation:** Scenario commits derive costs authoritatively from the database state. Client attempts to forge line item costs are rejected/ignored.
- **Cross-Event Isolation:** Quote approvals strictly validate that superseded items belong to the active scenario of the target event. Cross-event tampering raises an error.
- **Payment Idempotency & Conflict Guard:** Unique constraint `(event_id, idempotency_key)` protects payments. Retrying identical payloads returns the original transaction (`already_recorded: true`), while conflicting payloads under the same key return HTTP 409 Conflict. Separate payments without keys succeed independently.
- **Quote Parser & Negation Semantics:**
  - Advance deposits are extracted as payment obligations and never created as purchasable line items.
  - Multi-clause negations accurately classify "Diesel not included", "Outstation transport extra", "No corkage fee", "Diesel included at no extra charge", and "No surcharge for diesel".
  - Tax-inclusive pricing preserves exact gross totals across 1, 3, 100, and large guest headcounts with zero paise drift.
  - Unconfirmed quotes (e.g. rate TBD / on request) are tagged `PRICE_UNCONFIRMED` and blocked from zero-rate commitment approval.
- **Revision Revert & Snapshot Fidelity:** Reverting a scenario restores historical `event_date` and `setting`, snapshots `event_date` on new forward revisions, and supports repeated restore-of-restore.
- **Server-Owned Dependency Invalidation:** Task review flags (`NEEDS_REVIEW`) and vendor reconfirmations are computed authoritatively on the server using `DependencyDAG` when guest count, setting, or date shift.

## Latest audit repairs

Tax-inclusive prices now persist through approval, reload, scenario changes, and restores. Item-linked payments keep their allocation across newly created revisions. Scenario preview and save share task-dependency rules. Quote review allows price correction and explicitly selecting replaced estimates. Payment retries reuse an operation key; changed payloads under the same key are rejected.

Calendar inputs validate real dates, times, and IANA timezones. Timed calendar entries export in UTC, including overnight runbook cues. Short-notice tasks no longer start yesterday. Browser CORS defaults to same-origin; optional `PLANQIRA_ALLOWED_ORIGINS` allows explicit frontend origins. This is not an authentication mechanism.

The homepage calculator is illustrative and does not read the current saved ledger. A venue-setting change requires vendor reconfirmation, not an automatic price adjustment. Legacy records whose original inclusive-tax flag or payment lineage was never stored need manual reconciliation; migrations cannot reconstruct missing history reliably.

## Deployment and current limits

The repository includes a Vercel ASGI entry point and routing configuration. **Vercel is currently a demonstration deployment:** SQLite is stored in `/tmp`, which is not durable shared storage across serverless instances. `DATABASE_URL` is detected but does not activate a PostgreSQL adapter. Managed PostgreSQL support is unfinished.

Other remaining release work:

- Event-scoped object checks do not provide multi-user authentication or session login. Public demo data is shared; use fictional information only.
- Live provider/model compatibility was not verified in the isolated regression run.
- Automated browser checks are not a full accessibility audit or production certification.

The uploaded delivery report and older architecture notes contain broader claims than current evidence supports. This README and the current test report describe the verified scope. Confirm the official PromptWars rules, repository-size definition, branch requirements, and submission limits before submitting.
