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

    # For tournament_tiers, only every other value is an item ID
    if category.comparison_mode == ComparisonMode.TOURNAMENT_TIERS.value:
        item_ids_to_check = vote_request.choices[::2]  # Every other element starting at 0
    else:
        item_ids_to_check = vote_request.choices

    for item_id in item_ids_to_check:
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
        if vote_request.choices[0] == vote_request.choices[1]:
            raise HTTPException(
                status_code=400,
                detail="Winner and loser must be different items",
            )
    elif category.comparison_mode == ComparisonMode.RANKED_LIST.value:
        if len(vote_request.choices) < 2:
            raise HTTPException(
                status_code=400,
                detail="Ranked list mode requires at least two choices",
            )
    elif category.comparison_mode == ComparisonMode.TOURNAMENT_TIERS.value:
        # Format: [item_id, tier_index, item_id, tier_index, ...]
        if len(vote_request.choices) % 2 != 0:
            raise HTTPException(
                status_code=400,
                detail="Tournament tiers mode requires pairs of (item_id, tier_index)",
            )
        if len(vote_request.choices) < 2:
            raise HTTPException(
                status_code=400,
                detail="Tournament tiers mode requires at least one vote",
            )
        # Validate tier indices
        tier_options = category.settings.get("tier_options", [])
        num_tiers = len(tier_options) if tier_options else 7
        for i in range(1, len(vote_request.choices), 2):
            tier_idx = vote_request.choices[i]
            if tier_idx < 0 or tier_idx >= num_tiers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tier index: {tier_idx}",
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
    if category.comparison_mode == ComparisonMode.TOURNAMENT_TIERS.value:
        # Handle pairs: [item_id, tier_index, item_id, tier_index, ...]
        for i in range(0, len(vote_request.choices), 2):
            item_id = vote_request.choices[i]
            tier_index = vote_request.choices[i + 1]
            choice = VoteChoice(
                vote_id=vote.id,
                item_id=item_id,
                rank=tier_index,  # Store tier index in rank field
            )
            session.add(choice)
    else:
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


@router.post("/vote/upsert", response_model=VoteResponse)
async def upsert_vote(
    request: Request,
    vote_request: VoteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VoteResponse:
    """Upsert a single vote choice for tournament_tiers mode.

    Creates vote record if needed, then upserts the choice for one item.
    Expects choices as [item_id, tier_index] for a single item.
    """
    # Validate fingerprint format
    if not validate_fingerprint(vote_request.fingerprint):
        raise HTTPException(status_code=400, detail="Invalid fingerprint format")

    # Get vote identity
    fingerprint_hash, ip_hash = get_vote_identity(request, vote_request.fingerprint)

    # Get category
    result = await session.execute(
        select(Category).where(Category.id == vote_request.category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if not category.is_active:
        raise HTTPException(status_code=400, detail="Category is not active")

    # Only allow upsert for tournament_tiers mode
    if category.comparison_mode != ComparisonMode.TOURNAMENT_TIERS.value:
        raise HTTPException(
            status_code=400,
            detail="Upsert only supported for tournament_tiers mode",
        )

    # Validate request format: [item_id, tier_index]
    if len(vote_request.choices) != 2:
        raise HTTPException(
            status_code=400,
            detail="Upsert requires exactly [item_id, tier_index]",
        )

    item_id, tier_index = vote_request.choices[0], vote_request.choices[1]

    # Validate item belongs to category
    valid_items = await session.execute(
        select(CategoryItem.item_id).where(
            CategoryItem.category_id == vote_request.category_id
        )
    )
    valid_item_ids = {row[0] for row in valid_items.all()}
    if item_id not in valid_item_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Item {item_id} is not valid for this category",
        )

    # Validate tier index
    tier_options = category.settings.get("tier_options", [])
    num_tiers = len(tier_options) if tier_options else 7
    if tier_index < 0 or tier_index >= num_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier index: {tier_index}")

    # Find or create vote record
    existing_vote = await session.execute(
        select(Vote).where(
            Vote.category_id == vote_request.category_id,
            Vote.fingerprint_hash == fingerprint_hash,
        )
    )
    vote = existing_vote.scalar_one_or_none()

    if vote is None:
        # Check for manipulation before creating new vote
        redis_client = get_redis()
        anti_manipulation = AntiManipulationService(redis_client)
        is_suspicious, reason = anti_manipulation.check_suspicious_patterns(
            ip_hash, fingerprint_hash
        )
        if is_suspicious:
            raise HTTPException(status_code=429, detail=f"Suspicious activity: {reason}")

        vote = Vote(
            category_id=vote_request.category_id,
            fingerprint_hash=fingerprint_hash,
            ip_hash=ip_hash,
        )
        session.add(vote)
        await session.flush()

    # Upsert vote choice
    existing_choice = await session.execute(
        select(VoteChoice).where(
            VoteChoice.vote_id == vote.id,
            VoteChoice.item_id == item_id,
        )
    )
    choice = existing_choice.scalar_one_or_none()

    if choice is None:
        choice = VoteChoice(
            vote_id=vote.id,
            item_id=item_id,
            rank=tier_index,
        )
        session.add(choice)
    else:
        choice.rank = tier_index

    await session.commit()

    return VoteResponse(
        success=True,
        vote_id=vote.id,
        message="Vote saved",
    )


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
