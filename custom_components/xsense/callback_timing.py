"""Bounded, payload-free measurements of one synchronous MQTT delivery."""

from dataclasses import dataclass


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

    def snapshot(self, total: float) -> dict[str, float | int | str | None]:
        return {
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
