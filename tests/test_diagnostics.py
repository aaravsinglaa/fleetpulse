from datetime import UTC, datetime, timedelta

from app.diagnostics import diagnose_vehicle

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


def vehicle(**overrides):
    base = {
        "id": 1,
        "name": "Atlas-01",
        "temperature_c": 35.0,
        "timestamp": NOW.isoformat(),
    }
    return {**base, **overrides}


def test_high_temperature_is_critical_only_above_threshold():
    assert diagnose_vehicle(vehicle(temperature_c=50.0), now=NOW) == []
    incidents = diagnose_vehicle(vehicle(temperature_c=50.1), now=NOW)
    assert incidents[0]["type"] == "high_temperature"
    assert incidents[0]["severity"] == "critical"


def test_stale_telemetry_uses_reading_age():
    timestamp = (NOW - timedelta(seconds=9)).isoformat()
    incidents = diagnose_vehicle(vehicle(timestamp=timestamp), now=NOW)
    assert [incident["type"] for incident in incidents] == ["stale_telemetry"]
    assert incidents[0]["value"] == 9.0


def test_vehicle_can_trigger_both_rules():
    timestamp = (NOW - timedelta(seconds=20)).isoformat()
    incidents = diagnose_vehicle(vehicle(temperature_c=55, timestamp=timestamp), now=NOW)
    assert {incident["type"] for incident in incidents} == {"high_temperature", "stale_telemetry"}


def test_future_timestamp_is_not_reported_as_stale():
    timestamp = (NOW + timedelta(seconds=30)).isoformat()
    assert diagnose_vehicle(vehicle(timestamp=timestamp), now=NOW) == []
