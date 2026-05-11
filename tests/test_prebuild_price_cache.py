from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_prebuild_script_imports_when_launched_by_file_path(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "prebuild_price_cache.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy, sys; runpy.run_path(sys.argv[1], run_name='prebuild_import_test')",
            str(script),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
