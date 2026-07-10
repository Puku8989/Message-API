"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all configuration values
at startup, ensuring fast-fail behaviour when credentials are missing.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Immutable application settings sourced from the ``.env`` file.

    Attributes:
        telegram_bot_token: Telegram Bot API token from @BotFather.
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
