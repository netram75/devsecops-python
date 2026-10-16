"""Runtime settings. Everything comes from environment variables.

In Kubernetes the DB host/name/user come from a ConfigMap and the password from a
Secret. Tests and docker compose can pass one full DATABASE_URL instead, which wins.
"""
import os
import socket
from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GearLoop"
    app_version: str = Field(default="dev", alias="APP_VERSION")
    environment: str = Field(default="local", alias="APP_ENV")
    timezone: str = Field(default="Asia/Kolkata", alias="APP_TIMEZONE")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="gearloop", alias="DB_NAME")
    db_user: str = Field(default="gearloop", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")

    # Lending rules. The UI reads these from /api/info instead of hardcoding them.
    max_active_loans: int = Field(default=3, alias="MAX_ACTIVE_LOANS")
    max_advance_days: int = Field(default=30, alias="MAX_ADVANCE_DAYS")

    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    @cached_property
    def sqlalchemy_url(self) -> str | URL:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def pod_name(self) -> str:
        return os.environ.get("POD_NAME") or socket.gethostname()


settings = Settings()
