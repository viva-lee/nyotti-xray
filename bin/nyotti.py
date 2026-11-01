#!/usr/bin/env python3
"""nyotti-xray CLI. Run with `python -I bin/nyotti.py <command>` so nothing in the data folders can be imported."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nyotti.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
