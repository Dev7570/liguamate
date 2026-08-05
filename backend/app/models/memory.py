"""SQLAlchemy ORM models - Memory (long-term facts)"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean, SmallInteger, ForeignKey, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    importance: Mapped[int] = mapped_column(SmallInteger, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_referenced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="memories")

    __table_args__ = (
        CheckConstraint(
            "importance BETWEEN 1 AND 5", name="check_importance"
        ),
    )
