"""Telegram Bot API service.

Sends plain-text messages via the ``sendMessage`` endpoint of the
official Telegram Bot API using the credentials stored in ``.env``.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.utils import create_http_client, get_logger, with_retry

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


@with_retry()
async def send_telegram_message(
    message: str,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """Deliver a text message through the Telegram Bot API.

    Args:
        message: The text content to send.
        chat_id: Optional chat ID override. Falls back to the
            ``TELEGRAM_CHAT_ID`` environment variable when ``None``.

    Returns:
        The parsed JSON response from Telegram.

    Raises:
        httpx.HTTPStatusError: If Telegram returns a non-2xx status after
            all retry attempts are exhausted.
        httpx.TimeoutException: If the request times out after all retries.
        ValueError: If the Telegram API response indicates failure.
    """
    settings = get_settings()
    target_chat = chat_id or settings.telegram_chat_id
    url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "HTML",
    }

    logger.info(
        "Sending Telegram message to chat_id=%s (length=%d)",
        target_chat,
        len(message),
    )

    async with create_http_client() as client:
        response: httpx.Response = await client.post(url, json=payload)
        response.raise_for_status()

    data: dict[str, Any] = response.json()

    if not data.get("ok"):
        error_desc = data.get("description", "Unknown Telegram error")
        logger.error("Telegram API error: %s", error_desc)
        raise ValueError(f"Telegram API error: {error_desc}")

    logger.info("Telegram message delivered successfully (message_id=%s)",
                data.get("result", {}).get("message_id"))
    return data
