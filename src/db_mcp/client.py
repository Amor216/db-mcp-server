import threading
import time
from typing import Any

import httpx

BASE_URL = "https://v6.db.transport.rest"
TIMEOUT = 10.0
STATION_CACHE_TTL = 300.0
DEFAULT_RPS = 5.0


class TokenBucket:
    def __init__(self, rate_per_second: float, burst: int | None = None) -> None:
        self.rate = max(0.0, rate_per_second)
        self.capacity = float(burst if burst is not None else max(1, int(rate_per_second)))
        self.tokens = self.capacity
        self.last = time.monotonic()
        self._lock = threading.Lock()

    def take(self) -> float:
        if self.rate <= 0:
            return 0.0
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return 0.0
            needed = 1.0 - self.tokens
            wait = needed / self.rate
            self.tokens = 0.0
            self.last = now + wait
            return wait


class DBError(RuntimeError):
    kind: str = "error"

    def __init__(self, message: str, *, status: int | None = None, path: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.path = path


class NetworkError(DBError):
    kind = "network"


class UpstreamError(DBError):
    kind = "upstream"


class NotFoundError(DBError):
    kind = "not_found"


class BadRequestError(DBError):
    kind = "bad_request"


class InvalidResponseError(DBError):
    kind = "invalid_response"


class RateLimitedError(DBError):
    kind = "rate_limited"


class DBClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT,
                 cache_ttl: float = STATION_CACHE_TTL,
                 rate_per_second: float = DEFAULT_RPS,
                 burst: int | None = None) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers={
            "User-Agent": "db-mcp-server (https://github.com/Amor216/db-mcp-server)",
            "Accept": "application/json",
        })
        self._cache_ttl = cache_ttl
        self._cache: dict[tuple[str, frozenset[tuple[str, Any]]], tuple[float, Any]] = {}
        self._bucket = TokenBucket(rate_per_second, burst)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DBClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        wait = self._bucket.take()
        if wait > 0:
            time.sleep(wait)
        try:
            r = self._client.get(path, params=_clean_params(params or {}))
        except httpx.HTTPError as e:
            raise NetworkError(f"network: {e}", path=path) from e
        if r.status_code == 429:
            raise RateLimitedError(f"rate limited at {path}", status=429, path=path)
        if r.status_code >= 500:
            raise UpstreamError(f"upstream error {r.status_code}: {r.text[:200]}",
                                status=r.status_code, path=path)
        if r.status_code == 404:
            raise NotFoundError(f"not found: {path}", status=404, path=path)
        if r.status_code >= 400:
            raise BadRequestError(f"bad request {r.status_code}: {r.text[:200]}",
                                  status=r.status_code, path=path)
        try:
            return r.json()
        except ValueError as e:
            raise InvalidResponseError(f"invalid json: {e}", path=path) from e

    def locations(self, query: str, results: int = 5, fuzzy: bool = True) -> list[dict]:
        return self._cached_get("/locations", {"query": query, "results": results, "fuzzy": fuzzy})

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
        return self._cached_get("/locations/nearby", {
            "latitude": latitude, "longitude": longitude,
            "distance": distance_m, "results": results,
        })

    def _cached_get(self, path: str, params: dict[str, Any]) -> Any:
        if self._cache_ttl <= 0:
            return self._get(path, params)
        key = (path, frozenset((k, v) for k, v in params.items() if v is not None))
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit is not None and now - hit[0] < self._cache_ttl:
            return hit[1]
        data = self._get(path, params)
        self._cache[key] = (now, data)
        return data


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
