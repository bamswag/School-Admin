# Backend API inventory and verification

Task 002.2D, 26 November 2026. This local checkpoint integrates migration repair `2e1ff73` and stabilisation `2c9b56e` with the reviewed 002.2B isolation patch and 002.2C validation and integrity patch. Task 2.2 is verified within this backend scope. The checkpoint excludes the pending 2.3 authentication implementation and its working-tree edits. No GitHub push was made. GitHub CI is unverified and remains evidence for 2.10.

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

Built an isolated snapshot from `git archive 2c9b56e backend` plus the seven reviewed student code and test files in this checkpoint. The committed authentication tests were left intact. The earlier 81-pass PostgreSQL run included pending 2.3 work and is baseline evidence for that combined working tree.

| Full backend suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| PostgreSQL 17.12 | 72 | 2 | 0 |
| SQLite | 71 | 2 | 1 |

PostgreSQL applied all migrations on a disposable database, including `students.0001` and `students.0002`. Pytest then created a clean test database. Passing cases covered student creation, editing, search, archive, emergency contacts, institution and role isolation, unauthorised-access denial, uniqueness and foreign keys, late-failure rollback, and concurrent stale-write handling. The concurrent test observed the second PostgreSQL session waiting on the first session's row lock and verified one saved version increment and one audit event. SQLite skipped that PostgreSQL-only test.

Both full suites exited 1 for two existing tests. Both names also failed on an untouched SQLite snapshot of `2c9b56e` with the same cause. `GET /api/v1/auth/session/` returned `404`, so the tests raised `KeyError: 'csrftoken'` before login. The session routes belong to pending 2.3. Neither test was changed, skipped or marked expected-failure for this checkpoint.

- `tests/test_permissions_and_auth.py::test_session_login_logout_and_memberships`
- `tests/test_permissions_and_auth.py::test_login_errors_are_generic_and_throttled`

Ruff, Django system checks and migration drift passed. Django checks and drift ran on both databases. `python -m pip check` reported no broken requirements in the Python 3.12.10 test environment. `git diff --check` passed.

To reproduce from the committed checkpoint, use the versions in `backend/requirements.lock` and run from `backend/`. For PostgreSQL, set the local `POSTGRES_*` variables for a disposable PostgreSQL 17 instance with permission to create a fresh test database, then run `python manage.py migrate --noinput` and `python -m pytest -q -ra --tb=short --create-db`. With `POSTGRES_DB` unset, the same pytest command uses SQLite. Run `ruff check .`, `python manage.py check`, `python manage.py makemigrations --check --dry-run` and `python -m pip check` in the same test environment.
