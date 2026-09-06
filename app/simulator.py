"""Deterministic-enough synthetic telemetry producer."""

from __future__ import annotations

import asyncio
import math
import random
from datetime import UTC, datetime, timedelta

from app.database import FleetRepository

VEHICLES = [
    (1, "Atlas-01", "Volterra Cargo"),
    (2, "Beacon-02", "Volterra Cargo"),
    (3, "Comet-03", "Ion Transit"),
    (4, "Drift-04", "Ion Transit"),
    (5, "Echo-05", "Nova Hauler"),
    (6, "Flare-06", "Nova Hauler"),
    (7, "Glide-07", "Volterra Cargo"),
    (8, "Halo-08", "Ion Transit"),
    (9, "Juno-09", "Nova Hauler"),
    (10, "Kite-10", "Volterra Cargo"),
]


class TelemetrySimulator:
    """Writes a reading for each reporting vehicle on every tick."""

    def __init__(self, repository: FleetRepository, interval_seconds: float = 2.0, seed: int = 42):
        self.repository = repository
        self.interval_seconds = interval_seconds
        self.random = random.Random(seed)
        self.tick_number = 0

    def seed_demo_readings(self) -> None:
        """Create an immediately useful fleet state, including two intentional alerts."""
        now = datetime.now(UTC)
        rows = []
        for vehicle_id, _, _ in VEHICLES:
            timestamp = now - timedelta(seconds=18 if vehicle_id == 8 else 0)
            temperature = 53.4 if vehicle_id == 3 else 27.0 + vehicle_id * 0.8
            rows.append(
                (
                    vehicle_id,
                    94.0 - vehicle_id * 3.7,
                    temperature,
                    0.0 if vehicle_id == 8 else 24.0 + vehicle_id * 3.2,
                    timestamp.isoformat(),
                    "simulator",
                )
            )
        self.repository.insert_batch(rows)

    def generate_tick(self) -> None:
        self.tick_number += 1
        now = datetime.now(UTC).isoformat()
        rows = []
        for vehicle_id, _, _ in VEHICLES:
            if vehicle_id == 8:  # Intentional communications dropout for the stale rule.
                continue
            phase = self.tick_number / 3 + vehicle_id
            battery = max(8.0, 95.0 - vehicle_id * 3.7 - self.tick_number * 0.025)
            base_temperature = 52.5 if vehicle_id == 3 else 27.5 + vehicle_id * 0.75
            temperature = (
                base_temperature + math.sin(phase) * 1.3 + self.random.uniform(-0.25, 0.25)
            )
            speed = max(0.0, 43.0 + math.sin(phase * 0.72) * 29 + self.random.uniform(-3, 3))
            rows.append((vehicle_id, battery, temperature, speed, now, "simulator"))
        self.repository.insert_batch(rows)

    async def run(self) -> None:
        while True:
            self.generate_tick()
            await asyncio.sleep(self.interval_seconds)
