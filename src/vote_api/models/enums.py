"""Enumeration types for the voting system."""

from enum import Enum


class ComparisonMode(str, Enum):
    """Supported comparison modes for voting categories."""

    SINGLE_CHOICE = "single_choice"
    ELO_TOURNAMENT = "elo_tournament"
    RANKED_LIST = "ranked_list"
