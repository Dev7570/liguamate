"""SQLAlchemy ORM models - Vocabulary Progress"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VocabularyProgress(Base):
    __tablename__ = "vocabulary_progress"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    word: Mapped[str] = mapped_column(String(100), nullable=False)
    times_used: Mapped[int] = mapped_column(Integer, default=1)
    mastery_level: Mapped[str] = mapped_column(String(20), default="new")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    
    # SRS Fields (SuperMemo-2)
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    interval: Mapped[int] = mapped_column(Integer, default=1)  # Interval in days
    ease_factor: Mapped[float] = mapped_column(default=2.5)

    # Relationships
    user = relationship("User", back_populates="vocabulary")

    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_user_word"),
        CheckConstraint(
            "mastery_level IN ('new', 'learning', 'mastered')",
            name="check_mastery_level",
        ),
    )
