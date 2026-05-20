"""CLI entry: `hyperspectral-viz` runs the Streamlit app."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    app = Path(__file__).resolve().parent / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app)]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
