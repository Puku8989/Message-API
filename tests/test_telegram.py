"""Unit tests for the Telegram service module.

All external HTTP calls are mocked via ``respx``, so no real API
credentials or network access are required.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
import respx

from app.telegram import TELEGRAM_API_BASE, send_telegram_message


@pytest.mark.asyncio
class TestSendTelegramMessage:
    """Tests for :func:`send_telegram_message`."""

    @respx.mock
    async def test_successful_send(self) -> None:
        """A 200 response with ``ok: true`` should return the parsed JSON."""
        mock_response = {
            "ok": True,
            "result": {
                "message_id": 42,
                "chat": {"id": 123456789},
                "text": "Hello World",
            },
        }
        respx.post(f"{TELEGRAM_API_BASE}/bottest-bot-token/sendMessage").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await send_telegram_message("Hello World")

        assert result["ok"] is True
        assert result["result"]["message_id"] == 42

    @respx.mock
    async def test_api_returns_not_ok(self) -> None:
        """A 200 response with ``ok: false`` should raise ``ValueError``."""
        respx.post(f"{TELEGRAM_API_BASE}/bottest-bot-token/sendMessage").mock(
            return_value=httpx.Response(
                200,
                json={"ok": False, "description": "Bad Request: chat not found"},
            )
        )

        with pytest.raises(ValueError, match="chat not found"):
            await send_telegram_message("Hello World")

    @respx.mock
    async def test_http_error_raises(self) -> None:
        """A 4xx/5xx status should propagate as ``HTTPStatusError``."""
        respx.post(f"{TELEGRAM_API_BASE}/bottest-bot-token/sendMessage").mock(
            return_value=httpx.Response(401, json={"ok": False, "description": "Unauthorized"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await send_telegram_message("Hello World")

    @respx.mock
    async def test_timeout_raises(self) -> None:
        """A network timeout should propagate as ``TimeoutException``."""
        respx.post(f"{TELEGRAM_API_BASE}/bottest-bot-token/sendMessage").mock(
            side_effect=httpx.ConnectTimeout("Connection timed out")
        )

        with pytest.raises(httpx.TimeoutException):
            await send_telegram_message("Hello World")
