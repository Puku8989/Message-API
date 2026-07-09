"""Telegram Client API service (Telethon).

Sends messages to Telegram users by **phone number** using the Telegram
Client API.  This complements the Bot API in ``telegram.py`` which only
supports chat IDs.

Prerequisites
-------------
1. Obtain ``api_id`` and ``api_hash`` from https://my.telegram.org.
2. Run ``python auth_telethon.py`` once to authenticate and generate a
   ``.session`` file.
3. Set ``TELEGRAM_API_ID``, ``TELEGRAM_API_HASH``, and ``TELEGRAM_PHONE``
   in your ``.env`` file.
"""

from __future__ import annotations

import pathlib
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberInvalidError,
    UserNotMutualContactError,
)

from app.config import get_settings
from app.utils import get_logger

logger = get_logger(__name__)

# Session file lives next to the project root
_SESSION_DIR = pathlib.Path(__file__).resolve().parent.parent
_SESSION_NAME = str(_SESSION_DIR / "telethon_session")

# Module-level singleton — initialised lazily via ``connect()``.
_client: TelegramClient | None = None


def _is_configured() -> bool:
    """Return ``True`` if the Telethon credentials are present."""
    settings = get_settings()
    return all([
        settings.telegram_api_id,
        settings.telegram_api_hash,
        settings.telegram_phone,
    ])


async def connect() -> None:
    """Create and connect the Telethon client (called at app startup).

    If Telethon credentials are not configured, this is a no-op and the
    phone-number messaging route will gracefully fall back to an error.
    """
    global _client  # noqa: PLW0603

    if not _is_configured():
        logger.info(
            "Telethon credentials not configured — "
            "phone-number messaging will be unavailable"
        )
        return

    settings = get_settings()
    _client = TelegramClient(
        _SESSION_NAME,
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    await _client.connect()

    if not await _client.is_user_authorized():
        logger.warning(
            "Telethon session is not authorised. "
            "Run 'python auth_telethon.py' to authenticate first."
        )
        await _client.disconnect()
        _client = None
        return

    logger.info("Telethon client connected and authorised ✓")


async def disconnect() -> None:
    """Disconnect the Telethon client (called at app shutdown)."""
    global _client  # noqa: PLW0603
    if _client is not None:
        await _client.disconnect()
        _client = None
        logger.info("Telethon client disconnected")


def is_available() -> bool:
    """Return ``True`` if the Telethon client is connected and ready."""
    return _client is not None and _client.is_connected()


async def resolve_phone_to_entity(phone: str) -> Any:
    """Resolve a phone number to a Telethon entity (User)."""
    if not is_available():
        raise RuntimeError(
            "Telethon client is not available. "
            "Ensure TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE "
            "are set in .env and run 'python auth_telethon.py' to authenticate."
        )

    logger.info("Resolving phone number %s via Telethon", phone)

    try:
        return await _client.get_entity(phone)  # type: ignore[union-attr]
    except Exception as exc:
        logger.info("Direct resolution failed for %s. Attempting to import as contact...", phone)
        try:
            from telethon.tl.functions.contacts import ImportContactsRequest
            from telethon.tl.types import InputPhoneContact

            contact = InputPhoneContact(client_id=0, phone=phone, first_name="API Contact", last_name="")
            res = await _client(ImportContactsRequest([contact]))  # type: ignore[union-attr]

            if res and res.users:
                return res.users[0]
            else:
                # Try getting the entity again after import
                return await _client.get_entity(phone)  # type: ignore[union-attr]
        except Exception as import_exc:
            logger.error("Failed to resolve or import contact for %s: %s", phone, import_exc)
            raise ValueError(
                f"Could not resolve phone number {phone}. Make sure it is registered on Telegram."
            ) from exc


async def get_chat_id_by_phone(phone: str) -> int:
    """Resolve a phone number to a numeric Telegram Chat ID using Telethon."""
    entity = await resolve_phone_to_entity(phone)
    return entity.id


async def send_telegram_message_by_phone(
    phone: str,
    message: str,
) -> dict[str, Any]:
    """Send a text message to a Telegram user identified by phone number.

    The phone number must belong to a Telegram user who is in the
    authenticated account's contact list, or who has a public presence.

    Args:
        phone: Recipient phone number in E.164 format (e.g. ``+919876543210``).
        message: The text content to send.

    Returns:
        A dictionary with delivery metadata.

    Raises:
        RuntimeError: If the Telethon client is not connected.
        ValueError: If the phone number is invalid or the user cannot be
            resolved.
    """
    entity = await resolve_phone_to_entity(phone)

    logger.info(
        "Resolved %s → user_id=%s, sending message (length=%d)",
        phone,
        entity.id,
        len(message),
    )

    sent = await _client.send_message(entity, message)  # type: ignore[union-attr]

    result: dict[str, Any] = {
        "ok": True,
        "result": {
            "message_id": sent.id,
            "chat_id": entity.id,
            "phone": phone,
            "date": str(sent.date),
        },
    }

    logger.info(
        "Telethon message delivered (message_id=%s, user_id=%s)",
        sent.id,
        entity.id,
    )
    return result
