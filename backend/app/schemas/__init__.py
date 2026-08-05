"""Schemas package"""

from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserProfile
from app.schemas.chat import (
    SendMessageRequest,
    MessageResponse,
    ConversationCreate,
    ConversationResponse,
    LearningSignals,
    CorrectionItem,
)
from app.schemas.task import TaskResponse, TaskCompleteRequest
from app.schemas.progress import VocabItemResponse, DashboardResponse
