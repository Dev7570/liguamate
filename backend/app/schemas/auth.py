"""Pydantic schemas - Auth"""

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    english_level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    goal: str | None = None


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
    avatar_emoji: str
    created_at: str

    class Config:
        from_attributes = True
