"""Contract tests (plan §10, SPEC §7.4).

- the authored openapi.yaml validates as OpenAPI
- the FastAPI app exposes every path/method from the contract
- representative responses conform to the contract schemas
"""

from pathlib import Path
from urllib.parse import parse_qsl

import pytest
import yaml
from app.main import create_app
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_spec

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = REPO_ROOT / "packages" / "contracts" / "risk-assessment" / "openapi.yaml"


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def app_openapi() -> dict:
    return create_app().openapi()


def test_authored_spec_is_valid_openapi(spec: dict) -> None:
    validate_spec(spec)  # raises on invalid


def test_app_covers_contract_paths(spec: dict, app_openapi: dict) -> None:
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


def _resolve_refs(node, spec):  # type: ignore[no-untyped-def]
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


def _response_schema(spec, path: str, method: str, status: str):  # type: ignore[no-untyped-def]
    op = spec["paths"][path][method]
    resp = op["responses"][status]
    content = resp.get("content", {}).get("application/json")
    if content is None:
        return None
    return _resolve_refs(content["schema"], spec)


@pytest.mark.parametrize(
    "request_path,spec_path",
    [
        ("/health", "/health"),
        (
            "/risk/point?lat=-4.62&lon=137.40&sol=1360&hora=9",
            "/risk/point",
        ),
        ("/risk/factors", "/risk/factors"),
        ("/risk/vehicle-profiles", "/risk/vehicle-profiles"),
        ("/risk/meta", "/risk/meta"),
    ],
)
def test_get_responses_match_contract(client, spec, request_path, spec_path) -> None:  # type: ignore[no-untyped-def]
    url = request_path.split("?")[0]
    query = request_path.split("?")[1] if "?" in request_path else ""
    r = client.get(url, params=parse_qsl(query) if query else None)
    assert r.status_code == 200, r.text
    schema = _response_schema(spec, spec_path, "get", "200")
    assert schema is not None
    Draft202012Validator(schema).validate(r.json())


def test_evaluate_response_matches_contract(client, spec) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/risk/evaluate",
        json={
            "body": "mars",
            "path": [
                {"lat": -4.60, "lon": 137.44},
                {"lat": -4.65, "lon": 137.42},
            ],
            "factors": ["slope", "roughness", "dunes", "temperature", "radiation"],
            "sol": 1360,
            "hora": 9,
        },
    )
    assert r.status_code == 200, r.text
    schema = _response_schema(spec, "/risk/evaluate", "post", "200")
    assert schema is not None
    Draft202012Validator(schema).validate(r.json())


def test_area_response_matches_contract(client, spec) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/risk/area",
        json={"bbox": [137.345, -4.740, 137.455, -4.580], "hora": 12},
    )
    assert r.status_code == 200, r.text
    schema = _response_schema(spec, "/risk/area", "post", "200")
    assert schema is not None
    Draft202012Validator(schema).validate(r.json())


def test_error_response_matches_contract(client, spec) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/risk/point", params={"lat": 0.0, "lon": 0.0})
    assert r.status_code == 404
    schema = _resolve_refs(spec["components"]["schemas"]["Error"], spec)
    Draft202012Validator(schema).validate(r.json())
