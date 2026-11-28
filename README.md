# Horseracing Student Record Management System

Synthetic-data, non-production prototype for the four prospective education tenants named in [`School Admin Project Master Plan.md`](<School Admin Project Master Plan.md>). BHA is represented separately as an oversight organisation. No institution has approved or adopted this software.

## What is in the prototype

- Django 5.2/DRF backend with custom users, organisations, memberships, unverified persons, and minimal student records.
- Tenant-scoped student list, search, detail, create, edit, archive, history, and emergency-contact add/edit API. The backend enforces institution roles, validates writes, and rejects stale edits.
- Demo session login and logout, CSRF protection, active membership checks, and a 60-minute idle timeout.
- Idempotent synthetic seed command for BRS, SRA, NHC, The National Stud, BHA, demo role accounts, and one fictional student per school.
- Minimal Vite/React/TypeScript shell. Login UI and institution switching are the next frontend milestone.
- Local PostgreSQL Compose service and CI checks.

## Project roadmap and chats

The [Task 002 roadmap in the master plan](<School Admin Project Master Plan.md#243-task-002-completion-roadmap>) is the source for task assignments, dependencies and current implementation, test and GitHub status.

- **Roadmap & Decisions** manages scope, sequencing and handoffs.
- **Backend & API** owns Django, authentication, business rules and API tests.
- **Frontend & UX** owns React, accessibility and browser tests.
- **Database & Migrations** owns PostgreSQL schema, migrations and constraints.
- **Security & Tenant Isolation** reviews tenant, role and field boundaries.
- **CI & Release Verification** owns CI, Docker and release evidence.

Before starting, read [AGENTS.md](AGENTS.md), the [master plan](<School Admin Project Master Plan.md>) and the [decision register](<School Admin Project Decisions.md>). Use the lead chat and prerequisites named in the roadmap. Task 003 remains on hold.

## Local setup

Requires Python 3.12+, Node 24+, and Docker Compose.

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
cp .env.example .env
docker compose --env-file .env -f infrastructure/docker-compose.yml up -d
set -a; source .env; set +a
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py seed_demo
```

The seed command reads `DEMO_ACCOUNT_PASSWORD`; no demo password is stored in the repository. All seeded email addresses use the reserved `.invalid` domain.

Run the backend:

```bash
.venv/bin/python backend/manage.py runserver
```

Student routes require a valid session plus an `X-Organisation-Code` header matching an active institution membership. See the [backend API inventory](docs/backend-api-verification.md#institution-api) for routes, roles, and write errors.

The demo session API uses server-side sessions with a 60-minute idle timeout.

- `GET /api/v1/auth/session/` returns session state and sets the `csrftoken` cookie.
- `POST /api/v1/auth/login/` accepts JSON with `email` and `password`, then returns session state and rotates the CSRF token.
- `POST /api/v1/auth/logout/` clears the session and returns anonymous session state.

Send the current `csrftoken` cookie value in the `X-CSRFToken` header on login,
logout, and authenticated writes. Read the fresh cookie after login rotates it.
The demo limiter tracks failed logins per email and IP in one process. See the
[session contract and verification evidence](docs/backend-api-verification.md#demo-session-api).

Run the frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Checks

```bash
cd backend
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/pytest
../.venv/bin/ruff check .

cd ../frontend
npm test
npm run typecheck
npm run build
```

This prototype is not authorised for real personal data or production use.
