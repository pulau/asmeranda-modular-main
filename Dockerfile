# Dockerfile backend produksi. Dipertahankan untuk kompatibilitas build lama.
FROM python:3.11-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    ASMERANDA_HOST=0.0.0.0 \
    ASMERANDA_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-backend.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --retries 10 --timeout 120 \
        --index-url https://pypi.org/simple \
        -r /tmp/requirements.txt

COPY . /app
RUN mkdir -p /app/data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
