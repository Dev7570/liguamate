"""Pydantic schemas - Auth"""

from pydantic import BaseModel, EmailStr, Field


SUPPORTED_LANGUAGES = [
    "English", "Spanish", "French", "German", "Italian",
    "Japanese", "Mandarin", "Portuguese", "Russian", "Arabic",
    "Hindi", "Korean", "Dutch", "Swedish", "Turkish",
]

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    english_level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    goal: str | None = None
    companion: str = Field(default="mira", pattern="^(mira|leo)$")
    target_language: str = Field(default="English", max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    english_level: str
    goal: str | None
    companion: str
    target_language: str = "English"
    avatar_emoji: str
    created_at: str

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    english_level: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    goal: str | None = None
    companion: str | None = Field(default=None, pattern="^(mira|leo)$")
    target_language: str | None = Field(default=None, max_length=50)
