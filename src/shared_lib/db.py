"""Database connection utilities."""

import os


def get_database_uri(async_driver: bool = True) -> str:
    """Build database URI from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    db_name = os.getenv("DB_NAME", "splattop")

    driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
    uri = f"{driver}://{user}:{password}@{host}:{port}/{db_name}"

    # Disable SSL in dev mode
    if os.getenv("DEV_MODE", "false").lower() == "true":
        if async_driver:
            uri += "?ssl=disable"
        else:
            uri += "?sslmode=disable"

    return uri


def get_redis_url() -> str:
    """Build Redis URL from environment variables."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "0")
    return f"redis://{host}:{port}/{db}"
