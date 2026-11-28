# Backend API inventory and verification

This record covers the institution API checkpoint `a822b7c` (002.2D) and the demo authentication checkpoint `c78c81a` (002.3). See the [master plan roadmap](../School%20Admin%20Project%20Master%20Plan.md#243-task-002-completion-roadmap) for current task, GitHub, and release status.

## Demo session API

Routes are under `/api/v1/auth/`. The backend uses Django session authentication. A session does not grant institution access on its own. Student requests still require an active institution membership matching `X-Organisation-Code`.

| Method | Path | Behaviour |
| --- | --- | --- |
| `GET` | `/session/` | Returns session state and sets the `csrftoken` cookie. Usable before sign-in. |
| `POST` | `/login/` | Accepts JSON `email` and `password`. On success, starts a session, rotates the CSRF token, and returns session state. |
| `POST` | `/logout/` | Clears the session and returns anonymous session state. |

Session state contains `authenticated`, `user` (an object with `id` and `email`, or `null`), and `memberships` (empty when anonymous). Each membership includes `role` and an `organisation` with `id`, `code`, `name`, and `type`. The response includes only active memberships in active organisations. BHA oversight memberships are distinct from institution memberships.

Send the current CSRF cookie value in the `X-CSRFToken` header for login, logout, and authenticated writes. Read the new cookie after sign-in. The server expires an idle session after 60 minutes and checks current access on the next request after revocation. Expected login errors include `400` for invalid input, generic `401` for invalid credentials, `403` for CSRF rejection, and `429` for throttling. The five-failure limit per email and per IP in five minutes is process-local and may overshoot under concurrent attempts.

## Institution API

Routes are under `/api/v1/students/`. Require authentication and an active institution membership matching `X-Organisation-Code`. Writes require institution administrator or administrative staff membership. The role is evaluated in the selected institution. BHA-only and platform-only users have no access through these routes.

| Method | Path relative to `/api/v1/students/` | Behaviour |
| --- | --- | --- |
| `GET` | `/` | Unpaginated list. Supports `q`, `status` and `include_archived=true`. Archived records are omitted by default. |
| `POST` | `/` | Creates the student and person using a caller-supplied `student_number`. Accepts optional nested `emergency_contacts`. |
| `GET`, `PATCH` | `/{student_id}/` | Reads or edits a selected-school record. `PATCH` requires the current `version`. |
| `POST` | `/{student_id}/archive/` | Requires the current `version` and preserves lifecycle status. |
| `GET` | `/{student_id}/history/` | Returns current audit metadata, including actor email and changed-field names. The read-only metadata policy and full old/new history remain open for 2.9. |
| `GET`, `POST` | `/{student_id}/emergency-contacts/` | Lists or adds contacts under the selected student. `HEAD` is read-only. |
| `PATCH` | `/{student_id}/emergency-contacts/{contact_id}/` | Edits a contact only under its exact parent. Archived records reject contact writes. |

Invalid writes return `400` with safe validation errors. Role or membership denials return `403` for authenticated callers. Missing, malformed and out-of-scope record IDs use generic `404` responses. Stale writes return `409` with refresh guidance. Database errors use safe responses without SQL or internal diagnostics.

## Local test evidence

### 002.3 authentication checkpoint `c78c81a`

The Backend & API handoff reports a clean migration apply on disposable PostgreSQL 17.12, **14 focused tests passed**, and **82 full backend tests passed**. Both session tests deferred from 002.2D passed. The lead also ran 14 focused tests on SQLite. Independent Security & Tenant Isolation review cleared the Basic authentication alternative path after it was removed and passed 39 focused authentication and isolation tests on SQLite. Ruff, Django system checks (local and production configuration), migration drift, and Git diff checks passed.

### 002.2D backend checkpoint `a822b7c`

This checkpoint integrates migration repair `2e1ff73` and stabilisation `2c9b56e` with the reviewed 002.2B isolation and 002.2C validation and integrity changes. The snapshot predates the 2.3 authentication commit.

Built an isolated snapshot from `git archive 2c9b56e backend` plus the seven reviewed student code and test files in this checkpoint. The committed authentication tests were left intact. The earlier 81-pass PostgreSQL run included pending 2.3 work and is baseline evidence for that combined working tree.

| Full backend suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| PostgreSQL 17.12 | 72 | 2 | 0 |
| SQLite | 71 | 2 | 1 |

PostgreSQL applied all migrations on a disposable database, including `students.0001` and `students.0002`. Pytest then created a clean test database. Passing cases covered student creation, editing, search, archive, emergency contacts, institution and role isolation, unauthorised-access denial, uniqueness and foreign keys, late-failure rollback, and concurrent stale-write handling. The concurrent test observed the second PostgreSQL session waiting on the first session's row lock and verified one saved version increment and one audit event. SQLite skipped that PostgreSQL-only test.

Both full suites exited 1 for two existing tests. Both names also failed on an untouched SQLite snapshot of `2c9b56e` with the same cause. `GET /api/v1/auth/session/` returned `404`, so the tests raised `KeyError: 'csrftoken'` before login. The tests were preserved at this checkpoint and passed at the later 2.3 checkpoint.

- `tests/test_permissions_and_auth.py::test_session_login_logout_and_memberships`
- `tests/test_permissions_and_auth.py::test_login_errors_are_generic_and_throttled`

Ruff, Django system checks and migration drift passed. Django checks and drift ran on both databases. `python -m pip check` reported no broken requirements in the Python 3.12.10 test environment. `git diff --check` passed.

To reproduce from the committed checkpoint, use the versions in `backend/requirements.lock` and run from `backend/`. For PostgreSQL, set the local `POSTGRES_*` variables for a disposable PostgreSQL 17 instance with permission to create a fresh test database, then run `python manage.py migrate --noinput` and `python -m pytest -q -ra --tb=short --create-db`. With `POSTGRES_DB` unset, the same pytest command uses SQLite. Run `ruff check .`, `python manage.py check`, `python manage.py makemigrations --check --dry-run` and `python -m pip check` in the same test environment.
