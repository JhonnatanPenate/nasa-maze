# Build desde la raíz del repo: docker build -f routing-engine/Dockerfile -t ms6 .
# Run: docker run -p 8006:8006 -v "$PWD/data/gale:/data/gale:ro" ms6
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MS6_DATA_DIR=/data/gale \
    MS6_SCIENCE_DIR=/app/science

WORKDIR /app
COPY routing-engine/pyproject.toml ./
COPY routing-engine/app ./app
COPY science ./science
# libexpat1: required by the GDAL bundled in the rasterio wheel, missing from slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir . \
    && useradd --create-home ms6

USER ms6
EXPOSE 8006
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
