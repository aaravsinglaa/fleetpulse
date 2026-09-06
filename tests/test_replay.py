from datetime import UTC, datetime

import pytest

from app.replay import load_replay_rows


def test_replay_aligns_last_reading_to_now_and_marks_source(tmp_path):
    source = tmp_path / "readings.csv"
    source.write_text(
        "vehicle_id,battery_pct,temperature_c,speed_kph,timestamp\n"
        "1,80,30,40,2026-01-01T00:00:00+00:00\n"
        "1,79,31,42,2026-01-01T00:00:02+00:00\n",
        encoding="utf-8",
    )
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    rows = load_replay_rows(source, now=now)
    assert rows[-1][4] == now.isoformat()
    assert rows[1][4] > rows[0][4]
    assert {row[5] for row in rows} == {"csv_replay"}


def test_replay_requires_all_columns(tmp_path):
    source = tmp_path / "invalid.csv"
    source.write_text("vehicle_id,battery_pct\n1,80\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        load_replay_rows(source)
