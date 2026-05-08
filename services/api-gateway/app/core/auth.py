from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_refresh_token(token: str) -> str:
    # Store only a one-way hash in DB
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, user_id: int, role: str, session_id: int) -> str:
    expires = _now() + timedelta(minutes=settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "role": role,
        "sid": str(session_id),
        "type": "access",
        "exp": int(expires.timestamp()),
        "iat": int(_now().timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(*, user_id: int, session_id: int) -> tuple[str, datetime]:
    expires = _now() + timedelta(days=settings.refresh_token_ttl_days)
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "refresh",
        "exp": int(expires.timestamp()),
        "iat": int(_now().timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("invalid_token") from exc


def require_token_type(payload: dict[str, Any], token_type: str) -> None:
    if payload.get("type") != token_type:
        raise ValueError("invalid_token_type")


def parse_int_claim(payload: dict[str, Any], claim: str) -> int:
    value = payload.get(claim)
    if value is None:
        raise ValueError(f"missing_claim:{claim}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_claim:{claim}") from exc
