from db_mcp.formatters import (
    format_departures,
    format_journeys,
    format_stations,
    format_trip,
)


def test_stations_empty():
    assert format_stations([]) == "no stations found"


def test_stations_renders_id_and_name():
    out = format_stations([{"id": "8011160", "name": "Berlin Hbf",
                            "location": {"latitude": 52.5251, "longitude": 13.3694}}])
    assert "8011160" in out
    assert "Berlin Hbf" in out
    assert "52.5251" in out


def test_departures_empty():
    assert "no departures" in format_departures({"departures": []})


def test_departures_basic():
    out = format_departures({"departures": [{
        "when": "2026-06-06T15:42:00+02:00",
        "line": {"name": "ICE 1234"},
        "direction": "Munich Hbf",
        "platform": "8",
        "delay": 300,
    }]})
    assert "15:42" in out
    assert "+5m" in out
    assert "ICE 1234" in out
    assert "Munich" in out
    assert "Gleis 8" in out


def test_departures_cancelled_flag():
    out = format_departures({"departures": [{
        "when": "2026-06-06T15:42:00+02:00",
        "line": {"name": "ICE 1"}, "direction": "X", "platform": "1", "cancelled": True,
    }]})
    assert "CANCELLED" in out


def test_journeys_empty():
    assert format_journeys({"journeys": []}) == "no journeys found"


def test_journeys_renders_legs():
    out = format_journeys({"journeys": [{
        "legs": [
            {"departure": "2026-06-06T14:00:00+02:00", "arrival": "2026-06-06T16:30:00+02:00",
             "departurePlatform": "5", "arrivalPlatform": "8", "line": {"name": "ICE 100"}},
        ]
    }]})
    assert "14:00" in out
    assert "16:30" in out
    assert "ICE 100" in out
    assert "transfers: 0" in out
    assert "2h30" in out


def test_trip_renders_stopovers():
    out = format_trip({"trip": {
        "line": {"name": "ICE 1"}, "direction": "Berlin",
        "stopovers": [
            {"stop": {"name": "A"}, "arrival": "2026-06-06T10:00:00+02:00",
             "departure": "2026-06-06T10:02:00+02:00", "departurePlatform": "3"},
            {"stop": {"name": "B"}, "arrival": "2026-06-06T11:00:00+02:00",
             "departure": "2026-06-06T11:05:00+02:00", "departurePlatform": "5"},
        ],
    }})
    assert "ICE 1" in out
    assert "A" in out and "B" in out
    assert "10:00" in out and "11:05" in out
