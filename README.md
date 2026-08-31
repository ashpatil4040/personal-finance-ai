# personal-finance-ai

An AI-assisted personal finance app. Upload bank/credit-card statements and get
automatic categorization, spending breakdowns, and plain-language insights.

This repository implements **Phases 1–5** of the [project plan](#roadmap): a
multi-user foundation, statement ingestion (CSV and PDF), a LangGraph multi-agent
advisory system (analytics, anomaly, research), Personal RAG over your
transactions, and Knowledge RAG + web search. Insights and anomaly detection are
deterministic; **categorization** uses OpenAI when a key is provided and falls
back to transparent keyword rules otherwise. PDF ingestion likewise has an
**optional LLM-assisted fallback** (OpenAI) for messy formats.
Everything runs with no external keys — the LLM features simply activate when
`PFAI_LLM_ENABLED=true` and `OPENAI_API_KEY` are set.

## Stack

| Layer    | Tech                                                        |
| -------- | ----------------------------------------------------------- |
| Backend  | Python 3.12 · FastAPI · SQLAlchemy · **PostgreSQL + pgvector** |
| Auth     | JWT (OAuth2 bearer) with strict per-user data isolation     |
| Ingestion| CSV (pandas) + PDF (pdfplumber), optional LLM fallback (OpenAI) |
| AI agents | LangGraph multi-agent graph (analytics, anomaly, research, advisor) via OpenAI |
| Personal RAG | Transaction embeddings in pgvector (OpenAI) for semantic search |
| Knowledge RAG | Curated finance notes in pgvector + DuckDuckGo/Wikipedia web search |
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
| POST   | `/api/uploads`             | Upload a CSV or PDF statement (multipart) |
| GET    | `/api/transactions`        | List transactions (filters: category, account) |
| POST   | `/api/transactions`        | Add a transaction (auto-categorized)     |
| DELETE | `/api/transactions/{id}`   | Delete a transaction                     |
| GET    | `/api/insights`            | Summary, breakdowns, and insights        |
| POST   | `/api/ask`                 | Ask a natural-language question (multi-agent router) |
| GET    | `/api/digest`              | Proactive monthly digest (movers + recommendations) |
| GET    | `/api/anomalies`           | Unusual activity: duplicates, outliers, new merchants |

All data endpoints require a bearer token and are isolated by `user_id`.
Amount convention: negative = spending, positive = income.

## Roadmap

- **Phase 1** ✅ — foundation: Postgres data model, JWT auth, CSV ingestion, dashboard.
- **Phase 2** ✅ — ingestion intelligence: PDF statement parsing (pdfplumber), optional LLM extraction fallback, and LLM-assisted categorization (OpenAI).
- **Phase 3** ✅ (analytics agent) — a LangGraph ReAct agent answers natural-language questions grounded in your real transactions, via tools: `get_spending_summary`, `query_transactions`, and `calculate_savings_scenario`. Ask from the "Ask AI" tab.
- **Phase 4** ✅ (advisory + Personal RAG) — transaction embeddings in **pgvector** power a `search_similar_transactions` tool for fuzzy/semantic questions, plus a **proactive monthly digest** (`/api/digest`) with month-over-month movers and grounded recommendations, shown on the dashboard. Embeddings/narrative use OpenAI when enabled; the digest degrades to deterministic analysis without a key.
- **Phase 5** ✅ (multi-agent + anomalies + Knowledge RAG) — a LangGraph **router** sends each question to a specialist (analytics, anomaly, research, or general advisor). Deterministic **anomaly/fraud-style detection** (`/api/anomalies`) flags duplicate charges, amount outliers, and first-time large merchants (no key required) and is also an agent tool. **Knowledge RAG** retrieves curated personal-finance notes from pgvector, and a **web search** tool (DuckDuckGo Instant Answer + Wikipedia) covers current rates and news. Without a key, Ask AI stays disabled; anomalies, keyword knowledge search, and web search still work.

### Enabling the LLM fallback (optional)

PDF parsing works without any keys. To turn on the OpenAI fallback for
statements the heuristic parser can't read, set these environment variables and
restart the backend:

```bash
PFAI_LLM_ENABLED=true
OPENAI_API_KEY=sk-...          # standard OpenAI key
# optional: PFAI_OPENAI_MODEL=gpt-4o-mini
```

## Cloud Agent environment

`.cursor/environment.json` defines the environment. `.cursor/install.sh`
(idempotent) installs Python venv tooling, PostgreSQL + pgvector, sets up the
`finance` database, and installs backend + frontend deps. `.cursor/start.sh`
starts PostgreSQL on each boot, then the `backend` and `frontend` terminals run
the dev servers.
