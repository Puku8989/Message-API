"""Shared test fixtures and configuration.

Patches ``get_settings`` globally so that tests never require a real
``.env`` file or live API credentials.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def _mock_settings() -> Settings:
    """Return a ``Settings`` instance with dummy credentials."""
    return Settings(
        telegram_bot_token="test-bot-token",
        telegram_chat_id="123456789",
        api_timeout=5,
        max_retries=1,
        log_level="DEBUG",
    )


@pytest.fixture(autouse=True)
def _patch_settings(_mock_settings: Settings):
    """Auto-patch ``get_settings`` for every test in the suite."""
    with patch("app.config.get_settings", return_value=_mock_settings):
        # Also patch in each module that imports get_settings at module level
        with patch("app.utils.get_settings", return_value=_mock_settings):
            yield


@pytest.fixture()
async def client() -> AsyncClient:
    """Provide an async test client wired to the FastAPI app."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
