"""Task Service - Daily mission generation and management"""

import uuid
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.task import DailyTask

# ─── Mission Templates by Level ─────────────────────────────────────────────

TASK_TEMPLATES = {
    "beginner": [
        {
            "type": "speaking",
            "title": "🎤 Introduce Yourself",
            "description": "Tell Mira about yourself in 3-4 sentences. Say your name, where you're from, and one thing you like.",
            "difficulty": "easy",
        },
        {
            "type": "vocab",
            "title": "📚 Learn 5 New Words",
            "description": "During today's conversations, try to use 5 words you've never used before. Mira will help you find them!",
            "difficulty": "easy",
        },
        {
            "type": "speaking",
            "title": "🏠 Describe Your Room",
            "description": "Look around your room and describe what you see to Mira. Use colors, sizes, and positions (on, next to, under).",
            "difficulty": "easy",
        },
        {
            "type": "story",
            "title": "📖 Tell a Simple Story",
            "description": "Tell Mira about something that happened to you today or yesterday. Try to use past tense correctly!",
            "difficulty": "medium",
        },
        {
            "type": "vocab",
            "title": "🍎 Food & Cooking",
            "description": "Tell Mira about your favorite food. Describe how it tastes, looks, and how it's made.",
            "difficulty": "easy",
        },
    ],
    "intermediate": [
        {
            "type": "speaking",
            "title": "🎯 2-Minute Monologue",
            "description": "Speak about any topic for 2 minutes without stopping. Don't worry about mistakes — focus on fluency!",
            "difficulty": "medium",
        },
        {
            "type": "vocab",
            "title": "✨ Upgrade Your Words",
            "description": "Replace 5 common words (good, bad, nice, big, small) with stronger alternatives in today's chats.",
            "difficulty": "medium",
        },
        {
            "type": "story",
            "title": "📺 Movie Reviewer",
            "description": "Describe the last movie or show you watched. Give your opinion — what was great, what could've been better?",
            "difficulty": "medium",
        },
        {
            "type": "speaking",
            "title": "🗺️ Dream Vacation",
            "description": "Tell Mira about your dream vacation. Where would you go? What would you do? Who would you take?",
            "difficulty": "medium",
        },
        {
            "type": "speaking",
            "title": "💼 Job Interview Practice",
            "description": "Practice answering: 'Tell me about yourself' and 'Why should we hire you?' with Mira.",
            "difficulty": "hard",
        },
    ],
    "advanced": [
        {
            "type": "speaking",
            "title": "🎙️ 5-Minute Presentation",
            "description": "Present a topic you're passionate about to Mira for 5 minutes. Structure it with an intro, body, and conclusion.",
            "difficulty": "hard",
        },
        {
            "type": "vocab",
            "title": "🧠 Academic Vocabulary",
            "description": "Use 5 academic or formal words today: 'consequently', 'furthermore', 'nevertheless', 'whereas', 'subsequently'.",
            "difficulty": "hard",
        },
        {
            "type": "speaking",
            "title": "⚖️ Debate Time",
            "description": "Pick a controversial topic and argue both sides with Mira. Practice using evidence and counterarguments.",
            "difficulty": "hard",
        },
        {
            "type": "story",
            "title": "✍️ Story Builder",
            "description": "Build a story with Mira! She starts, you continue, she continues — use advanced narrative techniques.",
            "difficulty": "hard",
        },
        {
            "type": "speaking",
            "title": "📰 News Discussion",
            "description": "Discuss a current event with Mira. Express your opinion, analyze causes, and predict outcomes.",
            "difficulty": "hard",
        },
    ],
}

DAILY_TASK_COUNT = 4  # Tasks per day


async def generate_daily_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    english_level: str,
    task_date: date | None = None,
) -> list[DailyTask]:
    """Generate daily tasks for a user based on their level."""
    target_date = task_date or date.today()

    # Check if tasks already exist for today
    result = await db.execute(
        select(DailyTask).where(
            DailyTask.user_id == user_id,
            DailyTask.task_date == target_date,
        )
    )
    existing = result.scalars().all()
    if existing:
        return existing

    # Get templates for user's level
    templates = TASK_TEMPLATES.get(english_level, TASK_TEMPLATES["beginner"])

    # Pick tasks (rotate through templates based on day-of-year)
    import hashlib
    seed = int(hashlib.md5(f"{user_id}{target_date}".encode()).hexdigest()[:8], 16)
    import random
    rng = random.Random(seed)
    selected = rng.sample(templates, min(DAILY_TASK_COUNT, len(templates)))

    tasks = []
    for template in selected:
        task = DailyTask(
            user_id=user_id,
            task_date=target_date,
            task_type=template["type"],
            title=template["title"],
            description=template["description"],
            difficulty=template["difficulty"],
        )
        db.add(task)
        tasks.append(task)

    await db.flush()
    return tasks


async def complete_task(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    performance_notes: str | None = None,
) -> DailyTask | None:
    """Mark a task as completed."""
    result = await db.execute(
        select(DailyTask).where(
            DailyTask.id == task_id,
            DailyTask.user_id == user_id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.completed = True
    task.completed_at = datetime.now(timezone.utc)
    task.performance_notes = performance_notes
    await db.flush()
    return task


async def get_task_context_for_prompt(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> str | None:
    """Get today's pending tasks formatted for the AI prompt."""
    result = await db.execute(
        select(DailyTask).where(
            DailyTask.user_id == user_id,
            DailyTask.task_date == date.today(),
            DailyTask.completed == False,
        )
    )
    pending = result.scalars().all()
    if not pending:
        return None

    lines = [f"Pending tasks for today:"]
    for t in pending:
        lines.append(f"- {t.title}: {t.description}")
    return "\n".join(lines)


async def get_completion_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """Get task completion statistics."""
    # Today's stats
    result = await db.execute(
        select(DailyTask).where(
            DailyTask.user_id == user_id,
            DailyTask.task_date == date.today(),
        )
    )
    today_tasks = result.scalars().all()

    # Total completed ever
    result = await db.execute(
        select(func.count(DailyTask.id)).where(
            DailyTask.user_id == user_id,
            DailyTask.completed == True,
        )
    )
    total_completed = result.scalar() or 0

    return {
        "today_total": len(today_tasks),
        "today_completed": sum(1 for t in today_tasks if t.completed),
        "total_completed": total_completed,
    }
