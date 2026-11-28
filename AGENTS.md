# Codex project guidance

Read the [School Admin Project Master Plan](<School Admin Project Master Plan.md>) completely before changing this repository. It is the authoritative source for confirmed scope, constraints, phase gates, safety rules, and requirement IDs. Read the [decision register](<School Admin Project Decisions.md>) for approved decisions and the [README](README.md) for project setup.

- Work only on the explicitly requested task and milestone; do not pull later phases forward.
- Raise scope or requirement conflicts with Roadmap & Decisions for owner resolution before implementing the affected behaviour. Task 003 remains on hold.
- Use synthetic data only. Never add institutional records, credentials, logos, workflows, integrations, or unapproved BHA fields.
- Preserve strict tenant isolation. BHA is an oversight consumer, not a fifth school, and receives no personal fields without an active approved grant.
- Do not add courses, attendance, assessments, qualifications, placements, finance, analytics, training statistics, document uploads, or student accounts.
- Run and report the relevant tests. Any tenant, field, or privilege-isolation failure blocks release.
- Record owner-approved requirement changes in `docs/decision-log.md`; never silently turn a proposal or TBD into a confirmed requirement.

## Task briefs, verification, and handoffs

1. **Use one roadmap.** Look up task status, lead chat, and dependencies in [master plan §24.3](School%20Admin%20Project%20Master%20Plan.md#243-task-002-completion-roadmap). Keep live status there and link to it from other chats or documents. Use the [backend verification record](docs/backend-api-verification.md) for API contracts and test evidence by checkpoint. Flag newer evidence to Roadmap & Decisions.
2. **Start with a short brief.** State the task ID, lead chat, starting branch or commit, relevant requirement IDs or sections, acceptance criteria, exclusions, and evidence that prerequisites are met. After the required reading, inspect the relevant files and tests, check the checkout, and preserve existing work. Name supporting chats only for specific deliverables or reviews.
3. **Hand off the change and its contract.** Send the lead and Roadmap & Decisions the commit or diff, affected API, schema, or UI behaviour, checks and results, and any blockers. Report implementation, test verification, and GitHub push status separately. Give Frontend & UX the login response shape, CSRF behaviour, and expected errors when relevant. Give Security & Tenant Isolation the permissions and boundaries to verify. Keep the transcript in the original chat.
4. **Match checks to the stage.** Run focused checks during development and all required checks at the applicable verification gate. Summarise each check, its outcome, and relevant failures. Include longer logs when needed for diagnosis. Mark checks that could not run as **unverified**.
5. **Give each check an owner.** The implementation chat runs its task checks. **Security & Tenant Isolation** independently verifies access boundaries when required. **CI & Release Verification** records CI, PostgreSQL, and release evidence against the tested commit. Reuse verified results for the same commit when they satisfy the gate, while preserving required independent checks.
6. **Use a fresh chat for a substantially different task.** Keep related fixes and troubleshooting in the current task chat. At the transition, tell the owner which chat should lead, what to assign, and which prerequisites apply. Carry forward the short handoff and relevant document or commit references.
