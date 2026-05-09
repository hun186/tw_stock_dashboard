"""Development server entry point for the dashboard WSGI app."""

from __future__ import annotations

import os
from wsgiref.simple_server import make_server


def run_dev_server(app) -> None:
    """Serve the dashboard app with waitress when available, otherwise wsgiref."""
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    try:
        from waitress import serve

        print(f"Serving with waitress on http://{host}:{port}")
        serve(app, host=host, port=port)
    except ImportError:
        print("waitress not installed, fallback to wsgiref (development only).")
        print(f"Serving on http://{host}:{port}")
        with make_server(host, port, app) as httpd:
            httpd.serve_forever()
