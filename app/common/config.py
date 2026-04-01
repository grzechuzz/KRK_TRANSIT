import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.common.constants import TIMEZONE


def _read_secret_file(env_var: str, default: str = "") -> str:
    file_path = os.getenv(env_var)
    if file_path and Path(file_path).exists():
        return Path(file_path).read_text().strip()
    return default


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str

    @property
    def url(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class RedisConfig:
    host: str
    port: int
    db: int
    username: str
    password: str

    @property
    def url(self) -> str:
        if self.username:
            return f"redis://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    redis: RedisConfig | None
    timezone: str
    data_dir: Path


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Load configuration from environment variables. Cached after first call."""
    db_password = _read_secret_file("DB_PASSWORD_FILE") or os.getenv("DB_PASSWORD")
    if not db_password:
        raise ValueError("DB_PASSWORD must be set")

    redis_password = _read_secret_file("REDIS_PASSWORD_FILE") or os.getenv("REDIS_PASSWORD")
    redis: RedisConfig | None = None
    if redis_password:
        redis = RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            username=os.getenv("REDIS_USERNAME", "mpk_redis"),
            password=redis_password,
        )

    return AppConfig(
        database=DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            name=os.getenv("DB_NAME", "mpk_db"),
            user=os.getenv("DB_USER", "mpk"),
            password=db_password,
        ),
        redis=redis,
        timezone=os.getenv("TZ", TIMEZONE),
        data_dir=Path(os.getenv("DATA_DIR", "/app/data")),
    )
