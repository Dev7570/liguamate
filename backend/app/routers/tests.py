"""Tests Router — Mock IELTS/TOEFL Speaking Test Evaluation"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.test_result import TestResult
from app.utils.auth import get_current_user
from app.services.ai_service import transcribe_audio
from app.services.test_service import evaluate_speaking_test, get_prompts_for_test

router = APIRouter(prefix="/tests", tags=["Speaking Tests"])


@router.get("/prompts")
async def get_prompts(
    test_type: str = "ielts",
    part: str = "part1",
    current_user: User = Depends(get_current_user)
):
    """Get speaking prompts for a given test type and part."""
    prompts = get_prompts_for_test(test_type, part)
    return {
        "test_type": test_type,
        "part": part,
        "prompts": prompts,
        "timing": _get_timing(test_type, part)
    }


def _get_timing(test_type: str, part: str) -> dict:
    """Return prep and speaking time limits in seconds."""
    if test_type.lower() == "ielts":
        return {
            "part1": {"prep": 0, "speak": 90, "label": "1.5 min response"},
            "part2": {"prep": 60, "speak": 120, "label": "1 min prep + 2 min speaking"},
            "part3": {"prep": 0, "speak": 90, "label": "1.5 min discussion"},
        }.get(part, {"prep": 0, "speak": 90, "label": "90 seconds"})
    else:
        return {
            "task1": {"prep": 15, "speak": 45, "label": "15s prep + 45s response"},
            "task2": {"prep": 15, "speak": 60, "label": "15s prep + 60s response"},
        }.get(part, {"prep": 15, "speak": 45, "label": "45 seconds"})


@router.post("/evaluate")
async def evaluate_test(
    audio: UploadFile = File(...),
    test_type: str = Form(default="ielts"),
    part: str = Form(default="part1"),
    prompt_used: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate a speaking test response:
    1. Transcribe audio with Whisper
    2. Score with LLM using official rubric
    3. Save result to history
    4. Award XP
    """
    file_bytes = await audio.read()
    if len(file_bytes) < 500:
        raise HTTPException(status_code=400, detail="Recording too short. Please try again.")

    # Step 1: Transcribe
    try:
        transcript = await transcribe_audio(file_bytes, audio.filename or "test.webm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

    if not transcript or len(transcript.strip()) < 10:
        raise HTTPException(status_code=400, detail="Couldn't detect enough speech. Please speak clearly and try again.")

    # Step 2: Evaluate
    scores = await evaluate_speaking_test(test_type, part, transcript, prompt_used)

    # Step 3: Save result
    result = TestResult(
        user_id=current_user.id,
        test_type=test_type.lower(),
        part=part.lower(),
        band_score=float(scores.get("band_score", 0)),
        fluency=float(scores.get("fluency", 0)),
        lexical=float(scores.get("lexical", 0)),
        grammar=float(scores.get("grammar", 0)),
        pronunciation=float(scores.get("pronunciation", 0)),
        transcript=transcript,
        feedback=scores.get("overall_feedback", ""),
        prompt_used=prompt_used,
    )
    db.add(result)

    # Step 4: Award XP (10 XP per test)
    band = float(scores.get("band_score", 0))
    xp_scale = 9.0 if test_type.lower() == "ielts" else 30.0
    xp_earned = int((band / xp_scale) * 50) + 10
    current_user.xp = (current_user.xp or 0) + xp_earned

    await db.commit()

    return {
        "id": str(result.id),
        "transcript": transcript,
        "band_score": scores.get("band_score"),
        "fluency": scores.get("fluency"),
        "lexical": scores.get("lexical"),
        "grammar": scores.get("grammar"),
        "pronunciation": scores.get("pronunciation"),
        "strengths": scores.get("strengths", ""),
        "improvements": scores.get("improvements", ""),
        "overall_feedback": scores.get("overall_feedback", ""),
        "xp_earned": xp_earned,
        "test_type": test_type,
        "part": part,
    }


@router.get("/history")
async def get_test_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the user's past test results."""
    result = await db.execute(
        select(TestResult)
        .where(TestResult.user_id == current_user.id)
        .order_by(TestResult.created_at.desc())
        .limit(limit)
    )
    tests = result.scalars().all()
    return [{
        "id": str(t.id),
        "test_type": t.test_type,
        "part": t.part,
        "band_score": t.band_score,
        "fluency": t.fluency,
        "lexical": t.lexical,
        "grammar": t.grammar,
        "pronunciation": t.pronunciation,
        "feedback": t.feedback,
        "prompt_used": t.prompt_used,
        "created_at": str(t.created_at),
    } for t in tests]
