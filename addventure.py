"""
Addventure CLI — thin entry point for `python addventure.py`.
Prefer `uv run adv` instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from addventure.cli import main

if __name__ == "__main__":
    main()
