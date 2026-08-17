# personal-finance-ai

A small full-stack personal finance app that tracks income and spending and
generates AI-style insights (auto-categorization, spending breakdowns, and
plain-language money tips). It runs fully self-contained with **no external API
keys required** — the "AI" layer uses transparent, rule-based heuristics that can
later be swapped for an LLM behind the same interface.

## Stack

| Layer    | Tech                                             |
| -------- | ------------------------------------------------ |
| Backend  | Python 3.12, FastAPI, SQLAlchemy, SQLite         |
| Frontend | React 18, TypeScript, Vite, Recharts             |

## Project layout

```
backend/    FastAPI app (models, AI layer, REST API, sample-data seeder)
frontend/   React + Vite dashboard
.cursor/    Cloud Agent environment config + install script
```

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # seed sample transactions (idempotent)
uvicorn app.main:app --reload --port 8000
```

The API is served at `http://localhost:8000` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api to :8000)
```

## API

| Method | Path                       | Description                          |
| ------ | -------------------------- | ------------------------------------ |
| GET    | `/api/health`              | Health check                         |
| GET    | `/api/transactions`        | List transactions                    |
| POST   | `/api/transactions`        | Add a transaction (auto-categorized) |
| DELETE | `/api/transactions/{id}`   | Delete a transaction                 |
| POST   | `/api/categorize`          | Predict a category for a description |
| GET    | `/api/insights`            | Summary, breakdowns, and AI insights |

Amount convention: negative = expense, positive = income.

## Cloud Agent environment

`.cursor/environment.json` defines the environment. `.cursor/install.sh` is
idempotent and installs both backend and frontend dependencies, then the
`backend` and `frontend` terminals launch the two dev servers.
