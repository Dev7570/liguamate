"""Chat Service - The core message pipeline that orchestrates everything.

Every message flows through this pipeline:
1. Fetch recent turns from session/DB
2. Semantic search for relevant long-term memories
3. Get today's task context
4. Build system prompt with all context
5. Call LLM → get natural reply + learning signals
6. Store message, corrections, vocab, and new memories
7. Return reply to user
"""

import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.conversation import Conversation, Message
from app.models.user import User
from app.services.ai_service import build_system_prompt, generate_reply, generate_reply_stream
from app.services.memory_service import search_memories, store_memory, deactivate_old_memories
from app.services.vocab_service import track_vocabulary
from app.services.task_service import get_task_context_for_prompt
from app.schemas.chat import LearningSignals


async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    channel: str = "text",
) -> Conversation:
    """Start a new conversation session."""
    conversation = Conversation(
        user_id=user_id,
        channel=channel,
    )
    db.add(conversation)
    await db.commit()
    return conversation


async def process_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
    user_message: str,
) -> dict:
    """
    THE CORE PIPELINE — process a user message and return the AI response.

    This is where the magic happens. One user message triggers:
    - Memory search (semantic)
    - Recent turn retrieval
    - Task context loading
    - LLM call with full context
    - Signal extraction (corrections, vocab, memories, mood)
    - Storage of everything

    Returns a dict with the AI reply and metadata.
    """

    # ── Step 1: Store the user's message ─────────────────────────────────────
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.commit()

    # ── Step 2: Fetch recent conversation turns ──────────────────────────────
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    recent_messages = result.scalars().all()
    recent_turns = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent_messages)
    ]

    # ── Step 3: Search long-term memories ────────────────────────────────────
    memories = []
    try:
        memories = await search_memories(db, user.id, user_message, limit=5)
    except Exception:
        # If memory search fails (e.g., pgvector not set up), continue without
        pass

    # ── Step 4: Get today's task context ─────────────────────────────────────
    task_context = None
    try:
        task_context = await get_task_context_for_prompt(db, user.id)
    except Exception:
        pass

    # ── Step 5: Build system prompt ──────────────────────────────────────────
    system_prompt = build_system_prompt(
        user_name=user.name,
        english_level=user.english_level,
        goal=user.goal,
        memories=memories,
        recent_turns=recent_turns,
        task_context=task_context,
    )

    # ── Step 6: Call the LLM ─────────────────────────────────────────────────
    reply_text, learning_signals = await generate_reply(system_prompt, user_message)

    # ── Step 7: Store the AI's reply ─────────────────────────────────────────
    corrections_json = None
    if learning_signals.corrections:
        corrections_json = [
            {"original": c.original, "corrected": c.corrected, "explanation": c.explanation}
            for c in learning_signals.corrections
        ]

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply_text,
        corrections=corrections_json,
        vocab_used=learning_signals.vocab_used or [],
        mood_signal=learning_signals.mood_signal,
    )
    db.add(assistant_msg)
    await db.commit()

    # ── Step 8: Store new memories ───────────────────────────────────────────
    for mem in learning_signals.new_memories:
        try:
            new_memory = await store_memory(
                db,
                user.id,
                fact_text=mem.get("fact", ""),
                category=mem.get("category"),
                importance=mem.get("importance", 3),
            )
            # Deactivate older memories in the same category if this is a "replacing" fact
            if mem.get("category"):
                await deactivate_old_memories(
                    db, user.id, mem["category"], new_memory.id
                )
        except Exception:
            # Don't let memory storage failures break the response
            pass

    # ── Step 9: Track vocabulary ─────────────────────────────────────────────
    if learning_signals.vocab_used:
        try:
            await track_vocabulary(db, user.id, learning_signals.vocab_used)
        except Exception:
            pass

    await db.commit()

    # ── Step 10: Return the response ─────────────────────────────────────────
    return {
        "id": str(assistant_msg.id),
        "role": "assistant",
        "content": reply_text,
        "corrections": corrections_json,
        "vocab_used": learning_signals.vocab_used,
        "mood_signal": learning_signals.mood_signal,
        "vocabulary_suggestions": learning_signals.vocabulary_suggestions,
        "created_at": str(assistant_msg.created_at),
    }


async def end_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation | None:
    """End a conversation session and generate a summary."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        return None

    # Get message count for summary
    msg_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    msg_count = msg_result.scalar() or 0

    conversation.ended_at = datetime.now(timezone.utc)
    conversation.summary = f"Conversation with {msg_count} messages"
    await db.commit()

    return conversation


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        return False
        
    await db.delete(conversation)
    await db.commit()
    return True


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[Message]:
    """Get all messages in a conversation."""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        return []

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


async def get_user_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[dict]:
    """Get a user's conversation list with message counts."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.started_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()

    conv_list = []
    for conv in conversations:
        msg_result = await db.execute(
            select(func.count(Message.id)).where(
                Message.conversation_id == conv.id
            )
        )
        msg_count = msg_result.scalar() or 0

        conv_list.append({
            "id": str(conv.id),
            "channel": conv.channel,
            "started_at": str(conv.started_at),
            "ended_at": str(conv.ended_at) if conv.ended_at else None,
            "summary": conv.summary,
            "message_count": msg_count,
        })

    return conv_list


async def process_message_stream(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user: User,
    user_message: str,
):
    """
    Streaming version of process_message — yields SSE event dicts.

    Events:
      {"type": "token", "content": "..."}      — live text token
      {"type": "done", "message_id": "...", ...} — final metadata
    """

    # ── Step 1: Store & commit the user's message immediately ────────────────
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    await db.commit()

    # ── Step 2: Fetch recent conversation turns ──────────────────────────────
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    recent_messages = result.scalars().all()
    recent_turns = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent_messages)
    ]

    # ── Step 3: Search long-term memories ────────────────────────────────────
    memories = []
    try:
        memories = await search_memories(db, user.id, user_message, limit=5)
    except Exception:
        pass

    # ── Step 4: Get today's task context ─────────────────────────────────────
    task_context = None
    try:
        task_context = await get_task_context_for_prompt(db, user.id)
    except Exception:
        pass

    # ── Step 5: Build system prompt ──────────────────────────────────────────
    system_prompt = build_system_prompt(
        user_name=user.name,
        english_level=user.english_level,
        goal=user.goal,
        memories=memories,
        recent_turns=recent_turns,
        task_context=task_context,
    )

    # ── Step 6: Stream LLM reply ─────────────────────────────────────────────
    full_reply = ""
    learning_signals = LearningSignals()

    async for event in generate_reply_stream(system_prompt, user_message):
        if event["type"] == "token":
            yield event  # Forward token to client

        elif event["type"] == "done":
            full_reply = event["content"]
            try:
                learning_signals = LearningSignals(**event["learning_signals"])
            except Exception:
                pass

    # ── Step 7: Store the AI's reply ─────────────────────────────────────────
    corrections_json = None
    if learning_signals.corrections:
        corrections_json = [
            {"original": c.original, "corrected": c.corrected, "explanation": c.explanation}
            for c in learning_signals.corrections
        ]

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=full_reply,
        corrections=corrections_json,
        vocab_used=learning_signals.vocab_used or [],
        mood_signal=learning_signals.mood_signal,
    )
    db.add(assistant_msg)
    await db.commit()

    # ── Step 8: Store new memories ───────────────────────────────────────────
    for mem in learning_signals.new_memories:
        try:
            new_memory = await store_memory(
                db,
                user.id,
                fact_text=mem.get("fact", ""),
                category=mem.get("category"),
                importance=mem.get("importance", 3),
            )
            if mem.get("category"):
                await deactivate_old_memories(
                    db, user.id, mem["category"], new_memory.id
                )
        except Exception:
            pass

    # ── Step 9: Track vocabulary ─────────────────────────────────────────────
    if learning_signals.vocab_used:
        try:
            await track_vocabulary(db, user.id, learning_signals.vocab_used)
        except Exception:
            pass

    await db.commit()

    # ── Step 10: Yield final "done" event with metadata ──────────────────────
    yield {
        "type": "done",
        "message_id": str(assistant_msg.id),
        "content": full_reply,
        "corrections": corrections_json,
        "vocab_used": learning_signals.vocab_used,
        "mood_signal": learning_signals.mood_signal,
        "vocabulary_suggestions": learning_signals.vocabulary_suggestions,
        "created_at": str(assistant_msg.created_at),
    }

