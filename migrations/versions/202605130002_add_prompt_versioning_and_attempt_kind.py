"""add prompt versioning and attempt kind

Revision ID: 202605130002
Revises: 202605130001
Create Date: 2026-05-13 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605130002"
down_revision: str | None = "202605130001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trace_records",
        sa.Column("prompt_template_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "trace_records",
        sa.Column("prompt_template_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "model_call_records",
        sa.Column(
            "attempt_kind",
            sa.String(length=32),
            nullable=False,
            server_default="primary",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_call_records", "attempt_kind")
    op.drop_column("trace_records", "prompt_template_version")
    op.drop_column("trace_records", "prompt_template_name")
