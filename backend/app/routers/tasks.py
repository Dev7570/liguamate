"""Tasks Router - Daily missions API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.task import TaskResponse, TaskCompleteRequest
from app.services.task_service import generate_daily_tasks, complete_task, get_completion_stats
from app.utils.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Daily Tasks"])


@router.get("/today", response_model=list[TaskResponse])
async def get_today_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get today's missions. Auto-generates if none exist."""
    tasks = await generate_daily_tasks(
        db, current_user.id, current_user.english_level
    )
    return [
        TaskResponse(
            id=str(t.id),
            task_date=str(t.task_date),
            task_type=t.task_type,
            title=t.title,
            description=t.description,
            difficulty=t.difficulty,
            completed=t.completed,
            completed_at=str(t.completed_at) if t.completed_at else None,
        )
        for t in tasks
    ]


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task_endpoint(
    task_id: str,
    request: TaskCompleteRequest = TaskCompleteRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as completed."""
    task = await complete_task(
        db, task_id, current_user.id, request.performance_notes
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=str(task.id),
        task_date=str(task.task_date),
        task_type=task.task_type,
        title=task.title,
        description=task.description,
        difficulty=task.difficulty,
        completed=task.completed,
        completed_at=str(task.completed_at) if task.completed_at else None,
    )


@router.get("/stats")
async def get_task_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task completion statistics."""
    return await get_completion_stats(db, current_user.id)
