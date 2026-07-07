"""Unit tests for the WhatsApp service module.

All external HTTP calls are mocked via ``respx``, so no real API
credentials or network access are required.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
import respx

from app.whatsapp import GRAPH_API_BASE, GRAPH_API_VERSION, send_whatsapp_message


@pytest.mark.asyncio
class TestSendWhatsAppMessage:
    """Tests for :func:`send_whatsapp_message`."""

    def _url(self) -> str:
        """Build the expected WhatsApp API URL."""
        return f"{GRAPH_API_BASE}/{GRAPH_API_VERSION}/000000000000/messages"

    @respx.mock
    async def test_successful_send(self) -> None:
        """A 200 response without an ``error`` key should return parsed JSON."""
        mock_response = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "+10000000000", "wa_id": "10000000000"}],
            "messages": [{"id": "wamid.abc123"}],
        }
        respx.post(self._url()).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await send_whatsapp_message("Hello World")

        assert "messages" in result
        assert result["messages"][0]["id"] == "wamid.abc123"

    @respx.mock
    async def test_api_error_payload(self) -> None:
        """A 200 response with an ``error`` key should raise ``ValueError``."""
        respx.post(self._url()).mock(
            return_value=httpx.Response(
                200,
                json={
                    "error": {
                        "message": "Invalid OAuth access token.",
                        "type": "OAuthException",
                        "code": 190,
                    }
                },
            )
        )

        with pytest.raises(ValueError, match="Invalid OAuth"):
            await send_whatsapp_message("Hello World")

    @respx.mock
    async def test_http_error_raises(self) -> None:
        """A 4xx/5xx status should propagate as ``HTTPStatusError``."""
        respx.post(self._url()).mock(
            return_value=httpx.Response(403, json={"error": {"message": "Forbidden"}})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await send_whatsapp_message("Hello World")

    @respx.mock
    async def test_timeout_raises(self) -> None:
        """A network timeout should propagate as ``TimeoutException``."""
        respx.post(self._url()).mock(
            side_effect=httpx.ConnectTimeout("Connection timed out")
        )

        with pytest.raises(httpx.TimeoutException):
            await send_whatsapp_message("Hello World")
