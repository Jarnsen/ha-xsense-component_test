"""Bounded, payload-free measurements of one synchronous MQTT delivery."""

from dataclasses import dataclass


@dataclass(slots=True)
class SensorWriteTiming:
    """Measure the X-Sense portions of one sensor write."""

    sensor_type: str
    lookup_seconds: float = 0.0
    availability_seconds: float = 0.0
    value_seconds: float = 0.0


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
    slowest_sensor_write: SensorWriteTiming | None = None

    def snapshot(self, total: float) -> dict[str, float | int | str | None]:
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
        if (sensor := self.slowest_sensor_write) is not None:
            sample.update(
                slowest_sensor_type=sensor.sensor_type,
                slowest_sensor_lookup_seconds=round(sensor.lookup_seconds, 6),
                slowest_sensor_availability_seconds=round(sensor.availability_seconds, 6),
                slowest_sensor_value_seconds=round(sensor.value_seconds, 6),
            )
        return sample
