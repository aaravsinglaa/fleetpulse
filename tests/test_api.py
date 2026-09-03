from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    app = create_app(tmp_path / "test.db", run_simulator=False)
    return TestClient(app)


def test_list_vehicles_returns_seeded_fleet(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/vehicles")
    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) == 10
    assert set(vehicles[0]) >= {
        "id",
        "name",
        "battery_pct",
        "temperature_c",
        "speed_kph",
        "timestamp",
        "source",
        "status",
    }


def test_vehicle_detail_includes_history_and_validates_limit(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/vehicles/3?history=5")
        invalid = client.get("/vehicles/3?history=0")
    assert response.status_code == 200
    assert response.json()["id"] == 3
    assert len(response.json()["telemetry"]) <= 5
    assert invalid.status_code == 422


def test_unknown_vehicle_returns_404(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/vehicles/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Vehicle not found"}


def test_incidents_expose_hot_and_stale_demo_conditions(tmp_path):
    with make_client(tmp_path) as client:
        incidents = client.get("/incidents").json()
    types = {incident["type"] for incident in incidents}
    assert {"high_temperature", "stale_telemetry"} <= types


def test_health_endpoint(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_telemetry_updates_vehicle_and_returns_diagnostics(tmp_path):
    payload = {
        "vehicle_id": 1,
        "battery_pct": 72.4,
        "temperature_c": 51.2,
        "speed_kph": 48.0,
        "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
        "source": "sensor_gateway",
    }
    with make_client(tmp_path) as client:
        response = client.post("/telemetry", json=payload)
        vehicle = client.get("/vehicles/1?history=1").json()
    assert response.status_code == 201
    assert response.json()["accepted"] is True
    assert response.json()["incidents"][0]["type"] == "high_temperature"
    assert response.json()["reading"]["battery_pct"] == 72.4
    assert response.json()["reading"]["source"] == "sensor_gateway"
    assert vehicle["telemetry"][0]["battery_pct"] == 72.4
    assert vehicle["telemetry"][0]["source"] == "sensor_gateway"


def test_ingest_rejects_unknown_vehicle_and_invalid_values(tmp_path):
    valid = {
        "vehicle_id": 999,
        "battery_pct": 80,
        "temperature_c": 30,
        "speed_kph": 45,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with make_client(tmp_path) as client:
        unknown = client.post("/telemetry", json=valid)
        invalid = client.post("/telemetry", json={**valid, "vehicle_id": 1, "battery_pct": 120})
    assert unknown.status_code == 404
    assert invalid.status_code == 422
