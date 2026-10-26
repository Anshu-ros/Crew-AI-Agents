"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    serper_api_key: str
    linkedin_timezone: str
    scheduled_posts_path: Path
    serper_api_url: str
    external_api_max_attempts: int
    external_api_timeout_seconds: float


def load_settings(env_file: str | Path = ".env") -> Settings:
    """Load and validate all required settings from a dotenv file/environment."""
    load_dotenv(dotenv_path=Path(env_file), override=False)

    required = (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "SERPER_API_KEY",
        "LINKEDIN_TIMEZONE",
        "SCHEDULED_POSTS_PATH",
        "SERPER_API_URL",
        "EXTERNAL_API_MAX_ATTEMPTS",
        "EXTERNAL_API_TIMEOUT_SECONDS",
    )
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise ConfigurationError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    timezone = os.environ["LINKEDIN_TIMEZONE"].strip()
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ConfigurationError(
            f"LINKEDIN_TIMEZONE is not a recognized IANA timezone: {timezone}"
        ) from error

    try:
        max_attempts = int(os.environ["EXTERNAL_API_MAX_ATTEMPTS"])
        timeout = float(os.environ["EXTERNAL_API_TIMEOUT_SECONDS"])
    except ValueError as error:
        raise ConfigurationError(
            "EXTERNAL_API_MAX_ATTEMPTS must be an integer and "
            "EXTERNAL_API_TIMEOUT_SECONDS must be a number"
        ) from error
    if max_attempts < 1:
        raise ConfigurationError("EXTERNAL_API_MAX_ATTEMPTS must be at least 1")
    if timeout <= 0:
        raise ConfigurationError("EXTERNAL_API_TIMEOUT_SECONDS must be greater than 0")

    return Settings(
        openai_api_key=os.environ["OPENAI_API_KEY"].strip(),
        openai_model=os.environ["OPENAI_MODEL"].strip(),
        serper_api_key=os.environ["SERPER_API_KEY"].strip(),
        linkedin_timezone=timezone,
        scheduled_posts_path=Path(os.environ["SCHEDULED_POSTS_PATH"]).expanduser(),
        serper_api_url=os.environ["SERPER_API_URL"].strip(),
        external_api_max_attempts=max_attempts,
        external_api_timeout_seconds=timeout,
    )
