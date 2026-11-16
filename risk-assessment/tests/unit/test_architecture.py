"""Architecture guard (mirrors raster-service/tests/unit/test_architecture.py).

Inner layers must stay framework- and IO-free:

- ``core/domain``, ``core/ports``, ``features/*/application``,
  ``features/*/domain``: no fastapi/pydantic/httpx/sqlite3/openpyxl/pandas/yaml.
- No module outside ``app/ingest`` may import ``pandas``/``openpyxl``
  (workbook parsing is an offline-ingest concern only).
- No module may import ``rasterio`` — MS5 never reads GeoTIFFs directly;
  MS3 is the raster boundary.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

STRICT_DIRS = (
    "core/domain",
    "core/ports",
    "features",
)
STRICT_EXCLUDE = ("presentation",)
FORBIDDEN_IMPORTS = {
    "fastapi",
    "pydantic",
    "pydantic_settings",
    "httpx",
    "sqlite3",
    "openpyxl",
    "pandas",
    "yaml",
    "rasterio",
}
WORKBOOK_IMPORTS = {"pandas", "openpyxl"}


def _iter_py_files() -> list[Path]:
    return sorted(APP_ROOT.rglob("*.py"))


def _module_name_of(path: Path) -> str:
    return ".".join(path.relative_to(APP_ROOT.parent).with_suffix("").parts)


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _is_strict_module(rel_parts: tuple[str, ...]) -> bool:
    if not rel_parts:
        return False
    if (
        rel_parts[0] == "core"
        and len(rel_parts) > 1
        and rel_parts[1]
        in {
            "domain",
            "ports",
        }
    ):
        return True
    if rel_parts[0] == "features":
        return not any(part in STRICT_EXCLUDE for part in rel_parts)
    return False


def test_strict_layers_have_no_forbidden_imports() -> None:
    violations: list[str] = []
    for path in _iter_py_files():
        rel = path.relative_to(APP_ROOT).parts[:-1]
        if not _is_strict_module(rel):
            continue
        bad = _imported_roots(path) & FORBIDDEN_IMPORTS
        if bad:
            violations.append(f"{_module_name_of(path)}: {sorted(bad)}")
    assert not violations, "Forbidden imports in inner layers:\n" + "\n".join(violations)


def test_no_rasterio_anywhere() -> None:
    violations = [
        _module_name_of(path) for path in _iter_py_files() if "rasterio" in _imported_roots(path)
    ]
    assert not violations, f"rasterio imports found: {violations}"


def test_workbook_libs_only_in_ingest() -> None:
    violations: list[str] = []
    for path in _iter_py_files():
        rel = path.relative_to(APP_ROOT).parts
        if rel[0] == "ingest":
            continue
        bad = _imported_roots(path) & WORKBOOK_IMPORTS
        if bad:
            violations.append(f"{_module_name_of(path)}: {sorted(bad)}")
    assert not violations, "pandas/openpyxl may only be imported under app/ingest:\n" + "\n".join(
        violations
    )
