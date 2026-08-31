# Asmeranda Frontend

Next.js 14 (App Router, JavaScript) frontend untuk Asmeranda AI backend.

## Quick start (development)

```bash
cd frontend
npm install
npm run dev
# buka http://localhost:3000
```

Pastikan backend FastAPI sudah berjalan di `http://localhost:8000`.

## Build production

```bash
npm run build
npm start
```

## Konfigurasi

- `NEXT_PUBLIC_API_BASE` - URL backend FastAPI (default `http://localhost:8000`).
  Di dev, ``next.config.js`` sudah me-rewrite ``/api/*`` ke backend sehingga
  tidak ada masalah CORS.
