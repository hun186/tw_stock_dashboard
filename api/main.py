from __future__ import annotations

from api.dashboard_app import app


__all__ = ["app"]


if __name__ == "__main__":
    from api.dashboard_server import run_dev_server

    run_dev_server(app)
