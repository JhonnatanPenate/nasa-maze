# Risk Assessment Service - MS5 (offline; upstreams MS3 :8003 and MS4 :8004)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RISK_DATASOURCE_MODE=synthetic

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY config ./config
# Runtime dependencies only (no ingest extras: pandas/openpyxl stay offline-build tools)
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10005 risk

USER risk
EXPOSE 8005

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://localhost:8005/health',timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
