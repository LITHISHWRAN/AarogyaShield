# AarogyaShield

**AI-powered health insurance advisor for India — grounded in real policy documents, zero hallucinations.**

AarogyaShield helps users navigate the complexity of Indian health insurance. It analyses your profile, retrieves relevant clauses from actual policy documents via RAG, and recommends the plans most likely to cover you — honestly, with citations.

---

## What it does

- **Personalised recommendations** — answer a short profile questionnaire (age, city tier, income band, pre-existing conditions) and receive ranked policy suggestions with match scores and side-by-side comparisons.
- **Grounded chat** — every answer is backed by numbered citations pointing to exact chunks in the uploaded policy PDFs. No invented facts.
- **Intent-aware conversations** — the chat distinguishes greetings, jargon lookups, policy questions, and out-of-scope requests, routing each to the right handler.
- **Admin policy management** — upload PDF/TXT/JSON policy documents; they are automatically chunked, embedded, and indexed into the vector store.
- **Hidden admin portal** — click the logo on the onboarding page five times to access the admin panel (no visible button, no URL hint).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│              React 18 + TypeScript + Vite               │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTPS / REST
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI (Python 3.11)                  │
│                                                         │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │  Auth / JWT │  │  Chat (RAG)   │  │ Recommend.    │  │
│  └─────────────┘  └───────┬───────┘  └───────┬───────┘  │
│                           │                  │           │
│  ┌────────────────────────▼──────────────────▼────────┐  │
│  │              LangChain + Gemini 2.5 Flash           │  │
│  └────────────────────────┬───────────────────────────┘  │
│                           │ vector search                 │
│  ┌──────────┐  ┌──────────▼──────┐  ┌─────────────────┐  │
│  │ Postgres │  │  Qdrant (768-d) │  │  Redis sessions │  │
│  └──────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand, React Router v6 |
| Backend | FastAPI 0.115, Python 3.11, Uvicorn, Pydantic v2 |
| LLM | Google Gemini 2.5 Flash via LangChain |
| Embeddings | Google `embedding-001` (768 dimensions) |
| Vector store | Qdrant (cosine similarity, sentence-aware 400-word chunks) |
| Database | PostgreSQL 15 + SQLAlchemy 2 (async) + Alembic |
| Cache / sessions | Redis 7 (AOF persistence, 24 h TTL) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Document parsing | pdfplumber, custom chunker with overlap |
| Infra | Docker, Docker Compose, Nginx (prod) |

---

## Getting started

### Prerequisites

- Docker and Docker Compose v2
- A [Google AI Studio](https://aistudio.google.com) API key (free tier works)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/aarogyashield.git
cd aarogyashield
cp .env.example .env
```

Edit `.env` — the minimum required changes:

```bash
APP_SECRET_KEY=        # openssl rand -hex 32
GOOGLE_API_KEY=        # from Google AI Studio
POSTGRES_PASSWORD=     # choose a strong password
REDIS_PASSWORD=        # choose a strong password
ADMIN_USERNAME=        # your admin username
ADMIN_PASSWORD_HASH=   # see step 2
```

### 2. Generate the admin password hash

```bash
python scripts/hash_password.py
# Enter your desired admin password when prompted
# Copy the printed hash into ADMIN_PASSWORD_HASH in .env
```

### 3. Start the dev stack

```bash
docker compose up
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/api/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

### 4. Upload your first policy

Go to the onboarding page and **click the logo 5 times** to open the admin panel. Upload a health insurance policy PDF to start getting recommendations.

---

## Environment variables

All variables live in `.env` (copy from `.env.example`). Key ones:

| Variable | Description |
|---|---|
| `APP_SECRET_KEY` | JWT signing secret — generate with `openssl rand -hex 32` |
| `GOOGLE_API_KEY` | Gemini API key from [Google AI Studio](https://aistudio.google.com) |
| `ADMIN_USERNAME` | Admin portal username |
| `ADMIN_PASSWORD_HASH` | bcrypt hash — generate via `scripts/hash_password.py` |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins (e.g. your Vercel URL) |
| `VITE_API_BASE_URL` | Backend URL used by the frontend (empty = same origin) |
| `LLM_MODEL` | Gemini model name (default: `gemini-2.5-flash`) |
| `LLM_TEMPERATURE` | LLM temperature (default: `0.3`) |
| `EMBEDDING_DIMENSION` | Must match your embedding model (default: `768`) |
| `REDIS_SESSION_TTL` | Chat session lifetime in seconds (default: `86400`) |

---

## API reference

### Public endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/health/ready` | Readiness check (postgres, redis, qdrant) |
| `POST` | `/api/v1/auth/register` | Register a user |
| `POST` | `/api/v1/auth/login` | User login → JWT |
| `POST` | `/api/v1/recommendations` | Get policy recommendations |
| `POST` | `/api/v1/chat/` | Send a chat message |
| `GET` | `/api/v1/chat/{session_id}/session` | Get session metadata |
| `DELETE` | `/api/v1/chat/{session_id}` | Clear chat history |
| `GET` | `/api/v1/policies` | List all indexed policies |

### Admin endpoints (Bearer token required)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/admin/login` | Admin login → short-lived JWT (8 h) |
| `POST` | `/api/v1/admin/policies/upload` | Upload and index a policy document |
| `GET` | `/api/v1/admin/policies` | List policies with metadata |
| `DELETE` | `/api/v1/admin/policies/{id}` | Delete policy from DB + vector store |

Interactive docs available at `/api/docs` (Swagger UI) and `/api/redoc`.

---

## How the RAG pipeline works

```
User profile
     │
     ▼
Multi-query builder ──► 3-4 targeted search queries
     │
     ▼
Parallel Qdrant search (top-5 per query)
     │
     ▼
Deduplicate + build numbered context [1][2][3]...
     │
     ▼
Gemini 2.5 Flash (JSON mode, temp 0.3)
     │
     ▼
Output parser ──► validate citations, scores, profile refs
     │
     ▼
RecommendationResponse (policies + match scores + source chunks)
```

The chat pipeline adds intent classification and guardrails (blocks medical advice requests, out-of-scope queries) before and after the LLM call.

---

## Deployment

### Frontend → Vercel.

### Backend → Railway

---

## Project structure

```
aarogyashield/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/v1/          # Route registration
│   │   │   ├── modules/         # auth, chat, recommendations, admin
│   │   │   ├── chat/            # orchestrator, classifier, guardrails, retriever
│   │   │   ├── recommendation/  # chains, context builder, output parser
│   │   │   ├── ingestion/       # parsers, chunker, cleaner
│   │   │   ├── memory/          # Redis-backed session store
│   │   │   ├── services/        # llm, vector, embeddings, session
│   │   │   ├── db/              # models, session, repositories
│   │   │   └── core/            # config, security, logging, dependencies
│   │   └── tests/
│   └── frontend/
│       └── src/
│           ├── features/        # onboarding, chat, recommendations, admin, dashboard
│           ├── components/      # ui, chat widgets, recommendation cards
│           ├── services/        # axios API clients
│           ├── store/           # Zustand state
│           └── types/           # TypeScript interfaces
├── scripts/
│   └── hash_password.py         # bcrypt hash generator for admin setup
├── docker-compose.yml           # Dev stack
├── docker-compose.prod.yml      # Production overrides
└── .env.example                 # All environment variables with descriptions
```

---


