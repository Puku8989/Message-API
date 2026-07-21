"""Browser-friendly application entry point.

Run with:
    python app.py

Then open http://localhost:8000 in your browser to access the dashboard or docs.
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
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
