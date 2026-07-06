"""Test bootstrap for the bundled X-Sense client package."""

from __future__ import annotations

import sys
from pathlib import Path

VENDOR_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "xsense" / "_vendor"

if str(VENDOR_PATH) not in sys.path:
    sys.path.insert(0, str(VENDOR_PATH))
