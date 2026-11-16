# Location Service - Mars gazetteer/POI resolution (offline, read-only SQLite catalog)
# Build from the repo root: docker build -f location-service/Dockerfile -t location-service .
# The seed catalog is built from data/gale during the image build, so no host mounts are needed.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY location-service/pyproject.toml ./
COPY location-service/src ./src
COPY location-service/config ./config
COPY data/gale/processed/gale_puntos_quimica.xlsx /tmp/gale_puntos_quimica.xlsx
RUN pip install --no-cache-dir . \
    && python -m location_service.ingest build \
        --mission /tmp/gale_puntos_quimica.xlsx --config /app/config \
        --out /app/data/seed/location_catalog_seed.sqlite \
        --report /app/data/seed/ingest_report.json \
    && rm /tmp/gale_puntos_quimica.xlsx \
    && useradd --create-home --uid 10001 location

USER location
EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:8001/ready',timeout=4).status==200 else 1)"

CMD ["uvicorn", "location_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
