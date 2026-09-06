"""Small SQLite persistence layer for vehicles and telemetry."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class FleetRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    model TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
                    battery_pct REAL NOT NULL,
                    temperature_c REAL NOT NULL,
                    speed_kph REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'simulator'
                );

                CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_time
                    ON telemetry(vehicle_id, timestamp DESC);
                """
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(telemetry)").fetchall()
            }
            if "source" not in columns:
                connection.execute(
                    "ALTER TABLE telemetry ADD COLUMN source TEXT NOT NULL DEFAULT 'simulator'"
                )

    def seed_vehicles(self, vehicles: Iterable[tuple[int, str, str]]) -> None:
        with self.connect() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO vehicles(id, name, model) VALUES (?, ?, ?)", vehicles
            )

    def telemetry_count(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0])

    def insert_reading(
        self,
        vehicle_id: int,
        battery_pct: float,
        temperature_c: float,
        speed_kph: float,
        timestamp: str,
        source: str = "external_api",
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO telemetry(
                    vehicle_id, battery_pct, temperature_c, speed_kph, timestamp, source
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (vehicle_id, battery_pct, temperature_c, speed_kph, timestamp, source),
            )

    def insert_batch(self, rows: Iterable[tuple[int, float, float, float, str, str]]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO telemetry(
                    vehicle_id, battery_pct, temperature_c, speed_kph, timestamp, source
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def vehicle_exists(self, vehicle_id: int) -> bool:
        with self.connect() as connection:
            return (
                connection.execute("SELECT 1 FROM vehicles WHERE id = ?", (vehicle_id,)).fetchone()
                is not None
            )

    def list_vehicles(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT v.id, v.name, v.model,
                       t.battery_pct, t.temperature_c, t.speed_kph, t.timestamp, t.source
                FROM vehicles v
                LEFT JOIN telemetry t ON t.id = (
                    SELECT id FROM telemetry
                    WHERE vehicle_id = v.id
                    ORDER BY timestamp DESC, id DESC LIMIT 1
                )
                ORDER BY v.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_vehicle(self, vehicle_id: int, history_limit: int = 30) -> dict[str, Any] | None:
        with self.connect() as connection:
            vehicle = connection.execute(
                "SELECT id, name, model FROM vehicles WHERE id = ?", (vehicle_id,)
            ).fetchone()
            if vehicle is None:
                return None
            telemetry = connection.execute(
                """
                SELECT battery_pct, temperature_c, speed_kph, timestamp, source
                FROM telemetry WHERE vehicle_id = ?
                ORDER BY timestamp DESC, id DESC LIMIT ?
                """,
                (vehicle_id, history_limit),
            ).fetchall()
        return {**dict(vehicle), "telemetry": [dict(row) for row in telemetry]}
