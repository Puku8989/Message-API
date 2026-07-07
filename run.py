"""Application entry point.

Launches the uvicorn ASGI server with sensible defaults for local
development and production alike.
"""

import uvicorn


def main() -> None:
    """Start the uvicorn server.

    Reads the ASGI app from ``app.main:app`` so that module-level
    initialisation (logging, settings validation) happens inside the
    worker process.
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
