"""Admin endpoints for category management and moderation."""

import hashlib
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vote_api.connections import db_context, get_db_session
from vote_api.models.database import Category, Comment
from vote_api.services.category_sync import CategorySyncService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def verify_admin_token(x_admin_token: str = Header(...)) -> bool:
    """Verify admin token from header."""
    admin_tokens_hashed = os.getenv("ADMIN_API_TOKENS_HASHED", "")
    if not admin_tokens_hashed:
        raise HTTPException(status_code=500, detail="Admin tokens not configured")

    # Hash the provided token with pepper
    pepper = os.getenv("ADMIN_TOKEN_PEPPER", os.getenv("VOTE_IP_PEPPER", ""))
    token_hash = hashlib.sha256((pepper + x_admin_token).encode()).hexdigest()

    # Check if hash matches any configured admin token
    valid_hashes = [h.strip() for h in admin_tokens_hashed.split(",")]
    if token_hash not in valid_hashes:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    return True


@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_admin_token),
) -> dict[str, Any]:
    """Trigger category sync from YAML files."""

    async def do_sync():
        async with db_context() as session:
            sync_service = CategorySyncService(session)
            await sync_service.sync_all()

    background_tasks.add_task(do_sync)
    return {"status": "sync_initiated", "message": "Category sync started in background"}


@router.post("/sync/blocking")
async def trigger_sync_blocking(
    _: bool = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Trigger category sync and wait for completion."""
    sync_service = CategorySyncService(session)
    results = await sync_service.sync_all()
    return {"status": "completed", "results": results}


@router.get("/categories")
async def list_all_categories(
    _: bool = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List all categories including inactive ones."""
    result = await session.execute(
        select(Category).order_by(Category.created_at.desc())
    )
    categories = list(result.scalars().all())

    return {
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "comparison_mode": cat.comparison_mode,
                "is_active": cat.is_active,
                "created_at": cat.created_at.isoformat(),
            }
            for cat in categories
        ],
        "total": len(categories),
    }


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    is_active: bool,
    _: bool = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Update category status."""
    result = await session.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    category.is_active = is_active
    await session.commit()

    return {"success": True, "message": f"Category {'activated' if is_active else 'deactivated'}"}


@router.get("/comments/pending")
async def list_pending_comments(
    _: bool = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List comments pending approval."""
    result = await session.execute(
        select(Comment)
        .where(Comment.is_approved == False)
        .order_by(Comment.created_at.desc())
    )
    comments = list(result.scalars().all())

    return {
        "comments": [
            {
                "id": c.id,
                "vote_id": c.vote_id,
                "content": c.content,
                "created_at": c.created_at.isoformat(),
            }
            for c in comments
        ],
        "total": len(comments),
    }


@router.put("/comments/{comment_id}/approve")
async def approve_comment(
    comment_id: int,
    approve: bool = True,
    _: bool = Depends(verify_admin_token),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Approve or reject a comment."""
    result = await session.execute(
        select(Comment).where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if approve:
        comment.is_approved = True
        await session.commit()
        return {"success": True, "message": "Comment approved"}
    else:
        await session.delete(comment)
        await session.commit()
        return {"success": True, "message": "Comment rejected and deleted"}
