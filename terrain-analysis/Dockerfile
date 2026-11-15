FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MS4_DATASOURCE_KIND=rejilla \
    MS4_REJILLA_PATH=/data/gale/processed/rejilla_ruta_90m.tif

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
# libexpat1: required by the GDAL bundled in the rasterio wheel, missing from slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir . \
    && useradd --create-home ms4

USER ms4
EXPOSE 8004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
