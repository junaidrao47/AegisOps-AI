from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    parse_int_claim,
    require_token_type,
    verify_password,
)
from app.core.deps import get_current_user
from app.db.models.session import UserSession
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest
from app.schemas.tokens import TokenPair
from app.services.github_oauth import GitHubOAuthError, exchange_code_for_access_token, fetch_github_user
from app.core.config import settings

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_client_ip(request: Request) -> str | None:
    # Basic best-effort; if behind a proxy, you'll want trusted middleware.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_already_registered")

    user = User(email=str(payload.email).lower(), hashed_password=hash_password(payload.password), role="engineer")
    db.add(user)
    db.flush()  # assign user.id

    # Create session + tokens
    session = UserSession(
        user_id=user.id,
        refresh_token_hash="pending",
        created_at=_utcnow(),
        expires_at=_utcnow() + timedelta(days=settings.refresh_token_ttl_days),
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    db.flush()

    refresh_token, refresh_expires_at = create_refresh_token(user_id=user.id, session_id=session.id)
    session.refresh_token_hash = hash_refresh_token(refresh_token)
    session.expires_at = refresh_expires_at

    access_token = create_access_token(user_id=user.id, role=user.role, session_id=session.id)
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    # GitHub OAuth login
    if payload.github_code:
        try:
            gh_access_token = exchange_code_for_access_token(payload.github_code)
            gh_user = fetch_github_user(gh_access_token)
        except GitHubOAuthError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="github_oauth_failed")

        github_id = str(gh_user["id"])
        email = (gh_user.get("resolved_email") or gh_user.get("email") or "").lower()

        user = db.execute(select(User).where(User.github_id == github_id)).scalar_one_or_none()
        if not user and email:
            user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

        if not user:
            user = User(email=email or f"github:{github_id}", github_id=github_id, role="engineer", is_active=True)
            db.add(user)
            db.flush()
        else:
            user.github_id = user.github_id or github_id

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="inactive_user")

        session = UserSession(
            user_id=user.id,
            refresh_token_hash="pending",
            created_at=_utcnow(),
            expires_at=_utcnow(),
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        db.add(session)
        db.flush()

        refresh_token, refresh_expires_at = create_refresh_token(user_id=user.id, session_id=session.id)
        session.refresh_token_hash = hash_refresh_token(refresh_token)
        session.expires_at = refresh_expires_at
        access_token = create_access_token(user_id=user.id, role=user.role, session_id=session.id)
        db.commit()
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    # Password login
    if not payload.email or not payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_credentials")

    user = db.execute(select(User).where(User.email == str(payload.email).lower())).scalar_one_or_none()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="inactive_user")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    session = UserSession(
        user_id=user.id,
        refresh_token_hash="pending",
        created_at=_utcnow(),
        expires_at=_utcnow(),
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    db.flush()

    refresh_token, refresh_expires_at = create_refresh_token(user_id=user.id, session_id=session.id)
    session.refresh_token_hash = hash_refresh_token(refresh_token)
    session.expires_at = refresh_expires_at

    access_token = create_access_token(user_id=user.id, role=user.role, session_id=session.id)
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    try:
        token_payload = decode_token(payload.refresh_token)
        require_token_type(token_payload, "refresh")
        user_id = parse_int_claim(token_payload, "sub")
        session_id = parse_int_claim(token_payload, "sid")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")

    session = db.get(UserSession, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")
    if session.revoked_at is not None or session.expires_at <= _utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token_expired")

    # Verify presented refresh token matches stored hash
    if session.refresh_token_hash != hash_refresh_token(payload.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive_user")

    # Rotation: revoke old session row and create a new one
    session.revoked_at = _utcnow()
    session.last_used_at = _utcnow()

    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash="pending",
        created_at=_utcnow(),
        expires_at=_utcnow(),
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.add(new_session)
    db.flush()

    new_refresh_token, new_refresh_expires_at = create_refresh_token(user_id=user.id, session_id=new_session.id)
    new_session.refresh_token_hash = hash_refresh_token(new_refresh_token)
    new_session.expires_at = new_refresh_expires_at

    new_access_token = create_access_token(user_id=user.id, role=user.role, session_id=new_session.id)
    db.commit()

    return TokenPair(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    # Determine current session from access token 'sid'
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_authorization")
    token = authorization.split(" ", 1)[1].strip()

    try:
        token_payload = decode_token(token)
        require_token_type(token_payload, "access")
        session_id = parse_int_claim(token_payload, "sid")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    now = _utcnow()
    if payload.everywhere:
        sessions = db.execute(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        ).scalars().all()
        for s in sessions:
            s.revoked_at = now
        db.commit()
        return {"detail": "logged_out_everywhere"}

    session = db.get(UserSession, session_id)
    if session and session.user_id == user.id and session.revoked_at is None:
        session.revoked_at = now
        db.commit()
    return {"detail": "logged_out"}
