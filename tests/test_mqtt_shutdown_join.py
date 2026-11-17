"""Bounded liveness regression for an operation joining shutdown from finally."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("operation_count", [1, 8, 32])
def test_cancelled_operation_can_join_shutdown_from_finally(operation_count):
    root = Path(__file__).resolve().parent.parent
    # A broken implementation forms a cancellation-resistant task cycle. Keep
    # the liveness probe isolated so pytest's own loop can always be torn down.
    script = r'''
import asyncio
import os
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from test_audit_repairs import make_coordinator, make_station
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

async def main():
    coordinator = make_coordinator(make_station())
    close = AsyncMock()
    coordinator.xsense = NS(close=close)
    coordinator._async_disconnect_mqtt = AsyncMock()
    DataUpdateCoordinator.async_shutdown = AsyncMock()
    entered, joining = asyncio.Event(), asyncio.Event()
    started = 0

    async def operation():
        nonlocal started
        async with coordinator._async_operation():
            started += 1
            if started == int(os.environ["JOIN_OPERATION_COUNT"]):
                entered.set()
            try:
                await asyncio.Future()
            finally:
                joining.set()
                await coordinator.async_shutdown()

    operations = [asyncio.create_task(operation()) for _ in range(int(os.environ["JOIN_OPERATION_COUNT"]))]
    await entered.wait()
    shutdown = asyncio.create_task(coordinator.async_shutdown())
    await joining.wait()
    done, _ = await asyncio.wait({*operations, shutdown}, timeout=3)
    success = (
        len(done) == len(operations) + 1 and all(task.cancelled() for task in operations)
        and not shutdown.cancelled() and shutdown.exception() is None
        and close.await_count == 1 and not coordinator._operation_tasks
    )
    if not success:
        print({"shutdown_finished": shutdown.done(), "operations_finished": sum(task.done() for task in operations), "close_calls": close.await_count}, flush=True)
    os._exit(0 if success else 1)

asyncio.run(main())
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env={**os.environ, "JOIN_OPERATION_COUNT": str(operation_count), "PYTHONPATH": os.pathsep.join((str(root / "tests"), str(root)))},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
