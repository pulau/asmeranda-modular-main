"""
Endpoint /ws - WebSocket untuk broadcasting status progress.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("asmeranda.api.ws")
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Menyimpan active connections: dataset_id -> set of WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, dataset_id: str):
        await websocket.accept()
        if dataset_id not in self.active_connections:
            self.active_connections[dataset_id] = set()
        self.active_connections[dataset_id].add(websocket)
        logger.info(f"WebSocket connected for dataset {dataset_id}")

    def disconnect(self, websocket: WebSocket, dataset_id: str):
        if dataset_id in self.active_connections:
            self.active_connections[dataset_id].discard(websocket)
            if not self.active_connections[dataset_id]:
                del self.active_connections[dataset_id]
        logger.info(f"WebSocket disconnected for dataset {dataset_id}")

    async def broadcast(self, dataset_id: str, message: dict):
        if dataset_id in self.active_connections:
            websockets = list(self.active_connections[dataset_id])
            for connection in websockets:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as exc:
                    logger.error(f"Error sending message to websocket: {exc}")
                    self.disconnect(connection, dataset_id)

manager = ConnectionManager()

@router.websocket("/{dataset_id}")
async def websocket_endpoint(websocket: WebSocket, dataset_id: str):
    await manager.connect(websocket, dataset_id)
    try:
        while True:
            # Tetap terbuka dan mendengarkan ping/pesan dari client (jika ada)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, dataset_id)
    except Exception as exc:
        logger.error(f"WebSocket error for {dataset_id}: {exc}")
        manager.disconnect(websocket, dataset_id)
