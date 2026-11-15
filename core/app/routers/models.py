from fastapi import APIRouter, Depends

from app.datasources.soil_models import load_soil_models
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api", tags=["modelos"])


@router.get("/modelos")
def modelos(settings: Settings = Depends(get_settings)):
    return load_soil_models(settings.processed)
