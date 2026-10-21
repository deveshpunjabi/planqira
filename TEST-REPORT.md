# Planqira verification — 21 October 2026

## Current result

**40 tests passed locally:** 29 backend tests and 11 browser checks. After visual inspection identified clipped financial values, the three responsive cases were rerun after the CSS fix and passed.

The browser suite now manages its own server and isolated SQLite database. It no longer assumes a server on port 8080, writes artifacts to a hardcoded developer folder, or silently skips a calculator assertion when its selector is missing. Existing route tests use the new user-facing workspace label.

## Browser coverage

- Homepage/dashboard load and next-task content.
- All six workspaces, refresh context, and persisted collapsed navigation.
- Failed event loads, retry recovery, and empty event lists.
- Loading placeholders, busy state, and disabled refresh during a pending request.
- Quote parsing with percentage advance, basic-mode disclosure, modal focus wrapping, and Escape focus return.
- A ₹100 payment changes cash paid by ₹100 and survives page refresh.
- Scenario preview leaves the saved guest count unchanged.
- Mobile, tablet, and desktop navigation at 390, 768, and 1440 pixels; no page overflow or clipped financial values.
- In-product guide, reduced-motion preference, CSV/calendar responses, and light page background.
- Every browser case also fails on uncaught page JavaScript errors.

## Reproduce

```sh
pip install -r requirements-dev.txt
python -m playwright install chromium
python -m pytest test_engine.py test_e2e_playwright.py
```

Tests use temporary data and no provider credentials. Optional `PLAYWRIGHT_EXECUTABLE_PATH` selects an existing compatible Chromium installation. Optional `PLANQIRA_SCREENSHOT_DIR` captures review images outside the repository.

## What this does not certify

No production PostgreSQL path exists yet. No deployed durability test, user-authorization audit, complete calendar-standard validation, or live AI/model check was completed by this run. Scenario commits still accept client-supplied financial item dictionaries. Passing tests do not prove every claim in the earlier delivery report. Refer to the README's release limitations before presenting the project as finalized.
