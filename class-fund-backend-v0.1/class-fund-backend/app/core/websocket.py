"""
WebSocket + Redis Pub/Sub Real-time Communication Layer
"""

import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from redis.asyncio import Redis, ConnectionPool
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User, Role

logger = logging.getLogger(__name__)


@dataclass
class RealtimeEvent:
    """Standard realtime event format."""
    event_type: str
    payload: dict
    timestamp: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ConnectionManager:
    """
    Manages WebSocket connections and Redis Pub/Sub for real-time updates.
    Supports multiple channels: chat, transactions, admin, system.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or "redis://redis:6379/0"
        self._redis_pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}
        
        # Local connections: {channel: {user_id: Set[WebSocket]}}
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        
        # User subscriptions: {user_id: Set[channel]}
        self.user_subscriptions: Dict[str, Set[str]] = {}
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection pool."""
        if self._initialized:
            return
        
        self._redis_pool = ConnectionPool.from_url(
            self.redis_url, 
            decode_responses=True,
            max_connections=50
        )
        self._redis = Redis(connection_pool=self._redis_pool)
        self._initialized = True
        logger.info("WebSocket ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, channel: str, user_id: str):
        """Accept WebSocket connection and register user to channel."""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = {}
        if user_id not in self.active_connections[channel]:
            self.active_connections[channel][user_id] = set()
        self.active_connections[channel][user_id].add(websocket)
        
        # Track user subscriptions
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(channel)
        
        # Subscribe to Redis channel if first local connection
        if len(self.active_connections[channel]) == 1:
            await self._subscribe_redis(channel)
        
        logger.info(f"User {user_id} connected to channel {channel}")
    
    async def disconnect(self, websocket: WebSocket, channel: str, user_id: str):
        """Remove WebSocket connection and unsubscribe if no more local connections."""
        if channel in self.active_connections and user_id in self.active_connections[channel]:
            self.active_connections[channel][user_id].discard(websocket)
            
            if not self.active_connections[channel][user_id]:
                del self.active_connections[channel][user_id]
            
            if not self.active_connections[channel]:
                await self._unsubscribe_redis(channel)
        
        # Remove user subscription
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(channel)
            if not self.user_subscriptions[user_id]:
                del self.user_subscriptions[user_id]
        
        logger.info(f"User {user_id} disconnected from channel {channel}")
    
    async def broadcast(self, channel: str, event: RealtimeEvent, 
                       exclude_user: Optional[str] = None,
                       role_filter: Optional[str] = None):
        """Broadcast event to local connections AND publish to Redis."""
        # Local broadcast with role filtering
        if channel in self.active_connections:
            dead_connections = []
            for user_id, connections in self.active_connections[channel].items():
                if exclude_user and user_id == exclude_user:
                    continue
                if role_filter and not self._user_has_role(user_id, role_filter):
                    continue
                
                dead = set()
                for ws in connections:
                    try:
                        await ws.send_json({
                            "type": event.event_type,
                            "payload": event.payload,
                            "timestamp": event.timestamp
                        })
                    except Exception:
                        dead.add(ws)
                
                for ws in dead:
                    connections.discard(ws)
                    dead_connections.append((user_id, ws))
            
            # Clean up dead connections
            for user_id, ws in dead_connections:
                if channel in self.active_connections and user_id in self.active_connections[channel]:
                    self.active_connections[channel][user_id].discard(ws)
                    if not self.active_connections[channel][user_id]:
                        del self.active_connections[channel][user_id]
        
        # Publish to Redis for other instances
        if self._redis:
            await self._redis.publish(channel, json.dumps({
                "type": event.event_type,
                "payload": event.payload,
                "timestamp": event.timestamp,
                "user_id": event.user_id,
                "conversation_id": event.conversation_id
            }))
    
    async def _subscribe_redis(self, channel: str):
        """Subscribe to Redis channel and start listener."""
        if not self._redis:
            return
        
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        
        async def listener():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        await self._broadcast_local(channel, data)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Redis listener error for channel {channel}: {e}")
        
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
    
    async def _broadcast_local(self, channel: str, data: dict):
        """Broadcast message from Redis to local connections."""
        if channel in self.active_connections:
            dead = set()
            for user_id, connections in self.active_connections[channel].items():
                for ws in connections:
                    try:
                        await ws.send_json(data)
                    except Exception:
                        dead.add((user_id, ws))
            
            for user_id, ws in dead:
                if channel in self.active_connections and user_id in self.active_connections[channel]:
                    self.active_connections[channel][user_id].discard(ws)
                    if not self.active_connections[channel][user_id]:
                        del self.active_connections[channel][user_id]
    
    def _user_has_role(self, user_id: str, required_role: str) -> bool:
        """Check if user has required role (simplified - in production use DB)."""
        # In production, this would check the database
        # For now, return True for admin channels
        return True
    
    async def send_personal(self, user_id: str, event: RealtimeEvent):
        """Send event to specific user across all their connections."""
        if user_id in self.user_subscriptions:
            for channel in self.user_subscriptions[user_id]:
                if channel in self.active_connections and user_id in self.active_connections[channel]:
                    dead = set()
                    for ws in self.active_connections[channel][user_id]:
                        try:
                            await ws.send_json({
                                "type": event.event_type,
                                "payload": event.payload,
                                "timestamp": event.timestamp
                            })
                        except Exception:
                            dead.add(ws)
                    
                    for ws in dead:
                        self.active_connections[channel][user_id].discard(ws)
    
    async def close(self):
        """Close all connections and Redis pool."""
        for task in self._pubsub_tasks.values():
            task.cancel()
        for task in self._pubsub_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        if self._redis:
            await self._redis.close()
        if self._redis_pool:
            await self._redis_pool.disconnect()
        
        logger.info("ConnectionManager closed")


# Global instance
manager = ConnectionManager()


# Convenience functions for publishing events
async def publish_chat_event(conversation_id: str, event_type: str, payload: dict, 
                            user_id: Optional[str] = None):
    """Publish chat-related event."""
    event = RealtimeEvent(
        event_type=event_type,
        payload=payload,
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=user_id,
        conversation_id=conversation_id
    )
    await manager.broadcast(f"chat:{conversation_id}", event)


async def publish_transaction_event(event_type: str, payload: dict, 
                                   user_id: Optional[str] = None):
    """Publish transaction-related event."""
    event = RealtimeEvent(
        event_type=event_type,
        payload=payload,
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=user_id
    )
    await manager.broadcast("transactions", event, role_filter="MEMBER")


async def publish_admin_event(event_type: str, payload: dict, 
                             user_id: Optional[str] = None):
    """Publish admin-only event."""
    event = RealtimeEvent(
        event_type=event_type,
        payload=payload,
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_id=user_id
    )
    await manager.broadcast("admin", event, role_filter="OWNER_TREASURER")


async def publish_system_alert(event_type: str, payload: dict):
    """Publish system-wide alert."""
    event = RealtimeEvent(
        event_type=event_type,
        payload=payload,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    await manager.broadcast("system", event)


# FastAPI WebSocket Dependencies
async def get_current_user_ws(token: str = Query(...), db: Session = Depends(get_db)) -> User:
    """Authenticate user via WebSocket token query parameter."""
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
    except Exception:
        return None
    
    user = db.get(User, user_id)
    if not user or user.role.value != role:
        return None
    return user


# WebSocket Endpoints
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for real-time chat in a conversation."""
    user = await get_current_user_ws(token, db)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    channel = f"chat:{conversation_id}"
    await manager.connect(websocket, channel, user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                elif msg.get("type") == "typing":
                    # Broadcast typing indicator
                    await publish_chat_event(conversation_id, "user_typing", {
                        "user_id": user.id,
                        "user_name": user.name
                    }, user_id=user.id)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel, user.id)
    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
        await manager.disconnect(websocket, channel, user.id)


async def websocket_transactions(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for real-time transaction updates."""
    user = await get_current_user_ws(token, db)
    if not user or user.role not in (Role.MEMBER, Role.MODERATOR, Role.OWNER_TREASURER):
        await websocket.close(code=4003, reason="Insufficient permissions")
        return
    
    channel = "transactions"
    await manager.connect(websocket, channel, user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel, user.id)
    except Exception as e:
        logger.error(f"Transactions WebSocket error: {e}")
        await manager.disconnect(websocket, channel, user.id)


async def websocket_admin(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for admin dashboard real-time updates."""
    user = await get_current_user_ws(token, db)
    if not user or user.role != Role.OWNER_TREASURER:
        await websocket.close(code=4003, reason="Admin access required")
        return
    
    channels = ["admin", "system", "transactions"]
    for channel in channels:
        await manager.connect(websocket, channel, user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        for channel in channels:
            await manager.disconnect(websocket, channel, user.id)
    except Exception as e:
        logger.error(f"Admin WebSocket error: {e}")
        for channel in channels:
            await manager.disconnect(websocket, channel, user.id)