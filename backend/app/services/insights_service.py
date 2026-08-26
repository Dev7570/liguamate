"""Insights Service — Analytics computation for Conversation Intelligence Dashboard.

Computes live session stats and historical trends from existing chat data.
"""

import re
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.conversation import Conversation, Message
from app.models.vocabulary import VocabularyProgress


# Common filler words/phrases to detect
FILLER_PATTERNS = [
    r'\bum+\b', r'\buh+\b', r'\blike\b(?!\s+(?:a|the|to|it|this|that))',
    r'\byou know\b', r'\bi mean\b', r'\bbasically\b', r'\bactually\b',
    r'\bliterally\b', r'\bkind of\b', r'\bsort of\b', r'\bso+\b(?=\s*,)',
    r'\bwell\b(?=\s*,)', r'\banyway\b', r'\bhonestly\b',
]


def _count_fillers(text: str) -> int:
    """Count filler words/phrases in text."""
    count = 0
    text_lower = text.lower()
    for pattern in FILLER_PATTERNS:
        count += len(re.findall(pattern, text_lower))
    return count


def _count_unique_words(text: str) -> set:
    """Extract unique words from text (lowercase, alphabetic only)."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return set(words)


def _vocabulary_complexity_score(text: str) -> float:
    """
    Compute vocabulary complexity: ratio of unique words to total words.
    Higher = more diverse vocabulary. Range: 0.0 to 1.0.
    """
    words = re.findall(r'[a-zA-Z]+', text.lower())
    if not words:
        return 0.0
    unique = set(words)
    return round(len(unique) / len(words), 3)


def _calculate_fluency_score(
    grammar_accuracy: float,
    vocab_complexity: float,
    avg_message_length: float,
    filler_ratio: float,
) -> int:
    """
    Compute a composite fluency score (0-100) from multiple signals.
    Weights: grammar 35%, vocab diversity 25%, message length 25%, low fillers 15%.
    """
    # Normalize avg message length: 10-50 words is ideal range
    length_score = min(avg_message_length / 30.0, 1.0) if avg_message_length > 0 else 0

    # Low filler ratio is good (invert: fewer fillers = higher score)
    filler_score = max(0, 1.0 - filler_ratio * 5)  # >20% fillers = 0

    score = (
        grammar_accuracy * 0.35 +
        vocab_complexity * 0.25 +
        length_score * 0.25 +
        filler_score * 0.15
    ) * 100

    return max(0, min(100, round(score)))


async def compute_live_session_stats(
    db: AsyncSession,
    conversation_id: str,
    user_id: str,
) -> dict:
    """Compute real-time analytics for the current conversation."""

    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        return None

    # Fetch all messages in this conversation
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    if not messages:
        return {
            "conversation_id": conversation_id,
            "total_messages": 0,
            "user_messages": 0,
            "fluency_score": 0,
            "grammar_accuracy": 0,
            "vocab_complexity": 0,
            "vocab_diversity": 0,
            "avg_words_per_message": 0,
            "total_fillers": 0,
            "filler_ratio": 0,
            "mood_timeline": [],
            "message_lengths": [],
            "corrections_count": 0,
            "unique_words_used": [],
            "top_words": [],
        }

    user_messages = [m for m in messages if m.role == "user"]
    assistant_messages = [m for m in messages if m.role == "assistant"]

    # --- Text analysis on user messages ---
    all_user_text = " ".join(m.content for m in user_messages)
    all_unique_words = _count_unique_words(all_user_text)
    total_word_count = len(re.findall(r'[a-zA-Z]+', all_user_text.lower()))

    # Vocab complexity
    vocab_complexity = _vocabulary_complexity_score(all_user_text)

    # Average words per message
    msg_word_counts = []
    for m in user_messages:
        words = re.findall(r'[a-zA-Z]+', m.content)
        msg_word_counts.append(len(words))
    avg_words = round(sum(msg_word_counts) / len(msg_word_counts), 1) if msg_word_counts else 0

    # Filler count
    total_fillers = _count_fillers(all_user_text)
    filler_ratio = round(total_fillers / max(total_word_count, 1), 3)

    # Grammar accuracy (user messages that didn't trigger corrections)
    corrections_count = 0
    for m in assistant_messages:
        if m.corrections:
            corrections_count += len(m.corrections)

    msgs_with_corrections = sum(1 for m in assistant_messages if m.corrections)
    grammar_accuracy = round(
        (len(user_messages) - msgs_with_corrections) / max(len(user_messages), 1),
        3
    )

    # Mood timeline
    mood_timeline = []
    for m in assistant_messages:
        mood_timeline.append({
            "mood": m.mood_signal or "neutral",
            "timestamp": str(m.created_at),
        })

    # Message lengths over time (for sparkline)
    message_lengths = [
        {"index": i, "words": wc}
        for i, wc in enumerate(msg_word_counts)
    ]

    # Top words (most frequent, excluding common stop words)
    stop_words = {
        'i', 'me', 'my', 'we', 'you', 'your', 'he', 'she', 'it', 'they',
        'a', 'an', 'the', 'is', 'am', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can',
        'could', 'should', 'may', 'might', 'to', 'of', 'in', 'for', 'on',
        'with', 'at', 'by', 'from', 'and', 'or', 'but', 'not', 'so', 'if',
        'that', 'this', 'what', 'how', 'when', 'where', 'who', 'which',
        'there', 'here', 'just', 'also', 'very', 'really', 'about', 'some',
    }
    word_counter = Counter(re.findall(r'[a-zA-Z]+', all_user_text.lower()))
    top_words = [
        {"word": w, "count": c}
        for w, c in word_counter.most_common(30)
        if w not in stop_words and len(w) > 2
    ][:10]

    # Fluency score
    fluency_score = _calculate_fluency_score(
        grammar_accuracy, vocab_complexity, avg_words, filler_ratio
    )

    return {
        "conversation_id": conversation_id,
        "total_messages": len(messages),
        "user_messages": len(user_messages),
        "fluency_score": fluency_score,
        "grammar_accuracy": round(grammar_accuracy * 100, 1),
        "vocab_complexity": round(vocab_complexity * 100, 1),
        "vocab_diversity": len(all_unique_words),
        "avg_words_per_message": avg_words,
        "total_fillers": total_fillers,
        "filler_ratio": round(filler_ratio * 100, 1),
        "mood_timeline": mood_timeline,
        "message_lengths": message_lengths,
        "corrections_count": corrections_count,
        "unique_words_used": sorted(list(all_unique_words))[:50],
        "top_words": top_words,
    }


async def compute_historical_insights(
    db: AsyncSession,
    user_id: str,
) -> dict:
    """Compute historical analytics across all conversations."""

    # --- Get all conversations ---
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.started_at.asc())
    )
    conversations = conv_result.scalars().all()

    if not conversations:
        return {
            "total_conversations": 0,
            "total_practice_days": 0,
            "fluency_trend": [],
            "grammar_trend": [],
            "vocab_growth": [],
            "correction_categories": [],
            "activity_heatmap": [],
            "top_words": [],
            "milestones": [],
            "weekly_summary": {},
        }

    # --- Aggregate all messages ---
    msg_result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Message.created_at.asc())
    )
    all_messages = msg_result.scalars().all()

    user_msgs = [m for m in all_messages if m.role == "user"]
    assistant_msgs = [m for m in all_messages if m.role == "assistant"]

    # --- Fluency trend (per conversation) ---
    fluency_trend = []
    grammar_trend = []
    cumulative_words = set()
    vocab_growth = []

    for conv in conversations:
        conv_user_msgs = [m for m in user_msgs if m.conversation_id == conv.id]
        conv_asst_msgs = [m for m in assistant_msgs if m.conversation_id == conv.id]

        if not conv_user_msgs:
            continue

        # Text stats for this conversation
        conv_text = " ".join(m.content for m in conv_user_msgs)
        conv_unique = _count_unique_words(conv_text)
        total_words_conv = len(re.findall(r'[a-zA-Z]+', conv_text.lower()))
        word_counts = [len(re.findall(r'[a-zA-Z]+', m.content)) for m in conv_user_msgs]
        avg_wpm = sum(word_counts) / len(word_counts) if word_counts else 0

        vc = _vocabulary_complexity_score(conv_text)
        fillers = _count_fillers(conv_text)
        filler_r = fillers / max(total_words_conv, 1)

        msgs_w_corrections = sum(1 for m in conv_asst_msgs if m.corrections)
        ga = (len(conv_user_msgs) - msgs_w_corrections) / max(len(conv_user_msgs), 1)

        fs = _calculate_fluency_score(ga, vc, avg_wpm, filler_r)

        date_str = str(conv.started_at.date()) if conv.started_at else ""

        fluency_trend.append({"date": date_str, "score": fs, "conversation_id": str(conv.id)})
        grammar_trend.append({"date": date_str, "accuracy": round(ga * 100, 1)})

        # Cumulative vocab growth
        cumulative_words.update(conv_unique)
        vocab_growth.append({"date": date_str, "total_words": len(cumulative_words)})

    # --- Correction categories ---
    correction_types = Counter()
    for m in assistant_msgs:
        if m.corrections:
            for c in m.corrections:
                explanation = c.get("explanation", "").lower() if isinstance(c, dict) else ""
                if any(kw in explanation for kw in ["tense", "past", "present", "future"]):
                    correction_types["Tense"] += 1
                elif any(kw in explanation for kw in ["article", "a ", "an ", "the "]):
                    correction_types["Articles"] += 1
                elif any(kw in explanation for kw in ["preposition", "in ", "on ", "at "]):
                    correction_types["Prepositions"] += 1
                elif any(kw in explanation for kw in ["plural", "singular"]):
                    correction_types["Plurals"] += 1
                elif any(kw in explanation for kw in ["spelling", "spell"]):
                    correction_types["Spelling"] += 1
                elif any(kw in explanation for kw in ["word order", "sentence structure"]):
                    correction_types["Word Order"] += 1
                else:
                    correction_types["Other"] += 1

    correction_categories = [
        {"category": cat, "count": cnt}
        for cat, cnt in correction_types.most_common(8)
    ]

    # --- Activity heatmap (day of week × hour) ---
    activity_data = defaultdict(int)
    practice_dates = set()
    for conv in conversations:
        if conv.started_at:
            day = conv.started_at.strftime("%a")  # Mon, Tue, ...
            hour = conv.started_at.hour
            activity_data[f"{day}_{hour}"] += 1
            practice_dates.add(conv.started_at.date())

    # Build heatmap grid
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    activity_heatmap = []
    for day in days:
        for hour in range(0, 24, 3):  # 8 time slots
            count = sum(activity_data.get(f"{day}_{h}", 0) for h in range(hour, hour + 3))
            activity_heatmap.append({"day": day, "hour": hour, "count": count})

    # --- Top words across all conversations ---
    stop_words = {
        'i', 'me', 'my', 'we', 'you', 'your', 'he', 'she', 'it', 'they',
        'a', 'an', 'the', 'is', 'am', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can',
        'could', 'should', 'may', 'might', 'to', 'of', 'in', 'for', 'on',
        'with', 'at', 'by', 'from', 'and', 'or', 'but', 'not', 'so', 'if',
        'that', 'this', 'what', 'how', 'when', 'where', 'who', 'which',
        'there', 'here', 'just', 'also', 'very', 'really', 'about', 'some',
    }
    all_user_text = " ".join(m.content for m in user_msgs)
    word_counter = Counter(re.findall(r'[a-zA-Z]+', all_user_text.lower()))
    top_words = [
        {"word": w, "count": c}
        for w, c in word_counter.most_common(50)
        if w not in stop_words and len(w) > 2
    ][:15]

    # --- Milestones ---
    milestones = []
    total_user_msgs = len(user_msgs)
    total_convs = len(conversations)

    if total_convs >= 1:
        milestones.append({"icon": "🎯", "label": "First Conversation", "achieved": True})
    if total_convs >= 10:
        milestones.append({"icon": "🔥", "label": "10 Conversations", "achieved": True})
    if total_convs >= 50:
        milestones.append({"icon": "⚡", "label": "50 Conversations", "achieved": True})
    if len(cumulative_words) >= 100:
        milestones.append({"icon": "📚", "label": "100 Unique Words", "achieved": True})
    if len(cumulative_words) >= 500:
        milestones.append({"icon": "🏆", "label": "500 Unique Words", "achieved": True})
    if total_user_msgs >= 100:
        milestones.append({"icon": "💬", "label": "100 Messages Sent", "achieved": True})

    # Add upcoming milestones
    if total_convs < 10:
        milestones.append({"icon": "🔥", "label": f"10 Conversations ({total_convs}/10)", "achieved": False})
    if len(cumulative_words) < 100:
        milestones.append({"icon": "📚", "label": f"100 Unique Words ({len(cumulative_words)}/100)", "achieved": False})
    if total_user_msgs < 100:
        milestones.append({"icon": "💬", "label": f"100 Messages ({total_user_msgs}/100)", "achieved": False})

    # --- Weekly summary ---
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    this_week_convs = [c for c in conversations if c.started_at and c.started_at >= week_ago]
    this_week_msgs = [m for m in user_msgs if m.created_at and m.created_at >= week_ago]

    weekly_summary = {
        "conversations_this_week": len(this_week_convs),
        "messages_this_week": len(this_week_msgs),
        "practice_days_this_week": len({
            c.started_at.date() for c in this_week_convs if c.started_at
        }),
    }

    return {
        "total_conversations": len(conversations),
        "total_practice_days": len(practice_dates),
        "total_unique_words": len(cumulative_words),
        "fluency_trend": fluency_trend[-20:],  # Last 20 conversations
        "grammar_trend": grammar_trend[-20:],
        "vocab_growth": vocab_growth,
        "correction_categories": correction_categories,
        "activity_heatmap": activity_heatmap,
        "top_words": top_words,
        "milestones": milestones,
        "weekly_summary": weekly_summary,
    }
