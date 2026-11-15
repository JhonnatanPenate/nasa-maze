FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MS3_REJILLA_PATH=/data/gale/processed/rejilla_ruta_90m.tif

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
# libexpat1: required by the GDAL bundled in the rasterio wheel, missing from slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir . \
    && useradd --create-home ms3

USER ms3
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import json,sys,urllib.request; sys.exit(0 if json.load(urllib.request.urlopen('http://localhost:8003/health'))['status']=='ok' else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
