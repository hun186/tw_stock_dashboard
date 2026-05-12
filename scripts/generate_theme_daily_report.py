from __future__ import annotations

from pathlib import Path
import sys

# Allow `python scripts/generate_theme_daily_report.py` from any cwd without
# requiring PYTHONPATH to be preconfigured.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.theme_daily_report import main


if __name__ == "__main__":
    main()
