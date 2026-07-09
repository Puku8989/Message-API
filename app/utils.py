"""Shared utilities: logging setup, HTTP client factory, and retry decorator.

Centralises cross-cutting concerns so that service modules stay focused
on business logic.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, TypeVar

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

T = TypeVar("T")


# ── Logging ──────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Configure the root logger with a human-readable format.

    Called once at application startup.  Reads the desired log level from
    :func:`app.config.get_settings`.
    """
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Dot-separated logger name (usually ``__name__``).

    Returns:
        A :class:`logging.Logger` scoped to *name*.
    """
    return logging.getLogger(name)


# ── HTTP Client ──────────────────────────────────────────────────────

def create_http_client() -> httpx.AsyncClient:
    """Build a pre-configured async HTTP client.

    The client honours the ``api_timeout`` setting and follows redirects.

    Returns:
        An :class:`httpx.AsyncClient` ready for use.
    """
    settings = get_settings()
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.api_timeout),
        follow_redirects=True,
    )


# ── Retry Decorator ─────────────────────────────────────────────────

def _log_retry(retry_state: RetryCallState) -> None:
    """Log each retry attempt with context.

    Args:
        retry_state: Tenacity state object for the current retry cycle.
    """
    logger = get_logger("retry")
    logger.warning(
        "Retry attempt %d for %s — %s",
        retry_state.attempt_number,
        retry_state.fn.__name__ if retry_state.fn else "unknown",
        retry_state.outcome.exception() if retry_state.outcome else "N/A",
    )


def with_retry() -> Callable[..., Any]:
    """Return a tenacity retry decorator tuned to HTTP failures.

    Retries on :class:`httpx.HTTPStatusError`,
    :class:`httpx.TimeoutException`, and :class:`httpx.ConnectError`
    with exponential back-off (1 s → 2 s → 4 s …).

    Returns:
        A decorator that wraps an async function with retry logic.
    """
    settings = get_settings()
    return retry(
        retry=retry_if_exception_type(
            (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)
        ),
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=_log_retry,
        reraise=True,
    )
