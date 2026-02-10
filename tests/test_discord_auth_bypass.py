"""Tests for Discord auth bypass behavior in development."""

from __future__ import annotations

from starlette.requests import Request

from vote_api.services.discord_auth import (
    get_discord_identity,
    is_discord_auth_bypass_enabled,
)


def _build_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("utf-8"), value.encode("utf-8")))

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
    }
    return Request(scope)


def test_discord_identity_uses_forwarded_headers_when_bypass_disabled(monkeypatch):
    monkeypatch.delenv("DISCORD_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("DISCORD_AUTH_BYPASS_IN_DEV", "false")

    request = _build_request(
        {
            "x-discord-user-id": "12345",
            "x-discord-username": "player",
        }
    )

    user_id, username = get_discord_identity(request)
    assert user_id == "12345"
    assert username == "player"


def test_discord_auth_bypass_enabled_in_dev_with_flag(monkeypatch):
    monkeypatch.delenv("DISCORD_AUTH_BYPASS", raising=False)
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("DISCORD_AUTH_BYPASS_IN_DEV", "true")

    assert is_discord_auth_bypass_enabled() is True

    user_id, username = get_discord_identity(_build_request())
    assert user_id == "dev-bypass"
    assert username == "Dev Bypass"


def test_discord_auth_bypass_enabled_globally(monkeypatch):
    monkeypatch.setenv("DISCORD_AUTH_BYPASS", "true")
    monkeypatch.setenv("DEV_MODE", "false")
    monkeypatch.setenv("DISCORD_AUTH_BYPASS_IN_DEV", "false")
    monkeypatch.setenv("DISCORD_AUTH_BYPASS_USER_ID", "local-user")
    monkeypatch.setenv("DISCORD_AUTH_BYPASS_USERNAME", "Local Tester")

    assert is_discord_auth_bypass_enabled() is True

    user_id, username = get_discord_identity(_build_request())
    assert user_id == "local-user"
    assert username == "Local Tester"
