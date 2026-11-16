"""HTTP adapter for MS3 Raster Service (`/raster/{dataset}/*`).

`point_values` -> `GET /raster/{dataset}/point` (all bands at once);
`sample_band` -> `POST /raster/{dataset}/sample` per band (batched per
SPEC §6 NFR); `ping` -> `GET /health` plus dataset readability, mirroring
MS4's HttpRasterDatasource contract.
"""

from collections.abc import Sequence

import httpx

from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import BandSample
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamUnavailableError,
)
from app.infrastructure.datasources.guarded_call import call_with_retries


class HttpRasterSource:
    def __init__(
        self,
        client: httpx.Client,
        dataset: str,
        retries: int,
    ) -> None:
        self._client = client
        self._dataset = dataset
        self._retries = retries

    def ping(self) -> bool:
        try:
            response = self._client.get("/health")
        except (httpx.HTTPError, httpx.InvalidURL):
            return False
        if response.status_code != 200:
            return False
        try:
            body = response.json()
        except ValueError:
            return False
        if not isinstance(body, dict) or body.get("status") != "ok":
            return False
        datasets = body.get("datasets")
        if not isinstance(datasets, list):
            return False
        return any(
            isinstance(entry, dict)
            and entry.get("name") == self._dataset
            and entry.get("readable") is True
            for entry in datasets
        )

    def dataset_bands(self) -> tuple[str, ...]:
        def call() -> tuple[str, ...]:
            try:
                response = self._client.get(f"/raster/{self._dataset}/metadata")
            except (httpx.TimeoutException, httpx.TransportError):
                raise  # transport failures are retried by call_with_retries
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                raise UpstreamUnavailableError(f"Raster service request failed: {exc}") from exc
            self._raise_for_status(response)
            try:
                payload = response.json()
                bands = payload["bands"]
                return tuple(str(b["name"]) for b in bands)
            except (ValueError, KeyError, TypeError) as exc:
                raise UpstreamUnavailableError(
                    "Raster service returned malformed metadata"
                ) from exc

        return call_with_retries(call, retries=self._retries, what="MS3 metadata")

    def point_values(self, point: GeoPoint) -> dict[str, float | None]:
        def call() -> dict[str, float | None]:
            try:
                response = self._client.get(
                    f"/raster/{self._dataset}/point",
                    params={"lat": point.lat, "lon": point.lon},
                )
            except (httpx.TimeoutException, httpx.TransportError):
                raise  # transport failures are retried by call_with_retries
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                raise UpstreamUnavailableError(f"Raster service request failed: {exc}") from exc
            self._raise_for_status(response)
            try:
                payload = response.json()
                values = payload["values"]
            except (ValueError, KeyError, TypeError) as exc:
                raise UpstreamUnavailableError(
                    "Raster service returned a malformed point response"
                ) from exc
            if not isinstance(values, dict):
                raise UpstreamUnavailableError("Raster service returned malformed point values")
            return {
                str(name): (None if value is None else float(value))
                for name, value in values.items()
            }

        return call_with_retries(call, retries=self._retries, what="MS3 point")

    def sample_band(
        self,
        band: str,
        path: Sequence[GeoPoint],
        sample_distance_m: float,
    ) -> tuple[BandSample, ...]:
        body = {
            "band": band,
            "path": [{"lat": p.lat, "lon": p.lon} for p in path],
            "sample_distance_m": sample_distance_m,
        }

        def call() -> tuple[BandSample, ...]:
            try:
                response = self._client.post(f"/raster/{self._dataset}/sample", json=body)
            except (httpx.TimeoutException, httpx.TransportError):
                raise  # transport failures are retried by call_with_retries
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                raise UpstreamUnavailableError(f"Raster service request failed: {exc}") from exc
            self._raise_for_status(response)
            try:
                payload = response.json()
                samples = payload["samples"]
            except (ValueError, KeyError, TypeError) as exc:
                raise UpstreamUnavailableError(
                    "Raster service returned a malformed sample response"
                ) from exc
            result: list[BandSample] = []
            for entry in samples:
                try:
                    raw = entry.get("value")
                    result.append(
                        BandSample(
                            lat=float(entry["lat"]),
                            lon=float(entry["lon"]),
                            distance_m=float(entry["distance_m"]),
                            value=None if raw is None else float(raw),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise UpstreamUnavailableError(
                        "Raster service returned a malformed sample entry"
                    ) from exc
            return tuple(result)

        return call_with_retries(call, retries=self._retries, what="MS3 sample")

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 400:
            raise DomainValidationError(_response_detail(response))
        if response.status_code == 404:
            raise NoCoverageError(_response_detail(response))
        if response.status_code != 200:
            raise UpstreamUnavailableError(
                f"Raster service returned HTTP {response.status_code}: {_response_detail(response)}"
            )


def _response_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict) and body.get("detail") is not None:
        return f"raster service: {body['detail']}"
    return f"HTTP {response.status_code}"
