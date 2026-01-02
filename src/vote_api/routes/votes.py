"""Vote submission endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vote_api.connections import get_db_session, get_redis
from vote_api.models.database import (
    Category,
    CategoryItem,
    Comment,
    Vote,
    VoteChoice,
)
from vote_api.models.enums import ComparisonMode
from vote_api.models.schemas import (
    CommentRequest,
    VoteRequest,
    VoteResponse,
    VoteStatusResponse,
)
from vote_api.services.elo import EloService
from vote_api.services.fingerprint import (
    AntiManipulationService,
    get_vote_identity,
    validate_fingerprint,
)

router = APIRouter(prefix="/api/v1", tags=["votes"])


@router.post("/vote", response_model=VoteResponse)
async def submit_vote(
    request: Request,
    vote_request: VoteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VoteResponse:
    """Submit a vote for a category."""
    # Validate fingerprint format
    if not validate_fingerprint(vote_request.fingerprint):
        raise HTTPException(status_code=400, detail="Invalid fingerprint format")

    # Get vote identity
    fingerprint_hash, ip_hash = get_vote_identity(request, vote_request.fingerprint)

    # Check for manipulation
    redis_client = get_redis()
    anti_manipulation = AntiManipulationService(redis_client)
    is_suspicious, reason = anti_manipulation.check_suspicious_patterns(
        ip_hash, fingerprint_hash
    )
    if is_suspicious:
        raise HTTPException(status_code=429, detail=f"Suspicious activity: {reason}")

    # Get category
    result = await session.execute(
        select(Category).where(Category.id == vote_request.category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not category.is_active:
        raise HTTPException(status_code=400, detail="Category is not active")

    # Check if user already voted
    existing_vote = await session.execute(
        select(Vote).where(
            Vote.category_id == vote_request.category_id,
            Vote.fingerprint_hash == fingerprint_hash,
        )
    )
    if existing_vote.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already voted in this category")

    # Validate that all choices are valid items for this category
    valid_items = await session.execute(
        select(CategoryItem.item_id).where(
            CategoryItem.category_id == vote_request.category_id
        )
    )
    valid_item_ids = {row[0] for row in valid_items.all()}

    for item_id in vote_request.choices:
        if item_id not in valid_item_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Item {item_id} is not valid for this category",
            )

    # Validate choice count based on comparison mode
    if category.comparison_mode == ComparisonMode.SINGLE_CHOICE.value:
        if len(vote_request.choices) != 1:
            raise HTTPException(
                status_code=400,
                detail="Single choice mode requires exactly one choice",
            )
    elif category.comparison_mode == ComparisonMode.ELO_TOURNAMENT.value:
        if len(vote_request.choices) != 2:
            raise HTTPException(
                status_code=400,
                detail="ELO tournament mode requires exactly two choices (winner, loser)",
            )
    elif category.comparison_mode == ComparisonMode.RANKED_LIST.value:
        if len(vote_request.choices) < 2:
            raise HTTPException(
                status_code=400,
                detail="Ranked list mode requires at least two choices",
            )

    # Create vote
    vote = Vote(
        category_id=vote_request.category_id,
        fingerprint_hash=fingerprint_hash,
        ip_hash=ip_hash,
    )
    session.add(vote)
    await session.flush()

    # Create vote choices
    for rank, item_id in enumerate(vote_request.choices):
        choice = VoteChoice(
            vote_id=vote.id,
            item_id=item_id,
            rank=rank + 1 if category.comparison_mode == ComparisonMode.RANKED_LIST.value else None,
        )
        session.add(choice)

    # Handle ELO updates for tournament mode
    if category.comparison_mode == ComparisonMode.ELO_TOURNAMENT.value:
        winner_id, loser_id = vote_request.choices[0], vote_request.choices[1]
        elo_service = EloService(session)
        await elo_service.record_match(category.id, winner_id, loser_id)

    # Add comment if provided
    if vote_request.comment:
        comment = Comment(
            vote_id=vote.id,
            content=vote_request.comment,
            is_approved=False,
        )
        session.add(comment)

    await session.commit()

    # Record attempt
    anti_manipulation.record_vote_attempt(
        ip_hash, fingerprint_hash, vote_request.category_id, success=True
    )

    return VoteResponse(
        success=True,
        vote_id=vote.id,
        message="Vote recorded successfully",
    )


@router.get("/vote/status/{category_id}", response_model=VoteStatusResponse)
async def get_vote_status(
    request: Request,
    category_id: int,
    fingerprint: str,
    session: AsyncSession = Depends(get_db_session),
) -> VoteStatusResponse:
    """Check if the current user has voted in a category."""
    if not validate_fingerprint(fingerprint):
        raise HTTPException(status_code=400, detail="Invalid fingerprint format")

    fingerprint_hash, _ = get_vote_identity(request, fingerprint)

    result = await session.execute(
        select(Vote).where(
            Vote.category_id == category_id,
            Vote.fingerprint_hash == fingerprint_hash,
        )
    )
    vote = result.scalar_one_or_none()

    if vote:
        return VoteStatusResponse(
            has_voted=True,
            vote_id=vote.id,
            voted_at=vote.created_at,
        )
    return VoteStatusResponse(has_voted=False)


@router.post("/comments", response_model=dict)
async def submit_comment(
    comment_request: CommentRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Submit a comment on an existing vote."""
    # Check if vote exists
    result = await session.execute(
        select(Vote).where(Vote.id == comment_request.vote_id)
    )
    vote = result.scalar_one_or_none()
    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

    # Check if comment already exists
    existing = await session.execute(
        select(Comment).where(Comment.vote_id == comment_request.vote_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Comment already exists for this vote")

    comment = Comment(
        vote_id=comment_request.vote_id,
        content=comment_request.content,
        is_approved=False,
    )
    session.add(comment)
    await session.commit()

    return {"success": True, "message": "Comment submitted for approval"}
