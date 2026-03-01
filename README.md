# OptiFi — AI Personal Finance Platform

> **Chat-first financial decision platform** combining loan/goal optimization, AI card import, membership-aware purchase optimizer, weekly AI reviews, and tax insights — all powered by a multi-agent Claude AI backend.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
  - [Backend Environment Variables](#backend-environment-variables)
  - [Frontend Environment Variables](#frontend-environment-variables)
- [API Overview](#api-overview)
- [Multi-Agent System](#multi-agent-system)
- [Screenshots / Pages](#screenshots--pages)

---

## Overview

OptiFi is a full-stack AI personal finance platform where users interact primarily through a **natural language chat interface**. Behind the scenes, a multi-agent orchestrator routes each message to the right specialized AI agent — budget, goals, loans, purchase optimization, weekly review, or tax.

Users can:
- Track goals, budgets, loans, and transactions
- Import credit card reward rules automatically using AI
- Find the best card + merchant combo for any purchase (factoring in memberships like Costco, Amazon Prime)
- Get a weekly AI-generated financial review with actionable recommendations
- Ask anything in plain English and get structured, data-driven answers

---

## Key Features

| Feature | Description |
|---|---|
| **AI Chat Interface** | Natural language queries routed to specialized agents |
| **Goal Tracker** | Create and monitor savings/purchase goals with progress charts |
| **Budget Manager** | Set category budgets, track spending vs. limits |
| **Loan Optimizer** | Model loan scenarios, compare payoff strategies |
| **AI Card Import** | Paste a card URL — AI extracts reward rules automatically |
| **Purchase Optimizer** | Enter any product; finds best card + membership combo for lowest net cost |
| **Weekly AI Review** | Auto-generated weekly summary with spending analysis and tips |
| **Transaction Import** | Upload CSV bank exports; AI categorizes transactions |
| **Tax Insights** | AI-powered tax planning and deduction suggestions |
| **Smart Alerts** | Threshold-based alerts for budgets and goals |
| **Google OAuth** | Sign in with Google in addition to email/password |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                   │
│  (App Router · TypeScript · Tailwind · TanStack Query)   │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (axios, httpOnly cookies)
┌───────────────────────▼─────────────────────────────────┐
│                     FastAPI Backend                      │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Multi-Agent Orchestrator             │   │
│  │   keyword routing → LLM intent classifier        │   │
│  │                                                   │   │
│  │  budget  goal  loan  purchase  weekly_review tax  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Services: purchase_optimizer · card_import · tx_service │
│  Database: PostgreSQL (SQLAlchemy async + asyncpg)       │
└─────────────────────────────────────────────────────────┘
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
     Groq LLM      Serper API     PostgreSQL
  (LLaMA 3.3 70B) (web search)   (Supabase or self-hosted)
```

**Routing logic:** The orchestrator first tries fast keyword matching. If ambiguous, it falls back to an LLM intent classifier before dispatching to the appropriate specialized agent.

---

## Tech Stack

**Backend**
- FastAPI 0.111 · Python 3.11+
- SQLAlchemy 2.0 async + asyncpg
- PostgreSQL (Supabase recommended)
- Groq API (LLaMA 3.3 70B) for all AI inference
- Serper.dev for real-time product/merchant search
- Pydantic v2 · JWT httpOnly cookies · Authlib (Google OAuth)

**Frontend**
- Next.js 14 (App Router) · TypeScript
- Tailwind CSS · shadcn/ui components
- TanStack Query (server state) · Zustand (client state)
- Recharts (data visualization) · react-hook-form + zod
- Lucide icons

---

## Project Structure

```
OptiFi/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, middleware, router registration
│   ├── database.py              # Async engine, session factory, settings
│   ├── requirements.txt
│   ├── .env.example             # ← copy to .env and fill in values
│   ├── agents/
│   │   ├── orchestrator.py      # Routing: keywords → LLM fallback → agent dispatch
│   │   ├── base_agent.py        # BaseAgent with format_response()
│   │   ├── budget_agent.py
│   │   ├── goal_agent.py
│   │   ├── loan_agent.py
│   │   ├── purchase_agent.py
│   │   ├── weekly_review_agent.py
│   │   ├── tax_agent.py
│   │   └── general_agent.py
│   ├── routers/                 # FastAPI route handlers (auth, goals, budgets, …)
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/
│   │   ├── card_import_service.py    # AI card import pipeline
│   │   ├── purchase_optimizer.py     # Merchant search + card ranking
│   │   ├── transaction_service.py    # CSV parsing + categorization
│   │   └── notification_service.py   # OneSignal push alerts
│   └── prompts/                 # LLM system prompts
│
└── frontend/
    ├── app/
    │   ├── (auth)/              # login, register pages
    │   └── (dashboard)/         # protected app pages
    │       ├── dashboard/
    │       ├── chat/
    │       ├── goals/
    │       ├── budgets/
    │       ├── loans/
    │       ├── cards/
    │       ├── transactions/
    │       ├── purchase/
    │       ├── weekly-review/
    │       └── tax/
    ├── components/              # Reusable UI components
    ├── lib/api.ts               # All API calls (axios + withCredentials)
    ├── store/useAppStore.ts     # Zustand store
    ├── providers/               # React context providers
    └── .env.example             # ← copy to .env.local and fill in values
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A PostgreSQL database (Supabase free tier works great)
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone the repo

```bash
git clone <repo-url>
cd OptiFi
```

### 2. Backend setup

```bash
cd backend
cp .env.example .env
# Edit .env with your values (see Configuration Reference below)

pip install -r requirements.txt
uvicorn main:app --reload
# API runs at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 3. Frontend setup

```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your values

npm install
npm run dev
# App runs at http://localhost:3000
```

### 4. Verify

- Open [http://localhost:3000](http://localhost:3000) — you should see the login page
- Open [http://localhost:8000/health](http://localhost:8000/health) — should return `{"status":"ok"}`
- Register an account and start chatting

---

## Configuration Reference

### Backend Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in each value.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | **Yes** | PostgreSQL connection string. Must use `postgresql+asyncpg://` prefix. Example: `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SECRET_KEY` | **Yes** | JWT signing secret. Use a random string of 32+ characters. Never commit the real value. |
| `ALGORITHM` | No | JWT algorithm. Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token TTL in minutes. Default: `10080` (7 days) |
| `GROQ_API_KEY` | **Yes** | Groq API key for LLM inference. Get one free at [console.groq.com](https://console.groq.com). |
| `GROQ_MODEL` | No | Groq model to use. Default: `llama-3.3-70b-versatile` |
| `SERPER_API_KEY` | Recommended | Serper.dev API key for product/merchant search in the purchase optimizer. Free tier available at [serper.dev](https://serper.dev). Without this, purchase optimization falls back to mock data. |
| `FRONTEND_URL` | **Yes** | Your frontend origin for CORS. Development: `http://localhost:3000` |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID. Get from [Google Cloud Console](https://console.cloud.google.com/). Required only if you want Google sign-in. |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth client secret. Paired with `GOOGLE_CLIENT_ID`. |
| `ONESIGNAL_APP_ID` | Optional | OneSignal app ID for push notifications. In-app alerts work without this. |
| `ONESIGNAL_REST_API_KEY` | Optional | OneSignal REST key. Paired with `ONESIGNAL_APP_ID`. |
| `RESEND_API_KEY` | Optional | Resend.com API key for transactional email. Free tier: 100 emails/day. |

**Minimum required to run:** `DATABASE_URL`, `SECRET_KEY`, `GROQ_API_KEY`, `FRONTEND_URL`

### Frontend Environment Variables

Copy `frontend/.env.example` to `frontend/.env.local` and fill in each value.

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Yes** | Base URL of the backend API. Development: `http://localhost:8000`. Production: your deployed backend URL. |
| `NEXT_PUBLIC_ONESIGNAL_APP_ID` | Optional | OneSignal app ID for browser push notification prompts. Matches `ONESIGNAL_APP_ID` in backend. |

---

## API Overview

All endpoints are prefixed per their router. Full interactive docs available at `/docs` when running locally.

| Group | Endpoints |
|---|---|
| **Auth** | `POST /auth/register` · `POST /auth/login` · `GET /auth/google` · `GET /auth/me` · `POST /auth/logout` |
| **Goals** | `GET/POST /goals` · `GET/PUT/DELETE /goals/{id}` |
| **Budgets** | `GET/POST /budgets` · `GET/PUT/DELETE /budgets/{id}` |
| **Loans** | `GET/POST /loans` · `GET/PUT/DELETE /loans/{id}` |
| **Cards** | `GET/POST /cards` · Card import: `POST /cards/import/search`, `/cards/import/extract`, `/cards/import/confirm` |
| **Memberships** | `GET/POST /memberships` · `GET/PUT/DELETE /memberships/{id}` |
| **Transactions** | `GET /transactions` · `POST /transactions/upload` (CSV) |
| **Chat** | `POST /chat` · `GET /chat/history` |
| **Purchase** | `POST /purchase/optimize` |
| **Weekly Review** | `POST /weekly-review/run` · `GET /weekly-review/latest` |
| **Alerts** | `GET /alerts` · `PUT /alerts/{id}/read` |
| **Tax** | `GET /tax/insights` |
| **Health** | `GET /health` |

---

## Multi-Agent System

The chat endpoint routes each message through the orchestrator:

```
User message
     │
     ▼
Keyword matching (fast, no LLM call)
  • "budget", "spending" → BudgetAgent
  • "goal", "save for" → GoalAgent
  • "loan", "debt" → LoanAgent
  • "buy", "purchase", "best card" → PurchaseAgent
  • "weekly", "review" → WeeklyReviewAgent
  • "tax", "deduction" → TaxAgent
     │
     ▼ (ambiguous)
LLM intent classifier (Groq, single call)
     │
     ▼
Specialized Agent
  • Fetches relevant DB records for the user
  • Builds a structured prompt with user context
  • Calls Groq LLM with the prompt
  • Returns formatted markdown response
```

Each agent has access to the authenticated user's data, so responses are always personalized.

---

## Screenshots / Pages

| Page | What it does |
|---|---|
| **Chat** | Main interface — ask anything in natural language |
| **Dashboard** | Overview cards: net worth, goal progress, recent transactions, budget bars |
| **Goals** | Create/edit savings goals with target amounts and deadlines; progress charts |
| **Budgets** | Set monthly category budgets; visual spend vs. limit comparison |
| **Loans** | Track loans; model payoff scenarios |
| **Cards** | Manage credit cards; AI import wizard to auto-extract reward rules from any URL |
| **Transactions** | Upload CSV bank statements; view and filter transaction history |
| **Purchase** | Enter a product — get ranked list of merchants × cards by net cost after rewards/memberships |
| **Weekly Review** | One-click AI-generated weekly financial summary with recommendations |
| **Tax** | AI tax insights based on your transaction and income data |

---

Built with the [Groq API](https://console.groq.com), [Serper.dev](https://serper.dev), [FastAPI](https://fastapi.tiangolo.com), and [Next.js](https://nextjs.org).
