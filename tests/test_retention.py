from datetime import UTC, datetime, timedelta

import pytest

from app.database import FleetRepository
from app.main import get_retention_hours
from app.simulator import VEHICLES, TelemetrySimulator


def make_repository(tmp_path):
    repository = FleetRepository(tmp_path / "retention.db")
    repository.initialize()
    repository.seed_vehicles(VEHICLES)
    return repository


def test_prune_removes_expired_history_but_keeps_latest_reading(tmp_path):
    repository = make_repository(tmp_path)
    now = datetime(2026, 9, 6, 12, tzinfo=UTC)
    repository.insert_batch(
        [
            (1, 90, 30, 20, (now - timedelta(days=10)).isoformat(), "simulator"),
            (1, 80, 31, 25, now.isoformat(), "simulator"),
            (2, 70, 32, 0, (now - timedelta(days=10)).isoformat(), "simulator"),
        ]
    )

    deleted = repository.prune_readings_older_than((now - timedelta(days=7)).isoformat())

    assert deleted == 1
    assert repository.telemetry_count() == 2
    assert len(repository.get_vehicle(1)["telemetry"]) == 1
    assert len(repository.get_vehicle(2)["telemetry"]) == 1


def test_simulator_runs_retention_cleanup_on_schedule(tmp_path):
    repository = make_repository(tmp_path)
    repository.insert_reading(
        1,
        90,
        30,
        20,
        (datetime.now(UTC) - timedelta(days=10)).isoformat(),
        "simulator",
    )
    simulator = TelemetrySimulator(repository, retention_hours=24, cleanup_every_ticks=1)

    simulator.generate_tick()

    assert repository.telemetry_count() == 9


@pytest.mark.parametrize("value", [0, -1, "not-a-number"])
def test_retention_configuration_requires_positive_number(value):
    with pytest.raises(ValueError, match="FLEETPULSE_RETENTION_HOURS"):
        get_retention_hours(value)
