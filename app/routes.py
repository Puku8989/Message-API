"""API route definitions.

Keeps HTTP-layer concerns (validation, serialisation, error mapping)
separated from the business logic in the service modules.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, status

from app.models import ErrorResponse, MessageRequest, MessageResponse, Platform
from app.telegram import send_telegram_message
from app.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/send",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message",
    description=(
        "Dispatch a text message to **Telegram**. An optional `recipient` "
        "field overrides the default chat ID configured in `.env`."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request body."},
        502: {"model": ErrorResponse, "description": "Upstream API error."},
        504: {"model": ErrorResponse, "description": "Upstream API timeout."},
    },
)
async def send_message(request: MessageRequest) -> MessageResponse:
    """Handle POST /send — dispatch a message to Telegram.

    Args:
        request: Validated :class:`MessageRequest` from the client.

    Returns:
        A :class:`MessageResponse` on successful delivery.

    Raises:
        HTTPException: Mapped from upstream errors for clean client responses.
    """
    logger.info(
        "Incoming request — platform=%s, message_length=%d, recipient=%s",
        request.platform.value,
        len(request.message),
        request.recipient or "(default)",
    )

    try:
        result = await send_telegram_message(
            request.message,
            chat_id=request.recipient,
        )
        confirmation = "Message sent via Telegram successfully."

    except httpx.TimeoutException as exc:
        logger.error("Timeout contacting Telegram API: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Telegram API timed out after retries.",
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Telegram API returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"Telegram API returned HTTP {exc.response.status_code}."
            ),
        ) from exc

    except ValueError as exc:
        logger.error("Upstream value error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        logger.error("Service unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error sending message")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Check server logs.",
        ) from exc

    return MessageResponse(
        success=True,
        platform=Platform.TELEGRAM,
        message=confirmation,
        details=result,
    )
