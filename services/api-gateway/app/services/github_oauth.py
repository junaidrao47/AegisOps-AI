from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class GitHubOAuthError(Exception):
    pass


def _ensure_configured() -> None:
    if not settings.github_client_id or not settings.github_client_secret or not settings.github_redirect_uri:
        raise GitHubOAuthError("github_oauth_not_configured")


def exchange_code_for_access_token(code: str) -> str:
    _ensure_configured()

    url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
        "redirect_uri": settings.github_redirect_uri,
    }

    headers = {"Accept": "application/json"}

    with httpx.Client(timeout=15) as client:
        resp = client.post(url, data=data, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    token = payload.get("access_token")
    if not token:
        raise GitHubOAuthError("github_token_exchange_failed")

    return str(token)


def fetch_github_user(access_token: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    with httpx.Client(timeout=15) as client:
        resp = client.get("https://api.github.com/user", headers=headers)
        resp.raise_for_status()
        user = resp.json()

        # Primary email may require a second call
        email = user.get("email")
        if not email:
            emails_resp = client.get("https://api.github.com/user/emails", headers=headers)
            if emails_resp.status_code == 200:
                emails = emails_resp.json()
                primary = next((e for e in emails if e.get("primary")), None)
                verified = next((e for e in emails if e.get("verified")), None)
                email = (primary or verified or (emails[0] if emails else None) or {}).get("email")

    if not user.get("id"):
        raise GitHubOAuthError("github_user_fetch_failed")

    user["resolved_email"] = email
    return user
