# Horseracing Student Record Management System

Synthetic-data, non-production prototype for the four prospective education tenants named in [`School Admin Project Master Plan.md`](<School Admin Project Master Plan.md>). BHA is represented separately as an oversight organisation. No institution has approved or adopted this software.

## Task 001 scope

- Django 5.2/DRF backend with custom users, organisations, memberships, unverified persons, and minimal student records.
- Authenticated, read-only tenant-scoped student list/detail API.
- Idempotent synthetic seed command for BRS, SRA, NHC, The National Stud, BHA, demo role accounts, and one fictional student per school.
- Minimal Vite/React/TypeScript shell.
- Local PostgreSQL Compose service and CI checks.

Later-phase workflows are intentionally absent.

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

The API requires authentication plus an `X-Organisation-Code` header matching an active institution membership:

- `GET /api/v1/students/`
- `GET /api/v1/students/{uuid}/`

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
