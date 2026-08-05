"""Pydantic schemas - Chat"""

from pydantic import BaseModel, Field
from datetime import datetime


class CorrectionItem(BaseModel):
    original: str
    corrected: str
    explanation: str | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    corrections: list[CorrectionItem] | None = None
    vocab_used: list[str] | None = None
    mood_signal: str | None = None
    created_at: str

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    channel: str = "text"


class ConversationResponse(BaseModel):
    id: str
    channel: str
    started_at: str
    ended_at: str | None = None
    summary: str | None = None
    message_count: int = 0

    class Config:
        from_attributes = True


class LearningSignals(BaseModel):
    """Structured output from the LLM's tool call - what the AI learned from this exchange."""
    corrections: list[CorrectionItem] = []
    vocab_used: list[str] = []
    new_memories: list[dict] = []  # [{fact, category, importance}]
    mood_signal: str = "neutral"  # confident | neutral | hesitant
    vocabulary_suggestions: list[str] = []  # richer words to suggest
