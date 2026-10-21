# Planqira verification — 21 October 2026

## Current result

**64 tests passed locally:** 51 backend cases and 13 Chromium browser cases. These are regression checks, not a guarantee of zero defects or a PromptWars score.

The audit baseline passed 48 tests. Additional workflow tests cover inclusive-tax quote approval/reload/revisions, payment allocation through restores, invalid calendar inputs, same-day scheduling, overnight calendar times, malformed financial inputs, dependency preview/save parity, approval conflicts and rollback, lost-response payment retry, and editable quote approval with explicit replacement choices.

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

No production PostgreSQL path exists yet. No deployed durability test, user-authorization audit, complete calendar-standard validation, or live AI/model check was completed by this run. Scenario commit costs are derived from saved items; client financial dictionaries are ignored. New revisions preserve payment lineage; older revisions created before that lineage was recorded may require manual reconciliation. Passing tests do not prove every claim in the earlier delivery report. Refer to the README's release limitations before presenting the project as finalized.
