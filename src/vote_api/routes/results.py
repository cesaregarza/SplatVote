"""Results and statistics endpoints."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vote_api.connections import get_db_session
from vote_api.models.database import (
    Category,
    CategoryItem,
    EloRating,
    Item,
    Vote,
    VoteChoice,
)
from vote_api.models.enums import ComparisonMode
from vote_api.models.schemas import ItemResultResponse, ResultsResponse
from vote_api.services.fingerprint import get_vote_identity, validate_fingerprint
from vote_api.services.statistics import (
    calculate_average_rank,
    calculate_percentage,
    wilson_confidence_interval,
)

router = APIRouter(prefix="/api/v1/results", tags=["results"])


@router.get("/{category_id}", response_model=ResultsResponse)
async def get_results(
    category_id: int,
    request: Request,
    fingerprint: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ResultsResponse:
    """Get voting results for a category with statistics."""
    # Get category with items
    result = await session.execute(
        select(Category)
        .options(selectinload(Category.category_items).selectinload(CategoryItem.item))
        .where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    settings = category.settings or {}
    if settings.get("private_results"):
        if not fingerprint or not validate_fingerprint(fingerprint):
            raise HTTPException(
                status_code=403,
                detail="Results are private until you vote",
            )
        fingerprint_hash, _ = get_vote_identity(request, fingerprint)
        vote_result = await session.execute(
            select(Vote.id).where(
                Vote.category_id == category_id,
                Vote.fingerprint_hash == fingerprint_hash,
            )
        )
        if not vote_result.scalar_one_or_none():
            raise HTTPException(
                status_code=403,
                detail="Results are private until you vote",
            )

    # Get total vote count
    total_result = await session.execute(
        select(func.count(Vote.id)).where(Vote.category_id == category_id)
    )
    total_votes = total_result.scalar() or 0

    # Build item lookup
    items_by_id = {
        cat_item.item.id: cat_item.item for cat_item in category.category_items
    }

    # Calculate results based on comparison mode
    if category.comparison_mode == ComparisonMode.SINGLE_CHOICE.value:
        results = await _calculate_single_choice_results(
            session, category_id, items_by_id, total_votes
        )
    elif category.comparison_mode == ComparisonMode.ELO_TOURNAMENT.value:
        results = await _calculate_elo_results(session, category_id, items_by_id)
    elif category.comparison_mode == ComparisonMode.RANKED_LIST.value:
        results = await _calculate_ranked_results(
            session, category_id, items_by_id, total_votes
        )
    elif category.comparison_mode == ComparisonMode.TOURNAMENT_TIERS.value:
        results = await _calculate_tournament_tiers_results(
            session, category_id, items_by_id, total_votes, category.settings
        )
    else:
        results = []

    return ResultsResponse(
        category_id=category.id,
        category_name=category.name,
        comparison_mode=category.comparison_mode,
        total_votes=total_votes,
        results=results,
    )


async def _calculate_single_choice_results(
    session: AsyncSession,
    category_id: int,
    items_by_id: dict[int, Item],
    total_votes: int,
) -> list[ItemResultResponse]:
    """Calculate results for single choice voting."""
    # Count votes per item
    vote_counts = await session.execute(
        select(VoteChoice.item_id, func.count(VoteChoice.id))
        .join(Vote)
        .where(Vote.category_id == category_id)
        .group_by(VoteChoice.item_id)
    )
    counts = {row[0]: row[1] for row in vote_counts.all()}

    results = []
    for item_id, item in items_by_id.items():
        vote_count = counts.get(item_id, 0)
        percentage = calculate_percentage(vote_count, total_votes)
        wilson_lower, wilson_upper = wilson_confidence_interval(vote_count, total_votes)

        results.append(
            ItemResultResponse(
                item_id=item_id,
                item_name=item.name,
                image_url=item.image_url,
                vote_count=vote_count,
                percentage=round(percentage, 2),
                wilson_lower=wilson_lower,
                wilson_upper=wilson_upper,
            )
        )

    # Sort by percentage descending
    results.sort(key=lambda x: x.percentage, reverse=True)
    return results


async def _calculate_elo_results(
    session: AsyncSession,
    category_id: int,
    items_by_id: dict[int, Item],
) -> list[ItemResultResponse]:
    """Calculate results for ELO tournament voting."""
    # Get ELO ratings
    ratings_result = await session.execute(
        select(EloRating).where(EloRating.category_id == category_id)
    )
    ratings = {r.item_id: r for r in ratings_result.scalars().all()}

    # Count total games for percentage calculation
    total_games = sum(r.games_played for r in ratings.values()) // 2  # Each game has 2 players

    results = []
    for item_id, item in items_by_id.items():
        rating = ratings.get(item_id)
        games_played = rating.games_played if rating else 0
        elo_rating = rating.rating if rating else 1500.0

        # Calculate win percentage from games
        wins = 0
        if rating and games_played > 0:
            # Estimate wins from ELO change
            # This is approximate; for exact wins, we'd need to track them
            wins = max(0, int((elo_rating - 1500) / 32 + games_played / 2))

        percentage = calculate_percentage(games_played, total_games * 2) if total_games else 0

        results.append(
            ItemResultResponse(
                item_id=item_id,
                item_name=item.name,
                image_url=item.image_url,
                vote_count=games_played,
                percentage=round(percentage, 2),
                elo_rating=round(elo_rating, 2),
                games_played=games_played,
            )
        )

    # Sort by ELO rating descending
    results.sort(key=lambda x: x.elo_rating or 0, reverse=True)
    return results


async def _calculate_ranked_results(
    session: AsyncSession,
    category_id: int,
    items_by_id: dict[int, Item],
    total_votes: int,
) -> list[ItemResultResponse]:
    """Calculate results for ranked list voting."""
    # Get all rankings
    rankings_result = await session.execute(
        select(VoteChoice.item_id, VoteChoice.rank)
        .join(Vote)
        .where(Vote.category_id == category_id, VoteChoice.rank.isnot(None))
    )

    # Group rankings by item
    item_rankings: dict[int, list[int]] = defaultdict(list)
    for item_id, rank in rankings_result.all():
        item_rankings[item_id].append(rank)

    results = []
    for item_id, item in items_by_id.items():
        ranks = item_rankings.get(item_id, [])
        vote_count = len(ranks)
        average_rank = calculate_average_rank(ranks)

        # For percentage, use how often item was ranked 1st
        first_place_count = sum(1 for r in ranks if r == 1)
        percentage = calculate_percentage(first_place_count, total_votes)

        results.append(
            ItemResultResponse(
                item_id=item_id,
                item_name=item.name,
                image_url=item.image_url,
                vote_count=vote_count,
                percentage=round(percentage, 2),
                average_rank=average_rank,
            )
        )

    # Sort by average rank ascending (lower is better)
    results.sort(key=lambda x: x.average_rank or float("inf"))
    return results


async def _calculate_tournament_tiers_results(
    session: AsyncSession,
    category_id: int,
    items_by_id: dict[int, Item],
    total_votes: int,
    settings: dict,
) -> list[ItemResultResponse]:
    """Calculate results for tournament tier voting."""
    tier_options = settings.get("tier_options", ["X", "S+", "S", "A", "B", "C", "D"])

    # Get all tier votes (rank field stores tier index)
    tier_votes_result = await session.execute(
        select(VoteChoice.item_id, VoteChoice.rank)
        .join(Vote)
        .where(Vote.category_id == category_id, VoteChoice.rank.isnot(None))
    )

    # Group tier votes by item
    item_tiers: dict[int, list[int]] = defaultdict(list)
    for item_id, tier_index in tier_votes_result.all():
        item_tiers[item_id].append(tier_index)

    results = []
    for item_id, item in items_by_id.items():
        tiers = item_tiers.get(item_id, [])
        vote_count = len(tiers)

        # Calculate tier distribution
        tier_counts = defaultdict(int)
        for tier_idx in tiers:
            tier_counts[tier_idx] += 1

        # Build tier distribution dict with tier names
        tier_distribution = {}
        for idx, tier_name in enumerate(tier_options):
            tier_distribution[tier_name] = tier_counts.get(idx, 0)

        # Calculate average tier (lower index = higher tier)
        average_tier = None
        if tiers:
            # Filter out "Don't know" votes (last tier) for average
            known_tiers = [t for t in tiers if t < len(tier_options) - 1]
            if known_tiers:
                average_tier = round(sum(known_tiers) / len(known_tiers), 2)

        # Get item metadata for display name
        metadata = item.metadata_ or {}

        results.append(
            ItemResultResponse(
                item_id=item_id,
                item_name=metadata.get("display_name", item.name),
                image_url=item.image_url,
                vote_count=vote_count,
                percentage=round(calculate_percentage(vote_count, total_votes), 2),
                average_rank=average_tier,
                metadata={"tier_distribution": tier_distribution},
            )
        )

    # Sort by average tier ascending (lower = better tier)
    results.sort(key=lambda x: x.average_rank if x.average_rank is not None else float("inf"))
    return results
