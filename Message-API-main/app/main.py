"""FastAPI application factory.

Creates and configures the ASGI application with middleware, routes,
exception handlers, and OpenAPI metadata.
"""

from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router
<<<<<<< HEAD
from app.telegram_client import connect as telethon_connect, disconnect as telethon_disconnect
=======
>>>>>>> bc45bdcd3a030c6986506cfcb8f3301db22d6c75
from app.utils import get_logger, setup_logging

# Resolve the static directory relative to the project root
_STATIC_DIR = pathlib.Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler — runs setup on startup.

    Args:
        _app: The FastAPI instance (unused).

    Yields:
        Control back to the framework while the app is running.
    """
    setup_logging()
    logger = get_logger(__name__)
    logger.info("🚀 Message API is starting up")
<<<<<<< HEAD

    # Connect the Telethon client (no-op if credentials are not configured)
    await telethon_connect()

    yield

    # Disconnect the Telethon client
    await telethon_disconnect()
=======
    yield
>>>>>>> bc45bdcd3a030c6986506cfcb8f3301db22d6c75
    logger.info("🛑 Message API is shutting down")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application.

    Returns:
        A fully wired :class:`FastAPI` instance ready to serve.
    """
    app = FastAPI(
        title="Message API",
        description=(
            "A production-ready REST API for sending text messages to "
            "**Telegram** and **WhatsApp** via their official APIs.\n\n"
            "## Quick Start\n"
            "1. Copy `.env.example` → `.env` and fill in your credentials.\n"
            "2. `pip install -r requirements.txt`\n"
            "3. `python run.py`\n"
            "4. Open http://localhost:8000/docs for interactive Swagger UI."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────────────
    app.include_router(router, tags=["Messaging"])

    # ── Exception Handlers ───────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Return a 422 response with a clean error envelope."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Validation Error",
                "detail": str(exc.errors()),
            },
        )

    # ── Health Check ─────────────────────────────────────────────────
    @app.get(
        "/health",
        summary="Health check",
        tags=["System"],
    )
    async def health_check() -> dict[str, str]:
        """Return application health status.

        Returns:
            A dictionary with ``status`` key.
        """
        return {"status": "healthy"}

    # ── Static Files & Dashboard ─────────────────────────────────
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=_STATIC_DIR, html=True), name="static")

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        """Redirect the root URL to the dashboard."""
        return RedirectResponse(url="/static/index.html")

    return app


# Module-level app instance used by uvicorn
app: FastAPI = create_app()
