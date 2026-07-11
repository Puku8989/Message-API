"""Telegram messaging service — smart routing.

Automatically chooses the right transport based on the recipient format:

- **Phone number** (starts with ``+``) → Telethon Client API
- **Chat ID** (numeric) or ``@username`` → Bot API (``sendMessage``)

Both transports coexist; the Bot API path remains unchanged from the
original implementation.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import get_settings
from app.telegram_client import (
    get_chat_id_by_phone,
    is_available as telethon_available,
    send_telegram_message_by_phone,
)
from app.utils import create_http_client, get_logger, with_retry

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"

# Simple pattern: starts with + followed by digits (E.164 phone number)
_PHONE_RE = re.compile(r"^\+\d{7,15}$")


def _looks_like_phone(recipient: str) -> bool:
    """Return ``True`` if *recipient* looks like an E.164 phone number."""
    return bool(_PHONE_RE.match(recipient))


@with_retry()
async def _send_via_bot_api(
    message: str,
    chat_id: str | None = None,
    parse_mode: str | None = None,
) -> dict[str, Any]:
    """Deliver a text message through the Telegram Bot API.

    Args:
        message: The text content to send.
        chat_id: Optional chat ID override. Falls back to the
            ``TELEGRAM_CHAT_ID`` environment variable when ``None``.
        parse_mode: Optional formatting mode (``"HTML"``, ``"Markdown"``,
            or ``"MarkdownV2"``). Defaults to ``None`` (plain text).

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
    chat_id: str | None = None,
    parse_mode: str | None = None,
) -> dict[str, Any]:
    """Send a Telegram message, auto-selecting the transport.

    If *chat_id* looks like an E.164 phone number (``+<digits>``), the
    message is first resolved to a chat ID and sent via the Bot API.
    If the Bot API fails (e.g. user hasn't started the bot), it falls
    back to the Telethon Client API.  Otherwise it falls
    through to the standard Bot API.

    Args:
        message: The text content to send.
        chat_id: Optional recipient override — chat ID, @username, or
            phone number in E.164 format.
        parse_mode: Optional formatting mode (Bot API only).

    Returns:
        The parsed JSON response / delivery metadata.
    """
    # Determine if we should route through Telethon
    if chat_id and _looks_like_phone(chat_id):
        if not telethon_available():
            raise RuntimeError(
                f"Recipient '{chat_id}' looks like a phone number but the "
                "Telethon client is not available. Ensure TELEGRAM_API_ID, "
                "TELEGRAM_API_HASH, and TELEGRAM_PHONE are set in .env and "
                "run 'python auth_telethon.py' to authenticate."
            )
        
        logger.info("Phone number detected: %s. Attempting to resolve and send via Bot API...", chat_id)
        
        try:
            resolved_chat_id = await get_chat_id_by_phone(chat_id)
            logger.info("Resolved phone %s to chat_id %s", chat_id, resolved_chat_id)
            
            # Try to send via Bot API
            return await _send_via_bot_api(message, chat_id=str(resolved_chat_id), parse_mode=parse_mode)
        except (ValueError, httpx.HTTPError) as exc:
            logger.warning(
                "Bot API failed for resolved chat_id (bot blocked or not started?): %s. "
                "Falling back to Telethon Client API...",
                exc,
            )
            return await send_telegram_message_by_phone(chat_id, message)
        except Exception as exc:
            # Maybe get_chat_id_by_phone failed or something unexpected happened
            logger.error("Error resolving or sending via Bot API: %s. Falling back to Telethon.", exc)
            return await send_telegram_message_by_phone(chat_id, message)

    # Default: Bot API
    return await _send_via_bot_api(message, chat_id=chat_id, parse_mode=parse_mode)
