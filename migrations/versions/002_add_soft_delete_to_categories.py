"""Add soft-delete flag to categories.

Revision ID: 002
Revises: 001
Create Date: 2026-02-10 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "is_soft_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="voting",
    )
    op.create_index(
        "idx_categories_soft_deleted",
        "categories",
        ["is_soft_deleted"],
        schema="voting",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_categories_soft_deleted",
        table_name="categories",
        schema="voting",
    )
    op.drop_column("categories", "is_soft_deleted", schema="voting")
