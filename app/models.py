"""Pydantic models for request validation and API responses.

All models use strict validation and include OpenAPI examples so that
FastAPI's auto-generated Swagger UI is immediately useful.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────

class Platform(str, Enum):
    """Supported messaging platforms."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    BOTH = "both"


# ── Request Models ───────────────────────────────────────────────────

class MessageRequest(BaseModel):
    """Incoming request to send a message.

    Attributes:
        platform: Target platform (``telegram``, ``whatsapp``, or ``both``).
        message: The text content to deliver.
        recipient: Recipient for the message. For Telegram: a chat ID or
            @username (required). For WhatsApp: a phone number in E.164
            format (falls back to ``.env`` default when omitted).
    """

    platform: Platform = Field(
        ...,
        description="Target messaging platform.",
        examples=["telegram", "whatsapp", "both"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Text message to send (1–4 096 characters).",
        examples=["Hello World"],
    )
    recipient: str | None = Field(
        default=None,
        description=(
            "Recipient for the message. For Telegram: a chat ID or @username "
            "(required — no env default). For WhatsApp: a phone number in "
            "E.164 format (e.g., +1234567890; falls back to env default). "
            "When platform is 'both', use telegram_chat_id and "
            "whatsapp_recipient instead for per-platform targeting."
        ),
        examples=["+1234567890", "123456789"],
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description=(
            "Telegram chat ID or @username. Required when platform is "
            "'both' (there is no env default). Targets the Telegram chat "
            "independently of the WhatsApp recipient."
        ),
        examples=["123456789", "@username"],
    )
    whatsapp_recipient: str | None = Field(
        default=None,
        description=(
            "Optional WhatsApp phone number override in E.164 format. "
            "Used when platform is 'both' to target a specific WhatsApp "
            "number independently of the Telegram chat ID."
        ),
        examples=["+1234567890"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"platform": "telegram", "message": "Hello from the API!"},
                {"platform": "whatsapp", "message": "Hello from the API!", "recipient": "+1234567890"},
                {"platform": "both", "message": "Hello everywhere!"},
            ]
        }
    }


# ── Response Models ──────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Successful delivery response.

    Attributes:
        success: Always ``True`` for successful deliveries.
        platform: The platform the message was sent to.
        message: Confirmation text.
        details: Raw upstream API response payload.
    """

    success: bool = Field(default=True, description="Delivery succeeded.")
    platform: Platform = Field(description="Platform the message was sent to.")
    message: str = Field(description="Human-readable confirmation.")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw response from the upstream API.",
    )


class ErrorResponse(BaseModel):
    """Standardised error envelope.

    Attributes:
        success: Always ``False`` for errors.
        error: Short error category.
        detail: Human-readable explanation.
    """

    success: bool = Field(default=False)
    error: str = Field(description="Error category.")
    detail: str = Field(description="Human-readable error explanation.")
