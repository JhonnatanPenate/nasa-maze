import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

_FORBIDDEN_INNER = {"fastapi", "pydantic", "rasterio", "httpx"}

_STRICT_DIRS = [
    APP_ROOT / "core" / "domain",
    APP_ROOT / "core" / "ports",
    *sorted((APP_ROOT / "features").glob("*/application")),
    *sorted((APP_ROOT / "features").glob("*/domain")),
]


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(
                alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _offenders(directory: Path, forbidden: set[str]) -> dict[str, set[str]]:
    return {
        file.name: _imported_top_level_modules(file) & forbidden
        for file in sorted(directory.rglob("*.py"))
        if _imported_top_level_modules(file) & forbidden
    }


class TestInnerLayersStayPure:
    def test_domain_ports_and_inner_feature_dirs_import_no_web_or_drivers(
        self,
    ):
        offenders = {
            str(directory.relative_to(APP_ROOT)): _offenders(
                directory, _FORBIDDEN_INNER
            )
            for directory in _STRICT_DIRS
            if _offenders(directory, _FORBIDDEN_INNER)
        }

        assert not offenders


class TestRasterioStaysInInfrastructure:
    def test_no_rasterio_imports_outside_app_infrastructure(self):
        infrastructure = APP_ROOT / "infrastructure"
        offenders = [
            file.relative_to(APP_ROOT)
            for file in sorted(APP_ROOT.rglob("*.py"))
            if infrastructure not in file.parents
            and "rasterio" in _imported_top_level_modules(file)
        ]

        assert not offenders
