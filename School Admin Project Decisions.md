# Horseracing Student Record Management System
## Authoritative Discovery Answers and Architecture Decisions — Sections 1–6, A–O, and final clarifications

**Document ID:** HSRMS-DISCOVERY-002  
**Version:** 2.0  
**Updated:** 23 November 2026  
**Status:** Product-owner decisions recorded; stakeholder/legal confirmation still pending  
**Companion document:** `School Admin Project Master Plan.md`  
**Implementation instruction:** **Task 003 is ON HOLD. Do not implement it merely because these documents have been updated.**

### How to read this document

- **CONFIRMED BY OWNER** means the product owner explicitly chose this behaviour. It is not proof that a school, the BHA or any data controller has accepted it.
- **PROPOSED / ENGINEERING METHOD** means the outcome is confirmed but the exact implementation remains subject to repository inspection and technical testing.
- **STAKEHOLDER / LEGAL APPROVAL REQUIRED** means a product decision cannot itself authorise processing or disclosure of real student data.
- **DEFERRED** means planned for later and not part of the current task by default.
- More recent explicit decisions supersede older entries **only where they conflict**. An old historical answer below is retained for traceability and called out where superseded.
- Codex must inspect the actual repository and existing migrations/tests before determining what is missing. **Task 001 and Task 002 are reported completed by the owner, but were not independently inspected for this document.**

## Section 1 — Core purpose and system structure (original discovery)

1. **Purpose — CONFIRMED:** Reduce fragmented/manual student records; standardise core information across target institutions; make selected authorised data retrievable by the BHA.
2. **Institution independence — CONFIRMED:** Each institution owns independent student records; verified same-person identity may link them centrally, without revealing other schools' private records to school staff.
3. **BHA access — CONFIRMED:** Separate BHA web portal **and** secured external API.
4. **BHA disclosure — CONFIRMED, LATER REFINED:** Selected authorised fields only. Sections M/N later identify a proposed *baseline* of three fields after institutional authorisation; this is not blanket consent to share real records.
5. **Record initiation — CONFIRMED:** School staff directly create official records; students submit public forms for staff review, without student accounts.
6. **Product ambition — CONFIRMED:** Commercial product intended for real use by BRS, SRA, NHC and The National Stud, subject to their participation and agreements.

## Section 2 — Student data and records (original discovery)

1. **Core categories:** Legal name, DOB, gender, nationality, email, phone, home address and emergency/next-of-kin contacts.
2. **Fields:** Common fields plus school-specific configurable required/custom fields. **Later clarified:** Legal name and DOB always required for new records; institutions decide additional mandatory fields. A newly required field applies only to new records.
3. **Editing:** Only authorised institution staff may change official records.
4. **Documents:** No document uploads in first version.
5. **Statuses:** User-facing pending approval, Active, Completed, Withdrawn and Archived/Historical. **Refinement:** Pending belongs to *registration submission*; Active/Completed/Withdrawn are record statuses; archival and deletion are separate flags/workflows.
6. **Import:** Staff manually create and bulk-import records (CSV/XLSX), including current/recent historical data.
7. **Identity:** Centrally assigned stable person ID. Issuing a UUID does **not** establish that identity is verified.
8. **History:** Institution-specific cutoff for importing historical students is still undecided.

## Section 3 — Roles, permissions and workflows (original discovery, as amended)

1. **Roles:** Platform administrator; institution administrator; institution administrative staff; institution read-only staff; BHA administrator; BHA staff/user and separately scoped BHA machine client.
2. **No student accounts:** Student-submitted forms are public but secure and reviewed by staff.
3. **Every student submission:** Requires institution staff approval before becoming an official record.
4. **Staff direct creation:** Official record can be created immediately; possible duplicates may be saved but flagged.
5. **Editing:** Institution admins and authorised administrative staff can edit; read-only staff cannot.
6. **Deletion — SUPERSEDED ORIGINAL ANSWER:** The initial instruction restricted deletion to administrators. **Newest confirmed rule:** Institution administrators **and administrative staff** may delete their institution's student records without approval. Deletion has a **48-hour restoration window** with original data/ID intact; after it closes, permanent erasure follows retention/legal-hold obligations.
7. **History:** Record who changed information, when, and old/new values; restrict audit access.
8. **Cross-school attendance:** New independent institution record; only the BHA may verify central identity links across schools. Never disclose other-school records to an institution.
9. **Staff invitation:** Institution administrator invites and manages school staff; invitation required before sign-in.
10. **BHA:** Approved cross-school search, authorised consolidated views, CSV/XLSX exports and institution-history view where independently verified and approved.

## Section 4 — BHA API and integration (original discovery, as amended)

1. **Allowed fields — PARTLY RESOLVED:** Once a school has legally approved baseline sharing, default BHA-visible fields are **legal name, institution name, institution student ID**. Each school may disable defaults unless a legal obligation applies. Other fields, including DOB, email, phone and emergency contacts, need explicit approved grants. No live disclosure before formal arrangements.
2. **Potential search inputs:** Name, central person ID, DOB, institution student ID, institution, status, email and phone. Each search field still requires an approved search grant; being a search parameter does not imply a right to receive the field.
3. **Consolidation:** Verified same-person records can be shown as one BHA profile with each institution's data kept distinct and appropriately permission-filtered. Unverified identities remain separate.
4. **Freshness:** Authorised reads use current data, visible on refresh/reopen; no overnight BHA replication.
5. **Institution control:** Institutions manage approved sharing fields and individual record restrictions. Institution admins **and administrative staff** can configure within the formally approved envelope.
6. **API:** Individual, paginated and bulk authorised reads/exports.
7. **BHA exports:** CSV/XLSX, requested columns within authorised grants; **150 or more student records requires BHA administrator approval**. Large exports processed asynchronously and downloadable for 24 hours, subject to permission rechecks.
8. **Existing BHA systems:** Unknown until BHA engagement.
9. **Historical visibility — REFINED:** BHA sees Active, Completed and Withdrawn records only **when not archived**, and only while approved for sharing. Deleted records are never available via BHA access. Earlier school-configurable archived-history visibility is superseded by the non-archived-only rule.
10. **BHA account administration:** BHA administrators manage BHA user accounts and role-based search/export permissions; cannot override school sharing limits.
11. **Identity review:** **All authorised BHA staff** may manually verify, link and unlink cross-institution identities, recording evidence and audit history; no separately restricted 'identity reviewer only' role.

## Section 5 — Security, hosting and governance (original discovery, as amended)

1. **Production hosting preference:** UK-region managed hosting; provider unknown. Local/synthetic development may use Docker/PostgreSQL.
2. **Login:** Institution staff eventually use institution Microsoft/Google SSO; invitation required. Platform/BHA administrators use separate secure login with mandatory MFA. Ordinary staff MFA requirement remains optional unless institutional policy demands it. Existing demo login stays until the replacement is built/tested.
3. **Access:** Secure login from authorised devices/locations; 60-minute inactivity logout, enforced server-side; membership revocation must take effect promptly, including existing sessions.
4. **Cross-school verification:** All authorised BHA staff can manually verify/link/unlink; exact proof standards and organisational approvals await stakeholders.
5. **Applicants:** Both under-18s and adults; privacy requirements must be settled for live use.
6. **Retention:** Institution-specific legal retention periods and holds still require approval. Forty-eight-hour user restoration is **not** a promise of lawful permanent erasure at hour 48.
7. **Recovery — CONFIRMED:** Daily backups retained **30 days**, encrypted and stored separately from the main database. Production recovery-time goal **4 hours**; potential loss of up to ~24 hours since last backup in a worst-case unrecoverable incident. Test restores before production. No continuous point-in-time recovery is currently required by the owner.
8. **BHA sharing settings:** Institution admins and administrative staff may change within the approved legal/policy bounds; revocation takes effect on the next BHA read and blocks pending downloads, though prior copies cannot be recalled.
9. **Availability:** Aim for minimal production interruption; contractual uptime/SLA still undecided.
10. **Incident/privacy coordination:** Central platform team and institution privacy representatives cooperate; controller/processor obligations need formal definition.
11. **Operator privileges — NEW:** Platform administrator has **direct, unrestricted record access across all four institutions at any time** as a product decision; no approval prompt or reason-gated admin mode requested. Mandatory MFA, tamper-resistant audits and contractual/legal acceptance are necessary safeguards. This does not grant a school access to another school's records.

## Section 6 — Development, business and rollout (original discovery)

1. Independently developed with AI/Codex support; no institutions have committed to participation.
2. All current student records are **fictional**.
3. Initial budget **£0–£100**; one-month prototype aspiration, not full production certification.
4. Launch one school first, then expand to all four, after commercial/legal validation.
5. Independently owned/maintained commercial SaaS; pricing not yet agreed.
6. **Implementation state:** Owner reports Task 001 and Task 002 complete. **Task 003 is intentionally on hold**. Codex must not treat an updated planning document as an instruction to implement it.
7. **Environments:** One development environment for now, containing only fictional data; staging/production separation required before processing real data.

---

## Additional discovery — Section A: student-record rules (CONFIRMED)

1. System-generated institution-prefixed, non-reusable student IDs: **`BRS-0001`, `SRA-0001`, `NHC-0001`, `STUD-0001`** (confirmed initial formats; existing IDs must never be rewritten). Generation must be concurrency-safe.
2. Institutions configure additional mandatory fields; legal name and DOB are common minimums for new records.
3. Multiple records for the **same student at the same institution** are allowed only with appropriate institution staff review/approval of an intentional repeat; suspected duplicates can be saved and flagged pending review. **Institution staff**, not the platform owner, resolve them.
4. Preserve full prior values in access-controlled audit history.
5. Allow institution-specific custom fields.
6. Up to **two** emergency contacts per student.
7. Archived records excluded from default list, searchable and restorable by authorised institution staff.
8. Institution staff may change Active/Completed/Withdrawn status.

## Section B: institutional UI and workflow (CONFIRMED)

1. Dashboard immediately after login, restricted to record counts/links (no training statistics).
2. Toggle between student **table and card** views.
3. **Quick edit** (email, phone, address, status) and full edit page.
4. Institution admins and administrative staff restore archived records.
5. Institution admins and administrative staff manage mandatory/custom fields.
6. Combinable advanced search across authorised student fields.
7. Institution admins and administrative staff view full record edit history; read-only staff cannot.
8. **Explicit Save Changes** control; no auto-save.

## Section C: edge cases (CONFIRMED)

1. Reject stale concurrent edits; warn user and require refresh. Do not silently overwrite a more recent update.
2. Detect possible matches using legal name, DOB, email and phone; **flag** candidates, never automatically merge.
3. Allow authorised staff to save flagged suspected duplicates for institution review. Institution staff confirm legitimate repeats or resolve errors; platform admin approval is **not** required for routine school duplicate decisions.
4. Student IDs never reused after archive, deletion, or import.
5. Custom field types: short text, long notes, number, date, dropdown, Yes/No.
6. Newly mandatory fields apply **only to new records**; grandfather earlier records during future edits.
7. Populated custom-field permanent deletion is administrator-restricted and subject to legal retention; do not silently destroy historical data.
8. Restoration from archive requires staff to choose Active/Completed/Withdrawn status.
9. Historical imports always receive a new platform student ID; preserve source identifiers safely as import reference if needed.
10. Institution decides whether email and phone are mandatory; neither is globally required by owner.

## Section D: multi-tenant architecture (CONFIRMED / DEFERRED)

1. A staff member may belong to multiple schools, with separate invitations/memberships.
2. One shared website; separate authorised school contexts, optional branding.
3. One shared PostgreSQL database with strict institution isolation.
4. **DEFERRED:** Formal governance/verification evidence for cross-school identity linking until school/BHA engagement. Reviewer actor now decided: all authorised BHA staff.
5. Institution-wide sharing settings **and** per-student BHA restrictions.
6. Conflicting details between schools are retained separately, never silently overwritten.
7. BHA permission revocations effective immediately on future reads and pending downloads.
8. Repeat public registration detected/flagged for institution staff review; never automatically overwrite an existing record.
9. Import valid rows even when some rows fail, with preview and error reporting; individual row creation remains atomic.
10. Changing a populated custom field's data type is not directly allowed; controlled migration/new field required.
11. Institution admins can view BHA record-access and export history concerning their institution (administrative staff access also confirmed later for student access history).
12. **ONE development environment for now**; staging and production separate before live personal data.

## Section E: login and application behaviour (CONFIRMED)

1. Institution staff SSO through their organisation's Microsoft or Google identity provider, once available.
2. Staff with multiple memberships switch institution inside the website without signing out; warn about unsaved edits and clear prior-tenant cached context.
3. Changes visible after refresh or reopening a record; no real-time live screen synchronisation required.
4. View audit history and manually restore historical values (subject to current role permissions and validation); no one-click whole-record rollback.
5. Temporary caching for speed, **refined in Section G to non-sensitive institutional settings only**; fetch student records fresh.
6. Friendly non-technical error messages; never expose stack traces or other students' private information.

## Section F: invitation, admin login and session (CONFIRMED)

1. Only staff invited by an institution administrator may access that institution.
2. Platform and BHA administrators use separate secure administrator login with mandatory MFA.
3. Keep existing demo login temporarily; add institutional SSO only after providers and implementation are verified.
4. Manual staff revocation immediately; automated identity-provider offboarding synchronisation later.
5. Automatic logout after **one hour of inactivity**.

## Section G: visibility, export, notifications and audit (CONFIRMED)

1. Read-only staff can see all student fields, including home address and emergency contacts, **unless authorised institution staff hide specified fields or entire records**. Restrictions are optional, not mandatory on every student.
2. Institution admins and administrative staff may export authorised own-school records as CSV/XLSX.
3. Moving between schools creates a *new* institution-owned record; never transfer ownership of the old record.
4. **In-app notifications only**, not email notifications for these workflows.
5. Cache school settings/non-sensitive metadata only; fetch student records fresh.
6. Log edits, sensitive record views and exports.

## Section H: backend/API decisions (CONFIRMED)

1. Institution admins and administrative staff may hide individual sensitive fields **and** whole records from read-only staff.
2. Hidden entire records must not appear to restricted read-only staff in lists, searches, counts or exports. Hidden fields must not leak in detail/API/export responses.
3. Student list pagination **25 default, maximum 50** per page.
4. Edit one record at a time; separately supported bulk **import** (not bulk updates).
5. Large exports run as asynchronous jobs, with in-app completion notifications.
6. Separate rate limits for school staff, anonymous registration forms and BHA/API principals.
7. All changes for a single student save transactionally together or not at all. Partial batch import may succeed *by valid row*.
8. Version API routes e.g. **`/api/v1/`**.

## Section I: export and visibility controls (CONFIRMED)

1. Restricting information from school read-only users does **not** automatically restrict BHA; BHA has separate grants.
2. Entire records hidden from read-only users should be undiscoverable to them, including counts.
3. Institution export requester selects columns only from authorised fields.
4. Generated export downloads expire after **24 hours**, with permissions rechecked at access.
5. In-app notifications: new registration submissions, suspected duplicates, completed exports and important access changes.
6. Institution administrators **and administrative staff** can see who viewed a given student record, subject to tenant restrictions.

## Section J: resilience and recovery (CONFIRMED)

1. **Daily backups only** (not continuous recovery as an initial requirement).
2. Target resuming service within **4 hours** of a serious failure; aspirational until tested.
3. Preserve unsaved changes during a brief network interruption in browser memory, allow retry with stale-version check; clear on logout/session expiry; no permanent plaintext student storage in browser.
4. When DB unavailable, prevent edits; no offline write queue.
5. Cancel/revalidate BHA exports if sharing permission revoked mid-job.
6. Alert platform owner promptly on outages; alert affected institution admins for significant incidents.
7. Support safe application rollback without overwriting committed DB changes; migrations need compatibility/recovery checks.

## Section K: backups, deletion compliance, jobs (CONFIRMED)

1. Retain encrypted daily backups for **30 days**.
2. Store encrypted backups separately from the live database/system failure domain.
3. Permanent deletion must respect authorised retention/legal hold requirements. **Subsequently refined:** institution admins **and administrative staff** can initiate a 48-hour recoverable deletion without separate approval.
4. Platform admin can access cross-institution **security** logs, with minimum necessary security detail; separately the owner chose direct full student record access (Sections L/M).
5. Retry transient background job failures safely; report persistent failure through in-app notification; prevent duplicate imports/exports on retry.
6. Validate schema migrations and restore procedures before production updates.

## Section L: platform permissions/security (CONFIRMED)

1. **Platform administrator has full direct access to institution records at any time**, not break-glass-only, not dependent on school approval or reason prompts. This requires high-privilege MFA, protected access auditing and school contractual acceptance before real data.
2. Institution admins manage their staff invitations, roles and removals.
3. Warn about unsaved edits when switching schools, then clear previous school data/session context.
4. Enforce isolation in Django; evaluate PostgreSQL Row-Level Security for defence in depth without assuming it is already deployed.
5. Platform admin can access platform/technical organisation settings.
6. Log failed logins and suspicious behaviour with secure logs that don't contain passwords or unnecessary personal data.

## Section M: BHA and central identity (CONFIRMED, GOVERNANCE PENDING)

1. Platform administrator has **direct** record access at any time; audited automatically, mandatory MFA. No separate permission prompt.
2. BHA gets a *minimum baseline* automatically **after each institution has formally approved onboarding and lawful sharing**; actual baseline in Section N. No unauthorised auto-sharing in development/production.
3. BHA administrators manage BHA staff; institution staff govern shared information.
4. Potentially same-person records at different schools remain separate in BHA views until identity is verified; if each individually authorised they can appear independently.
5. Schools see an effective permission preview and can test what BHA will be shown, without granting unintended access.

## Section N: baseline BHA disclosure (CONFIRMED, SUBJECT TO INSTITUTIONAL APPROVAL)

1. Default baseline fields: **legal name, institution name, institution student ID**. DOB, phone, email and emergency details excluded by default.
2. Schools may disable any default field unless legally required otherwise; all user-configurable grants remain within legally approved limits.
3. **Only non-archived records** are BHA-visible. This includes Active, Completed and Withdrawn, where authorised; deleted records excluded.
4. BHA API can securely retrieve/export authorised records and fields, using scopes, rate limits and auditing.
5. Suspected same-person duplicates can appear as independently authorised separate records; never falsely describe them as verified links.

## Section O: BHA workflow and consolidation (CONFIRMED)

1. BHA may see Active, Completed and Withdrawn records when non-archived and authorised.
2. Verified same-person identity may produce one BHA consolidated view; retain individual institution information separately.
3. **All authorised BHA staff** (not only a specialist reviewer class) can verify, link and unlink cross-institution identities. Log actor, evidence/procedure, time and outcome; never alter school-owned records by linking.
4. BHA administrators control BHA users' ability to search/export, but these controls do not narrow the confirmed general ability of authorised BHA staff to perform identity-review actions without a future explicit owner change.
5. Exports of **150 or more student records** require BHA administrator approval.

## Final owner clarifications after Section O (CONFIRMED)

1. **Identity matching:** Compare identifying details to generate possible links; **all authorised BHA staff** manually confirm before cross-school linking, with documented rationale/evidence (exact evidence standards still stakeholder TBD).
2. **Competing identity decisions:** Maintain history, allow corrections/unlinks, reject conflicting concurrent decisions rather than silently overriding one.
3. **Student public forms:** Secure institution-specific public registration links, no student accounts.
4. **Delete without separate approval:** Institution administrators and administrative staff can delete student records. Deletion is immediately hidden from ordinary/ BHA visibility and recoverable by authorised staff for **48 hours**, with all fields and the original student ID intact. After this grace period, the record is no longer recoverable through the ordinary interface; permanent purge is subject to lawful retention, holds, audit/backup handling. **Do not claim immediate irreversible deletion at 48 hours.**
5. **Large BHA export trigger:** **150 or more rows**, not 500.
6. **Historical import:** CSV/XLSX preview, per-row validation/errors/duplicate flags; valid rows can import while invalid rows remain for correction. Allocate new institution-prefixed IDs to every imported student.
7. **Data-loss window accepted with daily backups:** If only the last daily backup survives a catastrophic failure, up to about **24 hours of committed changes** may be lost. Four-hour recovery time is a different measure; both are targets, not guarantees.
8. **Audit versions:** Preserve earlier student values for manual restoration when authorised, subject to retention/legal removal.
9. **Deletion permissions refined:** Read-only staff cannot delete; institution admins and admin staff can delete and restore within 48 hours; after 48 hours, retention-governed erasure replaces user-visible restore.
10. **Task 003 remains on hold.** These files record decisions but do not authorise coding, migrations, deployment or data ingestion.

---

## Fixed boundaries (unchanged)

- Exactly four prospective educational tenants: **BRS, SRA, NHC and The National Stud**. **BHA is an oversight/authorised consumer**, never a school tenant.
- Student record management only. No training statistics, courses/timetables, attendance, assessments, qualifications, placements, finance, student accounts, first-version documents, or uncontrolled external integrations.
- Independent institution records; BHA identity linking does not change school ownership and school staff must not gain other institutions' records.
- Development/test data fictional; no real student PII without formal approval, legal arrangements, privacy review and security controls.
- System is not currently contracted to the schools or BHA; do not claim that it is.
- One development environment currently. Real-data deployment requires properly isolated production environment and tested operations.
- The shared React/TypeScript + Django REST Framework + PostgreSQL modular-monolith architecture is the current existing implementation direction, subject to inspection; don't rewrite functioning Task 001/002 code merely because the plan is revised.

## Stakeholder- or evidence-dependent decisions still open

| Topic | Who must confirm | Safe current rule |
|---|---|---|
| Each institution's actual Microsoft/Google SSO tenant and technical configuration | Each school / IT | Keep demo login; invite-only authorisation design |
| Real mandatory fields, custom fields, exact incoming formats and recent-history cutoff | Each school | Legal name + DOB minimum; fictional configs/records |
| Data retention, erasure obligations, lawful holds and child privacy details | Each school / privacy and legal | Do not irreversibly erase protected live data on an invented schedule |
| Formal BHA data sharing purposes, lawful basis, baseline field approval and per-field/search/export grants | Schools + BHA / data protection leads | No real-data sharing until agreement; synthetic sample grants only |
| Contractual acceptability and governance of unrestricted platform-admin PII access | Schools / BHA / legal | Can design feature with MFA/audit; no inference of lawful live access |
| BHA systems, auth/client requirements, and actual API contract | BHA IT | Document and mock only |
| Evidence criteria, training, dispute escalation and official procedures for BHA identity confirmation | BHA + schools | Manual authorised BHA review, no automatic merge |
| UK-region production vendor, uptime commitments, backup/recovery guarantees, DPA/subprocessors, commercial contract and pilot choice | Product owner + prospective customers | One fictional-data dev environment, aspirational operations targets |
| Exact technical implementation state and test evidence of Tasks 001/002 | Repository audit by developer/Codex | Do not claim code changes are already present or absent without inspection |
| Whether platform-admin full access includes routine record **modification** or only unrestricted **view/read** | Product owner / later access design | Direct read/view is confirmed; don't silently infer unrestricted destructive operations |

## Engineering notes, not new owner decisions

- Retain separate `archived_at` and `deleted_at`; a 48-hour deletion grace period is distinct from archival and from 30-day backup retention.
- Enforce field hiding, tenant scoping, BHA grants and platform exceptions in backend policy checks; hiding a React component is insufficient.
- Use optimistic concurrency on edits and identity decisions; atomic student saves, idempotent import/background jobs and concurrency-safe student IDs.
- Keep exports private, grant-filtered, logged and expiring after 24 hours. A 150-row BHA export additionally needs administrator approval.
- Use authenticated HTTPS, CSRF-safe browser sessions, provider identity verification, MFA for administrators, secrets management, privacy notices and periodic backup restoration tests before production.
- Keep audit evidence access-controlled, append-only/tamper-evident; an administrator's elevated data access does not authorise removing their own audit trail.

**End of authoritative discovery register. No Task 003 implementation has been requested.**
