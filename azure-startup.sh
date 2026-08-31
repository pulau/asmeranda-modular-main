#!/usr/bin/env bash
# Asmeranda AI - Azure Container App startup script.
#
# Menjalankan 2 proses dalam 1 container:
#   - Backend FastAPI (uvicorn) di port 8000
#   - Frontend Next.js  (npx next start) di port 3000
#
# Disimpan di /app/azure/startup.sh (di-copy oleh Dockerfile.azure
# ke /app/startup.sh) dan dijalankan sebagai ENTRYPOINT alternatif
# atau via supervisord (lihat azure/supervisord.conf).
#
# Environment variables yang dipakai (lihat azure.env):
#   - ASMERANDA_HOST          (default 0.0.0.0)
#   - ASMERANDA_PORT          (default 8000)
#   - ASMERANDA_DATA_DIR      (default /app/data)
#   - ASMERANDA_LOG_LEVEL     (default INFO)
#   - NEXT_PUBLIC_API_BASE_PATH (default /api/v1)
#   - PORT                    (default 3000)
set -euo pipefail

LOG_DIR="${LOG_DIR:-/app/logs}"
DATA_DIR="${ASMERANDA_DATA_DIR:-/app/data}"
ASMERANDA_HOST="${ASMERANDA_HOST:-0.0.0.0}"
ASMERANDA_PORT="${ASMERANDA_PORT:-8000}"
ASMERANDA_LOG_LEVEL="${ASMERANDA_LOG_LEVEL:-INFO}"
PORT="${PORT:-3000}"

mkdir -p "$LOG_DIR" "$DATA_DIR"

echo "[startup] $(date) - Asmeranda AI starting (data=$DATA_DIR log=$LOG_DIR)"

# Trap SIGTERM untuk shutdown bersih
cleanup() {
    echo "[startup] Caught signal, shutting down..."
    if [ -n "${BACKEND_PID:-}" ]; then kill -TERM "$BACKEND_PID" 2>/dev/null || true; fi
    if [ -n "${FRONTEND_PID:-}" ]; then kill -TERM "$FRONTEND_PID" 2>/dev/null || true; fi
    wait 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# ---------------------------------------------------------------------------
# Backend (FastAPI) - background
# ---------------------------------------------------------------------------
echo "[startup] Starting backend on ${ASMERANDA_HOST}:${ASMERANDA_PORT}"
cd /app
PYTHONPATH=/app \
    ASMERANDA_HOST="$ASMERANDA_HOST" \
    ASMERANDA_PORT="$ASMERANDA_PORT" \
    ASMERANDA_DATA_DIR="$DATA_DIR" \
    ASMERANDA_LOG_LEVEL="$ASMERANDA_LOG_LEVEL" \
    PYTHONUNBUFFERED=1 \
    uvicorn backend.main:app \
        --host "$ASMERANDA_HOST" \
        --port "$ASMERANDA_PORT" \
        --workers 1 \
        >> "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "[startup] backend pid=$BACKEND_PID"

# Tunggu backend ready (max 60s)
for i in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${ASMERANDA_PORT}/health" >/dev/null 2>&1; then
        echo "[startup] backend ready after ${i}s"
        break
    fi
    sleep 1
done

# ---------------------------------------------------------------------------
# Frontend (Next.js) - background
# ---------------------------------------------------------------------------
echo "[startup] Starting frontend on 0.0.0.0:${PORT}"
cd /app/frontend
NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT="$PORT" \
    NEXT_PUBLIC_API_BASE_PATH="${NEXT_PUBLIC_API_BASE_PATH:-/api/v1}" \
    npx next start -p "$PORT" -H 0.0.0.0 \
        >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "[startup] frontend pid=$FRONTEND_PID"

# Tunggu frontend ready (max 60s)
for i in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
        echo "[startup] frontend ready after ${i}s"
        break
    fi
    sleep 1
done

echo "[startup] All services up. backend=$BACKEND_PID frontend=$FRONTEND_PID"
# Tunggu keduanya
wait $BACKEND_PID $FRONTEND_PID
