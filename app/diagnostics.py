"""Pure diagnostic rules for fleet telemetry."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

HIGH_TEMPERATURE_C = 50.0
STALE_AFTER_SECONDS = 8.0


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    aware = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return aware.astimezone(UTC)


def diagnose_vehicle(
    vehicle: dict[str, Any],
    *,
    now: datetime | None = None,
    high_temperature_c: float = HIGH_TEMPERATURE_C,
    stale_after_seconds: float = STALE_AFTER_SECONDS,
) -> list[dict[str, Any]]:
    """Return active incidents for one vehicle's latest telemetry."""
    if not vehicle.get("timestamp"):
        return []

    current_time = now or datetime.now(UTC)
    age_seconds = max(0.0, (current_time - parse_timestamp(vehicle["timestamp"])).total_seconds())
    incidents: list[dict[str, Any]] = []

    if float(vehicle["temperature_c"]) > high_temperature_c:
        incidents.append(
            {
                "vehicle_id": vehicle["id"],
                "vehicle_name": vehicle["name"],
                "type": "high_temperature",
                "severity": "critical",
                "message": f"Temperature is {float(vehicle['temperature_c']):.1f}°C",
                "value": round(float(vehicle["temperature_c"]), 1),
                "threshold": high_temperature_c,
                "detected_at": vehicle["timestamp"],
            }
        )

    if age_seconds > stale_after_seconds:
        incidents.append(
            {
                "vehicle_id": vehicle["id"],
                "vehicle_name": vehicle["name"],
                "type": "stale_telemetry",
                "severity": "warning",
                "message": f"No telemetry for {int(age_seconds)}s",
                "value": round(age_seconds, 1),
                "threshold": stale_after_seconds,
                "detected_at": vehicle["timestamp"],
            }
        )

    return incidents


def diagnose_fleet(
    vehicles: list[dict[str, Any]], *, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Return active incidents, ordered by severity then vehicle."""
    incidents = [
        incident for vehicle in vehicles for incident in diagnose_vehicle(vehicle, now=now)
    ]
    rank = {"critical": 0, "warning": 1}
    return sorted(incidents, key=lambda item: (rank[item["severity"]], item["vehicle_id"]))
