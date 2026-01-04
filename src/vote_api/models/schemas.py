"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from vote_api.models.enums import ComparisonMode


# Request schemas
class VoteRequest(BaseModel):
    """Request body for submitting a vote."""

    category_id: int
    fingerprint: str = Field(..., min_length=64, max_length=64)
    choices: list[int] = Field(..., min_length=1, description="Item IDs in preference order")
    comment: Optional[str] = Field(None, max_length=1000)


class CommentRequest(BaseModel):
    """Request body for submitting a comment."""

    vote_id: int
    content: str = Field(..., min_length=1, max_length=1000)


# Response schemas
class ItemResponse(BaseModel):
    """Item in API responses."""

    id: int
    name: str
    image_url: Optional[str] = None
    group_name: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    """Category in API responses."""

    id: int
    name: str
    description: Optional[str] = None
    comparison_mode: ComparisonMode
    is_active: bool
    settings: dict = Field(default_factory=dict)
    items: list[ItemResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    """List of categories."""

    categories: list[CategoryResponse]
    total: int


class VoteResponse(BaseModel):
    """Response after submitting a vote."""

    success: bool
    vote_id: int
    message: str


class VoteStatusResponse(BaseModel):
    """Response for vote status check."""

    has_voted: bool
    vote_id: Optional[int] = None
    voted_at: Optional[datetime] = None


class ItemResultResponse(BaseModel):
    """Individual item result with statistics."""

    item_id: int
    item_name: str
    image_url: Optional[str] = None
    vote_count: int
    percentage: float
    wilson_lower: Optional[float] = None
    wilson_upper: Optional[float] = None
    elo_rating: Optional[float] = None
    games_played: Optional[int] = None
    average_rank: Optional[float] = None
    metadata: dict = Field(default_factory=dict)


class ResultsResponse(BaseModel):
    """Full results for a category."""

    category_id: int
    category_name: str
    comparison_mode: ComparisonMode
    total_votes: int
    results: list[ItemResultResponse]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
