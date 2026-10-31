"""
Centralized Configuration for Antigravity Job Automation and SMTP Notifications.
Reads settings from the local .env file or OS environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Ensure project root directory is identified
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_PATH)
except ImportError:
    pass

def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "t")

def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default

def _get_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val.strip())
    except ValueError:
        return default

class Config:
    """Project-wide settings container."""

    VERSION: str = "1.3.0"

    # Paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    DATA_DIR: Path = PROJECT_ROOT / "data"
    DB_FILE: Path = DATA_DIR / "jobs_database.json"

    # Antigravity & LLM API Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    ANTIGRAVITY_MODEL: str = os.getenv("ANTIGRAVITY_MODEL", "gemini-3.8-flash")

    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = _get_int("SMTP_PORT", 587)
    SMTP_USE_TLS: bool = _get_bool("SMTP_USE_TLS", True)
    SMTP_USE_SSL: bool = _get_bool("SMTP_USE_SSL", False)
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", ""))
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Ahmad Faraz")
    SENDER_PHONE: str = os.getenv("SENDER_PHONE", "")
    ALERT_RECIPIENT_EMAIL: str = os.getenv("ALERT_RECIPIENT_EMAIL", "")

    # IMAP Inbox Listener Settings
    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    IMAP_PORT: int = _get_int("IMAP_PORT", 993)

    # Discord Notifications Webhook
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    # Discord Interactive Bot Configuration
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_OWNER_ID: str = os.getenv("DISCORD_OWNER_ID", "")

    # Job Preferences
    JOB_SEARCH_QUERY: str = os.getenv("JOB_SEARCH_QUERY", "Python AI Agent Developer")
    MIN_HOURLY_RATE: float = _get_float("MIN_HOURLY_RATE", 45.0)
    MIN_PROJECT_BUDGET: float = _get_float("MIN_PROJECT_BUDGET", 1000.0)
    REMOTE_ONLY: bool = _get_bool("REMOTE_ONLY", True)
    MIN_MATCH_SCORE: int = _get_int("MIN_MATCH_SCORE", 75)

    # Automation Interval
    SCAN_INTERVAL_SECONDS: int = _get_int("SCAN_INTERVAL_SECONDS", 3600)

    @classmethod
    def is_smtp_configured(cls) -> bool:
        """Checks if SMTP credentials have been populated."""
        return bool(
            cls.SMTP_HOST
            and cls.SMTP_USER
            and not cls.SMTP_USER.startswith("your_")
            and cls.SMTP_PASSWORD
            and not cls.SMTP_PASSWORD.startswith("your_")
            and cls.ALERT_RECIPIENT_EMAIL
            and not cls.ALERT_RECIPIENT_EMAIL.startswith("your_")
        )

    @classmethod
    def is_gemini_configured(cls) -> bool:
        """Checks if GEMINI_API_KEY is available."""
        return bool(cls.GEMINI_API_KEY and not cls.GEMINI_API_KEY.startswith("your_"))

    @classmethod
    def is_discord_bot_configured(cls) -> bool:
        """Checks if DISCORD_BOT_TOKEN is available."""
        return bool(cls.DISCORD_BOT_TOKEN and not cls.DISCORD_BOT_TOKEN.startswith("your_"))

    @classmethod
    def reload(cls) -> None:
        """Reloads settings from .env file into class attributes."""
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=ENV_PATH, override=True)
        except ImportError:
            pass

        cls.SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
        cls.SMTP_PORT = _get_int("SMTP_PORT", 587)
        cls.SMTP_USE_TLS = _get_bool("SMTP_USE_TLS", True)
        cls.SMTP_USE_SSL = _get_bool("SMTP_USE_SSL", False)
        cls.SMTP_USER = os.getenv("SMTP_USER", "")
        cls.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        cls.SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", cls.SMTP_USER)
        cls.SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Job Applicant")
        cls.SENDER_PHONE = os.getenv("SENDER_PHONE", "")
        cls.ALERT_RECIPIENT_EMAIL = os.getenv("ALERT_RECIPIENT_EMAIL", cls.SMTP_USER)
        cls.DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
        cls.DISCORD_OWNER_ID = os.getenv("DISCORD_OWNER_ID", "")
        cls.DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Ensure data directory exists
Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
