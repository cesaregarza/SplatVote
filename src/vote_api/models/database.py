"""SQLAlchemy ORM models for the voting system."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class ItemGroup(Base):
    """Groups of items (e.g., Weapons, Maps, Modes)."""

    __tablename__ = "item_groups"
    __table_args__ = {"schema": "voting"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    items: Mapped[list["Item"]] = relationship("Item", back_populates="group")


class Item(Base):
    """Individual items that can be voted on."""

    __tablename__ = "items"
    __table_args__ = {"schema": "voting"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("voting.item_groups.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # Relationships
    group: Mapped[Optional["ItemGroup"]] = relationship(
        "ItemGroup", back_populates="items"
    )
    category_items: Mapped[list["CategoryItem"]] = relationship(
        "CategoryItem", back_populates="item"
    )
    vote_choices: Mapped[list["VoteChoice"]] = relationship(
        "VoteChoice", back_populates="item"
    )
    elo_ratings: Mapped[list["EloRating"]] = relationship(
        "EloRating", back_populates="item"
    )


class Category(Base):
    """Voting categories with different comparison modes."""

    __tablename__ = "categories"
    __table_args__ = {"schema": "voting"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comparison_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    category_items: Mapped[list["CategoryItem"]] = relationship(
        "CategoryItem", back_populates="category"
    )
    votes: Mapped[list["Vote"]] = relationship("Vote", back_populates="category")
    elo_ratings: Mapped[list["EloRating"]] = relationship(
        "EloRating", back_populates="category"
    )


class CategoryItem(Base):
    """Junction table linking items to categories."""

    __tablename__ = "category_items"
    __table_args__ = {"schema": "voting"}

    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.categories.id"), primary_key=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.items.id"), primary_key=True
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category", back_populates="category_items"
    )
    item: Mapped["Item"] = relationship("Item", back_populates="category_items")


class Vote(Base):
    """Individual votes with fingerprint deduplication."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "fingerprint_hash", name="uq_vote_per_fingerprint"
        ),
        {"schema": "voting"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.categories.id"), nullable=False
    )
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="votes")
    choices: Mapped[list["VoteChoice"]] = relationship(
        "VoteChoice", back_populates="vote", cascade="all, delete-orphan"
    )
    comment: Mapped[Optional["Comment"]] = relationship(
        "Comment", back_populates="vote", uselist=False
    )


class VoteChoice(Base):
    """Individual choices within a vote (supports ranking)."""

    __tablename__ = "vote_choices"
    __table_args__ = (
        UniqueConstraint("vote_id", "item_id", name="uq_choice_per_vote"),
        {"schema": "voting"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.votes.id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.items.id"), nullable=False
    )
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    vote: Mapped["Vote"] = relationship("Vote", back_populates="choices")
    item: Mapped["Item"] = relationship("Item", back_populates="vote_choices")


class Comment(Base):
    """Optional comments on votes."""

    __tablename__ = "comments"
    __table_args__ = {"schema": "voting"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.votes.id"), nullable=False, unique=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    vote: Mapped["Vote"] = relationship("Vote", back_populates="comment")


class EloRating(Base):
    """ELO ratings for tournament-style categories."""

    __tablename__ = "elo_ratings"
    __table_args__ = (
        UniqueConstraint("category_id", "item_id", name="uq_elo_per_item"),
        {"schema": "voting"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.categories.id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voting.items.id"), nullable=False
    )
    rating: Mapped[float] = mapped_column(Float, default=1500.0, nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category", back_populates="elo_ratings"
    )
    item: Mapped["Item"] = relationship("Item", back_populates="elo_ratings")
