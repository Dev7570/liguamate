"""Models package - import all models so Alembic can see them"""

from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.memory import Memory
from app.models.task import DailyTask
from app.models.vocabulary import VocabularyProgress
from app.models.flashcard import FlashcardDeck, Flashcard
from app.models.test_result import TestResult

__all__ = [
    "User",
    "Conversation",
    "Message",
    "Memory",
    "DailyTask",
    "VocabularyProgress",
    "FlashcardDeck",
    "Flashcard",
    "TestResult",
]
