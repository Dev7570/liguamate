"""SQLAlchemy ORM models - User"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    english_level: Mapped[str] = mapped_column(
        String(20), default="beginner"
    )
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    companion: Mapped[str] = mapped_column(String(20), default="mira")
    avatar_emoji: Mapped[str] = mapped_column(String(10), default="😊")
    xp: Mapped[int] = mapped_column(default=0)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    conversations = relationship("Conversation", back_populates="user", lazy="selectin")
    memories = relationship("Memory", back_populates="user", lazy="selectin")
    daily_tasks = relationship("DailyTask", back_populates="user", lazy="selectin")
    vocabulary = relationship("VocabularyProgress", back_populates="user", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "english_level IN ('beginner', 'intermediate', 'advanced')",
            name="check_english_level",
        ),
    )
