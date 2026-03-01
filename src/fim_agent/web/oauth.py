"""OAuth provider helpers -- GitHub and Google."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


@dataclass
class OAuthProvider:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    user_info_url: str
    scopes: list[str]


@dataclass
class OAuthUserInfo:
    provider: str
    id: str
    username: str
    email: str | None
    display_name: str | None


_PROVIDERS: dict[str, dict] = {
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "scopes": ["read:user", "user:email"],
        "env_prefix": "GITHUB",
    },
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": ["openid", "email", "profile"],
        "env_prefix": "GOOGLE",
    },
}


def get_provider(name: str) -> OAuthProvider | None:
    """Get provider config if env vars are set, else None."""
    cfg = _PROVIDERS.get(name)
    if not cfg:
        return None
    prefix = cfg["env_prefix"]
    client_id = os.environ.get(f"{prefix}_CLIENT_ID", "")
    client_secret = os.environ.get(f"{prefix}_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None
    return OAuthProvider(
        name=name,
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=cfg["authorize_url"],
        token_url=cfg["token_url"],
        user_info_url=cfg["user_info_url"],
        scopes=cfg["scopes"],
    )


def get_configured_providers() -> list[str]:
    """Return names of providers that have credentials configured."""
    return [name for name in _PROVIDERS if get_provider(name) is not None]


def build_authorize_url(provider: OAuthProvider, state: str, redirect_uri: str) -> str:
    """Build the OAuth authorization URL."""
    params = {
        "client_id": provider.client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(provider.scopes),
    }
    if provider.name == "google":
        params["response_type"] = "code"
        params["access_type"] = "offline"
    return f"{provider.authorize_url}?{urlencode(params)}"


async def exchange_code(provider: OAuthProvider, code: str, redirect_uri: str) -> str:
    """Exchange authorization code for access token. Returns the access token."""
    async with httpx.AsyncClient() as client:
        headers = {"Accept": "application/json"}
        data = {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if provider.name == "google":
            data["grant_type"] = "authorization_code"
        resp = await client.post(provider.token_url, data=data, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        token = body.get("access_token")
        if not token:
            raise ValueError(f"No access_token in response: {body}")
        return token


async def fetch_user_info(provider: OAuthProvider, access_token: str) -> OAuthUserInfo:
    """Fetch user profile from the OAuth provider."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        if provider.name == "github":
            headers["Accept"] = "application/vnd.github+json"
        resp = await client.get(provider.user_info_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if provider.name == "github":
            email = data.get("email")
            # If email is private, fetch from /user/emails
            if not email:
                email_resp = await client.get(
                    "https://api.github.com/user/emails", headers=headers
                )
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next((e for e in emails if e.get("primary")), None)
                    email = primary["email"] if primary else None
            return OAuthUserInfo(
                provider="github",
                id=str(data["id"]),
                username=data.get("login", ""),
                email=email,
                display_name=data.get("name"),
            )
        elif provider.name == "google":
            return OAuthUserInfo(
                provider="google",
                id=data["id"],
                username=data.get("email", "").split("@")[0],
                email=data.get("email"),
                display_name=data.get("name"),
            )
        else:
            raise ValueError(f"Unknown provider: {provider.name}")
