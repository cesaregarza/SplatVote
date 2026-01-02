"""ELO rating system for tournament-style voting."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vote_api.models.database import EloRating


def calculate_elo_update(
    winner_rating: float,
    loser_rating: float,
    k_factor: float = 32,
) -> tuple[float, float]:
    """
    Calculate new ELO ratings after a match.

    The ELO rating system calculates the expected probability of each player
    winning based on their rating difference, then adjusts ratings based on
    the actual outcome.

    Args:
        winner_rating: Current rating of the winner
        loser_rating: Current rating of the loser
        k_factor: Maximum rating change per game (higher = more volatile)

    Returns:
        (new_winner_rating, new_loser_rating)
    """
    # Expected score for winner (probability of winning)
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 - expected_winner

    # Actual scores: winner = 1, loser = 0
    new_winner = winner_rating + k_factor * (1 - expected_winner)
    new_loser = loser_rating + k_factor * (0 - expected_loser)

    return (round(new_winner, 2), round(new_loser, 2))


class EloService:
    """Service for managing ELO ratings in tournament-style categories."""

    def __init__(
        self,
        session: AsyncSession,
        initial_rating: float = 1500.0,
        k_factor: float = 32.0,
    ):
        self.session = session
        self.initial_rating = initial_rating
        self.k_factor = k_factor

    async def get_or_create_rating(
        self,
        category_id: int,
        item_id: int,
    ) -> EloRating:
        """Get existing rating or create a new one with initial rating."""
        result = await self.session.execute(
            select(EloRating).where(
                EloRating.category_id == category_id,
                EloRating.item_id == item_id,
            )
        )
        rating = result.scalar_one_or_none()

        if rating is None:
            rating = EloRating(
                category_id=category_id,
                item_id=item_id,
                rating=self.initial_rating,
                games_played=0,
            )
            self.session.add(rating)
            await self.session.flush()

        return rating

    async def record_match(
        self,
        category_id: int,
        winner_id: int,
        loser_id: int,
    ) -> tuple[float, float]:
        """
        Record a match result and update ELO ratings.

        Args:
            category_id: The category this match belongs to
            winner_id: Item ID of the winner
            loser_id: Item ID of the loser

        Returns:
            (new_winner_rating, new_loser_rating)
        """
        winner = await self.get_or_create_rating(category_id, winner_id)
        loser = await self.get_or_create_rating(category_id, loser_id)

        new_winner_rating, new_loser_rating = calculate_elo_update(
            winner.rating, loser.rating, self.k_factor
        )

        winner.rating = new_winner_rating
        winner.games_played += 1
        winner.updated_at = datetime.utcnow()

        loser.rating = new_loser_rating
        loser.games_played += 1
        loser.updated_at = datetime.utcnow()

        return (new_winner_rating, new_loser_rating)

    async def get_rankings(
        self,
        category_id: int,
        limit: Optional[int] = None,
    ) -> list[EloRating]:
        """Get ELO rankings for a category, sorted by rating descending."""
        query = (
            select(EloRating)
            .where(EloRating.category_id == category_id)
            .order_by(EloRating.rating.desc())
        )
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
