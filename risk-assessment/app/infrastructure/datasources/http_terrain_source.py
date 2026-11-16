"""HTTP adapter for MS4 Terrain Analysis (`/terrain/*`).

One batched `POST /terrain/profile` per path (SPEC §6 NFR) and
`GET /terrain/point` for single points. Error mapping follows the MS4
convention: 400 -> DomainValidationError, 404 -> NoCoverageError, any
other failure -> UpstreamUnavailableError (-> HTTP 502).
"""

from collections.abc import Sequence

import httpx

from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import SlopeSample
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamUnavailableError,
)
from app.infrastructure.datasources.guarded_call import call_with_retries


class HttpTerrainSource:
    def __init__(
        self,
        client: httpx.Client,
        body: str,
        retries: int,
    ) -> None:
        self._client = client
        self._body = body
        self._retries = retries

    def ping(self) -> bool:
        try:
            response = self._client.get("/health")
        except (httpx.HTTPError, httpx.InvalidURL):
            return False
        if response.status_code != 200:
            return False
        try:
            payload = response.json()
        except ValueError:
            return False
        return isinstance(payload, dict) and payload.get("status") == "ok"

    def slope_at(self, point: GeoPoint) -> float:
        def call() -> float:
            try:
                response = self._client.get(
                    "/terrain/point",
                    params={"lat": point.lat, "lon": point.lon, "body": self._body},
                )
            except (httpx.TimeoutException, httpx.TransportError):
                raise  # transport failures are retried by call_with_retries
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                raise UpstreamUnavailableError(f"Terrain service request failed: {exc}") from exc
            self._raise_for_status(response, "Terrain service")
            try:
                payload = response.json()
                slope = float(payload["slope_deg"])
            except (ValueError, KeyError, TypeError) as exc:
                raise UpstreamUnavailableError(
                    "Terrain service returned a malformed point response"
                ) from exc
            return slope

        return call_with_retries(call, retries=self._retries, what="MS4 point")

    def slope_profile(
        self, path: Sequence[GeoPoint], sample_distance_m: float
    ) -> tuple[SlopeSample, ...]:
        body = {
            "body": self._body,
            "path": [{"lat": p.lat, "lon": p.lon} for p in path],
            "sample_distance_m": sample_distance_m,
        }

        def call() -> tuple[SlopeSample, ...]:
            try:
                response = self._client.post("/terrain/profile", json=body)
            except (httpx.TimeoutException, httpx.TransportError):
                raise  # transport failures are retried by call_with_retries
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                raise UpstreamUnavailableError(f"Terrain service request failed: {exc}") from exc
            self._raise_for_status(response, "Terrain service")
            try:
                payload = response.json()
                samples = payload["samples"]
            except (ValueError, KeyError, TypeError) as exc:
                raise UpstreamUnavailableError(
                    "Terrain service returned a malformed profile response"
                ) from exc
            result: list[SlopeSample] = []
            for entry in samples:
                try:
                    result.append(
                        SlopeSample(
                            lat=float(entry["lat"]),
                            lon=float(entry["lon"]),
                            distance_m=float(entry["distance_m"]),
                            slope_deg=(
                                None
                                if entry.get("slope_deg") is None
                                else float(entry["slope_deg"])
                            ),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise UpstreamUnavailableError(
                        "Terrain service returned a malformed profile sample"
                    ) from exc
            return tuple(result)

        return call_with_retries(call, retries=self._retries, what="MS4 profile")

    @staticmethod
    def _raise_for_status(response: httpx.Response, service: str) -> None:
        if response.status_code == 400:
            raise DomainValidationError(_response_detail(response, service))
        if response.status_code == 404:
            raise NoCoverageError(_response_detail(response, service))
        if response.status_code != 200:
            raise UpstreamUnavailableError(
                f"{service} returned HTTP {response.status_code}: "
                f"{_response_detail(response, service)}"
            )


def _response_detail(response: httpx.Response, service: str) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict) and body.get("detail") is not None:
        return f"{service.lower()}: {body['detail']}"
    return f"HTTP {response.status_code}"
