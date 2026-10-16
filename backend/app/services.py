"""Lending rules. Routes stay thin; every rule lives here so it is tested once.

Concurrency: two backend replicas can receive conflicting requests at the same moment.
Before checking a rule we lock what the rule depends on, inside the transaction:
  * the asset row (SELECT ... FOR UPDATE) for the "no overlapping loans" rule
  * a per-borrower advisory lock for the "max active loans" rule
Locks are always taken in that order (borrower, then asset) so they cannot deadlock.
SQLite (tests) has no row locks; the checks still run, just without the lock.
"""
from datetime import date, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import clock
from .config import settings
from .db import is_postgres
from .metrics import LOAN_TRANSITIONS
from .models import ACTIVE_LOAN_STATUSES, MAX_LOAN_DAYS, Asset, Event, Loan
from .schemas import AssetCreate, AssetUpdate, LoanCreate, LoanUpdate


class RuleViolation(Exception):
    """A request that is well-formed but breaks a lending rule."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class NotFound(Exception):
    def __init__(self, what: str, ident: int):
        super().__init__(f"{what} {ident} not found")
        self.message = f"{what} {ident} not found"


# Allowed loan transitions: action -> (from status, to status)
TRANSITIONS = {
    "checkout": ("reserved", "checked_out"),
    "return": ("checked_out", "returned"),
    "cancel": ("reserved", "cancelled"),
}


def record(db: Session, entity: str, entity_id: int, action: str, summary: str) -> None:
    db.add(Event(entity=entity, entity_id=entity_id, action=action, summary=summary[:240]))


# ---------------------------------------------------------------- locks
def _lock_borrower(db: Session, roll: str) -> None:
    if is_postgres(db):
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"borrower:{roll}"})


def _lock_asset(db: Session, asset_id: int) -> Asset:
    asset = db.scalars(select(Asset).where(Asset.id == asset_id).with_for_update()).first()
    if asset is None:
        raise NotFound("asset", asset_id)
    return asset


# ---------------------------------------------------------------- helpers
def blocking_end(loan: Loan, today: date) -> date:
    """A checked-out item blocks the asset until it is physically back, even if overdue."""
    if loan.status == "checked_out":
        return max(loan.due_date, today + timedelta(days=1))
    return loan.due_date


def is_overdue(loan: Loan, today: date) -> bool:
    return loan.status == "checked_out" and loan.due_date < today


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFound("asset", asset_id)
    return asset


def get_loan(db: Session, loan_id: int) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise NotFound("loan", loan_id)
    return loan


def active_loans(db: Session, asset_id: int) -> list[Loan]:
    return list(
        db.scalars(
            select(Loan)
            .where(Loan.asset_id == asset_id, Loan.status.in_(ACTIVE_LOAN_STATUSES))
            .order_by(Loan.start_date)
        )
    )


def _check_window(category: str, start: date, due: date, today: date) -> None:
    if start < today:
        raise RuleViolation(422, "start_in_past", f"start_date {start} is in the past")
    if start > today + timedelta(days=settings.max_advance_days):
        raise RuleViolation(
            422,
            "too_far_ahead",
            f"reservations open at most {settings.max_advance_days} days ahead",
        )
    limit = MAX_LOAN_DAYS[category]
    if (due - start).days > limit:
        raise RuleViolation(
            422, "loan_too_long", f"{category} loans can last at most {limit} days"
        )


def _check_overlap(db: Session, asset: Asset, start: date, due: date, today: date, ignore_id=None):
    for other in active_loans(db, asset.id):
        if other.id == ignore_id:
            continue
        if other.start_date < due and start < blocking_end(other, today):
            raise RuleViolation(
                409,
                "asset_unavailable",
                f"{asset.tag} is already {other.status.replace('_', ' ')} "
                f"from {other.start_date} to {other.due_date} (loan #{other.id})",
            )


def _check_borrower_limit(db: Session, roll: str, ignore_id=None) -> None:
    q = select(func.count(Loan.id)).where(
        Loan.borrower_roll == roll, Loan.status.in_(ACTIVE_LOAN_STATUSES)
    )
    if ignore_id is not None:
        q = q.where(Loan.id != ignore_id)
    if db.scalar(q) >= settings.max_active_loans:
        raise RuleViolation(
            409,
            "borrower_limit",
            f"{roll} already has {settings.max_active_loans} active loans",
        )


# ---------------------------------------------------------------- assets
def create_asset(db: Session, data: AssetCreate) -> Asset:
    if db.scalar(select(Asset.id).where(Asset.tag == data.tag)) is not None:
        raise RuleViolation(409, "duplicate_tag", f"asset tag {data.tag} already exists")
    asset = Asset(**data.model_dump())
    db.add(asset)
    db.flush()
    record(db, "asset", asset.id, "created", f"Added {asset.tag} · {asset.name}")
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset_id: int, data: AssetUpdate) -> Asset:
    asset = _lock_asset(db, asset_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    new_state = changes.get("state")
    if new_state and new_state != "in_service" and active_loans(db, asset.id):
        raise RuleViolation(
            409,
            "asset_has_active_loans",
            f"{asset.tag} has active loans; return or cancel them before setting {new_state}",
        )
    new_category = changes.get("category")
    if new_category and new_category != asset.category and active_loans(db, asset.id):
        raise RuleViolation(
            409, "asset_has_active_loans", f"{asset.tag} has active loans; category is locked"
        )
    for key, value in changes.items():
        setattr(asset, key, value)
    if changes:
        record(db, "asset", asset.id, "updated", f"Updated {asset.tag}: {', '.join(changes)}")
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int) -> None:
    asset = _lock_asset(db, asset_id)
    if db.scalar(select(func.count(Loan.id)).where(Loan.asset_id == asset.id)):
        raise RuleViolation(
            409, "asset_has_history", f"{asset.tag} has loan history; retire it instead"
        )
    record(db, "asset", asset.id, "deleted", f"Deleted {asset.tag} · {asset.name}")
    db.delete(asset)
    db.commit()


# ---------------------------------------------------------------- loans
def create_loan(db: Session, data: LoanCreate) -> Loan:
    today = clock.today()
    _lock_borrower(db, data.borrower_roll)
    asset = _lock_asset(db, data.asset_id)
    if asset.state != "in_service":
        raise RuleViolation(409, "asset_not_in_service", f"{asset.tag} is {asset.state}")
    _check_window(asset.category, data.start_date, data.due_date, today)
    _check_borrower_limit(db, data.borrower_roll)
    _check_overlap(db, asset, data.start_date, data.due_date, today)

    loan = Loan(**data.model_dump(), status="reserved")
    db.add(loan)
    db.flush()
    record(
        db,
        "loan",
        loan.id,
        "reserved",
        f"{loan.borrower_name} reserved {asset.tag} for {loan.start_date} → {loan.due_date}",
    )
    db.commit()
    db.refresh(loan)
    LOAN_TRANSITIONS.labels(action="reserve").inc()
    return loan


def update_loan(db: Session, loan_id: int, data: LoanUpdate) -> Loan:
    today = clock.today()
    loan = get_loan(db, loan_id)
    _lock_borrower(db, loan.borrower_roll)
    asset = _lock_asset(db, loan.asset_id)
    db.refresh(loan)
    if loan.status != "reserved":
        raise RuleViolation(
            409, "loan_locked", f"loan #{loan.id} is {loan.status}; only reservations can change"
        )
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    start = changes.get("start_date", loan.start_date)
    due = changes.get("due_date", loan.due_date)
    if due <= start:
        raise RuleViolation(422, "bad_dates", "due_date must be after start_date")
    if "start_date" in changes or "due_date" in changes:
        _check_window(asset.category, start, due, today)
        _check_overlap(db, asset, start, due, today, ignore_id=loan.id)
    for key, value in changes.items():
        setattr(loan, key, value)
    if changes:
        record(db, "loan", loan.id, "updated", f"Loan #{loan.id} ({asset.tag}) now {start} → {due}")
    db.commit()
    db.refresh(loan)
    return loan


def transition_loan(db: Session, loan_id: int, action: str) -> Loan:
    today = clock.today()
    loan = get_loan(db, loan_id)
    asset = _lock_asset(db, loan.asset_id)
    db.refresh(loan)
    source, target = TRANSITIONS[action]
    if loan.status != source:
        raise RuleViolation(
            409,
            "illegal_transition",
            f"cannot {action} loan #{loan.id}: it is {loan.status.replace('_', ' ')}",
        )
    if action == "checkout":
        if asset.state != "in_service":
            raise RuleViolation(409, "asset_not_in_service", f"{asset.tag} is {asset.state}")
        if today < loan.start_date:
            raise RuleViolation(
                409, "too_early", f"loan #{loan.id} starts on {loan.start_date}; check-out not yet open"
            )
        if today >= loan.due_date:
            raise RuleViolation(409, "window_passed", f"loan #{loan.id} was due {loan.due_date}")
        loan.checked_out_at = clock.now()
    if action == "return":
        loan.returned_at = clock.now()
    loan.status = target
    late = action == "return" and today > loan.due_date
    verb = {"checkout": "checked out", "return": "returned", "cancel": "cancelled"}[action]
    record(
        db,
        "loan",
        loan.id,
        target,
        f"{loan.borrower_name} {verb} {asset.tag}" + (f" ({(today - loan.due_date).days}d late)" if late else ""),
    )
    db.commit()
    db.refresh(loan)
    LOAN_TRANSITIONS.labels(action=action).inc()
    return loan


def delete_loan(db: Session, loan_id: int) -> None:
    loan = get_loan(db, loan_id)
    if loan.status not in ("reserved", "cancelled"):
        raise RuleViolation(
            409,
            "loan_locked",
            f"loan #{loan.id} is {loan.status.replace('_', ' ')}; lending history is kept",
        )
    record(db, "loan", loan.id, "deleted", f"Deleted loan #{loan.id} ({loan.borrower_name})")
    db.delete(loan)
    db.commit()
