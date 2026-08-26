"""Insights Router — Conversation Intelligence API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.insights_service import (
    compute_live_session_stats,
    compute_historical_insights,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/live/{conversation_id}")
async def get_live_insights(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time analytics for the current conversation session.

    Returns fluency score, grammar accuracy, vocabulary complexity,
    mood timeline, filler count, message length trends, and top words.
    """
    stats = await compute_live_session_stats(db, conversation_id, str(current_user.id))
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or unauthorized",
        )
    return stats


@router.get("/history")
async def get_historical_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical analytics across all conversations.

    Returns fluency trend, grammar trend, vocabulary growth curve,
    correction categories, activity heatmap, top words, and milestones.
    """
    return await compute_historical_insights(db, str(current_user.id))
