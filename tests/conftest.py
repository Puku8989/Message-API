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
        whatsapp_access_token="test-access-token",
        whatsapp_phone_number_id="000000000000",
        whatsapp_recipient_number="+10000000000",
        api_timeout=5,
        max_retries=1,
        log_level="DEBUG",
    )


@pytest.fixture(autouse=True)
def _patch_settings(_mock_settings: Settings):
    """Auto-patch ``get_settings`` for every test in the suite.

    Every module that does ``from app.config import get_settings`` gets
    its own local reference, so we must patch each one individually.
    """
    with (
        patch("app.config.get_settings", return_value=_mock_settings),
        patch("app.utils.get_settings", return_value=_mock_settings),
        patch("app.telegram.get_settings", return_value=_mock_settings),
        patch("app.whatsapp.get_settings", return_value=_mock_settings),
    ):
        yield


@pytest.fixture()
async def client() -> AsyncClient:
    """Provide an async test client wired to the FastAPI app."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
