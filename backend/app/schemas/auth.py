"""Pydantic schemas for authentication — task 3.3."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshRequest(BaseModel):
    user_id: str
    jti: str
    refresh_token: str


class LogoutRequest(BaseModel):
    jti: str
    user_id: str
    refresh_token: str | None = None
