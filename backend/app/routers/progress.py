"""Progress Router - Dashboard and vocabulary tracking API"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.vocabulary import VocabularyProgress
from app.schemas.progress import VocabItemResponse, DashboardResponse
from app.services.vocab_service import get_user_vocabulary, get_vocabulary_stats
from app.services.task_service import get_completion_stats
from app.utils.auth import get_current_user

router = APIRouter(prefix="/progress", tags=["Progress"])

# Encouragement messages based on stats
ENCOURAGEMENTS = [
    "You're building something amazing — one conversation at a time! 🌟",
    "Every word you learn is a step closer to fluency. Keep going! 💪",
    "I've noticed real improvement in your English. You should be proud! 🎉",
    "Consistency is your superpower. You're doing great! 🔥",
    "Your vocabulary is growing beautifully. I love chatting with you! 😊",
    "Remember — even native speakers make mistakes. You're doing wonderfully! ✨",
    "The fact that you show up every day? That's what makes the difference! 🏆",
]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the main dashboard with all progress stats."""

    # Total conversations
    conv_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.user_id == current_user.id
        )
    )
    total_conversations = conv_result.scalar() or 0

    # Total messages sent by user
    msg_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(
            Conversation.user_id == current_user.id,
            Message.role == "user",
        )
    )
    total_messages = msg_result.scalar() or 0

    # Vocabulary stats
    vocab_stats = await get_vocabulary_stats(db, current_user.id)

    # Task stats
    task_stats = await get_completion_stats(db, current_user.id)

    # Calculate streak (simplified — count consecutive days with conversations)
    streak = await _calculate_streak(db, current_user.id)

    # Get recent corrections
    recent_corrections = await _get_recent_corrections(db, current_user.id, limit=5)

    # Pick encouragement based on stats
    import hashlib
    from datetime import date
    seed = int(hashlib.md5(f"{current_user.id}{date.today()}".encode()).hexdigest()[:8], 16)
    encouragement = ENCOURAGEMENTS[seed % len(ENCOURAGEMENTS)]

    return DashboardResponse(
        total_conversations=total_conversations,
        total_messages_sent=total_messages,
        total_words_learned=vocab_stats["total_words"],
        words_mastered=vocab_stats["mastered"],
        current_streak=streak,
        tasks_completed_today=task_stats["today_completed"],
        tasks_total_today=task_stats["today_total"],
        recent_corrections=recent_corrections,
        encouragement=encouragement,
    )


@router.get("/vocabulary", response_model=list[VocabItemResponse])
async def get_vocabulary(
    mastery: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's vocabulary list with mastery levels."""
    vocab = await get_user_vocabulary(db, current_user.id, mastery_filter=mastery)
    return [
        VocabItemResponse(
            word=v.word,
            times_used=v.times_used,
            mastery_level=v.mastery_level,
            first_seen_at=str(v.first_seen_at),
            last_used_at=str(v.last_used_at),
        )
        for v in vocab
    ]


async def _calculate_streak(db: AsyncSession, user_id) -> int:
    """Calculate the current conversation streak in days."""
    from datetime import timedelta
    result = await db.execute(
        select(Conversation.started_at)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.started_at.desc())
    )
    dates = [row[0].date() for row in result.all()]
    if not dates:
        return 0

    dates = sorted(list(set(dates)), reverse=True)
    streak = 0
    current_date = datetime.now(timezone.utc).date()

    # If they haven't chatted today or yesterday, streak is 0
    if dates[0] < current_date - timedelta(days=1):
        return 0

    for i in range(len(dates)):
        expected_date = current_date - timedelta(days=i if dates[0] == current_date else i + 1)
        if dates[i] == expected_date:
            streak += 1
        else:
            break

    return streak


@router.get("/leaderboard")
async def get_leaderboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get top 10 users by XP for the leaderboard."""
    result = await db.execute(
        select(User.id, User.name, User.avatar_emoji, User.xp, User.english_level)
        .order_by(User.xp.desc())
        .limit(10)
    )
    users = result.all()
    
    leaderboard = []
    for rank, u in enumerate(users, 1):
        leaderboard.append({
            "rank": rank,
            "id": str(u.id),
            "name": u.name,
            "avatar_emoji": u.avatar_emoji,
            "xp": u.xp,
            "level": (u.xp // 100) + 1 if u.xp else 1,
            "english_level": u.english_level
        })
        
    return {"leaderboard": leaderboard}


async def _get_recent_corrections(db: AsyncSession, user_id, limit: int = 5) -> list[dict]:
    """Get recent grammar corrections from messages."""
    result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(
            Conversation.user_id == user_id,
            Message.role == "assistant",
            Message.corrections.isnot(None),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()

    corrections = []
    for msg in messages:
        if msg.corrections:
            for c in msg.corrections:
                corrections.append({
                    "original": c.get("original", ""),
                    "corrected": c.get("corrected", ""),
                    "explanation": c.get("explanation", ""),
                    "date": str(msg.created_at),
                })
    return corrections[:limit]
