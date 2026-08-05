"""Activities Router - Games, Quizzes, Scenarios, and Achievements API"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.activity_service import (
    SCENARIOS,
    generate_quiz_questions,
    process_quiz_submission,
    get_user_achievements,
    generate_match_game,
    generate_fill_blanks_game,
)

router = APIRouter(prefix="/activities", tags=["Activities"])


class QuizSubmitRequest(BaseModel):
    score: int
    total: int


@router.get("/quiz")
async def get_quiz(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dynamic 5-question Word Master quiz."""
    questions = await generate_quiz_questions(db, current_user.id, count=5)
    return {"questions": questions}


@router.post("/quiz/submit")
async def submit_quiz(
    request: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit quiz results and claim XP rewards."""
    result = await process_quiz_submission(
        db, current_user, request.score, request.total
    )
    return result

@router.get("/games/match")
async def get_match_game(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pairs for Word Match game."""
    pairs = await generate_match_game(db, current_user.id)
    return {"pairs": pairs}

@router.get("/games/blanks")
async def get_blanks_game(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get sentences for Fill-in-the-Blanks game."""
    rounds = await generate_fill_blanks_game(db, current_user.id)
    return {"rounds": rounds}

@router.get("/scenarios")
async def get_scenarios(
    current_user: User = Depends(get_current_user),
):
    """Get list of available roleplay scenarios."""
    return {"scenarios": SCENARIOS}


@router.get("/achievements")
async def get_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's XP, level, and badge achievement status."""
    achievements = await get_user_achievements(db, current_user)
    return achievements
