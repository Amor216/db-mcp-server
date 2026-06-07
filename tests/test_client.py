import pytest
import respx
from httpx import Response

from db_mcp.client import (
    BASE_URL,
    BadRequestError,
    DBClient,
    DBError,
    NotFoundError,
    RateLimitedError,
    UpstreamError,
)


@respx.mock
def test_locations_ok():
    respx.get(f"{BASE_URL}/locations").mock(
        return_value=Response(200, json=[{"id": "8011160", "name": "Berlin Hbf"}])
    )
    with DBClient() as c:
        out = c.locations("Berlin")
    assert out[0]["id"] == "8011160"


@respx.mock
def test_departures_passes_params():
    route = respx.get(f"{BASE_URL}/stops/8011160/departures").mock(
        return_value=Response(200, json={"departures": []})
    )
    with DBClient() as c:
        c.departures("8011160", duration=30, results=5)
    assert route.calls.last.request.url.params["duration"] == "30"
    assert route.calls.last.request.url.params["results"] == "5"


@respx.mock
def test_journeys_drops_none_params():
    route = respx.get(f"{BASE_URL}/journeys").mock(
        return_value=Response(200, json={"journeys": []})
    )
    with DBClient() as c:
        c.journeys("A", "B", departure=None)
    qs = route.calls.last.request.url.params
    assert "departure" not in qs
    assert qs["from"] == "A"


@respx.mock
def test_server_error_raises():
    respx.get(f"{BASE_URL}/locations").mock(return_value=Response(503, text="upstream gone"))
    with DBClient() as c, pytest.raises(DBError, match="503"):
        c.locations("x")


@respx.mock
def test_404_raises():
    respx.get(f"{BASE_URL}/trips/nope").mock(return_value=Response(404))
    with DBClient() as c, pytest.raises(DBError, match="not found"):
        c.trip("nope")


@respx.mock
def test_bool_params_lowercased():
    route = respx.get(f"{BASE_URL}/locations").mock(
        return_value=Response(200, json=[])
    )
    with DBClient() as c:
        c.locations("Berlin", fuzzy=True)
    assert route.calls.last.request.url.params["fuzzy"] == "true"


@respx.mock
def test_locations_are_cached():
    route = respx.get(f"{BASE_URL}/locations").mock(
        return_value=Response(200, json=[{"id": "1", "name": "Berlin"}])
    )
    with DBClient() as c:
        c.locations("Berlin")
        c.locations("Berlin")
    assert route.call_count == 1


@respx.mock
def test_cache_distinguishes_query():
    route = respx.get(f"{BASE_URL}/locations").mock(
        return_value=Response(200, json=[])
    )
    with DBClient() as c:
        c.locations("Berlin")
        c.locations("Munich")
    assert route.call_count == 2


@respx.mock
def test_cache_disabled_with_zero_ttl():
    route = respx.get(f"{BASE_URL}/locations").mock(
        return_value=Response(200, json=[])
    )
    with DBClient(cache_ttl=0) as c:
        c.locations("Berlin")
        c.locations("Berlin")
    assert route.call_count == 2


@respx.mock
def test_departures_not_cached():
    route = respx.get(f"{BASE_URL}/stops/1/departures").mock(
        return_value=Response(200, json={"departures": []})
    )
    with DBClient() as c:
        c.departures("1")
        c.departures("1")
    assert route.call_count == 2


@respx.mock
def test_typed_errors_carry_status_and_path():
    respx.get(f"{BASE_URL}/locations").mock(return_value=Response(503, text="boom"))
    with DBClient() as c, pytest.raises(UpstreamError) as ei:
        c.locations("x")
    assert ei.value.status == 503
    assert ei.value.path == "/locations"
    assert isinstance(ei.value, DBError)
    assert ei.value.kind == "upstream"


@respx.mock
def test_429_raises_rate_limited():
    respx.get(f"{BASE_URL}/locations").mock(return_value=Response(429))
    with DBClient() as c, pytest.raises(RateLimitedError) as ei:
        c.locations("x")
    assert ei.value.kind == "rate_limited"


@respx.mock
def test_404_is_not_found_subclass():
    respx.get(f"{BASE_URL}/trips/nope").mock(return_value=Response(404))
    with DBClient() as c, pytest.raises(NotFoundError):
        c.trip("nope")


@respx.mock
def test_400_is_bad_request_subclass():
    respx.get(f"{BASE_URL}/locations").mock(return_value=Response(400, text="bad"))
    with DBClient() as c, pytest.raises(BadRequestError):
        c.locations("x")


def test_token_bucket_zero_rate_no_wait():
    from db_mcp.client import TokenBucket
    b = TokenBucket(0.0)
    assert b.take() == 0.0
    assert b.take() == 0.0


def test_token_bucket_serves_burst_immediately():
    from db_mcp.client import TokenBucket
    b = TokenBucket(rate_per_second=10.0, burst=5)
    for _ in range(5):
        assert b.take() == 0.0


def test_token_bucket_delays_after_burst():
    from db_mcp.client import TokenBucket
    b = TokenBucket(rate_per_second=10.0, burst=1)
    assert b.take() == 0.0
    wait = b.take()
    assert wait > 0
    assert wait <= 0.11
