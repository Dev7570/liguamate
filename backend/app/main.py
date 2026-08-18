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
from app.routers import pronunciation, flashcards, exchange, tests

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
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
