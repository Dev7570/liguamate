"""SQLAlchemy ORM model - Test Results (IELTS/TOEFL)"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)   # 'ielts' | 'toefl'
    part: Mapped[str] = mapped_column(String(20), nullable=False)         # 'part1' | 'part2' | 'task1' etc.
    band_score: Mapped[float] = mapped_column(Float, nullable=False)      # Overall band/score
    fluency: Mapped[float] = mapped_column(Float, default=0.0)
    lexical: Mapped[float] = mapped_column(Float, default=0.0)
    grammar: Mapped[float] = mapped_column(Float, default=0.0)
    pronunciation: Mapped[float] = mapped_column(Float, default=0.0)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
