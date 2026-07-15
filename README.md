# Enterprise Marketing Intelligence Platform (MISP)

![CI](https://github.com/aliyan2525/misp/actions/workflows/ci.yml/badge.svg)

A multi-tenant, full-stack business intelligence platform that ingests marketing campaign data, forecasts future performance, and generates automated optimization recommendations — with authentication, monitoring, and a containerized deployment pipeline built the way production systems actually are.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Streamlit UI    │─────▶│   FastAPI (JWT)   │─────▶│   PostgreSQL     │
│  (dashboard.py)  │ HTTP │   (main.py)       │ ORM  │   (via Alembic   │
└─────────────────┘      └──────────────────┘      │    migrations)   │
                                  │                   └─────────────────┘
                                  ├──▶ Prophet forecasting (forecasting.py)
                                  ├──▶ Rule-based recommendations (recommendations.py)
                                  ├──▶ PDF reporting (reports.py)
                                  └──▶ Sentry + structured logging (logging_config.py)
```

**Database layer** — SQLAlchemy ORM models (`models.py`) with versioned Alembic migrations, replacing hand-written SQL. Every table is scoped to an `org_id`, enforcing tenant isolation at the query level.

**Backend API (FastAPI)** — JWT auth with short-lived access tokens (15 min) and refresh tokens (7 days), rate-limited login/signup endpoints, CSV ingestion, org-scoped analytics endpoints, a Prophet-based forecasting engine, a rule-based recommendation engine, and PDF report generation.

**Frontend (Streamlit)** — a fully decoupled dashboard that talks to the API exclusively over HTTP, with automatic silent token refresh so users aren't logged out every 15 minutes.

**Monitoring** — structured logging to file + console, Sentry error tracking, and a `/health` endpoint for uptime monitoring.

## Features

- 🔐 **Multi-tenant authentication** — JWT access + refresh tokens, bcrypt password hashing, rate-limited auth endpoints, minimum password strength enforcement
- 📥 **CSV data ingestion** — validated schema, org-scoped campaign/metric storage
- 📊 **Analytics dashboard** — spend, conversions, clicks, channel breakdowns, cost-efficiency charts
- 🔮 **30-day conversion forecasting** — Prophet time-series model, scoped per organization
- 💡 **Rule-based recommendation engine** — flags zero-conversion campaigns, high-cost campaigns, top performers, and declining forecast trends
- 📄 **PDF reporting** — on-demand downloadable report combining campaign data and recommendations
- 🩺 **Monitoring** — structured logging, Sentry integration, `/health` endpoint for uptime checks
- ✅ **Automated testing** — pytest suite covering auth, multi-tenant data isolation, CSV validation, and recommendation logic, run against a real isolated test database
- 🐳 **Containerized** — Docker + docker-compose spins up Postgres, the API, and the dashboard together
- 🔄 **CI/CD** — GitHub Actions runs the full test suite against a real Postgres instance on every push

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, Plotly |
| Backend | FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy ORM, Alembic migrations |
| Auth | JWT (python-jose), bcrypt (passlib), slowapi rate limiting |
| Forecasting | Facebook Prophet |
| Reporting | ReportLab |
| Monitoring | Sentry SDK, Python logging |
| Testing | pytest, FastAPI TestClient |
| DevOps | Docker, docker-compose, GitHub Actions |

## Running the Platform

### Option A — Docker (recommended)

The whole stack — database, API, and dashboard — starts with one command.

**Prerequisites:** Docker Desktop with WSL2 (Windows) or Docker Engine (Mac/Linux).

1. Create a `.env` file in the project root:
   ```
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_NAME=misp_db
   JWT_SECRET_KEY=replace-with-a-real-secret
   SENTRY_DSN=
   ALLOWED_ORIGINS=*
   ```
2. Build and start everything:
   ```bash
   docker compose up --build
   ```
3. Open the dashboard at **http://localhost:8501** and the API docs at **http://localhost:8000/docs**.

### Option B — Manual local setup

**Prerequisites:** Python 3.11+, a running local PostgreSQL instance.

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your `.env` file (same as above, with `DB_HOST=localhost`).
3. Create the database and apply migrations:
   ```bash
   createdb misp_db
   alembic upgrade head
   ```
4. Start the backend:
   ```bash
   uvicorn main:app --reload
   ```
5. In a separate terminal, start the dashboard:
   ```bash
   streamlit run dashboard.py
   ```

## Running Tests

Tests run against a fully isolated `misp_test_db`, never against your real data.

```bash
createdb misp_test_db
pip install -r requirements-dev.txt
pytest -v
```

The same suite runs automatically on every push via GitHub Actions (see `.github/workflows/ci.yml`), spinning up a fresh Postgres instance in CI so tests never depend on local machine state.

## Project Structure

```
misp/
├── main.py                  # FastAPI app: all API endpoints
├── database.py               # SQLAlchemy engine + session dependency
├── models.py                  # ORM models (Organization, User, Campaign, DailyMetric)
├── auth.py                    # Password hashing, JWT access/refresh tokens
├── forecasting.py             # Prophet-based conversion forecasting
├── recommendations.py         # Rule-based recommendation engine
├── reports.py                  # PDF report generation
├── logging_config.py           # Structured logging setup
├── dashboard.py                # Streamlit frontend
├── alembic/                    # Versioned database migrations
├── conftest.py, test_*.py      # pytest suite
├── Dockerfile, docker-compose.yml
└── .github/workflows/ci.yml    # CI pipeline
```

## Security Notes

- All API endpoints (except `/health`, `/auth/*`) require a valid JWT and are scoped to the caller's organization — verified by an automated multi-tenancy test suite
- Passwords are hashed with bcrypt, never stored or logged in plaintext
- `/auth/login` and `/auth/signup` are rate-limited to 5 requests/minute per IP
- Secrets (`JWT_SECRET_KEY`, database credentials) are loaded from `.env`, which is git-ignored and never committed

## Roadmap / Known Limitations

- Scheduled email delivery of PDF reports (Celery + Redis) is designed but not yet automated
- Google Analytics 4 as a live data source (in addition to CSV upload) is not yet implemented
- Frontend is currently Streamlit; a React-based UI is a planned future upgrade for a more polished production feel
