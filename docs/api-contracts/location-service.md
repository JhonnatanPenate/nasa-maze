# Location Service API — usage examples

Contract: `packages/contracts/location-service/openapi.yaml`.
Base URL: `http://localhost:8001`. All coordinate-bearing payloads carry
`coordinate_system` (`body=mars`, `crs=IAU_2015:49900`,
`lat_type=planetocentric`, `lon_convention=east_positive_0_360`,
`radius_m=3396190`).

## 1. Search by name (UI autocomplete)

```bash
curl -s 'http://localhost:8001/v1/places/search?q=Glen%20Etive&limit=5' | jq
```

Returns `mars:msl:glen-etive` first (`match_type: exact_name`,
`center.lat -4.7303`, `center.lon 137.3835`). Empty result list (HTTP 200)
when nothing matches.

## 2. Resolve a route (Core service main flow)

```bash
curl -s -X POST http://localhost:8001/v1/resolve \
  -H 'Content-Type: application/json' \
  -d '{
    "origin": {"query": "Bradbury Landing"},
    "destination": {"place_id": "mars:msl:glen-etive"}
  }' | jq
```

`status: resolved`, `straight_line_distance_m ≈ 9026`,
`shared_regions: ["aoi:gale-90m"]`. Ambiguous endpoints return
`status: ambiguous` with `alternatives` and `point: null` — the service
never picks silently.

## 3. Reverse geocoding (click on map)

```bash
curl -s 'http://localhost:8001/v1/places/reverse?lat=-4.668&lon=137.3703&radius_m=5000' | jq
```

`nearest[0]` is Buckskin at ≈ 0 m; coincident POIs (John Klein/Cumberland,
Big Sky/Greenhorn) are all returned.

## 4. Health / readiness

```bash
curl -s http://localhost:8001/health   # liveness, always 200 when up
curl -s http://localhost:8001/ready    # 200 only after catalog load
```

Errors are RFC 7807 `application/problem+json` with a `code`
(`INVALID_PARAMETER`, `OUT_OF_RANGE`, `UNSUPPORTED_BODY`, `NOT_FOUND`,
`CATALOG_UNAVAILABLE`, ...) and the `X-Request-ID` header echoed back.
