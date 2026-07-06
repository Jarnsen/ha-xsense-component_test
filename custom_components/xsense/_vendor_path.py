"""Make the bundled X-Sense client package importable."""

from __future__ import annotations

import sys
from pathlib import Path

VENDOR_PATH = Path(__file__).with_name("_vendor")


def install_vendor_path() -> None:
    """Prefer the reviewed package snapshot bundled with the integration."""
    vendor = str(VENDOR_PATH)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
