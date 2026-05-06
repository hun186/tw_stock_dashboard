from __future__ import annotations

import json
from pathlib import Path


SERVER_CONFIG_DIR = Path(__file__).resolve().parent.parent / "data" / "dashboard_configs"


def load_server_config_presets() -> list[dict[str, object]]:
    if not SERVER_CONFIG_DIR.exists():
        return []
    presets: list[dict[str, object]] = []
    for path in sorted(SERVER_CONFIG_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        cfg = payload.get("config") if isinstance(payload, dict) else payload
        if not isinstance(cfg, dict):
            continue
        presets.append({
            "id": path.name,
            "label": str(payload.get("name", path.stem)) if isinstance(payload, dict) else path.stem,
            "config": cfg,
        })
    return presets


