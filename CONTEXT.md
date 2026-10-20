# UtsavAI project contract

Build Challenge 5: Celebration & Event Planner.
Required pillars: budgets, timelines, vendor checklists, personalized ideas.

## Platform
- GitHub source control and Vercel deployment.
- No GCP hosting, Cloud Run, Vertex AI, Firebase, gcloud or Docker requirement.
- Next.js App Router, TypeScript, locally built styles.
- Server-only Gemini Developer API using @google/genai and schema-based output.
- GEMINI_API_KEY, GEMINI_MODEL and AI_ENABLED are server environment variables.
- No browser API-key entry or NEXT_PUBLIC secret.
- Build must succeed without API credentials. Initialize the provider lazily.
- No database or login required for the MVP. Local saves are browser-specific.

## Product
- Support weddings, birthdays and community events.
- Every visible button works or is visibly disabled with a reason.
- Sample plans have a persistent Sample Plan label.
- Live results have a Live AI label only after successful provider response.
- Never silently substitute sample content for a failed live request.
- Editing a live plan locally marks it as locally edited.
- Show assumptions and allow users to correct them.
- Prices are planning estimates, not vendor quotes.
- Never fabricate vendor businesses, contact details, availability or live weather.
- Vendor messages are copyable drafts; never send them automatically.

## Domain correctness
- All currency values use integer minor units; initially support INR, USD and EUR.
- Reserve 12% by default as a product choice, not an official event rule.
- Compute totals, percentages and rounding in code.
- Budget category totals plus reserve must equal total budget exactly.
- Line items must sum to their category.
- Use explicit date, local event time and IANA timezone.
- No milestone can be scheduled before today without an overdue flag or explicit repair.
- Short-notice events need compressed preparation schedules.
- Low budgets and locked-cost conflicts produce visible feasibility warnings.
- Do not invent savings guarantees.

## State and revisions
- Stable IDs for plans, categories, items, milestones and vendors.
- Separate AI content from user completion/booking state.
- Replanning receives the actual accepted current plan and constraints.
- Preserve completed tasks, booked vendors and locked costs.
- Preview proposed changes before applying them; provide undo.
- Never overwrite a plan with an invalid response or stale request.
- Save schemaVersion, revision, updatedAt and source metadata.

## Reliability
- Runtime validation for requests, AI responses and imported files.
- Bound prompt lengths, list sizes, response sizes and generation time.
- Handle missing key, unavailable model, refusal, malformed output, quota and timeout.
- Preserve the last accepted plan on every error.
- No unbounded automatic retries.
- Never render AI strings as raw HTML.
- Provide text error messages, keyboard navigation and print styles.
- Keep node_modules, .next, test artifacts and environment secrets out of Git.
- Measure the actual submission archive; target below 10 MB pending official rules.
- Never claim a build, test, deployment or live AI check passed without evidence.
