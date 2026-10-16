import logging
from datetime import timedelta
from typing import Literal

from fastapi import Depends, FastAPI, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as http_metrics
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from . import clock, metrics, services
from .config import settings
from .db import get_db
from .models import ACTIVE_LOAN_STATUSES, ASSET_STATES, CATEGORIES, MAX_LOAN_DAYS, Asset, Event, Loan
from .schemas import (
    AssetCreate,
    AssetOut,
    AssetState,
    AssetUpdate,
    Category,
    EventOut,
    InfoOut,
    LoanCreate,
    LoanOut,
    LoanStatus,
    LoanUpdate,
    Rules,
    StatsOut,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="GearLoop API",
    version=settings.app_version,
    description="Campus equipment lending: catalogue, reservations, check-out and returns.",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Buckets start at 5 ms: the defaults start at 100 ms, which puts every request in the
# first bucket and makes p95 meaningless for a fast API.
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).add(
    http_metrics.default(latency_lowr_buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
metrics.register()


# ---------------------------------------------------------------- errors
@app.exception_handler(services.RuleViolation)
def rule_violation(_: Request, exc: services.RuleViolation):
    metrics.RULE_REJECTIONS.labels(rule=exc.code).inc()
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})


@app.exception_handler(services.NotFound)
def not_found(_: Request, exc: services.NotFound):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(IntegrityError)
def integrity_error(_: Request, exc: IntegrityError):
    logging.getLogger("gearloop").warning("integrity error: %s", exc.orig)
    return JSONResponse(
        status_code=409, content={"detail": "conflicts with existing data", "code": "integrity"}
    )


# ---------------------------------------------------------------- serialisers
def asset_out(asset: Asset, loans: list[Loan], today) -> AssetOut:
    current = next((l for l in loans if l.status == "checked_out"), None)
    blocked_today = any(
        l.start_date <= today < services.blocking_end(l, today) for l in loans
    )
    upcoming = sorted(l.start_date for l in loans if l.status == "reserved" and l.start_date >= today)
    out = AssetOut.model_validate(asset)
    out.available_now = asset.state == "in_service" and not blocked_today
    out.current_loan_id = current.id if current else None
    out.next_reservation = upcoming[0] if upcoming else None
    return out


def loan_out(loan: Loan, today) -> LoanOut:
    overdue = services.is_overdue(loan, today)
    returned_late = bool(loan.returned_at) and clock.local_date(loan.returned_at) > loan.due_date
    return LoanOut(
        **{c: getattr(loan, c) for c in LoanOut.model_fields if hasattr(Loan, c)},
        asset_tag=loan.asset.tag,
        asset_name=loan.asset.name,
        asset_category=loan.asset.category,
        overdue=overdue,
        days_overdue=(today - loan.due_date).days if overdue else 0,
        returned_late=returned_late,
    )


def _asset_with_loans(db: Session, asset: Asset) -> AssetOut:
    return asset_out(asset, services.active_loans(db, asset.id), clock.today())


# ---------------------------------------------------------------- probes
@app.get("/", include_in_schema=False)
def root():
    return {"service": "gearloop-backend", "version": settings.app_version, "docs": "/docs"}


@app.get("/health", tags=["probes"])
def health():
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@app.get("/ready", tags=["probes"])
def ready(response: Response, db: Session = Depends(get_db)):
    """Readiness: the database is reachable and migrated."""
    try:
        db.execute(text("SELECT 1 FROM assets LIMIT 1"))
        db.execute(text("SELECT 1 FROM events LIMIT 1"))
    except SQLAlchemyError as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "reason": type(exc).__name__}
    return {"status": "ready"}


# ---------------------------------------------------------------- info / stats
@app.get("/api/info", response_model=InfoOut, tags=["info"])
def info():
    return InfoOut(
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        pod=settings.pod_name,
        today=clock.today(),
        timezone=settings.timezone,
        categories=list(CATEGORIES),
        asset_states=list(ASSET_STATES),
        rules=Rules(
            max_active_loans=settings.max_active_loans,
            max_advance_days=settings.max_advance_days,
            max_loan_days=MAX_LOAN_DAYS,
        ),
    )


@app.get("/api/stats", response_model=StatsOut, tags=["info"])
def stats(db: Session = Depends(get_db)):
    today = clock.today()
    by_state = dict(db.execute(select(Asset.state, func.count()).group_by(Asset.state)).all())
    by_status = dict(db.execute(select(Loan.status, func.count()).group_by(Loan.status)).all())
    by_category = dict(db.execute(select(Asset.category, func.count()).group_by(Asset.category)).all())
    assets = list(db.scalars(select(Asset)))
    active = list(db.scalars(select(Loan).where(Loan.status.in_(ACTIVE_LOAN_STATUSES))))
    per_asset: dict[int, list[Loan]] = {}
    for loan in active:
        per_asset.setdefault(loan.asset_id, []).append(loan)
    available = sum(asset_out(a, per_asset.get(a.id, []), today).available_now for a in assets)
    on_loan = by_status.get("checked_out", 0)
    in_service = by_state.get("in_service", 0)
    return StatsOut(
        assets_total=len(assets),
        assets_in_service=in_service,
        assets_available_now=available,
        loans_by_status={s: by_status.get(s, 0) for s in ("reserved", "checked_out", "returned", "cancelled")},
        on_loan_now=on_loan,
        overdue=sum(services.is_overdue(l, today) for l in active),
        due_today=sum(l.status == "checked_out" and l.due_date == today for l in active),
        utilisation_pct=round(100 * on_loan / in_service, 1) if in_service else 0.0,
        by_category={c: by_category.get(c, 0) for c in CATEGORIES},
    )


@app.get("/api/activity", response_model=list[EventOut], tags=["info"])
def activity(limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)):
    return list(db.scalars(select(Event).order_by(Event.id.desc()).limit(limit)))


# ---------------------------------------------------------------- assets
@app.get("/api/assets", response_model=list[AssetOut], tags=["assets"])
def list_assets(
    category: Category | None = None,
    state: AssetState | None = None,
    q: str | None = Query(default=None, max_length=60),
    available: bool | None = None,
    db: Session = Depends(get_db),
):
    query = select(Asset).order_by(Asset.tag)
    if category:
        query = query.where(Asset.category == category)
    if state:
        query = query.where(Asset.state == state)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Asset.name.ilike(like), Asset.tag.ilike(like), Asset.location.ilike(like)))
    assets = list(db.scalars(query))
    today = clock.today()
    per_asset: dict[int, list[Loan]] = {}
    for loan in db.scalars(select(Loan).where(Loan.status.in_(ACTIVE_LOAN_STATUSES))):
        per_asset.setdefault(loan.asset_id, []).append(loan)
    out = [asset_out(a, per_asset.get(a.id, []), today) for a in assets]
    if available is not None:
        out = [a for a in out if a.available_now == available]
    return out


@app.post("/api/assets", response_model=AssetOut, status_code=201, tags=["assets"])
def create_asset(data: AssetCreate, db: Session = Depends(get_db)):
    return _asset_with_loans(db, services.create_asset(db, data))


@app.get("/api/assets/{asset_id}", response_model=AssetOut, tags=["assets"])
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    return _asset_with_loans(db, services.get_asset(db, asset_id))


@app.put("/api/assets/{asset_id}", response_model=AssetOut, tags=["assets"])
def update_asset(asset_id: int, data: AssetUpdate, db: Session = Depends(get_db)):
    return _asset_with_loans(db, services.update_asset(db, asset_id, data))


@app.delete("/api/assets/{asset_id}", status_code=204, tags=["assets"])
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    services.delete_asset(db, asset_id)
    return Response(status_code=204)


@app.get("/api/assets/{asset_id}/loans", response_model=list[LoanOut], tags=["assets"])
def asset_loans(asset_id: int, db: Session = Depends(get_db)):
    services.get_asset(db, asset_id)
    today = clock.today()
    loans = db.scalars(
        select(Loan).options(joinedload(Loan.asset)).where(Loan.asset_id == asset_id).order_by(Loan.start_date.desc())
    )
    return [loan_out(l, today) for l in loans]


# ---------------------------------------------------------------- loans
@app.get("/api/loans", response_model=list[LoanOut], tags=["loans"])
def list_loans(
    status_: LoanStatus | None = Query(default=None, alias="status"),
    asset_id: int | None = None,
    roll: str | None = Query(default=None, max_length=20),
    overdue: bool | None = None,
    view: Literal["all", "active", "history"] = "all",
    db: Session = Depends(get_db),
):
    today = clock.today()
    query = select(Loan).options(joinedload(Loan.asset)).order_by(Loan.start_date.desc(), Loan.id.desc())
    if status_:
        query = query.where(Loan.status == status_)
    if view == "active":
        query = query.where(Loan.status.in_(ACTIVE_LOAN_STATUSES))
    elif view == "history":
        query = query.where(Loan.status.not_in(ACTIVE_LOAN_STATUSES))
    if asset_id:
        query = query.where(Loan.asset_id == asset_id)
    if roll:
        query = query.where(Loan.borrower_roll == roll.strip().upper())
    if overdue:
        query = query.where(Loan.status == "checked_out", Loan.due_date < today)
    return [loan_out(l, today) for l in db.scalars(query)]


@app.post("/api/loans", response_model=LoanOut, status_code=201, tags=["loans"])
def create_loan(data: LoanCreate, db: Session = Depends(get_db)):
    return loan_out(services.create_loan(db, data), clock.today())


@app.get("/api/loans/{loan_id}", response_model=LoanOut, tags=["loans"])
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    return loan_out(services.get_loan(db, loan_id), clock.today())


@app.put("/api/loans/{loan_id}", response_model=LoanOut, tags=["loans"])
def update_loan(loan_id: int, data: LoanUpdate, db: Session = Depends(get_db)):
    return loan_out(services.update_loan(db, loan_id, data), clock.today())


@app.delete("/api/loans/{loan_id}", status_code=204, tags=["loans"])
def delete_loan(loan_id: int, db: Session = Depends(get_db)):
    services.delete_loan(db, loan_id)
    return Response(status_code=204)


@app.post("/api/loans/{loan_id}/{action}", response_model=LoanOut, tags=["loans"])
def transition_loan(
    loan_id: int, action: Literal["checkout", "return", "cancel"], db: Session = Depends(get_db)
):
    return loan_out(services.transition_loan(db, loan_id, action), clock.today())
