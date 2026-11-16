# Location Service - Mars gazetteer/POI resolution (offline, read-only SQLite catalog)
# The versioned seed catalog (data/seed) and config are baked in; mount them to override.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY data/seed ./data/seed
# Runtime dependencies only (no ingest extras: pandas/openpyxl stay offline-build tools)
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 location

USER location
EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:8001/ready',timeout=4).status==200 else 1)"

CMD ["uvicorn", "location_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
