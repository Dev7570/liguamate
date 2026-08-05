"""Memory Service - Long-term memory storage and search compatible with both SQLite & PostgreSQL"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import numpy as np

from app.models.memory import Memory
from app.utils.embeddings import generate_embedding


async def store_memory(
    db: AsyncSession,
    user_id: str,
    fact_text: str,
    category: str | None = None,
    importance: int = 3,
) -> Memory:
    """Store a new memory fact with its embedding list."""
    embedding = None
    try:
        embedding = await generate_embedding(fact_text)
    except Exception:
        pass

    memory = Memory(
        user_id=str(user_id),
        fact_text=fact_text,
        category=category,
        importance=importance,
        embedding=embedding,
    )
    db.add(memory)
    await db.flush()
    return memory


async def search_memories(
    db: AsyncSession,
    user_id: str,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Semantic search for relevant memories using cosine similarity."""
    result = await db.execute(
        select(Memory).where(
            Memory.user_id == str(user_id),
            Memory.is_active == True,
        )
    )
    memories = result.scalars().all()
    if not memories:
        return []

    try:
        query_vec = np.array(await generate_embedding(query))
        scored = []
        for m in memories:
            if m.embedding:
                m_vec = np.array(m.embedding)
                denom = (np.linalg.norm(query_vec) * np.linalg.norm(m_vec))
                score = np.dot(query_vec, m_vec) / denom if denom > 0 else 0
                scored.append((score, m))
            else:
                scored.append((0, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_memories = [m for score, m in scored[:limit]]
    except Exception:
        top_memories = memories[:limit]

    # Update last_referenced_at
    if top_memories:
        memory_ids = [m.id for m in top_memories]
        await db.execute(
            update(Memory)
            .where(Memory.id.in_(memory_ids))
            .values(last_referenced_at=datetime.now(timezone.utc))
        )

    return [
        {
            "fact": m.fact_text,
            "category": m.category,
            "importance": m.importance,
            "created_at": str(m.created_at),
        }
        for m in top_memories
    ]


async def deactivate_old_memories(
    db: AsyncSession,
    user_id: str,
    category: str,
    keep_id: str,
):
    """Deactivate older memories in the same category."""
    await db.execute(
        update(Memory)
        .where(
            Memory.user_id == str(user_id),
            Memory.category == category,
            Memory.id != str(keep_id),
            Memory.is_active == True,
        )
        .values(is_active=False)
    )


async def get_all_active_memories(
    db: AsyncSession,
    user_id: str,
) -> list[dict]:
    """Get all active memories for a user."""
    result = await db.execute(
        select(Memory)
        .where(Memory.user_id == str(user_id), Memory.is_active == True)
        .order_by(Memory.created_at.desc())
    )
    memories = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "fact": m.fact_text,
            "category": m.category,
            "importance": m.importance,
            "created_at": str(m.created_at),
        }
        for m in memories
    ]
