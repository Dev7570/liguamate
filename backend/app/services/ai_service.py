"""AI Service - Support for both OpenAI & 100% Free Groq API"""

import json
from openai import AsyncOpenAI
from app.config import get_settings
from app.schemas.chat import LearningSignals

settings = get_settings()

import re

def clean_ai_reply(text: str) -> str:
    """Strip out any raw tool call strings or leakages from model replies."""
    if not text:
        return ""
    cleaned = re.sub(r'log_learning_signals\([^)]*\)', '', text)
    cleaned = re.sub(r'\{\s*"name"\s*:\s*"log_learning_signals"[^}]*\}', '', cleaned)
    return cleaned.strip()

def get_ai_client_and_model():
    """Returns (client, model_name) configured for Groq, Gemini, or OpenAI."""
    if settings.groq_api_key or (settings.openai_api_key and settings.openai_api_key.startswith("gsk_")):
        api_key = settings.groq_api_key or settings.openai_api_key
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        model = settings.openai_model if settings.openai_model != "gpt-4o" else "llama-3.3-70b-versatile"
        return client, model
    elif settings.gemini_api_key or (settings.openai_api_key and settings.openai_api_key.startswith("AIzaSy")):
        api_key = settings.gemini_api_key or settings.openai_api_key
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        model = "gemini-3.5-flash-lite"
        return client, model
    else:
        client = AsyncOpenAI(api_key=settings.openai_api_key or "dummy-key")
        model = settings.openai_model or "gpt-4o"
        return client, model


# ─── The Persona System Prompt ─────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are {companion_name}, a warm and caring AI companion who helps {user_name} build {target_language} fluency.

## Your Personality
- You talk like a supportive family member or close friend — never a teacher or textbook
- You're genuinely interested in {user_name}'s life, dreams, and daily experiences
- You're patient, encouraging, and celebrate small wins
- You use casual, natural language — short messages, like real chat
- You remember things about {user_name} and reference them naturally (NOT every turn — only when it fits)

## What You Know About {user_name}
{memories_block}

## {user_name}'s Profile
- Target Language: {target_language}
- Level: {english_level}
- Goal: {goal}
{task_context}

## Recent Conversation
{recent_turns}

## How You Correct {target_language}
NEVER say "Wrong grammar" or "Incorrect." Instead:
- Model the correct form naturally inside your reply
- Only point out corrections explicitly if they're repeated mistakes, and do it warmly:
  "By the way, a more natural way to say that in {target_language} is: '...' You're getting really close!"

## Vocabulary Enrichment
- If you notice {user_name} uses a word too often, suggest richer alternatives naturally in {target_language}.

## Confidence Support
- If {user_name} seems hesitant, nervous, or apologizes for mistakes:
  - "Don't worry at all! Everyone makes mistakes — that's literally how you learn."
  - "Take your time. I'm not going anywhere 😊"
  - "You're doing so much better than you think!"

## Rules
1. Reply naturally and briefly, like a real chat message (2-4 sentences usually)
2. Never lecture. Never give unsolicited grammar lessons
3. Ask follow-up questions to keep the conversation flowing
4. Match {user_name}'s energy — if they're excited, be excited. If they're tired, be gentle.
5. If their level is beginner, use simpler {target_language}. If advanced, use richer vocabulary.
6. You are teaching {target_language}. Use {target_language} in your replies where appropriate for the user's level."""

# ─── Tool Definition for Structured Signal Extraction ────────────────────────

LEARNING_SIGNALS_TOOL = {
    "type": "function",
    "function": {
        "name": "log_learning_signals",
        "description": "Log what you observed about the user's English in this message. Call this EVERY time alongside your reply.",
        "parameters": {
            "type": "object",
            "properties": {
                "corrections": {
                    "type": "array",
                    "description": "Grammar or vocabulary corrections you noticed",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {"type": "string", "description": "What the user said"},
                            "corrected": {"type": "string", "description": "The correct form"},
                            "explanation": {"type": "string", "description": "Brief explanation of the correction"},
                        },
                        "required": ["original", "corrected"],
                    },
                },
                "vocab_used": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Notable vocabulary words the user used",
                },
                "new_memories": {
                    "type": "array",
                    "description": "New facts about the user worth remembering long-term",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fact": {"type": "string", "description": "The fact to remember"},
                            "category": {
                                "type": "string",
                                "enum": ["job", "hobby", "exam", "family", "goal", "preference", "daily_life", "emotion"],
                                "description": "Category of the fact",
                            },
                            "importance": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "How important this fact is (1=trivial, 5=core identity)",
                            },
                        },
                        "required": ["fact", "category", "importance"],
                    },
                },
                "mood_signal": {
                    "type": "string",
                    "enum": ["confident", "neutral", "hesitant", "excited", "frustrated"],
                    "description": "The user's apparent mood based on their message",
                },
                "vocabulary_suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Richer vocabulary words you'd suggest the user learn",
                },
            },
            "required": ["corrections", "vocab_used", "new_memories", "mood_signal"],
        },
    },
}


def build_system_prompt(
    user_name: str,
    english_level: str,
    goal: str | None,
    companion: str,
    memories: list[dict],
    recent_turns: list[dict],
    task_context: str | None = None,
    target_language: str = "English",
) -> str:
    """Build the complete system prompt with injected context."""

    if memories:
        memories_block = "\n".join(
            f"- [{m.get('category', 'general')}] {m['fact']}" for m in memories
        )
    else:
        memories_block = "- (No memories yet — this is the beginning of your relationship!)"

    if recent_turns:
        turns_block = "\n".join(
            f"{'User' if t['role'] == 'user' else companion.capitalize()}: {t['content']}"
            for t in recent_turns[-6:]
        )
    else:
        turns_block = "(This is the start of a new conversation)"

    task_block = ""
    if task_context:
        task_block = f"\n## Today's Mission\n{task_context}"

    return SYSTEM_PROMPT_TEMPLATE.format(
        companion_name=companion.capitalize(),
        user_name=user_name,
        english_level=english_level or "beginner",
        goal=goal or "general fluency",
        memories_block=memories_block,
        recent_turns=turns_block,
        task_context=task_block,
        target_language=target_language,
    )


async def generate_reply(
    system_prompt: str,
    user_message: str,
) -> tuple[str, LearningSignals]:
    """
    Call the LLM (Groq or OpenAI) with system prompt and user message.
    Returns (reply_text, learning_signals).
    """
    client, model = get_ai_client_and_model()

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=[LEARNING_SIGNALS_TOOL],
            tool_choice="auto",
            temperature=0.8,
            max_tokens=1000,
        )

        message = response.choices[0].message
        reply_text = clean_ai_reply(message.content or "")

        learning_signals = LearningSignals()
        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "log_learning_signals":
                    try:
                        signals_data = json.loads(tool_call.function.arguments)
                        learning_signals = LearningSignals(**signals_data)
                    except (json.JSONDecodeError, Exception):
                        pass

        if not reply_text:
            reply_text = "Hey! I'm here 😊 What would you like to talk about today?"

        return reply_text, learning_signals

    except Exception as e:
        # Fallback friendly message if API key is invalid/missing
        return (
            f"Hey! I'm Mira 🤗 (Note: Please set a valid free GROQ_API_KEY or OPENAI_API_KEY in backend/.env to start talking live! Error: {str(e)})",
            LearningSignals(),
        )


async def generate_reply_stream(
    system_prompt: str,
    user_message: str,
    target_language: str = "English",
):
    """
    Stream LLM reply tokens as they arrive (async generator).

    Yields dicts:
      {"type": "token", "content": "..."}
      {"type": "done", "content": "full_reply", "learning_signals": {...}}

    Tool-calling is done in a separate non-streaming follow-up call to extract
    learning signals, since most providers don't support tool_choice with streaming.
    """
    client, model = get_ai_client_and_model()
    full_reply = ""

    try:
        # ── Phase A: Stream the reply text ────────────────────────────────
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.8,
            max_tokens=1000,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_reply += delta.content
                yield {"type": "token", "content": delta.content}

        full_reply = clean_ai_reply(full_reply)
        if not full_reply:
            full_reply = "Hey! I'm here 😊 What would you like to talk about today?"
            yield {"type": "token", "content": full_reply}

        # ── Phase B: Extract learning signals (non-streaming tool call) ───
        learning_signals = LearningSignals()
        try:
            signals_response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are a {target_language} learning analysis tool. Analyze the user's message for grammar corrections, vocabulary, mood, and memorable facts. Call the log_learning_signals tool with your analysis."},
                    {"role": "user", "content": f"User said: \"{user_message}\"\n\nCompanion replied: \"{full_reply}\""},
                ],
                tools=[LEARNING_SIGNALS_TOOL],
                tool_choice={"type": "function", "function": {"name": "log_learning_signals"}},
                temperature=0.3,
                max_tokens=500,
            )
            sig_msg = signals_response.choices[0].message
            if sig_msg.tool_calls:
                for tool_call in sig_msg.tool_calls:
                    if tool_call.function.name == "log_learning_signals":
                        try:
                            signals_data = json.loads(tool_call.function.arguments)
                            learning_signals = LearningSignals(**signals_data)
                        except (json.JSONDecodeError, Exception):
                            pass
        except Exception:
            # If signal extraction fails, continue with empty signals
            pass

        yield {
            "type": "done",
            "content": full_reply,
            "learning_signals": learning_signals.model_dump(),
        }

    except Exception as e:
        fallback = f"Hey! I'm Mira 🤗 (Connection issue: {str(e)})"
        yield {"type": "token", "content": fallback}
        yield {
            "type": "done",
            "content": fallback,
            "learning_signals": LearningSignals().model_dump(),
        }


async def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribe audio bytes to text using Groq Whisper (free) or OpenAI Whisper.
    Returns the transcribed text string.
    """
    import io

    groq_key = settings.groq_api_key or (settings.openai_api_key if settings.openai_api_key.startswith("gsk_") else None)
    openai_key = settings.openai_api_key if (settings.openai_api_key and not settings.openai_api_key.startswith("sk-your-openai") and not settings.openai_api_key.startswith("gsk_") and not settings.openai_api_key.startswith("AIzaSy")) else None

    if groq_key:
        transcribe_client = AsyncOpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
        )
        whisper_model = "whisper-large-v3-turbo"
    elif openai_key:
        transcribe_client = AsyncOpenAI(api_key=openai_key)
        whisper_model = "whisper-1"
    else:
        transcribe_client, _ = get_ai_client_and_model()
        whisper_model = "whisper-large-v3-turbo" if settings.groq_api_key else "whisper-1"

    audio_file = io.BytesIO(file_bytes)
    audio_file.name = filename

    try:
        transcription = await transcribe_client.audio.transcriptions.create(
            model=whisper_model,
            file=audio_file,
            response_format="text",
        )
        return transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
    except Exception as e:
        raise Exception(f"Voice transcription service error ({whisper_model}): {str(e)}")
