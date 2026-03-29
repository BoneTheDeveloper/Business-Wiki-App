"""WebSocket connection manager for real-time updates."""
from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self):
        # user_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Send message to all connections for a specific user."""
        async with self._lock:
            connections = self.active_connections.get(user_id, set()).copy()

        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        for dead in dead_connections:
            await self.disconnect(dead, user_id)

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    async def send_document_status(
        self,
        user_id: str,
        document_id: str,
        status: str,
        metadata: dict = None
    ) -> None:
        """Send document processing status update."""
        await self.send_to_user(user_id, {
            "type": "document_status",
            "document_id": document_id,
            "status": status,
            "metadata": metadata or {}
        })


# Singleton instance
ws_manager = ConnectionManager()
