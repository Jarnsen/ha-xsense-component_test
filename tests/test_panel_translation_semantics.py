"""Run panel dictionary contracts and real translation-method regressions."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_panel_translation_semantics():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for frontend translation tests")
    script = Path(__file__).with_suffix(".mjs")
    result = subprocess.run(
        [node, "--test", str(script)], check=False, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
