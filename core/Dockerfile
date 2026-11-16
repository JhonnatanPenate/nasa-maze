FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CORE_DATA_DIR=/data/gale

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
# libexpat1: required by the GDAL bundled in the rasterio wheel, missing from slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir . \
    && useradd --create-home core

USER core
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
