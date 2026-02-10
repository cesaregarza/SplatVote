"""Helpers for Discord auth forwarded by an upstream auth proxy."""

import os
from typing import Iterable

from fastapi import Request


DEFAULT_DISCORD_USER_ID_HEADERS = (
    "x-discord-user-id",
    "x-discord-id",
    "x-auth-request-user-id",
    "x-auth-request-user",
    "x-forwarded-user",
    "remote-user",
)

DEFAULT_DISCORD_USERNAME_HEADERS = (
    "x-discord-username",
    "x-auth-request-preferred-username",
    "x-auth-request-email",
    "x-forwarded-preferred-username",
    "x-forwarded-email",
)


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse boolean-ish env vars."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def is_discord_auth_bypass_enabled() -> bool:
    """Return whether Discord auth should be bypassed.

    Intended for local development only.
    """
    if _env_flag("DISCORD_AUTH_BYPASS", default=False):
        return True
    return _env_flag("DEV_MODE", default=False) and _env_flag(
        "DISCORD_AUTH_BYPASS_IN_DEV",
        default=True,
    )


def _iter_header_names(env_var_name: str, defaults: tuple[str, ...]) -> Iterable[str]:
    """Get header names from env override(s) plus defaults, preserving order."""
    seen: set[str] = set()

    env_headers = os.getenv(env_var_name, "")
    if env_headers:
        for raw_header in env_headers.split(","):
            header = raw_header.strip().lower()
            if header and header not in seen:
                seen.add(header)
                yield header

    for header in defaults:
        normalized = header.lower()
        if normalized not in seen:
            seen.add(normalized)
            yield normalized


def _first_header_value(request: Request, header_names: Iterable[str]) -> str | None:
    """Return first non-empty header value from provided header names."""
    for header_name in header_names:
        value = request.headers.get(header_name)
        if value:
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def get_discord_identity(request: Request) -> tuple[str | None, str | None]:
    """Extract Discord identity from trusted forwarded headers."""
    if is_discord_auth_bypass_enabled():
        return (
            os.getenv("DISCORD_AUTH_BYPASS_USER_ID", "dev-bypass"),
            os.getenv("DISCORD_AUTH_BYPASS_USERNAME", "Dev Bypass"),
        )

    user_id = _first_header_value(
        request,
        _iter_header_names(
            "DISCORD_AUTH_USER_ID_HEADERS",
            DEFAULT_DISCORD_USER_ID_HEADERS,
        ),
    )
    username = _first_header_value(
        request,
        _iter_header_names(
            "DISCORD_AUTH_USERNAME_HEADERS",
            DEFAULT_DISCORD_USERNAME_HEADERS,
        ),
    )
    return user_id, username


def get_discord_login_url() -> str:
    """Get Discord login URL used by frontend login CTA."""
    return os.getenv("DISCORD_LOGIN_URL", "/auth/discord/login")
