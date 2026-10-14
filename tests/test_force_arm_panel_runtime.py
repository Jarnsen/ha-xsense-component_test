"""Run force-arm frontend tests with a mocked DOM and service transport."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_force_arm_panel_runtime():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for frontend runtime tests")
    script = Path(__file__).with_suffix(".mjs")
    result = subprocess.run(
        [node, "--test", str(script)], check=False, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
