"""Pydantic schemas - Tasks"""

from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: str
    task_date: str
    task_type: str | None
    title: str
    description: str | None
    difficulty: str
    completed: bool
    completed_at: str | None = None

    class Config:
        from_attributes = True


class TaskCompleteRequest(BaseModel):
    performance_notes: str | None = None
