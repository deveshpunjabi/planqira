# UtsavAI — Test Verification & Execution Report

**Prepared:** 21 October 2026  
**Project:** UtsavAI (EventOS) — Celebration & Event Planner (Challenge 5)  
**Environment:** Windows, Node.js v26.8.1, npm 11.11.0, Next.js 15.2.1, Vitest 3.2.7

---

## 1. Executive Summary

| Category | Status | Details |
|---|---|---|
| **Domain & Unit Tests** | **PASSED** | 30 tests passed across 5 test suites (0 failures). |
| **TypeScript Typecheck** | **PASSED** | `tsc --noEmit` passed with 0 errors. |
| **ESLint Static Analysis** | **PASSED** | `next lint` passed with 0 warnings, 0 errors. |
| **Production Server Build** | **PASSED** | `next build` compiled successfully (7 static & dynamic routes). |
| **Submission Archive Size** | **PASSED** | Uncompressed: **611.36 KB**, ZIP: **166.23 KB** (Vastly under 10 MB limit). |
| **Live AI Provider Check** | **BLOCKED** | Live Gemini key not provided in this offline environment; credential-free sample mode verified. |
| **Public Vercel Deployment** | **BLOCKED** | Awaiting user's remote repository push and Vercel dashboard credentials. |

---

## 2. Automated Test Execution

Command: `npm test` (`node ./node_modules/vitest/vitest.mjs run`)

```
 RUN  v3.2.7 D:/Hackathon/prompt wars virutal/Challenge 5 - Celebration & Event Planner

 ✓ tests/budget.test.ts (7 tests) 98ms
   - computes reserveMinor as exactly round(totalMinor * 12 / 100)
   - satisfies strict budget sum invariant: sum(categories) + reserve == total exactly (100 randomized budgets)
   - satisfies line item invariant: category line items sum exactly to category amountMinor
   - preserves locked categories during re-allocation
   - detects impossible budget deficits when locked costs exceed allocatable budget
   - detects all-locked surplus when all categories are locked but don't match allocatable budget
   - formats currencies correctly for INR, USD, and EUR

 ✓ tests/dates.test.ts (6 tests) 15ms
   - calculates date differences and additions accurately
   - generates standard macro countdown for events with > 45 days lead time
   - compresses preparation schedule for short-notice events (e.g. 3 days away)
   - handles same-day and immediate events with same-day protocol
   - flags past-due tasks as overdue when due date precedes today
   - generates valid chronological Day-Of run-of-show blocks

 ✓ tests/replan.test.ts (7 tests) 17ms
   - calculates 15% budget cut consistently and balances budget
   - scales guest count by ceil(guests * 1.25) within fixed budget
   - safeguards locked category costs during budget squeeze
   - rejects applying a proposal if baseRevision does not match current plan revision (stale check)
   - rejects applying an infeasible budget deficit proposal
   - applies proposal, increments revision, and preserves user task/vendor state by stable ID
   - restores plan on Undo with a fresh monotonically increasing revision number

 ✓ tests/storage.test.ts (5 tests) 23ms
   - successfully imports a valid serialized EventPlan
   - rejects malformed non-JSON strings
   - rejects JSON missing mandatory fields
   - rejects unsupported schema versions (expected version 1)
   - rejects plans with corrupted budget math (reserve != 12%)

 ✓ tests/api.test.ts (5 tests) 46ms
   - GET /api/health returns healthy configuration without leaking secrets
   - POST /api/plan rejects malformed or missing brief with 400
   - POST /api/plan gracefully reports 503 when AI_ENABLED is false
   - POST /api/replan successfully generates Plan Rescue proposal
   - POST /api/replan rejects invalid actions with 400

Test Files  5 passed (5)
Tests       30 passed (30)
Duration    4.39s
```

---

## 3. Static Type Analysis & Linting

### Typecheck: `npm run typecheck`
- Command: `node ./node_modules/typescript/bin/tsc --noEmit`
- Result: **0 errors**

### Linter: `npm run lint`
- Command: `node ./node_modules/next/dist/bin/next lint`
- Result: **0 errors, 0 warnings** (`✔ No ESLint warnings or errors`)

---

## 4. Production Build Verification

Command: `npm run build` (`node ./node_modules/next/dist/bin/next build`)

```
   ▲ Next.js 15.2.1

   Creating an optimized production build ...
 ✓ Compiled successfully in 21.5s
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (7/7) ...
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                 Size  First Load JS
┌ ○ /                                    47.1 kB         150 kB
├ ○ /_not-found                            996 B         104 kB
├ ƒ /api/health                            130 B         103 kB
├ ƒ /api/plan                              130 B         103 kB
└ ƒ /api/replan                            130 B         103 kB
+ First Load JS shared by all             103 kB

○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```

---

## 5. Submission Packaging Measurement

Measurement command:
```powershell
$exclude = @('node_modules', '.next', '.git', 'utsav-ai-source.zip');
# Filtered files excluding generated directories and credentials
```

- **Uncompressed Source Size**: **626,033 bytes (611.36 KB)**
- **Compressed ZIP Archive Size**: **170,224 bytes (166.23 KB)**
- **Target Limit**: < 10,000,000 bytes (10 MB)
- **Compliance**: **PASSED (Uses ~1.6% of the 10 MB limit)**

---

## 6. Honest Audit & Limitations

1. **Live Gemini AI Execution**:
   - Status: **BLOCKED (Offline Environment)**
   - Rationale: The local build environment does not possess a live `GEMINI_API_KEY`. In accordance with CONTEXT.md rule (*"Never claim a build, test, deployment or live AI check passed without evidence"*), live generation is marked BLOCKED.
   - Guardrail: When `AI_ENABLED=false`, the server responds with HTTP 503 and preserves the current plan without crashing or substituting fake AI labels.
2. **Public Vercel URL**:
   - Status: **UNVERIFIED (Pending Remote Git Push)**
   - Rationale: Vercel deployment requires connecting the user's authenticated GitHub repository. Detailed step-by-step instructions are provided in `README.md`.
