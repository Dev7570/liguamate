"""SQLAlchemy ORM models - Flashcard Decks and Cards"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="English")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    cards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan", lazy="selectin")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id: Mapped[str] = mapped_column(String(36), ForeignKey("flashcard_decks.id"), nullable=False)
    front: Mapped[str] = mapped_column(Text, nullable=False)   # Word / Question
    back: Mapped[str] = mapped_column(Text, nullable=False)    # Definition / Answer
    phonetic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    times_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    interval: Mapped[int] = mapped_column(Integer, default=1)      # Days until next review
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)  # SM-2 ease factor
    is_mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    deck = relationship("FlashcardDeck", back_populates="cards")
