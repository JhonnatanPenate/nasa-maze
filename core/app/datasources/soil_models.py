import json
from pathlib import Path

from app.settings import DataUnavailableError


def load_soil_models(processed: Path) -> dict:
    try:
        return json.loads((processed / "modelos_por_suelo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise DataUnavailableError(f"modelos_por_suelo.json ilegible: {e}") from e
