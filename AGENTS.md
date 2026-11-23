# Codex project guidance

Read `School Admin Project Master Plan.md` completely before changing this repository. It is the authoritative source for confirmed scope, constraints, phase gates, safety rules, and requirement IDs.

- Work only on the explicitly requested task and milestone; do not pull later phases forward.
- Use synthetic data only. Never add institutional records, credentials, logos, workflows, integrations, or unapproved BHA fields.
- Preserve strict tenant isolation. BHA is an oversight consumer, not a fifth school, and receives no personal fields without an active approved grant.
- Do not add courses, attendance, assessments, qualifications, placements, finance, analytics, training statistics, document uploads, or student accounts.
- Run and report the relevant tests. Any tenant, field, or privilege-isolation failure blocks release.
- Record owner-approved requirement changes in `docs/decision-log.md`; never silently turn a proposal or TBD into a confirmed requirement.
