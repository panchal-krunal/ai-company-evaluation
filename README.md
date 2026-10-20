# Company Evaluation Platform

A research dashboard where an analyst reviews an NSE/BSE-listed non-financial company, checks its financial and qualitative information, traces every finding back to a source document, adds comments, and approves or overrides the evaluation.

The system automates collecting filings, standardising data and calculating metrics. The analyst still interprets the results and makes the final investment decision.

> Scope and plan come from *Company Evaluation Platform Management Proposal* (`../Company_Evaluation_Platform_Management_Proposal_Final.docx`), a 3-month MVP in 7 phases.

## MVP scope at a glance

- **10 modules:** Management Outlook · Products & Segments · Industry Outlook · Competitors · Debt Structure · RPT · Financial Warning Checks · Growth Analysis · Company Risks · Why Not Invest
- **8 warning checks:** debt · working capital · operating cash flow · promoter holding/pledging · RPT · dilution · tax/dividend · RoCE. Each returns `clear` / `watch` / `flag`.
- **Traceability:** each figure and conclusion links to its source document, reporting period, filing date and consolidated/standalone basis.
- **First release:** 20–25 companies, 5 years of annual data, 12 quarters, 3 years of RPT data, 12 quarters of shareholding data, and 5–8 competitors per company.

## Architecture principle

Financial arithmetic (CAGR, margins, debt ratios, cash conversion, warning thresholds) lives in **deterministic, unit-tested code** in `backend/app/modules/financial_engine`. The LLM **extracts and interprets evidence** from source passages, with citations. It is never the source of truth for any number.

```
React + TS dashboard ──► FastAPI (modular monolith) ──► PostgreSQL + pgvector
                                 │                         ▲
                                 └─► Redis queue ─► arq worker ── S3 (raw filings, immutable)
                                                       │
                                                       └─► Claude (RAG research) + Voyage (embeddings)
```

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript 6, Vite 8, Tailwind CSS 4, TanStack Query & Table, React Router 8, React Hook Form + Zod 4, Recharts |
| Frontend tests | Vitest 5, Testing Library, Playwright |
| Backend | Python 3.14, FastAPI, Pydantic 2, SQLAlchemy 2 (async) + asyncpg, Alembic |
| Data / AI | Pandas 3, pgvector, Anthropic SDK (Claude Opus 5.5), Voyage AI embeddings, pdfplumber / pypdf |
| Jobs | arq + Redis |
| Storage | PostgreSQL 18 + pgvector, AWS S3 for source documents |
| Tooling | uv, ruff, mypy (strict), pytest, ESLint 10, Prettier |
| Delivery | GitHub Actions; AWS hosting (RDS + S3) to be decided in Phase 7 |

## Repository layout

```
company-evaluation-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/      # health, companies, warnings (more per phase)
│   │   ├── core/               # settings, DB session, logging
│   │   ├── models/             # companies, filings, source docs, financial facts, chunks, evaluations, audit
│   │   ├── modules/
│   │   │   ├── ingestion/      # PDF extraction, chunking, S3 storage
│   │   │   ├── financial_engine/  # deterministic metrics + 8 warning checks
│   │   │   ├── ownership/      # debt, shareholding, pledging, dilution, RPT (phase 4)
│   │   │   ├── research/       # embeddings, retrieval, Claude structured research
│   │   │   ├── workflow/       # comments, overrides, approvals (phase 6)
│   │   │   └── reporting/      # evaluation export (phase 6)
│   │   ├── providers/          # data-vendor adapter interface
│   │   ├── main.py             # FastAPI app
│   │   └── worker.py           # arq background worker
│   ├── alembic/                # migrations
│   └── tests/{unit,integration}
├── frontend/
│   ├── src/{app,components,features,lib,test}
│   └── e2e/                    # Playwright
└── .github/workflows/ci.yml
```

## Getting started

### Prerequisites

- **Python 3.14** and **[uv](https://docs.astral.sh/uv/)**
- **Node.js 24.13.0 LTS** (`nvm use` reads `frontend/.nvmrc`). Vite 8 and Vitest 5 need Node ≥ 22.12, so Node 20 won't work.
- **PostgreSQL 18 + pgvector** and **Redis**, installed with Homebrew (no Docker)

### 1. Start local services

Homebrew's pgvector supports only PostgreSQL 17 and 18. Run Postgres 18 on **port 5433** so it stays separate from any other Postgres already on 5432:

```bash
brew install postgresql@18 pgvector redis

# Run Postgres 18 on port 5433
sed -i '' 's/^#\{0,1\}port = .*/port = 5433/' /opt/homebrew/var/postgresql@18/postgresql.conf
brew services start postgresql@18
brew services start redis            # only needed for the background worker

# Create the app user and database
/opt/homebrew/opt/postgresql@18/bin/psql -p 5433 -d postgres \
  -c "CREATE ROLE evaluation LOGIN PASSWORD 'evaluation';" \
  -c "CREATE DATABASE evaluation OWNER evaluation;"
/opt/homebrew/opt/postgresql@18/bin/psql -p 5433 -d evaluation -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Source documents are stored in `backend/storage/objects/` locally (`STORAGE_BACKEND=local`); UAT and production use S3 (`STORAGE_BACKEND=s3`).

If your database was created before 6 Oct 2026, apply the one-off schema patch:
`psql -p 5433 -d evaluation -f backend/alembic/manual/2026_10_06_research_workflow.sql`

### 2. Backend

```bash
cd backend
# .env is already set up for localhost (copy .env.example if it's missing).
# Fill in API keys only after the LLM data-handling policy is approved.
uv sync                       # creates .venv and installs all dependencies from uv.lock
uv run fastapi dev app/main.py              # http://localhost:8000/docs (creates missing tables on startup)
uv run arq app.worker.WorkerSettings        # in a second terminal
```

### 3. Load data and documents

```bash
cd backend
uv run python -m scripts.load_seed data/seeds/ather_energy.json   # repeat for each file in data/seeds/
uv run python -m scripts.load_peers                               # 21 peer companies + peer links
uv run python -m scripts.ingest_documents                         # store PDFs, extract text, embed (needs VOYAGE_API_KEY)
```

### 4. Turn on AI research

Add the keys to `backend/.env` (never commit them):

```bash
ANTHROPIC_API_KEY=...   # Claude, for the research modules
VOYAGE_API_KEY=...      # embeddings, for retrieving passages
```

Then embed the documents and run the AI modules, in one go per company or for all of them:

```bash
uv run python -m scripts.ingest_documents             # embeds the passages extracted earlier
uv run python -m scripts.run_research --all           # new evaluation per company, all 10 modules
uv run python -m scripts.run_research --evaluation <id>   # or re-run AI modules on an existing evaluation
```

Or press **Run AI research** on an evaluation page. Restart the backend after editing `.env`.

### 5. Frontend

```bash
cd frontend
npm install                   # .env is already set up for localhost
npm run dev                   # http://localhost:5173 (proxies /api to :8000)
npm run gen:api               # optional: generate TS types from the FastAPI OpenAPI schema
```

## How an evaluation works

| Module | How it is produced | Needs |
|---|---|---|
| Financial Warning Checks | 8 rule-based checks on stored figures | Financial data |
| Growth Analysis | Calculated from stored figures | Financial data |
| Competitors | Latest-year metrics vs peer median and rank | Peer data |
| Debt Structure | Debt metrics in code + borrowing lines extracted from the annual report | Figures; AI for borrowings |
| Related Party Transactions | Lines extracted from the annual report; totals computed in code and fed back into the RPT warning check | AI |
| Management Outlook, Products & Segments, Industry Outlook, Company Risks | Retrieval over the company's documents + Claude, with quotes | AI |
| Why Not Invest | Rule-based concerns from all modules, plus an AI narrative | AI for the narrative |

Every AI claim must quote a retrieved passage; the quote is checked in code against that passage, and a claim
without a verified quote is shown struck through as **unsupported**. Extracted amounts only count when the printed
figure appears in the quote, and unit conversion (lakh / crore / million) is done in code.

Analysts (name entered in the header until login exists) can comment on any module, override a conclusion with a
required reason, submit for review, return to draft, and approve. Approval locks the evaluation. Every action is in
the audit trail, and evaluations export as Markdown or JSON.

## Quality checks

| | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Lint | `uv run ruff check .` | `npm run lint` |
| Format | `uv run ruff format .` | `npm run format` |
| Types | `uv run mypy app` | `npm run typecheck` |
| Unit / integration | `uv run pytest` (integration tests use `TEST_DATABASE_URL`, default local `evaluation_test`) | `npm test` |
| E2E | — | `npm run test:e2e` |

CI (`.github/workflows/ci.yml`) runs all of the above on every PR. UAT deployment, smoke tests and the production approval gate get wired up in Phase 7.

## Delivery phases

| Phase | Weeks | Focus | Status |
|---|---|---|---|
| 1. Rules & Architecture | 1 | Formulas, thresholds, source priority, data model | Done; thresholds still placeholders pending sign-off |
| 2. Data Foundation | 2–3 | Company master, filings, storage, ingestion | Done: 4 companies + 21 peers, 14 filings ingested (text extracted; embeddings need VOYAGE_API_KEY) |
| 3. Financial Engine | 4–5 | Normalisation, growth, margins, 8 warnings | Done |
| 4. Ownership & Transactions | 6 | Debt, shareholding, pledging, dilution, RPT | Done (debt metrics live; borrowing and RPT extraction run with the AI keys) |
| 5. Research + RAG | 7–8 | Evidence-backed research, Why Not Invest | Built and tested with fake AI clients; runs live once keys are added |
| 6. Analyst Dashboard | 9–10 | Modules, comments, overrides, approvals, audit, export | Done (login still to add) |
| 7. Validation & Production | 11–12 | 20–25 companies, hardening, AWS deploy, UAT | Not started |

## Decisions still open (from the proposal)

These need sign-off before the matching code can be finished:

1. First 20–25 companies and their sectors
2. Approved warning formulas and thresholds (`financial_engine/warnings.py` uses **placeholders** until then)
3. Data provider and commercial data rights (implement `providers/base.py::MarketDataProvider`)
4. Final evaluation/approval format
5. Financial-domain reviewer for UAT
6. LLM provider and data-handling policy (the default config uses Claude Opus 5.5 with server-side refusal fallback)
7. AWS environment and security ownership

## Conventions

- Raw source documents are **immutable**. They're content-addressed by SHA-256, so unchanged files are never re-processed.
- Formulas, thresholds and prompts are **versioned** (`FORMULA_VERSION`, `PROMPT_VERSION`), and each evaluation records the versions it used.
- Every AI claim carries verbatim evidence, and an unsupported claim is marked `supported: false`, never presented as fact.
- Banks, NBFCs and insurers get **separate rule templates**. Normal-company debt, working-capital and RoCE rules must not be applied to them.
- Never commit secrets. Use `.env` locally and AWS Secrets Manager for UAT and production.
