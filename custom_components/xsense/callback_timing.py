"""Bounded, payload-free measurements of one synchronous MQTT delivery."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from sys import _current_frames
from threading import Event, Thread, get_ident
from time import perf_counter, thread_time

SLOW_STATE_WRITE_SECONDS = 0.1
_STACK_SAMPLE_AT = (0.1, 0.25, 0.5, 1.0, 2.0)
_MAX_STACK_FRAMES = 12


@dataclass(slots=True)
class _ActiveStateWrite:
    started: float
    cpu_started: float
    stacks: list[tuple[float, list[str]]] = field(default_factory=list)


class StateWriteProbe:
    """Sample a slow MQTT sensor write without patching Home Assistant."""

    def __init__(self) -> None:
        self._thread_id = get_ident()
        self._stop = Event()
        self._active: _ActiveStateWrite | None = None
        self._last_write = perf_counter()
        self._thread = Thread(target=self._sample, name="X-Sense write diagnostics", daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        return not self._stop.is_set() and self._thread.is_alive()

    def close(self) -> None:
        self._stop.set()

    def begin(self) -> tuple[_ActiveStateWrite, _ActiveStateWrite | None]:
        previous = self._active
        started = self._last_write = perf_counter()
        write = self._active = _ActiveStateWrite(started, thread_time())
        return write, previous

    def finish(self, scope, key: str) -> dict | None:
        write, previous = scope
        wall = perf_counter() - write.started
        cpu = thread_time() - write.cpu_started
        self._active = previous
        if wall < SLOW_STATE_WRITE_SECONDS:
            return None
        stacks = [
            {"elapsed_seconds": round(elapsed, 6), "frames": frames}
            for elapsed, frames in write.stacks if elapsed <= wall and frames
        ]
        return {
            "sensor_type": key,
            "completed_at_utc": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "wall_seconds": round(wall, 6),
            "thread_cpu_seconds": round(cpu, 6),
            "non_cpu_seconds": round(max(0., wall - cpu), 6),
            "stack_capture": "captured" if stacks else "no_sample_during_write",
            "stack_samples": stacks,
        }

    def _sample(self) -> None:
        while not self._stop.wait(0.05):
            write = self._active
            now = perf_counter()
            if write is None:
                if now - self._last_write >= 60:
                    return
                continue
            elapsed = now - write.started
            if len(write.stacks) >= len(_STACK_SAMPLE_AT) or elapsed < _STACK_SAMPLE_AT[len(write.stacks)]:
                continue
            frames = []
            frame = _current_frames().get(self._thread_id)
            for _ in range(_MAX_STACK_FRAMES):
                if frame is None:
                    break
                # Code locations only: no arguments, locals, paths or entity IDs.
                module = frame.f_globals.get("__name__", "")
                name = frame.f_code.co_name
                if isinstance(module, str) and len(module) <= 100 and all(
                    part.isidentifier() for part in module.split(".")
                ) and name.isidentifier() and len(name) <= 100:
                    frames.append(f"{module}.{name}:{frame.f_lineno}")
                frame = frame.f_back
            if self._active is write:
                write.stacks.append((elapsed, frames))


@dataclass
class CallbackTiming:
    """Accumulate discovery and entity work without retaining devices or messages."""

    discovery_seconds: float = 0.0
    discovery_calls: int = 0
    entity_write_seconds: float = 0.0
    entity_write_calls: int = 0
    reported_child_count: int | None = None
    slowest_entity_write_seconds: float = 0.0
    slowest_entity_write_class: str | None = None
    state_write_probe: StateWriteProbe | None = None
    slowest_sensor_state_write: dict | None = None
    slowest_traced_sensor_state_write: dict | None = None

    def record_sensor_state_write(self, sample: dict) -> None:
        previous = self.slowest_sensor_state_write
        if previous is None or sample["wall_seconds"] > previous["wall_seconds"]:
            self.slowest_sensor_state_write = sample
        if sample["stack_samples"]:
            previous = self.slowest_traced_sensor_state_write
            if previous is None or sample["wall_seconds"] > previous["wall_seconds"]:
                self.slowest_traced_sensor_state_write = sample

    def snapshot(self, total: float) -> dict:
        sample = {
            "total_seconds": total,
            "reported_child_count": self.reported_child_count,
            "discovery_seconds": round(self.discovery_seconds, 6),
            "discovery_calls": self.discovery_calls,
            "entity_write_seconds": round(self.entity_write_seconds, 6),
            "entity_write_calls": self.entity_write_calls,
            "slowest_entity_write_seconds": round(self.slowest_entity_write_seconds, 6),
            "slowest_entity_write_class": self.slowest_entity_write_class,
            "other_seconds": round(max(0.0, total - self.discovery_seconds - self.entity_write_seconds), 6),
        }
        if self.slowest_sensor_state_write is not None:
            sample["slowest_sensor_state_write"] = self.slowest_sensor_state_write
        return sample
