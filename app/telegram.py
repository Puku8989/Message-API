"""Telegram messaging service — Bot API only.

All outgoing messages are sent through the Telegram Bot API using
the BotFather token.  The sender will always appear as the bot.

The ``chat_id`` (recipient) must be provided per-request — there is
no default from the environment.

Supported recipient formats:
- Numeric chat ID  (e.g. ``"123456789"``)
- ``@username``    (e.g. ``"@mychannel"``)

Phone-number recipients are **not** supported by the Bot API and
will return a clear error.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import get_settings
from app.utils import create_http_client, get_logger, with_retry

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"

# Pattern to detect E.164 phone numbers so we can return a helpful error.
_PHONE_RE = re.compile(r"^\+\d{7,15}$")


@with_retry()
async def _send_via_bot_api(
    message: str,
    chat_id: str,
    parse_mode: str | None = None,
) -> dict[str, Any]:
    """Deliver a text message through the Telegram Bot API.

    Args:
        message: The text content to send.
        chat_id: The target chat ID, @username, or numeric ID.
        parse_mode: Optional formatting mode (``"HTML"``, ``"Markdown"``,
            or ``"MarkdownV2"``). Defaults to ``None`` (plain text).

    Returns:
        The parsed JSON response from Telegram.

    Raises:
        httpx.HTTPStatusError: If Telegram returns a non-2xx status after
            all retry attempts are exhausted.
        httpx.TimeoutException: If the request times out after all retries.
        ValueError: If no chat_id is provided or the Telegram API response
            indicates failure.
    """
    if not chat_id:
        raise ValueError(
            "A chat_id is required. Provide a numeric chat ID or @username "
            "in the request body."
        )
    settings = get_settings()
    target_chat = chat_id
    url = f"{TELEGRAM_API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": target_chat,
        "text": message,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    logger.info(
        "Sending Telegram message via Bot API to chat_id=%s (length=%d)",
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


async def send_telegram_message(
    message: str,
    chat_id: str,
    parse_mode: str | None = None,
) -> dict[str, Any]:
    """Send a Telegram message via the Bot API.

    The message is always sent using the bot token, so the sender will
    appear as the bot (not a personal account).

    Args:
        message: The text content to send.
        chat_id: The target recipient — a numeric chat ID or ``@username``.
            This is required and must be provided in the request body.
        parse_mode: Optional formatting mode (``"HTML"``, ``"Markdown"``,
            or ``"MarkdownV2"``).

    Returns:
        The parsed JSON response from Telegram.

    Raises:
        ValueError: If the recipient is a phone number (unsupported by
            the Bot API), if no chat_id is provided, or if the Telegram
            API response indicates failure.
        httpx.HTTPStatusError: On non-2xx upstream responses.
        httpx.TimeoutException: On upstream timeouts.
    """
    # Reject phone-number recipients with a clear explanation.
    if chat_id and _PHONE_RE.match(chat_id):
        raise ValueError(
            f"Recipient '{chat_id}' is a phone number.  The Telegram Bot API "
            "does not support sending messages by phone number.  Please use a "
            "numeric chat_id or @username instead.  The recipient must have "
            "started the bot (sent /start) at least once."
        )

    # Normalise chat ID: auto-prepend '@' for alphabetical usernames if missing
    chat_id = chat_id.strip()
    if not chat_id.lstrip('-').isdigit() and not chat_id.startswith('@'):
        chat_id = f"@{chat_id}"

    return await _send_via_bot_api(message, chat_id=chat_id, parse_mode=parse_mode)
