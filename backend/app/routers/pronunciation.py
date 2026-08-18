"""Pronunciation Evaluator Router — Voice pronunciation scoring via Whisper + LLM"""

import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.ai_service import get_ai_client_and_model, transcribe_audio

router = APIRouter(prefix="/pronunciation", tags=["Pronunciation"])

# ─── Target Word Banks by Level ──────────────────────────────────────────────

WORD_BANKS = {
    "beginner": [
        {"word": "hello", "phonetic": "/həˈloʊ/", "meaning": "a greeting"},
        {"word": "beautiful", "phonetic": "/ˈbjuːtɪfəl/", "meaning": "pleasing to the eye"},
        {"word": "together", "phonetic": "/təˈɡɛðər/", "meaning": "in company"},
        {"word": "comfortable", "phonetic": "/ˈkʌmftərbəl/", "meaning": "feeling at ease"},
        {"word": "restaurant", "phonetic": "/ˈrɛstərɑnt/", "meaning": "a place to eat"},
        {"word": "especially", "phonetic": "/ɪˈspɛʃəli/", "meaning": "to a great extent"},
        {"word": "wednesday", "phonetic": "/ˈwɛnzdeɪ/", "meaning": "the fourth day of the week"},
        {"word": "family", "phonetic": "/ˈfæməli/", "meaning": "a group of related people"},
    ],
    "intermediate": [
        {"word": "pronunciation", "phonetic": "/prəˌnʌnsiˈeɪʃən/", "meaning": "the way a word is spoken"},
        {"word": "entrepreneur", "phonetic": "/ˌɒntrəprəˈnɜːr/", "meaning": "a person who starts businesses"},
        {"word": "hierarchy", "phonetic": "/ˈhaɪərɑːrki/", "meaning": "a system of ranking"},
        {"word": "thoroughly", "phonetic": "/ˈθɜːrəli/", "meaning": "in a complete manner"},
        {"word": "particularly", "phonetic": "/pərˈtɪkjələrli/", "meaning": "especially; specifically"},
        {"word": "inevitable", "phonetic": "/ɪnˈɛvɪtəbəl/", "meaning": "certain to happen"},
        {"word": "vulnerability", "phonetic": "/ˌvʌlnərəˈbɪlɪti/", "meaning": "the state of being exposed to harm"},
        {"word": "conscientious", "phonetic": "/ˌkɒnʃiˈɛnʃəs/", "meaning": "careful and diligent"},
    ],
    "advanced": [
        {"word": "ubiquitous", "phonetic": "/juːˈbɪkwɪtəs/", "meaning": "present everywhere"},
        {"word": "ephemeral", "phonetic": "/ɪˈfɛmərəl/", "meaning": "lasting a very short time"},
        {"word": "serendipity", "phonetic": "/ˌsɛrənˈdɪpɪti/", "meaning": "fortunate accident"},
        {"word": "surreptitiously", "phonetic": "/ˌsʌrəpˈtɪʃəsli/", "meaning": "in a secretive manner"},
        {"word": "onomatopoeia", "phonetic": "/ˌɒnəˌmætəˈpiːə/", "meaning": "words that imitate sounds"},
        {"word": "conscientious", "phonetic": "/ˌkɒnʃiˈɛnʃəs/", "meaning": "careful and diligent"},
        {"word": "exacerbate", "phonetic": "/ɪɡˈzæsərbeɪt/", "meaning": "to make worse"},
        {"word": "ambiguous", "phonetic": "/æmˈbɪɡjuəs/", "meaning": "open to multiple interpretations"},
    ]
}

PHRASES = [
    {"phrase": "She sells seashells by the seashore.", "level": "intermediate", "tip": "Focus on the 'sh' and 's' sounds"},
    {"phrase": "How much wood would a woodchuck chuck?", "level": "beginner", "tip": "Practice the 'w' and 'ch' sounds"},
    {"phrase": "The thirty-three thieves thought.", "level": "advanced", "tip": "The 'th' sound requires tongue between teeth"},
    {"phrase": "I scream, you scream, we all scream for ice cream.", "level": "beginner", "tip": "Natural rhythm and stress"},
    {"phrase": "Red lorry, yellow lorry.", "level": "intermediate", "tip": "The 'l' and 'r' sounds side by side"},
]


@router.get("/words")
async def get_practice_words(
    level: str = "beginner",
    current_user: User = Depends(get_current_user)
):
    """Get a set of pronunciation target words for the user's level."""
    import random
    bank = WORD_BANKS.get(level, WORD_BANKS["beginner"])
    selected_words = random.sample(bank, min(6, len(bank)))
    selected_phrases = random.sample(PHRASES, min(2, len(PHRASES)))
    return {
        "words": selected_words,
        "phrases": selected_phrases,
        "level": level
    }


@router.post("/evaluate")
async def evaluate_pronunciation(
    audio: UploadFile = File(...),
    target: str = Form(...),
    level: str = Form(default="beginner"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate pronunciation by:
    1. Transcribing the audio with Whisper
    2. Comparing the transcription to the target with the LLM
    3. Returning a score + detailed feedback
    """
    # Step 1: Transcribe audio
    file_bytes = await audio.read()
    if len(file_bytes) < 500:
        raise HTTPException(status_code=400, detail="Audio too short. Please record again.")

    try:
        transcribed = await transcribe_audio(file_bytes, audio.filename or "recording.webm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

    # Step 2: Evaluate with LLM
    client, model = get_ai_client_and_model()

    evaluation_prompt = f"""You are a pronunciation coach. The student was asked to say: "{target}"
They said: "{transcribed}"

Evaluate their pronunciation on a scale of 0-100 and return ONLY a JSON object with exactly these fields:
{{
  "score": <integer 0-100>,
  "accuracy": <"excellent"|"good"|"fair"|"needs_work">,
  "feedback": "<2-3 sentence encouraging feedback about what was right and what to improve>",
  "what_they_said": "{transcribed}",
  "tip": "<one specific phonetic tip for this word/phrase>"
}}

Scoring guide:
- 90-100: Nearly perfect, minor accent differences only
- 75-89: Good, clearly understandable
- 55-74: Fair, some sounds unclear
- 0-54: Needs work, significant differences

Be encouraging and specific. Return ONLY valid JSON."""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": evaluation_prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        # Strip markdown code blocks if present
        if content.startswith("`"):
            content = content.split("`")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
    except (json.JSONDecodeError, Exception):
        # Fallback scoring by string similarity
        target_clean = target.lower().strip()
        transcribed_clean = transcribed.lower().strip()
        similarity = sum(c in transcribed_clean for c in target_clean) / max(len(target_clean), 1)
        score = int(similarity * 100)
        result = {
            "score": score,
            "accuracy": "good" if score >= 75 else "fair" if score >= 55 else "needs_work",
            "feedback": f"You said '{transcribed}'. Keep practicing — you're making progress!",
            "what_they_said": transcribed,
            "tip": "Try saying it slowly, then gradually speed up."
        }

    # Step 3: Award XP for good scores
    xp_earned = 0
    if result.get("score", 0) >= 80:
        xp_earned = 15
        current_user.xp = (current_user.xp or 0) + xp_earned
        await db.commit()

    result["xp_earned"] = xp_earned
    result["target"] = target

    return result
