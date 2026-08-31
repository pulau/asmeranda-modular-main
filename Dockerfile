FROM python:3.11-slim

LABEL maintainer="ASMERA NDA Team"
LABEL description="Asmeranda AI - Modular Machine Learning Backend"
LABEL version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies untuk kompilasi native packages
# (LightGBM, XGBoost, CatBoost, Prophet, UMAP, HDBSCAN, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libgomp1 \
        libffi-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements-backend.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Create necessary directories
RUN mkdir -p /app/data /app/models /app/uploads /app/logs

EXPOSE 8000

ENV ASMERANDA_HOST=0.0.0.0 \
    ASMERANDA_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

