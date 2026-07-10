"""API route definitions.

Keeps HTTP-layer concerns (validation, serialisation, error mapping)
separated from the business logic in the service modules.
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi import APIRouter, HTTPException, status

from app.models import ErrorResponse, MessageRequest, MessageResponse, Platform
from app.telegram import send_telegram_message
from app.utils import get_logger
from app.whatsapp import send_whatsapp_message

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/send",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message",
    description=(
        "Dispatch a text message to **Telegram**, **WhatsApp**, or **both** "
        "simultaneously. The platform is selected via the `platform` field "
        "in the request body. An optional `recipient` field overrides the "
        "default recipient configured in `.env`."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request body."},
        502: {"model": ErrorResponse, "description": "Upstream API error."},
        504: {"model": ErrorResponse, "description": "Upstream API timeout."},
    },
)
async def send_message(request: MessageRequest) -> MessageResponse:
    """Handle POST /send — dispatch a message to the chosen platform(s).

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
        if request.platform is Platform.BOTH:
            # Resolve per-platform recipients
            tg_chat = (
                request.telegram_chat_id
                or request.recipient
            )
            wa_number = (
                request.whatsapp_recipient
                or request.recipient
            )

            if not tg_chat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "A Telegram chat_id is required. Provide it via "
                        "'telegram_chat_id' or 'recipient' in the request body."
                    ),
                )

            # Fire both simultaneously
            tg_result, wa_result = await asyncio.gather(
                send_telegram_message(
                    request.message,
                    chat_id=tg_chat,
                ),
                send_whatsapp_message(
                    request.message,
                    recipient_number=wa_number,
                ),
            )
            result = {"telegram": tg_result, "whatsapp": wa_result}
            confirmation = "Message sent via Telegram and WhatsApp successfully."
            platform_label = Platform.BOTH

        elif request.platform is Platform.TELEGRAM:
            tg_chat = request.recipient
            if not tg_chat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "A Telegram chat_id is required. Provide it via "
                        "'recipient' in the request body (e.g. a numeric "
                        "chat ID or @username)."
                    ),
                )
            result = await send_telegram_message(
                request.message,
                chat_id=tg_chat,
            )
            confirmation = "Message sent via Telegram successfully."
            platform_label = Platform.TELEGRAM

        else:
            result = await send_whatsapp_message(
                request.message,
                recipient_number=request.recipient,
            )
            confirmation = "Message sent via Whatsapp successfully."
            platform_label = Platform.WHATSAPP

    except httpx.TimeoutException as exc:
        logger.error("Timeout contacting %s API: %s", request.platform.value, exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{request.platform.value.title()} API timed out after retries.",
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(
            "%s API returned HTTP %s: %s",
            request.platform.value,
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"{request.platform.value.title()} API returned "
                f"HTTP {exc.response.status_code}."
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
        platform=platform_label,
        message=confirmation,
        details=result,
    )
