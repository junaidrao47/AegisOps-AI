from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    # Either email/password OR github_code (OAuth)
    email: EmailStr | None = None
    password: str | None = None
    github_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    # If everywhere=True, revoke all active sessions for this user.
    everywhere: bool = False
