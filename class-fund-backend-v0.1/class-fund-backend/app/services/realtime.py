"""Real-time communication service using Redis Pub/Sub and WebSockets."""
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from redis.asyncio import Redis, ConnectionPool
from app.core.config import get_settings


class ConnectionManager:
    """Manages WebSocket connections and Redis Pub/Sub for real-time updates."""
    
    def __init__(self):
        self.redis_pool: ConnectionPool | None = None
        self.redis: Redis | None = None
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection pool."""
        if self._initialized:
            return
        
        settings = get_settings()
        redis_url = settings.redis_url or "redis://redis:6379"
        
        self.redis_pool = ConnectionPool.from_url(redis_url, decode_responses=True)
        self.redis = Redis(connection_pool=self.redis_pool)
        self._initialized = True
    
    async def connect(self, websocket: WebSocket, channel: str):
        """Accept WebSocket connection and subscribe to Redis channel."""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        
        # Subscribe to Redis channel if first local connection
        if len(self.active_connections[channel]) == 1:
            await self._subscribe_redis(channel)
    
    async def disconnect(self, websocket: WebSocket, channel: str):
        """Remove WebSocket connection and unsubscribe if no more local connections."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                await self._unsubscribe_redis(channel)
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to local connections AND publish to Redis."""
        # Local broadcast
        if channel in self.active_connections:
            dead = set()
            for ws in self.active_connections[channel]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self.active_connections[channel].discard(ws)
        
        # Publish to Redis for other instances
        if self.redis:
            await self.redis.publish(channel, json.dumps(message))
    
    async def _subscribe_redis(self, channel: str):
        """Subscribe to Redis channel and start listener."""
        if not self.redis:
            return
        
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        async def listener():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._broadcast_local(channel, data)
                    except Exception:
                        pass
        
        task = asyncio.create_task(listener())
        self._pubsub_tasks[channel] = task
    
    async def _unsubscribe_redis(self, channel: str):
        """Unsubscribe from Redis channel."""
        if channel in self._pubsub_tasks:
            self._pubsub_tasks[channel].cancel()
            try:
                await self._pubsub_tasks[channel]
            except asyncio.CancelledError:
                pass
            del self._pubsub_tasks[channel]
    
    async def _broadcast_local(self, channel: str, message: dict):
        """Broadcast message to local connections only."""
        if channel in self.active_connections:
            dead = set()
            for ws in self.active_connections[channel]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self.active_connections[channel].discard(ws)
    
    async def close(self):
        """Close all connections and Redis pool."""
        for task in self._pubsub_tasks.values():
            task.cancel()
        for task in self._pubsub_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self.redis:
            await self.redis.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()


# Global instance
manager = ConnectionManager()


# Convenience functions for publishing events
async def publish_message_update(conversation_id: str, message_data: dict):
    """Publish message update to conversation channel."""
    await manager.broadcast(f"messages:{conversation_id}", {
        "type": "message_update",
        "data": message_data
    })


async def publish_worker_status(worker_data: dict):
    """Publish worker status update."""
    await manager.broadcast("worker_status", {
        "type": "worker_update",
        "data": worker_data
    })


async def publish_system_alert(alert_data: dict):
    """Publish system-wide alert."""
    await manager.broadcast("system", {
        "type": "system_alert",
        "data": alert_data
    })