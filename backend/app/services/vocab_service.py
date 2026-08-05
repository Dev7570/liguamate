"""Vocabulary Service - Track word usage and mastery progression"""

import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.vocabulary import VocabularyProgress


async def track_vocabulary(
    db: AsyncSession,
    user_id: uuid.UUID,
    words: list[str],
):
    """Update vocabulary tracking for words used in a conversation turn."""
    for word in words:
        word_lower = word.lower().strip()
        if len(word_lower) < 3:  # Skip very short words
            continue

        # Check if word already exists
        result = await db.execute(
            select(VocabularyProgress).where(
                VocabularyProgress.user_id == user_id,
                VocabularyProgress.word == word_lower,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update usage count and mastery
            new_count = existing.times_used + 1
            new_mastery = existing.mastery_level
            if new_count >= 10:
                new_mastery = "mastered"
            elif new_count >= 4:
                new_mastery = "learning"

            # SuperMemo-2 simplified logic for successful recall (using it in chat = success)
            new_ease = max(1.3, existing.ease_factor + 0.1)
            
            if existing.times_used == 0:
                new_interval = 1
            elif existing.times_used == 1:
                new_interval = 6
            else:
                new_interval = int(round(existing.interval * existing.ease_factor))
                
            new_next_review = datetime.now(timezone.utc) + timedelta(days=new_interval)

            await db.execute(
                update(VocabularyProgress)
                .where(VocabularyProgress.id == existing.id)
                .values(
                    times_used=new_count,
                    mastery_level=new_mastery,
                    last_used_at=datetime.now(timezone.utc),
                    interval=new_interval,
                    ease_factor=new_ease,
                    next_review_at=new_next_review,
                )
            )
        else:
            # New word
            vocab = VocabularyProgress(
                user_id=user_id,
                word=word_lower,
                times_used=1,
                mastery_level="new",
                interval=1,
                ease_factor=2.5,
                next_review_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            db.add(vocab)

    await db.flush()


async def get_user_vocabulary(
    db: AsyncSession,
    user_id: uuid.UUID,
    mastery_filter: str | None = None,
) -> list[VocabularyProgress]:
    """Get a user's vocabulary list, optionally filtered by mastery level."""
    query = select(VocabularyProgress).where(
        VocabularyProgress.user_id == user_id
    )
    if mastery_filter:
        query = query.where(VocabularyProgress.mastery_level == mastery_filter)
    # SRS: Sort by words that are due soonest
    query = query.order_by(VocabularyProgress.next_review_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_vocabulary_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict:
    """Get vocabulary statistics for a user."""
    result = await db.execute(
        select(VocabularyProgress).where(VocabularyProgress.user_id == user_id)
    )
    all_vocab = result.scalars().all()

    return {
        "total_words": len(all_vocab),
        "new_words": sum(1 for v in all_vocab if v.mastery_level == "new"),
        "learning": sum(1 for v in all_vocab if v.mastery_level == "learning"),
        "mastered": sum(1 for v in all_vocab if v.mastery_level == "mastered"),
    }
