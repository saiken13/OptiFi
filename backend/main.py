from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from database import create_tables, settings
from routers import auth, goals, budgets, loans, transactions, alerts, weekly_review, chat, cards, memberships, purchase, tax


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="OptiFi API",
    description="Multi-agent AI personal finance platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)

app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(budgets.router)
app.include_router(loans.router)
app.include_router(transactions.router)
app.include_router(alerts.router)
app.include_router(weekly_review.router)
app.include_router(chat.router)
app.include_router(cards.router)
app.include_router(memberships.router)
app.include_router(purchase.router)
app.include_router(tax.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "OptiFi API"}
