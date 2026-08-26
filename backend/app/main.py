"""
LinguaMate AI - Main FastAPI Application
"Your AI family member who helps you become fluent in English."
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base
import app.models  # Ensures all ORM models are registered
from app.routers import auth, conversations, tasks, progress, activities
from app.routers import pronunciation, flashcards, exchange, tests, insights

settings = get_settings()


async def _ensure_schema(conn):
    """Inspect the live DB and add any columns/tables the ORM models expect."""
    from sqlalchemy import inspect as sa_inspect, text

    inspector = sa_inspect(conn)
    existing_tables = inspector.get_table_names()

    # ── Add missing columns to existing tables ───────────────────────────
    desired_columns = {
        "users": {
            "companion": "VARCHAR(20) DEFAULT 'mira' NOT NULL",
            "xp": "INTEGER DEFAULT 0 NOT NULL",
            "target_language": "VARCHAR(50) DEFAULT 'English' NOT NULL",
        },
    }

    for table_name, columns in desired_columns.items():
        if table_name not in existing_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for col_name, col_def in columns.items():
            if col_name not in existing_cols:
                try:
                    conn.execute(text(
                        f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}'
                    ))
                except Exception:
                    pass  # Column might already exist in a race condition

    # ── Create any completely new tables ──────────────────────────────────
    Base.metadata.create_all(bind=conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(_ensure_schema)
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-powered English learning companion that talks like a caring family member",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://liguamate.vercel.app",
    ],
    allow_origin_regex=r"(http://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include Routers ─────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(tasks.router)
app.include_router(progress.router)
app.include_router(activities.router)
app.include_router(pronunciation.router)
app.include_router(flashcards.router)
app.include_router(exchange.router)
app.include_router(tests.router)
app.include_router(insights.router)


# ─── Health Check ────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.app_name,
        "status": "running",
        "message": "Welcome to LinguaMate AI! 🌟 Your AI family member for English fluency.",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
