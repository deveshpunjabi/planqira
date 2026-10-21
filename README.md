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

The latest local review passed **29 backend tests and 11 browser checks (40 total)**. Browser tests start their own loopback server and use a temporary database; no manually running server is needed. They cover navigation, refresh, error recovery, loading/empty states, quote review, payment persistence, scenario previews, dialog focus, exports, and layouts at 390/768/1440 pixels. See [TEST-REPORT.md](TEST-REPORT.md) for scope and limitations.

For an existing compatible browser installation, tests accept `PLAYWRIGHT_EXECUTABLE_PATH`. Optional `PLANQIRA_SCREENSHOT_DIR` saves preview images outside the repository. GitHub Actions installs browser dependencies and runs both suites.

## Deployment and current limits

The repository includes a Vercel ASGI entry point and routing configuration. **Vercel is currently a demonstration deployment:** SQLite is stored in `/tmp`, which is not durable shared storage across serverless instances. `DATABASE_URL` is detected but does not activate a PostgreSQL adapter. Managed PostgreSQL support is unfinished.

Other remaining release work:

- Event-scoped object checks do not provide user authentication or private multi-tenant authorization.
- Scenario commit still accepts client-provided item dictionaries; the server must own consequential financial calculations and invalidations.
- Date restoration, full schedule/calendar semantics, and concurrency need additional end-to-end verification.
- Live provider/model compatibility was not verified in the isolated regression run.
- Automated browser checks are not a full accessibility audit or production certification.

The uploaded delivery report and older architecture notes contain broader claims than current evidence supports. This README and the current test report describe the verified scope. Confirm the official PromptWars rules, repository-size definition, branch requirements, and submission limits before submitting.
