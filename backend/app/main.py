"""
LinguaMate AI - Main FastAPI Application
"Your AI family member who helps you become fluent in English."
"""

import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base
import app.models  # Ensures all ORM models are registered
from app.routers import auth, conversations, tasks, progress, activities
from app.routers import pronunciation, flashcards, exchange, tests, insights

logger = logging.getLogger("linguamate")
settings = get_settings()

# Store startup schema info for debugging
_startup_info = {"status": "pending", "errors": [], "tables": [], "columns": {}}


 def _ensure_schema(conn):
    """Inspect the live DB and add any columns/tables the ORM models expect."""
    from sqlalchemy import inspect as sa_inspect, text

    inspector = sa_inspect(conn)
    existing_tables = inspector.get_table_names()
    _startup_info["tables"] = list(existing_tables)

    # ── Add missing columns to existing tables ───────────────────────────
    # PostgreSQL-safe: DEFAULT must come before NOT NULL
    desired_columns = {
        "users": {
            "companion": "VARCHAR(20) DEFAULT 'mira'",
            "xp": "INTEGER DEFAULT 0",
            "target_language": "VARCHAR(50) DEFAULT 'English'",
        },
        "vocabulary_progress": {
            "next_review_at": "TIMESTAMP WITH TIME ZONE",
            "interval": "INTEGER DEFAULT 1",
            "ease_factor": "DOUBLE PRECISION DEFAULT 2.5",
        },
    }

    for table_name, columns in desired_columns.items():
        if table_name not in existing_tables:
            logger.info(f"Table {table_name} does not exist yet, skipping ALTER")
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        _startup_info["columns"][table_name] = list(existing_cols)
        for col_name, col_def in columns.items():
            if col_name not in existing_cols:
                sql = f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}'
                try:
                    conn.execute(text(sql))
                    logger.info(f"Added column: {sql}")
                    _startup_info["errors"].append(f"OK: {sql}")
                except Exception as e:
                    msg = f"WARN ALTER: {sql} -> {e}"
                    logger.warning(msg)
                    _startup_info["errors"].append(msg)

    # ── Create any completely new tables ──────────────────────────────────
    try:
        Base.metadata.create_all(bind=conn)
        _startup_info["status"] = "ok"
    except Exception as e:
        msg = f"create_all failed: {e}"
        logger.error(msg)
        _startup_info["status"] = f"error: {msg}"
        _startup_info["errors"].append(msg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_ensure_schema)
    except Exception as e:
        _startup_info["status"] = f"lifespan_error: {e}"
        _startup_info["errors"].append(traceback.format_exc())
        logger.error(f"Schema setup failed: {e}")
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


# ─── Temporary Debug Endpoint (remove after fixing) ─────────────────────────
@app.get("/debug/schema", tags=["Debug"])
async def debug_schema():
    """Temporary endpoint to diagnose DB schema issues on production."""
    from sqlalchemy import inspect as sa_inspect, text
    from app.database import engine as db_engine

    result = {"startup_info": _startup_info, "current_schema": {}, "test_query": None}
    try:
        async with db_engine.connect() as conn:
            def inspect_db(sync_conn):
                inspector = sa_inspect(sync_conn)
                tables = inspector.get_table_names()
                schema = {}
                for t in tables:
                    cols = inspector.get_columns(t)
                    schema[t] = [c["name"] for c in cols]
                return schema
            result["current_schema"] = await conn.run_sync(inspect_db)
    except Exception as e:
        result["current_schema"] = f"Error: {e}"

    # Try a simple user query to reproduce the exact error
    try:
        async with db_engine.connect() as conn:
            row = await conn.execute(text("SELECT * FROM users LIMIT 1"))
            cols = list(row.keys()) if row else []
            result["test_query"] = {"status": "ok", "columns_returned": cols}
    except Exception as e:
        result["test_query"] = {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

    return result
