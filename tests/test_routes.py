"""Integration tests for API routes.

Tests the full request → response cycle through the FastAPI application
with external APIs mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for GET /health."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """Health endpoint should return 200 with status healthy."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
class TestSendEndpoint:
    """Tests for POST /send."""

    async def test_send_telegram_success(self, client: AsyncClient) -> None:
        """Valid Telegram request should return 200 with success payload."""
        mock_result = {"ok": True, "result": {"message_id": 1}}
        with patch(
            "app.routes.send_telegram_message",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await client.post(
                "/send",
                json={"platform": "telegram", "message": "Test message"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["platform"] == "telegram"

    async def test_invalid_platform_returns_422(self, client: AsyncClient) -> None:
        """An unknown platform should trigger a 422 validation error."""
        response = await client.post(
            "/send",
            json={"platform": "signal", "message": "Test"},
        )
        assert response.status_code == 422

    async def test_empty_message_returns_422(self, client: AsyncClient) -> None:
        """An empty message string should trigger a 422 validation error."""
        response = await client.post(
            "/send",
            json={"platform": "telegram", "message": ""},
        )
        assert response.status_code == 422

    async def test_missing_message_returns_422(self, client: AsyncClient) -> None:
        """A request with missing message field should return 422."""
        response = await client.post("/send", json={})
        assert response.status_code == 422

