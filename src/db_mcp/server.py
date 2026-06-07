from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import formatters
from .client import DBClient, DBError

mcp = FastMCP("deutsche-bahn")
_client: DBClient | None = None


def _db() -> DBClient:
    global _client
    if _client is None:
        _client = DBClient()
    return _client


@mcp.tool()
def search_station(
    query: Annotated[str, Field(description="Station name or fragment, e.g. 'Berlin Hbf'")],
    limit: Annotated[int, Field(description="Max results (1-10)", ge=1, le=10)] = 5,
) -> str:
    """Find German train stations by name. Returns one line per match with the station ID and full name.

    The station ID is what you pass to get_departures or plan_journey."""
    try:
        items = _db().locations(query=query, results=limit)
    except DBError as e:
        return f"error: {e}"
    return formatters.format_stations(items)


@mcp.tool()
def get_departures(
    station_id: Annotated[str, Field(description="Station ID from search_station, e.g. '8011160'")],
    minutes_ahead: Annotated[int, Field(description="Time window in minutes (10-180)", ge=10, le=180)] = 60,
    limit: Annotated[int, Field(description="Max departures (1-20)", ge=1, le=20)] = 8,
) -> str:
    """Get upcoming departures from a German train station.

    Returns one line per departure: time, train line, direction, platform, delay."""
    try:
        payload = _db().departures(stop_id=station_id, duration=minutes_ahead, results=limit)
    except DBError as e:
        return f"error: {e}"
    return formatters.format_departures(payload)


@mcp.tool()
def plan_journey(
    from_station_id: Annotated[str, Field(description="Origin station ID from search_station")],
    to_station_id: Annotated[str, Field(description="Destination station ID from search_station")],
    departure: Annotated[
        str | None,
        Field(description="ISO-8601 departure time, e.g. '2026-06-06T14:00:00+02:00'. Omit for now."),
    ] = None,
    results: Annotated[int, Field(description="Number of options (1-5)", ge=1, le=5)] = 3,
) -> str:
    """Plan a train journey between two German stations.

    Returns one block per option: departure / arrival times, platforms, duration, transfers, lines used."""
    try:
        payload = _db().journeys(
            from_id=from_station_id, to_id=to_station_id, departure=departure, results=results,
        )
    except DBError as e:
        return f"error: {e}"
    return formatters.format_journeys(payload)


@mcp.tool()
def get_trip_details(
    trip_id: Annotated[str, Field(description="Trip ID from a journey leg or departure")],
) -> str:
    """Get the full stop-by-stop schedule for a specific train trip, including real-time delays."""
    try:
        payload = _db().trip(trip_id=trip_id)
    except DBError as e:
        return f"error: {e}"
    return formatters.format_trip(payload)


@mcp.tool()
def get_station_info(
    station_id: Annotated[str, Field(description="Station ID from search_station, e.g. '8011160'")],
) -> str:
    """Get full details for a German train station: address, coordinates, facilities (lifts,
    accessible toilets, parking, taxis, dining, shops, etc.)."""
    try:
        payload = _db().station_info(station_id=station_id)
    except DBError as e:
        return f"error: {e}"
    return formatters.format_station_info(payload)


@mcp.tool()
def nearby_stations(
    latitude: Annotated[float, Field(description="Latitude in WGS84")],
    longitude: Annotated[float, Field(description="Longitude in WGS84")],
    radius_m: Annotated[int, Field(description="Search radius in meters (100-10000)", ge=100, le=10000)] = 1000,
    limit: Annotated[int, Field(description="Max results (1-12)", ge=1, le=12)] = 6,
) -> str:
    """Find train stations near a geographic coordinate."""
    try:
        items = _db().nearby(latitude=latitude, longitude=longitude,
                             distance_m=radius_m, results=limit)
    except DBError as e:
        return f"error: {e}"
    return formatters.format_nearby(items)


def run() -> None:
    mcp.run()
