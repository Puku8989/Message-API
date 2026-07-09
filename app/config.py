"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all configuration values
at startup, ensuring fast-fail behaviour when credentials are missing.
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Immutable application settings sourced from the ``.env`` file.

    Attributes:
        telegram_bot_token: Telegram Bot API token from @BotFather.
        telegram_chat_id: Target chat/group/channel ID for Telegram messages.
        whatsapp_access_token: Meta Graph API access token for WhatsApp Cloud.
        whatsapp_phone_number_id: Sender phone-number ID registered in Meta.
        whatsapp_recipient_number: Default recipient in E.164 format.
        api_timeout: HTTP request timeout in seconds.
        max_retries: Maximum retry attempts for failed API calls.
        log_level: Python logging level string.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram (Bot API)
    telegram_bot_token: str
    telegram_chat_id: str

    # Telegram (Client API / Telethon) — optional, for phone-number messaging
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None

    @field_validator("telegram_api_id", mode="before")
    @classmethod
    def _coerce_api_id(cls, v: Any) -> int | None:
        """Parse api_id as int; return None for placeholder strings."""
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator("telegram_api_hash", "telegram_phone", mode="before")
    @classmethod
    def _blank_placeholder(cls, v: Any) -> str | None:
        """Treat obvious placeholder values as None."""
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.startswith("your_"):
            return None
        return s

    # WhatsApp
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_recipient_number: str

    # Application
    api_timeout: int = 30
    max_retries: int = 3
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` singleton.

    Returns:
        The validated application settings instance.
    """
    return Settings()  # type: ignore[call-arg]
