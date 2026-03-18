"""
Redis pub/sub broadcaster — bridges Django signals / Celery tasks
with the FastAPI WebSocket real-time layer.

- Publishes events from FastAPI to Redis channels
- Subscribes to Redis channels and forwards messages to WebSocket connections
"""
import asyncio
import json
import logging

import redis.asyncio as aioredis

from services.config import get_settings
from services.realtime.events import REDIS_CHANNELS, Channel

logger = logging.getLogger(__name__)


class RedisBroadcaster:
    """Manages Redis pub/sub for cross-service real-time events."""

    def __init__(self, ws_manager):
        self.settings = get_settings()
        self.ws_manager = ws_manager
        self.redis = None
        self.pubsub = None
        self._listener_task = None

    async def connect(self):
        """Connect to Redis."""
        self.redis = aioredis.from_url(
            self.settings.REDIS_URL, decode_responses=True
        )
        logger.info("Redis broadcaster connected")

    async def disconnect(self):
        """Clean shutdown."""
        if self._listener_task:
            self._listener_task.cancel()
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        logger.info("Redis broadcaster disconnected")

    # ── Publishing ────────────────────────────────────────────────

    async def publish_event(self, channel: str, data: dict):
        """Publish an event to a Redis channel."""
        if not self.redis:
            return
        redis_channel = REDIS_CHANNELS.get(channel, f"jhbridge:{channel}")
        await self.redis.publish(redis_channel, json.dumps(data))

    async def broadcast_event(self, channel: str, data: dict):
        """Publish to Redis AND broadcast to local WebSocket connections."""
        await self.publish_event(channel, data)
        if self.ws_manager:
            await self.ws_manager.broadcast(channel, data)

    # ── Subscribing ───────────────────────────────────────────────

    async def start_listener(self):
        """Subscribe to all Redis channels and forward to WebSocket."""
        if not self.redis:
            return

        self.pubsub = self.redis.pubsub()
        redis_to_ws = {v: k for k, v in REDIS_CHANNELS.items()}

        await self.pubsub.subscribe(*REDIS_CHANNELS.values())
        logger.info(f"Redis listener subscribed to: {list(REDIS_CHANNELS.values())}")

        self._listener_task = asyncio.current_task()

        try:
            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue

                redis_channel = message["channel"]
                ws_channel = redis_to_ws.get(redis_channel)
                if not ws_channel:
                    continue

                try:
                    data = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                # Forward to all WebSocket clients on this channel
                if self.ws_manager:
                    await self.ws_manager.broadcast(ws_channel, data)

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def run_listener_loop(self):
        """Wrapper that restarts the listener on failure."""
        while True:
            try:
                await self.start_listener()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis listener crashed, restarting in 5s: {e}")
                await asyncio.sleep(5)
