"""Initial voting schema.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create voting schema
    op.execute("CREATE SCHEMA IF NOT EXISTS voting")

    # Item Groups
    op.create_table(
        "item_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_url", sa.String(512), nullable=True),
        schema="voting",
    )

    # Items
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("voting.item_groups.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        schema="voting",
    )

    # Categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("comparison_mode", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False
        ),
        schema="voting",
    )

    # Category Items junction table
    op.create_table(
        "category_items",
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("voting.categories.id"),
            primary_key=True,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("voting.items.id"),
            primary_key=True,
        ),
        schema="voting",
    )

    # Votes
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("voting.categories.id"),
            nullable=False,
        ),
        sa.Column("fingerprint_hash", sa.String(64), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False
        ),
        sa.UniqueConstraint(
            "category_id", "fingerprint_hash", name="uq_vote_per_fingerprint"
        ),
        schema="voting",
    )

    # Vote Choices
    op.create_table(
        "vote_choices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vote_id",
            sa.Integer(),
            sa.ForeignKey("voting.votes.id"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("voting.items.id"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.UniqueConstraint("vote_id", "item_id", name="uq_choice_per_vote"),
        schema="voting",
    )

    # Comments
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vote_id",
            sa.Integer(),
            sa.ForeignKey("voting.votes.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False
        ),
        schema="voting",
    )

    # ELO Ratings
    op.create_table(
        "elo_ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("voting.categories.id"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("voting.items.id"),
            nullable=False,
        ),
        sa.Column("rating", sa.Float(), server_default="1500", nullable=False),
        sa.Column("games_played", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False
        ),
        sa.UniqueConstraint("category_id", "item_id", name="uq_elo_per_item"),
        schema="voting",
    )

    # Indexes for performance
    op.create_index(
        "idx_votes_category", "votes", ["category_id"], schema="voting"
    )
    op.create_index(
        "idx_votes_fingerprint", "votes", ["fingerprint_hash"], schema="voting"
    )
    op.create_index(
        "idx_elo_category", "elo_ratings", ["category_id"], schema="voting"
    )
    op.create_index("idx_items_group", "items", ["group_id"], schema="voting")


def downgrade() -> None:
    op.drop_table("elo_ratings", schema="voting")
    op.drop_table("comments", schema="voting")
    op.drop_table("vote_choices", schema="voting")
    op.drop_table("votes", schema="voting")
    op.drop_table("category_items", schema="voting")
    op.drop_table("categories", schema="voting")
    op.drop_table("items", schema="voting")
    op.drop_table("item_groups", schema="voting")
    op.execute("DROP SCHEMA IF EXISTS voting")
