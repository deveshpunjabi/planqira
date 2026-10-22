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
- `PLANQIRA_API_KEY`: optional server-side API authorization key for mutation endpoints (`X-API-Key`).
- `GEMINI_API_KEY`: optional server-side key for quote extraction. Never commit credentials.
- Model configuration is defined in `ai_service.py` and `.env.example`. A configured key is not proof of a successful model request.

Without a provider key, quote reading uses a basic parser. Always review extracted prices, deposits, inclusions, and exclusions before approval. This fallback still needs the application server; it is not a fully offline web app.

## How it works

- `main.py`: application lifecycle, middleware (security headers, rate limiting, GZip, payload size limit), and event routes.
- `schemas.py`: validated API request contracts with null-byte rejection and XSS tag neutralization.
- `engine.py`: integer-paise pricing, budget calculations, and task dependencies.
- `database.py`: event reads, payments, quotes, scenario revisions, and operational updates.
- `database_setup.py`, `seed_data.py`, `event_creation.py`: schema setup, fictional examples, and initial event construction.
- `exports.py`: CSV and calendar routes with CSV formula injection mitigation and RFC-5545 calendar folding.
- `ai_service.py`: quote extraction and the basic-parser fallback.
- `static/`: homepage, dashboard, shared styles, and browser behavior.

See [the architecture guide](DOCUMENTATION.md) for responsibilities and financial invariants.

Money calculations use integer paise. The default reserve is 10% of the target budget. Quote approval and cash payment are separate actions. Budget estimates are illustrative planning inputs, not verified vendor availability or market quotations. Cultural and dietary preferences need review by the organiser.

## Tests

```sh
pip install -r requirements-dev.txt
python -m playwright install chromium
python -m ruff check .
python -m ruff format --check .
python -m pytest test_engine.py test_e2e_playwright.py
```

The test suite passes **70 backend tests and 14 browser checks (84 total)**. Browser tests start their own loopback server and use a temporary database; no manually running server is needed. They cover navigation, refresh, error recovery, loading/empty states, quote review, payment persistence, scenario previews, dialog focus, exports, security headers, rate limiting, and layouts at 390/768/1440 pixels. See [TEST-REPORT.md](TEST-REPORT.md) for scope and limitations.

For an existing compatible browser installation, tests accept `PLAYWRIGHT_EXECUTABLE_PATH`. Optional `PLANQIRA_SCREENSHOT_DIR` saves preview images outside the repository. GitHub Actions installs browser dependencies and runs both suites.

## Verified Security & Performance Hardening

- **Enterprise Security Headers:** Full OWASP compliance with `Content-Security-Policy`, `Strict-Transport-Security: max-age=31536000`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Cross-Origin-Opener-Policy: same-origin`, and `Cross-Origin-Resource-Policy: same-origin`.
- **DoS & Flood Protection:** In-memory sliding-window rate limiting middleware with standard RFC-6585 response headers (`Retry-After`, `X-RateLimit-*`).
- **Payload Ceiling Protection:** Max 2MB request body size enforcement (`HTTP 413 Content Too Large`).
- **Input Sanitization & Injection Defense:** Pydantic base models strictly block null-byte injection and strip unescaped script tags across all text inputs.
- **SQL Injection Defense (Bandit Clean):** 100% static parameterized DDL and SQL queries with zero dynamic string interpolations in execution paths; verified 0 issues in Bandit SAST.
- **Formula Injection Mitigation:** CSV exports prefix dangerous triggers (`=`, `+`, `-`, `@`, `\t`, `\r`, `%`, `|`) with single quotes.
- **High-Concurrency SQLite PRAGMAs:** WAL (Write-Ahead Logging) journal mode, `synchronous = NORMAL`, 64MB memory page cache, RAM temp store, and 256MB memory-mapped I/O (`mmap_size`).
- **Wire Compression:** Automatic GZip response compression on all API payloads and static files over 500 bytes (reducing transfer sizes by >80%).
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

## Deployment and current limits

The repository includes a Vercel ASGI entry point and routing configuration. **Vercel is currently a demonstration deployment:** SQLite is stored in `/tmp`, which is not durable shared storage across serverless instances. `DATABASE_URL` does not activate a PostgreSQL adapter. Managed PostgreSQL support is unfinished.

Other remaining release work:

- Event-scoped object checks do not provide multi-user authentication or session login. Public demo data is shared; use fictional information only.
- Live provider/model compatibility was not verified in the isolated regression run.
- Automated browser checks are not a full accessibility audit or production certification.

The uploaded delivery report contains broader claims than current evidence supports; repository architecture notes have been consolidated and corrected. This README and the current test report describe the verified scope.
