"""Meta WhatsApp Cloud API service.

Sends plain-text messages via the WhatsApp Business Cloud API (Graph API v21.0)
using the credentials stored in ``.env``.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.utils import create_http_client, get_logger, with_retry

logger = get_logger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com"
GRAPH_API_VERSION = "v21.0"


@with_retry()
async def send_whatsapp_message(
    message: str,
    recipient_number: str | None = None,
) -> dict[str, Any]:
    """Deliver a text message through the WhatsApp Cloud API.

    Args:
        message: The text content to send.
        recipient_number: Optional recipient phone number override in
            E.164 format. Falls back to the ``WHATSAPP_RECIPIENT_NUMBER``
            environment variable when ``None``.

    Returns:
        The parsed JSON response from the Graph API.

    Raises:
        httpx.HTTPStatusError: If Meta returns a non-2xx status after
            all retry attempts are exhausted.
        httpx.TimeoutException: If the request times out after all retries.
        ValueError: If the Graph API response contains an error payload.
    """
    settings = get_settings()
    target_number = recipient_number or settings.whatsapp_recipient_number
    url = (
        f"{GRAPH_API_BASE}/{GRAPH_API_VERSION}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": target_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message,
        },
    }

    logger.info(
        "Sending WhatsApp message to %s (length=%d)",
        target_number,
        len(message),
    )

    async with create_http_client() as client:
        response: httpx.Response = await client.post(
            url, json=payload, headers=headers,
        )
        response.raise_for_status()

    data: dict[str, Any] = response.json()

    if "error" in data:
        error_msg = data["error"].get("message", "Unknown WhatsApp error")
        logger.error("WhatsApp API error: %s", error_msg)
        raise ValueError(f"WhatsApp API error: {error_msg}")

    logger.info("WhatsApp message delivered successfully (response=%s)", data)
    return data
