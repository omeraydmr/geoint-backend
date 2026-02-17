"""
WebSocket connection manager for real-time updates.

Manages WebSocket connections per user and broadcasts events.
"""

import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        # user_id -> Set[WebSocket connections]
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Connect a new WebSocket for a user.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user: {user_id} (total: {len(self.active_connections[user_id])})")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Disconnect a WebSocket from a user.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Remove user entry if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

            logger.info(f"WebSocket disconnected for user: {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send message to all connections of a specific user.

        Args:
            message: Message dictionary to send
            user_id: Target user identifier
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user: {user_id}")
            return

        # Send to all user's connections
        disconnected = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected.append(connection)

        # Clean up disconnected sockets
        for conn in disconnected:
            await self.disconnect(conn, user_id)

    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected users.

        Args:
            message: Message dictionary to send
        """
        for user_id, connections in self.active_connections.items():
            await self.send_personal_message(message, user_id)

    def get_connection_count(self, user_id: str = None) -> int:
        """
        Get number of active connections.

        Args:
            user_id: Optional user ID to get count for specific user

        Returns:
            Number of active connections
        """
        if user_id:
            return len(self.active_connections.get(user_id, set()))

        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()
