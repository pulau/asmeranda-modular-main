"""
Asmeranda Backend (FastAPI) package.

Modul ini membungkus modul-modul ML yang sudah di-refactor (core/*,
utils.py, advanced_ml.py, dll) menjadi REST/WebSocket API untuk
frontend Next.js baru.

Sub-package:
- ``api``     - routers (FastAPI endpoints)
- ``core``    - konfigurasi, security, dependency
- ``services`` - business logic (no HTTP)
- ``schemas``  - Pydantic models
"""
__version__ = "0.1.0"
