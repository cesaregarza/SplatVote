"""Authentication helper endpoints."""

from fastapi import APIRouter, Request

from vote_api.services.discord_auth import (
    get_discord_identity,
    get_discord_login_url,
    is_discord_auth_bypass_enabled,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/discord/status", response_model=dict)
async def get_discord_status(request: Request) -> dict:
    """Return whether request has a Discord-authenticated user context."""
    user_id, username = get_discord_identity(request)
    bypass_enabled = is_discord_auth_bypass_enabled()
    return {
        "authenticated": bool(user_id),
        "user_id": user_id,
        "username": username,
        "login_url": get_discord_login_url(),
        "bypass_enabled": bypass_enabled,
    }
