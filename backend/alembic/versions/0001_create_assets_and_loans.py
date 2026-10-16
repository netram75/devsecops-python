"""create assets and loans

Revision ID: 0001
Revises:
Create Date: 2026-10-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tag", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="in_service"),
        sa.Column("location", sa.String(120), nullable=False, server_default=""),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tag", name="uq_assets_tag"),
        sa.CheckConstraint(
            "category IN ('camera', 'drone', 'audio', 'lab_kit', 'laptop', 'vr')",
            name="ck_assets_category",
        ),
        sa.CheckConstraint(
            "state IN ('in_service', 'maintenance', 'retired')", name="ck_assets_state"
        ),
        sa.CheckConstraint("length(tag) >= 3", name="ck_assets_tag_length"),
    )
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id", ondelete="RESTRICT", name="fk_loans_asset"),
            nullable=False,
        ),
        sa.Column("borrower_name", sa.String(80), nullable=False),
        sa.Column("borrower_roll", sa.String(20), nullable=False),
        sa.Column("borrower_email", sa.String(120), nullable=False),
        sa.Column("purpose", sa.String(200), nullable=False, server_default=""),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="reserved"),
        sa.Column("checked_out_at", sa.DateTime(timezone=True)),
        sa.Column("returned_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("due_date > start_date", name="ck_loans_dates"),
        sa.CheckConstraint(
            "status IN ('reserved', 'checked_out', 'returned', 'cancelled')",
            name="ck_loans_status",
        ),
        sa.CheckConstraint(
            "(status = 'returned') = (returned_at IS NOT NULL)", name="ck_loans_returned_at"
        ),
    )
    op.create_index("ix_loans_asset_status", "loans", ["asset_id", "status"])
    op.create_index("ix_loans_borrower_status", "loans", ["borrower_roll", "status"])


def downgrade() -> None:
    op.drop_index("ix_loans_borrower_status", table_name="loans")
    op.drop_index("ix_loans_asset_status", table_name="loans")
    op.drop_table("loans")
    op.drop_table("assets")
