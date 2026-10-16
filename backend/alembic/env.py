from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

from app.config import settings
from app.db import Base
from app import models  # noqa: F401  (registers the tables on Base.metadata)

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Several backend replicas start at once and each runs `alembic upgrade head`.
# A Postgres advisory lock makes them take turns: the first migrates, the rest
# wait, then find nothing left to do.
MIGRATION_LOCK_ID = 7_310_042


def run_migrations_offline() -> None:
    context.configure(
        url=str(settings.sqlalchemy_url),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.sqlalchemy_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        use_lock = connection.dialect.name == "postgresql"
        if use_lock:
            print("waiting for migration lock", flush=True)
            connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
            connection.commit()
            print("migration lock acquired", flush=True)
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
            connection.commit()
        finally:
            if use_lock:
                connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})
                connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
