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


# ── Request Models ───────────────────────────────────────────────────

class MessageRequest(BaseModel):
    """Incoming request to send a message.

    Attributes:
        platform: Target platform (``telegram``).
        message: The text content to deliver.
        recipient: Optional recipient override (chat ID or @username
            for Telegram). Falls back to the ``.env`` default when omitted.
    """

    platform: Platform = Field(
        default=Platform.TELEGRAM,
        description="Target messaging platform.",
        examples=["telegram"],
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
            "Optional Telegram chat ID or @username override. "
            "Falls back to the TELEGRAM_CHAT_ID in ``.env`` when omitted."
        ),
        examples=["123456789", "@username"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"platform": "telegram", "message": "Hello from the API!"},
                {"platform": "telegram", "message": "Hello!", "recipient": "123456789"},
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
