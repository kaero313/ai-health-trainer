"""add catalog source adapter fields

Revision ID: a8c4d2e6f901
Revises: f7d4c8b9a102
Create Date: 2026-05-05 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a8c4d2e6f901"
down_revision: Union[str, Sequence[str], None] = "f7d4c8b9a102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rag_catalog_plan_items", sa.Column("acquisition_type", sa.String(length=50), nullable=True))
    op.add_column("rag_catalog_plan_items", sa.Column("origin_uri", sa.String(length=1000), nullable=True))
    op.add_column("rag_catalog_plan_items", sa.Column("parser_type", sa.String(length=50), nullable=True))
    op.create_index(
        "ix_rag_catalog_plan_items_acquisition",
        "rag_catalog_plan_items",
        ["acquisition_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rag_catalog_plan_items_acquisition", table_name="rag_catalog_plan_items")
    op.drop_column("rag_catalog_plan_items", "parser_type")
    op.drop_column("rag_catalog_plan_items", "origin_uri")
    op.drop_column("rag_catalog_plan_items", "acquisition_type")
