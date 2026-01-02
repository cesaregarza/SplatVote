"""Statistical calculations for voting results."""

import math
from typing import Optional


def calculate_percentage(votes: int, total: int) -> float:
    """Calculate simple percentage."""
    if total == 0:
        return 0.0
    return (votes / total) * 100


def wilson_confidence_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Calculate Wilson score confidence interval.

    The Wilson score interval is a binomial proportion confidence interval
    that works well even with small sample sizes and extreme proportions.

    Args:
        successes: Number of successes (votes for this item)
        total: Total number of trials (total votes)
        confidence: Confidence level (0.90, 0.95, or 0.99)

    Returns:
        (lower_bound, upper_bound) as percentages (0-100)
    """
    if total == 0:
        return (0.0, 0.0)

    # Z-score for common confidence levels
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    p = successes / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator

    lower = max(0, center - spread) * 100
    upper = min(1, center + spread) * 100

    return (round(lower, 2), round(upper, 2))


def calculate_average_rank(
    rankings: list[Optional[int]],
) -> Optional[float]:
    """
    Calculate average rank from a list of rankings.

    Args:
        rankings: List of rank positions (1 = first, 2 = second, etc.)
                  None values are ignored.

    Returns:
        Average rank or None if no valid rankings.
    """
    valid_ranks = [r for r in rankings if r is not None]
    if not valid_ranks:
        return None
    return round(sum(valid_ranks) / len(valid_ranks), 2)


def borda_count(
    rankings: list[list[int]],
    num_items: int,
) -> dict[int, int]:
    """
    Calculate Borda count scores from ranked lists.

    In Borda count, each voter ranks candidates. The candidate ranked first
    gets N-1 points, second gets N-2 points, etc., where N is the number
    of candidates.

    Args:
        rankings: List of ranked lists, each containing item_ids in preference order
        num_items: Total number of items being ranked

    Returns:
        Dictionary mapping item_id to total Borda score
    """
    scores: dict[int, int] = {}

    for ranking in rankings:
        for position, item_id in enumerate(ranking):
            # Higher rank = more points (N-1 for 1st, N-2 for 2nd, etc.)
            points = len(ranking) - 1 - position
            scores[item_id] = scores.get(item_id, 0) + points

    return scores
