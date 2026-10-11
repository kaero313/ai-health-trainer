"""add server default to ai_generation_traces.started_at

모델(app/models/rag.py AIGenerationTrace.started_at)은 server_default=now()를 갖지만
c4d5e6f70819는 컬럼을 NOT NULL로 바꾸면서 기본값을 두지 않았다. 마이그레이션으로 만든 DB와
create_all로 만든 테스트 DB의 스키마를 맞춘다. 기존 행은 이미 값이 있으므로 데이터는 바꾸지 않는다.

Revision ID: 4d4ea61f1957
Revises: b92a3b4c5d6e
Create Date: 2026-09-25 16:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d4ea61f1957"
down_revision: Union[str, Sequence[str], None] = "b92a3b4c5d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ai_generation_traces",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "ai_generation_traces",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=None,
    )
