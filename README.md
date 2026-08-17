# personal-finance-ai

An AI-assisted personal finance app. Upload bank/credit-card statements and get
automatic categorization, spending breakdowns, and plain-language insights.

This repository implements **Phase 1 (Foundation)** of the
[project plan](#roadmap): a multi-user foundation with statement ingestion and a
modern dashboard. The AI layer is currently transparent, rule-based heuristics
(no external keys required); later phases swap in LLM-assisted categorization and
a LangGraph multi-agent advisory system behind the same interfaces.

## Stack

| Layer    | Tech                                                        |
| -------- | ----------------------------------------------------------- |
| Backend  | Python 3.12 · FastAPI · SQLAlchemy · **PostgreSQL + pgvector** |
| Auth     | JWT (OAuth2 bearer) with strict per-user data isolation     |
| Ingestion| CSV parsing/normalization via pandas                        |
| Frontend | React 18 · TypeScript · Vite · **Tailwind + shadcn/ui** · Recharts |

## Project layout

```
backend/    FastAPI app: auth, accounts, transactions, uploads, insights
frontend/   React + Vite + shadcn/ui dashboard
.cursor/    Cloud Agent environment (install.sh, start.sh, environment.json)
```

## Run on your own computer

Cross-platform (macOS / Windows / Linux). Prerequisites: **Python 3.12+**,
**Node 20+**, and **Docker Desktop** (the easiest way to get PostgreSQL +
pgvector without installing Postgres yourself).

```bash
git clone <repo-url>
cd personal-finance-ai
git checkout cursor/scaffold-personal-finance-ai-env-7441
```

### 1. Start PostgreSQL (with pgvector)

```bash
docker compose up -d           # starts Postgres 16 + pgvector on :5432
```

Already have PostgreSQL installed and prefer not to use Docker? Instead create
the role/db manually and skip this step:

```sql
CREATE ROLE finance LOGIN PASSWORD 'finance';
CREATE DATABASE finance OWNER finance;
\c finance
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional; defaults already work
python -m app.seed                 # create demo user + sample data (idempotent)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs at `http://localhost:8000/docs`.

### 3. Frontend (in a second terminal)

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173 (proxies /api to :8000)
```

Open `http://localhost:5173` and sign in with the demo login below.

> On Linux you can alternatively run `bash .cursor/install.sh`, which installs
> Postgres + pgvector via `apt` and both stacks in one step (needs `sudo`).

### Demo login

`demo@financeai.app` / `demo1234` — pre-filled on the sign-in screen. A sample
statement to try the upload flow lives at `backend/sample_statement.csv`.

## API

| Method | Path                       | Description                              |
| ------ | -------------------------- | ---------------------------------------- |
| POST   | `/api/auth/register`       | Create account, returns JWT              |
| POST   | `/api/auth/login`          | Log in, returns JWT                      |
| GET    | `/api/auth/me`             | Current user                             |
| GET    | `/api/accounts`            | List accounts (scoped to user)          |
| POST   | `/api/uploads`             | Upload a CSV statement (multipart)       |
| GET    | `/api/transactions`        | List transactions (filters: category, account) |
| POST   | `/api/transactions`        | Add a transaction (auto-categorized)     |
| DELETE | `/api/transactions/{id}`   | Delete a transaction                     |
| GET    | `/api/insights`            | Summary, breakdowns, and insights        |

All data endpoints require a bearer token and are isolated by `user_id`.
Amount convention: negative = spending, positive = income.

## Roadmap

Phase 1 (this repo): foundation — Postgres data model, JWT auth, CSV ingestion,
dashboard. Later phases add PDF parsing, LLM-assisted extraction, a LangGraph
analytics/advisory multi-agent system, and Personal/Knowledge RAG over pgvector.

## Cloud Agent environment

`.cursor/environment.json` defines the environment. `.cursor/install.sh`
(idempotent) installs Python venv tooling, PostgreSQL + pgvector, sets up the
`finance` database, and installs backend + frontend deps. `.cursor/start.sh`
starts PostgreSQL on each boot, then the `backend` and `frontend` terminals run
the dev servers.
