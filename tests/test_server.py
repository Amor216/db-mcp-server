import respx
from httpx import Response

from db_mcp import server
from db_mcp.client import BASE_URL


@respx.mock
def test_search_station_returns_text():
    respx.get(f"{BASE_URL}/locations").mock(
        return_value=Response(200, json=[{"id": "8011160", "name": "Berlin Hbf"}])
    )
    server._client = None  # force fresh client
    out = server.search_station("Berlin")
    assert "8011160" in out
    assert "Berlin Hbf" in out


@respx.mock
def test_get_departures_error_path():
    respx.get(f"{BASE_URL}/stops/x/departures").mock(return_value=Response(503))
    server._client = None
    out = server.get_departures("x")
    assert out.startswith("error:")


@respx.mock
def test_plan_journey_renders_block():
    respx.get(f"{BASE_URL}/journeys").mock(return_value=Response(200, json={"journeys": [{
        "legs": [{"departure": "2026-06-06T14:00:00+02:00",
                  "arrival": "2026-06-06T16:30:00+02:00",
                  "departurePlatform": "1", "arrivalPlatform": "2",
                  "line": {"name": "ICE 1"}}]
    }]}))
    server._client = None
    out = server.plan_journey("A", "B")
    assert "ICE 1" in out
    assert "2h30" in out


def test_mcp_registers_six_tools():
    for name in ("search_station", "get_departures", "plan_journey",
                 "get_trip_details", "get_station_info", "nearby_stations"):
        assert hasattr(server, name)


def test_run_rejects_unknown_transport():
    import pytest
    with pytest.raises(ValueError, match="unknown transport"):
        server.run(transport="quic")
