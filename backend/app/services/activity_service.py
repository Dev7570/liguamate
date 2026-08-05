"""Activity Service - Quizzes, Roleplay Scenarios, and Badges/XP System"""

import random
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.vocabulary import VocabularyProgress
from app.models.conversation import Conversation, Message
from app.models.task import DailyTask

# ─── Curated Roleplay Scenarios ─────────────────────────────────────────────

SCENARIOS = [
    {
        "id": "coffee_shop",
        "title": "The Coffee Shop Order",
        "emoji": "☕",
        "category": "Daily Life",
        "difficulty": "Easy",
        "description": "Order your favorite drink and a snack at a trendy cafe in London. Customize your order and practice polite ordering phrases!",
        "initial_prompt": "Welcome to Bean & Bloom Cafe! ☕ What can I get started for you today?",
        "context_instruction": "You are a friendly barista at a high-end London coffee shop. Roleplay as the barista. Respond politely, ask clarifying questions (milk choice, size, name for cup), and encourage natural, friendly conversation."
    },
    {
        "id": "job_interview",
        "title": "Tech Job Interview",
        "emoji": "💼",
        "category": "Career",
        "difficulty": "Medium",
        "description": "Practice answering common interview questions for your dream role with hiring manager Mira. Show off your skills and confidence!",
        "initial_prompt": "Thanks for taking the time to meet with us today! To start off, could you tell me a little bit about yourself and your background?",
        "context_instruction": "You are a supportive but professional hiring manager interviewing the candidate. Roleplay as the interviewer. Ask thoughtful follow-up questions about their experience, problem solving, and why they want this role."
    },
    {
        "id": "airport_help",
        "title": "Airport Connection Emergency",
        "emoji": "✈️",
        "category": "Travel",
        "difficulty": "Medium",
        "description": "Your flight was delayed and you have 20 minutes to reach your connecting flight! Ask the airline clerk for help navigating the terminal.",
        "initial_prompt": "Hello there! You look a bit rushed. How can I assist you today at the customer service desk?",
        "context_instruction": "You are a helpful airport customer service agent at JFK Airport. Roleplay as the agent. Help the user rebook or hurry to their gate, practice giving directions, and keep them calm and clear."
    },
    {
        "id": "road_trip",
        "title": "Road Trip Plan Negotiation",
        "emoji": "🚗",
        "category": "Social",
        "difficulty": "Hard",
        "description": "You and Mira are planning a weekend road trip. Convince her to visit your favorite destination and decide on activities together!",
        "initial_prompt": "I'm so excited for our weekend trip! I was thinking we should head to the beach, but what destination do you have in mind?",
        "context_instruction": "You are Mira, planning a fun weekend road trip with your friend (the user). Practice negotiating, expressing preferences, suggesting activities, and using convincing, enthusiastic English!"
    }
]

# ─── Achievements & Badges Definition ───────────────────────────────────────

BADGES_DEFINITION = [
    {
        "id": "first_chat",
        "name": "First Steps",
        "emoji": "🎯",
        "description": "Send your first message to Mira",
        "check": lambda stats: stats["total_messages"] >= 1
    },
    {
        "id": "chat_master",
        "name": "Chatterbox",
        "emoji": "🗣️",
        "description": "Send 25 messages in conversations",
        "check": lambda stats: stats["total_messages"] >= 25
    },
    {
        "id": "vocab_builder",
        "name": "Vocab Explorer",
        "emoji": "📚",
        "description": "Learn at least 10 new vocabulary words",
        "check": lambda stats: stats["total_words"] >= 10
    },
    {
        "id": "quiz_whiz",
        "name": "Quiz Master",
        "emoji": "🧠",
        "description": "Score 100% on a Word Master quiz",
        "check": lambda stats: stats["perfect_quizzes"] >= 1
    },
    {
        "id": "streak_3",
        "name": "Streak Starter",
        "emoji": "🔥",
        "description": "Maintain a 3-day learning streak",
        "check": lambda stats: stats["streak"] >= 3
    },
    {
        "id": "level_5",
        "name": "Fluent Scholar",
        "emoji": "👑",
        "description": "Reach Level 5 (500+ XP)",
        "check": lambda stats: stats["xp"] >= 500
    }
]

# ─── Quiz Generator ──────────────────────────────────────────────────────────

CURATED_QUIZ_POOL = [
    {
        "id": 1,
        "type": "synonym",
        "question": "Which word is a richer synonym for 'VERY GOOD'?",
        "options": ["Outstanding", "Tired", "Slow", "Ordinary"],
        "correct": 0,
        "explanation": "'Outstanding' means exceptionally good or distinguished!"
    },
    {
        "id": 2,
        "type": "fill_blank",
        "question": "Choose the correct phrase: 'I am looking forward ___ you soon.'",
        "options": ["to see", "to seeing", "for see", "seeing"],
        "correct": 1,
        "explanation": "'Look forward to' is followed by a gerund (verb + -ing)."
    },
    {
        "id": 3,
        "type": "idiom",
        "question": "What does the idiom 'Break a leg' mean?",
        "options": ["Get injured", "Good luck", "Run fast", "Stop talking"],
        "correct": 1,
        "explanation": "'Break a leg' is a well-known English idiom used to wish someone good luck!"
    },
    {
        "id": 4,
        "type": "vocab",
        "question": "Select the correct word: 'Her proposal was so ___ that everyone agreed immediately.'",
        "options": ["persuasive", "hesitant", "reluctant", "vague"],
        "correct": 0,
        "explanation": "'Persuasive' means convincing or able to persuade."
    },
    {
        "id": 5,
        "type": "grammar",
        "question": "Which sentence is grammatically correct?",
        "options": [
            "She have been working here for two years.",
            "She has been working here for two years.",
            "She is work here since two years.",
            "She worked here for since two years."
        ],
        "correct": 1,
        "explanation": "Use 'has been working' (present perfect continuous) with 'for' to describe an action continuing to the present."
    },
    {
        "id": 6,
        "type": "synonym",
        "question": "What is a natural synonym for 'HAPPY' when feeling extremely joyful?",
        "options": ["Thrilled", "Anxious", "Gloomy", "Perplexed"],
        "correct": 0,
        "explanation": "'Thrilled' means extremely pleased and excited!"
    },
    {
        "id": 7,
        "type": "fill_blank",
        "question": "Complete the sentence: 'Despite ___ tired, she finished her presentation.'",
        "options": ["of being", "being", "she was", "that she"],
        "correct": 1,
        "explanation": "'Despite' is followed directly by a noun or gerund (-ing form)."
    }
]


async def generate_quiz_questions(db: AsyncSession, user_id: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate 5 dynamic quiz questions blending user's vocabulary and curated challenges."""
    # Fetch user vocabulary if available
    result = await db.execute(
        select(VocabularyProgress)
        .where(VocabularyProgress.user_id == user_id)
        .limit(10)
    )
    user_words = [v.word for v in result.scalars().all()]

    questions = random.sample(CURATED_QUIZ_POOL, min(count, len(CURATED_QUIZ_POOL)))
    
    # Customize one question if user has tracked vocabulary
    if user_words and len(questions) > 0:
        target_word = random.choice(user_words)
        questions[0] = {
            "id": 99,
            "type": "user_vocab",
            "question": f"You recently practiced the word '{target_word.upper()}'. What is the best way to use it in conversation?",
            "options": [
                f"Using '{target_word}' confidently in active conversation!",
                f"Avoiding '{target_word}' because it's too complex.",
                f"Only using '{target_word}' in writing.",
                f"Substituting '{target_word}' with 'thing'."
            ],
            "correct": 0,
            "explanation": f"Awesome job using '{target_word}' in your chats with Mira! Keep practicing it!"
        }

    return questions

async def generate_match_game(db: AsyncSession, user_id: str, count: int = 6) -> List[Dict[str, Any]]:
    """Generate pairs for the Word Match game."""
    result = await db.execute(
        select(VocabularyProgress)
        .where(VocabularyProgress.user_id == user_id)
        .order_by(func.random())
        .limit(count)
    )
    user_words = result.scalars().all()
    
    pairs = [{"word": w.word, "meaning": w.meaning, "id": w.id} for w in user_words]
    
    # Fill remaining with curated if not enough user words
    if len(pairs) < count:
        curated = [
            {"id": 101, "word": "Ephemeral", "meaning": "Lasting for a very short time"},
            {"id": 102, "word": "Serendipity", "meaning": "Finding something good without looking for it"},
            {"id": 103, "word": "Eloquent", "meaning": "Fluent or persuasive in speaking or writing"},
            {"id": 104, "word": "Resilient", "meaning": "Able to withstand or recover quickly from difficult conditions"},
            {"id": 105, "word": "Ubiquitous", "meaning": "Present, appearing, or found everywhere"},
            {"id": 106, "word": "Pragmatic", "meaning": "Dealing with things sensibly and realistically"}
        ]
        needed = count - len(pairs)
        random.shuffle(curated)
        pairs.extend(curated[:needed])
        
    return pairs

async def generate_fill_blanks_game(db: AsyncSession, user_id: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate Fill-in-the-Blanks game rounds."""
    curated = [
        {
            "id": 201,
            "sentence": "The CEO's _____ speech convinced the investors to fund the project.",
            "options": ["eloquent", "hesitant", "quiet", "confusing"],
            "correct": 0
        },
        {
            "id": 202,
            "sentence": "Despite the storm, the _____ community quickly rebuilt their homes.",
            "options": ["fragile", "resilient", "tired", "weak"],
            "correct": 1
        },
        {
            "id": 203,
            "sentence": "Smartphones have become _____ in modern society.",
            "options": ["rare", "ubiquitous", "obsolete", "expensive"],
            "correct": 1
        },
        {
            "id": 204,
            "sentence": "Her _____ approach to problem-solving saved the company time and money.",
            "options": ["pragmatic", "dreamy", "careless", "random"],
            "correct": 0
        },
        {
            "id": 205,
            "sentence": "The beauty of a sunset is _____, lasting only a few minutes.",
            "options": ["ephemeral", "permanent", "eternal", "boring"],
            "correct": 0
        }
    ]
    random.shuffle(curated)
    return curated[:count]

async def process_quiz_submission(db: AsyncSession, user: User, score: int, total: int) -> Dict[str, Any]:
    """Process quiz results, award XP, update level, and check badge unlocks."""
    xp_earned = score * 20  # 20 XP per correct answer
    if score == total:
        xp_earned += 50  # 50 bonus XP for perfect score!

    user.xp = (user.xp or 0) + xp_earned
    await db.commit()

    # Calculate Level
    current_level = (user.xp // 100) + 1

    return {
        "score": score,
        "total": total,
        "xp_earned": xp_earned,
        "total_xp": user.xp,
        "current_level": current_level,
        "is_perfect": score == total
    }


async def get_user_achievements(db: AsyncSession, user: User) -> Dict[str, Any]:
    """Calculate user's level, XP, and status for all badges."""
    # Calculate stats
    msg_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.user_id == user.id, Message.role == "user")
    )
    total_messages = msg_result.scalar() or 0

    vocab_result = await db.execute(
        select(func.count(VocabularyProgress.id))
        .where(VocabularyProgress.user_id == user.id)
    )
    total_words = vocab_result.scalar() or 0

    # Streak calculation
    from app.routers.progress import _calculate_streak
    streak = await _calculate_streak(db, user.id)

    stats = {
        "total_messages": total_messages,
        "total_words": total_words,
        "perfect_quizzes": 1 if user.xp >= 100 else 0,
        "streak": streak,
        "xp": user.xp or 0
    }

    unlocked_badges = []
    locked_badges = []

    for b in BADGES_DEFINITION:
        is_unlocked = b["check"](stats)
        badge_data = {
            "id": b["id"],
            "name": b["name"],
            "emoji": b["emoji"],
            "description": b["description"],
            "unlocked": is_unlocked
        }
        if is_unlocked:
            unlocked_badges.append(badge_data)
        else:
            locked_badges.append(badge_data)

    current_xp = user.xp or 0
    level = (current_xp // 100) + 1
    xp_in_level = current_xp % 100

    titles = [
        "Novice Explorer", "Curious Learner", "Fluent Explorer",
        "Vocab Strategist", "Grammar Master", "Eloquent Speaker", "Mira's Best Friend"
    ]
    title = titles[min(level - 1, len(titles) - 1)]

    return {
        "level": level,
        "title": title,
        "total_xp": current_xp,
        "xp_in_level": xp_in_level,
        "next_level_xp": 100,
        "unlocked_count": len(unlocked_badges),
        "total_badges": len(BADGES_DEFINITION),
        "badges": unlocked_badges + locked_badges
    }
