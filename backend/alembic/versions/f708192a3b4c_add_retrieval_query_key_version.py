"""add retrieval query fingerprint key version

Revision ID: f708192a3b4c
Revises: e6f708192a3b
Create Date: 2026-07-12 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f708192a3b4c"
down_revision: Union[str, Sequence[str], None] = "e6f708192a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rag_retrieval_traces",
        sa.Column("query_key_version", sa.String(length=50), nullable=True),
    )
    op.execute(
        "UPDATE rag_retrieval_traces "
        "SET query_key_version = 'legacy-unkeyed-v1' "
        "WHERE query_key_version IS NULL"
    )
    op.alter_column(
        "rag_retrieval_traces",
        "query_key_version",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("rag_retrieval_traces", "query_key_version")
