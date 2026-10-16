"""Business metrics for Prometheus.

HTTP metrics (requests, latency, status) come from prometheus-fastapi-instrumentator.
The gauges below are read from the database at scrape time, so every replica reports
the same numbers; dashboards aggregate them with max(), not sum().
"""
import logging

from prometheus_client import REGISTRY, Counter
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import func, select

from . import clock
from .config import settings
from .db import SessionLocal
from .models import ASSET_STATES, LOAN_STATUSES, Asset, Loan

log = logging.getLogger(__name__)

LOAN_TRANSITIONS = Counter(
    "gearloop_loan_transitions_total", "Loan state changes handled by this pod", ["action"]
)
RULE_REJECTIONS = Counter(
    "gearloop_rule_rejections_total", "Requests refused by a lending rule", ["rule"]
)


class BusinessCollector(Collector):
    def collect(self):
        info = GaugeMetricFamily(
            "gearloop_build_info", "Build running in this pod", labels=["version", "environment"]
        )
        info.add_metric([settings.app_version, settings.environment], 1)
        yield info

        db_up = GaugeMetricFamily("gearloop_db_up", "1 if the last scrape could read the database")
        try:
            with SessionLocal() as db:
                today = clock.today()
                assets = dict(db.execute(select(Asset.state, func.count()).group_by(Asset.state)).all())
                loans = dict(db.execute(select(Loan.status, func.count()).group_by(Loan.status)).all())
                overdue = db.scalar(
                    select(func.count()).where(Loan.status == "checked_out", Loan.due_date < today)
                )
                busy = (
                    select(Loan.asset_id)
                    .where(Loan.status == "checked_out")
                    .scalar_subquery()
                )
                available = db.scalar(
                    select(func.count()).where(Asset.state == "in_service", Asset.id.not_in(busy))
                )
        except Exception:  # never let a DB hiccup break the scrape
            log.exception("business metrics collection failed")
            db_up.add_metric([], 0)
            yield db_up
            return

        db_up.add_metric([], 1)
        yield db_up

        g = GaugeMetricFamily("gearloop_assets", "Assets by state", labels=["state"])
        for state in ASSET_STATES:
            g.add_metric([state], assets.get(state, 0))
        yield g

        g = GaugeMetricFamily("gearloop_loans", "Loans by status", labels=["status"])
        for status in LOAN_STATUSES:
            g.add_metric([status], loans.get(status, 0))
        yield g

        yield GaugeMetricFamily(
            "gearloop_loans_overdue", "Checked-out loans past their due date", value=overdue or 0
        )
        yield GaugeMetricFamily(
            "gearloop_assets_available_now", "In-service assets not checked out", value=available or 0
        )


_collector = BusinessCollector()


def register() -> None:
    try:
        REGISTRY.register(_collector)
    except ValueError:  # already registered (e.g. module reloaded in tests)
        pass
