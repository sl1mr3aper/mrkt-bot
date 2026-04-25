"""Test fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure `pydantic-settings` does not try to load .env from CWD.
os.environ.setdefault("BOT_TOKEN", "")
os.environ.setdefault("MRKT_API_ID", "0")
os.environ.setdefault("MRKT_API_HASH", "")
