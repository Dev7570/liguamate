"""Pydantic schemas - Progress & Dashboard"""

from pydantic import BaseModel


class VocabItemResponse(BaseModel):
    word: str
    times_used: int
    mastery_level: str
    first_seen_at: str
    last_used_at: str

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    total_conversations: int
    total_messages_sent: int
    total_words_learned: int
    words_mastered: int
    current_streak: int
    tasks_completed_today: int
    tasks_total_today: int
    recent_corrections: list[dict]
    encouragement: str
