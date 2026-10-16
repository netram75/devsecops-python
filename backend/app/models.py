from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

CATEGORIES = ("camera", "drone", "audio", "lab_kit", "laptop", "vr")
ASSET_STATES = ("in_service", "maintenance", "retired")
LOAN_STATUSES = ("reserved", "checked_out", "returned", "cancelled")
ACTIVE_LOAN_STATUSES = ("reserved", "checked_out")

# How long one loan may last, per category (days). Published through /api/info.
MAX_LOAN_DAYS = {"camera": 7, "drone": 3, "audio": 7, "lab_kit": 14, "laptop": 14, "vr": 5}


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(_in("category", CATEGORIES), name="ck_assets_category"),
        CheckConstraint(_in("state", ASSET_STATES), name="ck_assets_state"),
        CheckConstraint("length(tag) >= 3", name="ck_assets_tag_length"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="in_service")
    location: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    loans: Mapped[list["Loan"]] = relationship(back_populates="asset")


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("due_date > start_date", name="ck_loans_dates"),
        CheckConstraint(_in("status", LOAN_STATUSES), name="ck_loans_status"),
        CheckConstraint(
            "(status = 'returned') = (returned_at IS NOT NULL)", name="ck_loans_returned_at"
        ),
        Index("ix_loans_asset_status", "asset_id", "status"),
        Index("ix_loans_borrower_status", "borrower_roll", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False)
    borrower_name: Mapped[str] = mapped_column(String(80), nullable=False)
    borrower_roll: Mapped[str] = mapped_column(String(20), nullable=False)
    borrower_email: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reserved")
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped[Asset] = relationship(back_populates="loans")


class Event(Base):
    """Append-only audit trail; the UI shows it as the activity feed."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    entity: Mapped[str] = mapped_column(String(10), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    summary: Mapped[str] = mapped_column(String(240), nullable=False)
