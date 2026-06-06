from typing import Any

import httpx

BASE_URL = "https://v6.db.transport.rest"
TIMEOUT = 10.0


class DBError(RuntimeError):
    pass


class DBClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers={
            "User-Agent": "db-mcp-server (https://github.com/Amor216/db-mcp-server)",
            "Accept": "application/json",
        })

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DBClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            r = self._client.get(path, params=_clean_params(params or {}))
        except httpx.HTTPError as e:
            raise DBError(f"network: {e}") from e
        if r.status_code >= 500:
            raise DBError(f"upstream error {r.status_code}: {r.text[:200]}")
        if r.status_code == 404:
            raise DBError(f"not found: {path}")
        if r.status_code >= 400:
            raise DBError(f"bad request {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except ValueError as e:
            raise DBError(f"invalid json: {e}") from e

    def locations(self, query: str, results: int = 5, fuzzy: bool = True) -> list[dict]:
        return self._get("/locations", {"query": query, "results": results, "fuzzy": fuzzy})

    def departures(self, stop_id: str, duration: int = 60, results: int = 8,
                   when: str | None = None) -> dict:
        return self._get(f"/stops/{stop_id}/departures",
                         {"duration": duration, "results": results, "when": when})

    def journeys(self, from_id: str, to_id: str, departure: str | None = None,
                 results: int = 3) -> dict:
        return self._get("/journeys", {
            "from": from_id, "to": to_id, "departure": departure, "results": results,
            "stopovers": False, "remarks": True,
        })

    def trip(self, trip_id: str) -> dict:
        return self._get(f"/trips/{trip_id}", {"stopovers": True, "remarks": True})

    def nearby(self, latitude: float, longitude: float, distance_m: int = 1000,
               results: int = 6) -> list[dict]:
        return self._get("/locations/nearby", {
            "latitude": latitude, "longitude": longitude,
            "distance": distance_m, "results": results,
        })


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = "true" if v else "false"
        else:
            out[k] = v
    return out
