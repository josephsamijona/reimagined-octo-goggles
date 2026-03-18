"""
WebSocket connection manager — tracks active connections by channel and user.
"""
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by channel."""

    def __init__(self):
        # {channel: {user_id: WebSocket}}
        self.connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str, user_id: str):
        """Accept a WebSocket connection and register it to a channel."""
        await websocket.accept()
        if channel not in self.connections:
            self.connections[channel] = {}
        self.connections[channel][user_id] = websocket
        logger.info(f"WS connected: user={user_id} channel={channel}")

    def disconnect(self, channel: str, user_id: str):
        """Remove a WebSocket connection."""
        if channel in self.connections:
            self.connections[channel].pop(user_id, None)
            if not self.connections[channel]:
                del self.connections[channel]
        logger.info(f"WS disconnected: user={user_id} channel={channel}")

    async def send_personal(self, channel: str, user_id: str, data: dict):
        """Send a message to a specific user on a channel."""
        ws = self.connections.get(channel, {}).get(user_id)
        if ws:
            try:
                await ws.send_json({
                    **data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.warning(f"WS send_personal failed: {e}")
                self.disconnect(channel, user_id)

    async def broadcast(self, channel: str, data: dict):
        """Broadcast a message to all connections on a channel."""
        connections = self.connections.get(channel, {})
        payload = {
            **data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        disconnected = []
        for user_id, ws in connections.items():
            try:
                await ws.send_json(payload)
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.disconnect(channel, uid)

    def get_channel_users(self, channel: str) -> list[str]:
        """Return list of user IDs connected to a channel."""
        return list(self.connections.get(channel, {}).keys())

    def get_connection_count(self) -> dict[str, int]:
        """Return connection counts per channel."""
        return {ch: len(users) for ch, users in self.connections.items()}
