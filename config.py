"""
TC Dashboard — Configuration.
Environment-driven config for standalone deployment.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # App
    APP_NAME = "TC Dashboard"
    DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8050))

    # Redis cache (optional — app runs without it)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Google Analytics 4 (leave blank to disable tracking)
    GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")


def get_config() -> Config:
    """Return the application configuration."""
    return Config()
