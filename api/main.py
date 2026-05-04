"""Vercel Python entrypoint.

This repository's primary UI is a Streamlit app (`app.py`), which is not a native
Vercel serverless framework target. This file provides a minimal WSGI-compatible
entrypoint so Vercel can build and serve a response instead of failing at build time.
"""

from __future__ import annotations


def app(environ, start_response):
    body = (
        "tw_stock_dashboard is a Streamlit app. "
        "Run `streamlit run app.py` locally or deploy it on a container host "
        "that supports long-running processes."
    ).encode("utf-8")

    status = "200 OK"
    headers = [
        ("Content-Type", "text/plain; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status, headers)
    return [body]
