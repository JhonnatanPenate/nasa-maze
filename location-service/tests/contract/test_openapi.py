"""Contract tests (case 24 + T0.2/T0.3 acceptance).

- the authored openapi.yaml validates as OpenAPI
- the FastAPI app exposes every path/method from the contract
- representative responses conform to the contract schemas
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_spec

from location_service.main import create_app
from location_service.settings import Settings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SPEC_PATH = REPO_ROOT / "packages/contracts/location-service/openapi.yaml"
CONFIG_DIR = REPO_ROOT / "location-service/config"


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text())


@pytest.fixture(scope="module")
def app_openapi(catalog_path) -> dict:
    settings = Settings(catalog_path=catalog_path, config_dir=CONFIG_DIR)
    return create_app(settings).openapi()


def test_authored_spec_is_valid_openapi(spec):
    validate_spec(spec)  # raises on invalid


def test_app_covers_contract_paths(spec, app_openapi):
    contract_paths = {
        (path, method.upper())
        for path, item in spec["paths"].items()
        for method in item
        if method in {"get", "post", "put", "delete", "patch"}
    }
    app_paths = {
        (path, method.upper())
        for path, item in app_openapi["paths"].items()
        for method in item
        if method in {"get", "post", "put", "delete", "patch"}
    }
    missing = contract_paths - app_paths
    assert not missing, f"contract paths missing from app: {missing}"


def test_place_schema_matches_contract(spec, app_openapi):
    contract_place = spec["components"]["schemas"]["Place"]["required"]
    app_place = app_openapi["components"]["schemas"]["PlaceOut"]["required"]
    assert set(contract_place) == set(app_place)


def _resolve_refs(node, spec):
    """Minimal $ref resolver for local '#/components/...' references."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("#/"):
            target = node["$ref"][2:].split("/")
            cur = spec
            for part in target:
                cur = cur[part]
            return _resolve_refs(cur, spec)
        return {k: _resolve_refs(v, spec) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(v, spec) for v in node]
    return node


def _response_schema(spec, path, method, status):
    op = spec["paths"][path][method]
    resp = op["responses"][status]
    content = resp.get("content", {}).get("application/json")
    if content is None:
        return None
    return _resolve_refs(content["schema"], spec)


@pytest.mark.parametrize(
    "path,spec_path",
    [
        ("/v1/places/search?q=Glen%20Etive", "/v1/places/search"),
        ("/v1/places/reverse?lat=-4.668&lon=137.3703", "/v1/places/reverse"),
        ("/v1/places/mars:msl:glen-etive", "/v1/places/{place_id}"),
        ("/v1/places?limit=5", "/v1/places"),
        ("/v1/regions", "/v1/regions"),
        ("/v1/meta/catalog", "/v1/meta/catalog"),
        ("/v1/meta/feature-types", "/v1/meta/feature-types"),
    ],
)
def test_get_responses_match_contract(client, spec, path, spec_path):
    url = path.split("?")[0]
    query = path.split("?")[1] if "?" in path else ""
    from urllib.parse import parse_qsl

    r = client.get(url, params=parse_qsl(query) if query else None)
    assert r.status_code == 200, r.text
    schema = _response_schema(spec, spec_path, "get", "200")
    assert schema is not None
    Draft202012Validator(schema).validate(r.json())


def test_resolve_response_matches_contract(client, spec):
    r = client.post(
        "/v1/resolve",
        json={
            "origin": {"query": "Bradbury Landing"},
            "destination": {"place_id": "mars:msl:glen-etive"},
        },
    )
    assert r.status_code == 200, r.text
    schema = _response_schema(spec, "/v1/resolve", "post", "200")
    Draft202012Validator(schema).validate(r.json())


def test_problem_response_matches_contract(client, spec):
    r = client.get("/v1/places/reverse", params={"lat": 95, "lon": 0})
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    # find the 422 problem schema via components
    schema = _resolve_refs(spec["components"]["schemas"]["Problem"], spec)
    Draft202012Validator(schema).validate(r.json())
