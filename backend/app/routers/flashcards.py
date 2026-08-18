"""Flashcards Router — Custom Deck & Card Management with SM-2 SRS"""

import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.vocabulary import VocabularyProgress
from app.utils.auth import get_current_user

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


class DeckCreate(BaseModel):
    name: str
    language: str = "English"
    description: str | None = None


class CardCreate(BaseModel):
    front: str
    back: str
    phonetic: str | None = None
    example: str | None = None


class ReviewSubmit(BaseModel):
    quality: int  # 0-5 (SM-2 scale: 0=blackout, 5=perfect)


def _sm2_update(card: Flashcard, quality: int):
    """Apply SM-2 algorithm to update card scheduling."""
    if quality < 3:
        card.interval = 1
        card.ease_factor = max(1.3, card.ease_factor - 0.2)
    else:
        if card.times_reviewed == 0:
            card.interval = 1
        elif card.times_reviewed == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.ease_factor)
        card.ease_factor = max(1.3, card.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    card.times_reviewed += 1
    card.last_reviewed_at = datetime.now(timezone.utc)
    card.next_review_at = datetime.now(timezone.utc) + timedelta(days=card.interval)
    card.is_mastered = card.interval >= 21


# ─── Decks ────────────────────────────────────────────────────────────────────

@router.get("/decks")
async def get_decks(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get all flashcard decks for the current user."""
    result = await db.execute(select(FlashcardDeck).where(FlashcardDeck.user_id == current_user.id))
    decks = result.scalars().all()
    return [{
        "id": d.id,
        "name": d.name,
        "language": d.language,
        "description": d.description,
        "card_count": len(d.cards),
        "due_count": sum(1 for c in d.cards if c.next_review_at <= datetime.now(timezone.utc)),
        "mastered_count": sum(1 for c in d.cards if c.is_mastered),
        "created_at": str(d.created_at),
    } for d in decks]


@router.post("/decks", status_code=201)
async def create_deck(data: DeckCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    deck = FlashcardDeck(user_id=current_user.id, name=data.name, language=data.language, description=data.description)
    db.add(deck)
    await db.commit()
    return {"id": deck.id, "name": deck.name, "language": deck.language, "card_count": 0, "due_count": 0, "mastered_count": 0}


@router.delete("/decks/{deck_id}")
async def delete_deck(deck_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == current_user.id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    await db.delete(deck)
    await db.commit()
    return {"ok": True}


# ─── Cards ────────────────────────────────────────────────────────────────────

@router.get("/decks/{deck_id}/cards")
async def get_cards(deck_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == current_user.id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return [{
        "id": c.id, "front": c.front, "back": c.back, "phonetic": c.phonetic,
        "example": c.example, "times_reviewed": c.times_reviewed,
        "next_review_at": str(c.next_review_at), "interval": c.interval,
        "is_mastered": c.is_mastered, "is_due": c.next_review_at <= datetime.now(timezone.utc),
    } for c in deck.cards]


@router.post("/decks/{deck_id}/cards", status_code=201)
async def add_card(deck_id: str, data: CardCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FlashcardDeck).where(FlashcardDeck.id == deck_id, FlashcardDeck.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Deck not found")
    card = Flashcard(deck_id=deck_id, front=data.front, back=data.back, phonetic=data.phonetic, example=data.example)
    db.add(card)
    await db.commit()
    return {"id": card.id, "front": card.front, "back": card.back, "is_due": True}


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Flashcard).join(FlashcardDeck).where(Flashcard.id == card_id, FlashcardDeck.user_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.delete(card)
    await db.commit()
    return {"ok": True}


@router.post("/cards/{card_id}/review")
async def review_card(card_id: str, data: ReviewSubmit, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Submit a review result for a card using SM-2 algorithm."""
    result = await db.execute(
        select(Flashcard).join(FlashcardDeck).where(Flashcard.id == card_id, FlashcardDeck.user_id == current_user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    _sm2_update(card, max(0, min(5, data.quality)))
    await db.commit()
    return {"id": card.id, "next_review_at": str(card.next_review_at), "interval": card.interval, "is_mastered": card.is_mastered}


@router.post("/decks/import-vocab")
async def import_from_vocab(
    data: DeckCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new deck auto-populated from the user's tracked vocabulary."""
    deck = FlashcardDeck(user_id=current_user.id, name=data.name, language=data.language or "English", description="Imported from vocabulary tracker")
    db.add(deck)
    await db.flush()

    vocab_result = await db.execute(select(VocabularyProgress).where(VocabularyProgress.user_id == current_user.id))
    words = vocab_result.scalars().all()

    for w in words:
        card = Flashcard(deck_id=deck.id, front=w.word, back=w.meaning or f"(tracked word — {w.mastery_level} level)", example=None)
        db.add(card)

    await db.commit()
    return {"id": deck.id, "name": deck.name, "card_count": len(words), "message": f"Imported {len(words)} words!"}
