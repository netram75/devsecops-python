"""audit trail: events table

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("entity", sa.String(10), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(240), nullable=False),
        sa.CheckConstraint("entity IN ('asset', 'loan')", name="ck_events_entity"),
    )
    op.create_index("ix_events_at", "events", ["at"])


def downgrade() -> None:
    op.drop_index("ix_events_at", table_name="events")
    op.drop_table("events")
