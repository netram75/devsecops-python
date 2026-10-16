"""Block until the database accepts connections (used by the container entrypoint)."""
import sys
import time

from sqlalchemy import create_engine, text

from .config import settings


def main(timeout: float = 90.0) -> int:
    engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True)
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"database reachable after {attempt} attempt(s)", flush=True)
            return 0
        except Exception as exc:  # noqa: BLE001 - any failure means "not yet"
            if time.monotonic() > deadline:
                print(f"database not reachable after {timeout:.0f}s: {exc}", file=sys.stderr)
                return 1
            print(f"waiting for database ({type(exc).__name__})", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
