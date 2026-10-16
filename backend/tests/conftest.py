"""Test setup: a throwaway SQLite database, never the real Postgres.

DATABASE_URL must be set before `app` is imported, because the engine is created at
import time. The schema is built by running the real Alembic migrations, so every
test run also proves the migrations work.
"""
import os
import tempfile
from datetime import timedelta
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{tempfile.mkdtemp()}/gearloop-test.db"
os.environ.setdefault("APP_VERSION", "test")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import clock  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
TODAY = clock.today()


def days(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    yield cfg


@pytest.fixture(autouse=True)
def clean_tables():
    with engine.begin() as conn:
        for table in ("events", "loans", "assets"):
            conn.exec_driver_sql(f"DELETE FROM {table}")
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_asset(client):
    counter = {"n": 0}

    def _make(category="camera", **overrides):
        counter["n"] += 1
        body = {
            "tag": f"T{category[:3].upper()}-{counter['n']:03d}",
            "name": f"Test {category} {counter['n']}",
            "category": category,
            "location": "Media Lab",
        }
        body.update(overrides)
        r = client.post("/api/assets", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    return _make


@pytest.fixture
def make_loan(client):
    def _make(asset_id, start=0, due=2, roll="24BCS10329", expect=201, **overrides):
        body = {
            "asset_id": asset_id,
            "borrower_name": "Asha Verma",
            "borrower_roll": roll,
            "borrower_email": "asha@example.edu",
            "purpose": "Club shoot",
            "start_date": days(start),
            "due_date": days(due),
        }
        body.update(overrides)
        r = client.post("/api/loans", json=body)
        assert r.status_code == expect, r.text
        return r.json()

    return _make


@pytest.fixture
def shift_today(monkeypatch):
    """Pretend the campus clock is `n` days ahead (for overdue / late-return cases)."""

    real_now = clock.now

    def _shift(n: int):
        monkeypatch.setattr(clock, "now", lambda: real_now() + timedelta(days=n))

    return _shift
