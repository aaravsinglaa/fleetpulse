"""CSV parsing and timestamp alignment for telemetry replay."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from app.diagnostics import parse_timestamp

REQUIRED_COLUMNS = {
    "vehicle_id",
    "battery_pct",
    "temperature_c",
    "speed_kph",
    "timestamp",
}


def load_replay_rows(
    csv_path: str | Path, *, align_to_now: bool = True, now: datetime | None = None
) -> list[tuple[int, float, float, float, str, str]]:
    """Load CSV readings and optionally move the final timestamp to the present."""
    with Path(csv_path).open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
        parsed = [
            (
                int(row["vehicle_id"]),
                float(row["battery_pct"]),
                float(row["temperature_c"]),
                float(row["speed_kph"]),
                parse_timestamp(row["timestamp"]),
            )
            for row in reader
        ]

    if not parsed:
        raise ValueError("CSV contains no telemetry rows")

    offset = None
    if align_to_now:
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        offset = current_time - max(row[4] for row in parsed)

    return [
        (
            vehicle_id,
            battery,
            temperature,
            speed,
            (timestamp + offset if offset is not None else timestamp).isoformat(),
            "csv_replay",
        )
        for vehicle_id, battery, temperature, speed, timestamp in parsed
    ]
