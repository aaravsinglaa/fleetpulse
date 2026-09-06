import sqlite3

from app.database import FleetRepository


def test_initialize_upgrades_legacy_telemetry_table(tmp_path):
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE vehicles (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                model TEXT NOT NULL
            );
            CREATE TABLE telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
                battery_pct REAL NOT NULL,
                temperature_c REAL NOT NULL,
                speed_kph REAL NOT NULL,
                timestamp TEXT NOT NULL
            );
            INSERT INTO vehicles VALUES (1, 'Atlas-01', 'Volterra Cargo');
            INSERT INTO telemetry(
                vehicle_id, battery_pct, temperature_c, speed_kph, timestamp
            ) VALUES (1, 80, 30, 40, '2026-09-06T12:00:00+00:00');
            """
        )

    repository = FleetRepository(database_path)
    repository.initialize()

    reading = repository.get_vehicle(1, 1)["telemetry"][0]
    assert reading["source"] == "simulator"
