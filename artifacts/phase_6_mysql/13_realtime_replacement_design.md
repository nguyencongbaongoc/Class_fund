# Phase 6 Realtime Replacement Design

## Overview
This document designs the self-hosted realtime communication system to replace Supabase Realtime, preserving all current functionality for message updates, worker status, and frontend live updates.

---

## 1. Current Realtime Architecture

### 1.1 Supabase Realtime Usage

| Component | Channel | Event | Consumers |
|-----------|---------|-------|-----------|
| Backend | `messages:{conversation_id}` | `postgres_changes` on `messages` table | Worker (job claiming) |
| Backend | `worker_status` | `postgres_changes` on `worker_status` table | Worker (monitoring) |
| Frontend | `messages:{conversation_id}` | `postgres_changes` on `messages` table | Chat UI (live updates) |

### 1.2 Frontend Realtime Adapter (133 lines)
```typescript
// classfund/classfund/src/lib/realtime.ts
class RealtimeAdapter {
    // - Auto-reconnect with exponential backoff
    // - Connection status callbacks
    // - Message filtering by status
    // - Supabase JS client
}
```

### 1.3 Worker Main (Supabase-Backed)
```python
# worker/main.py
# Uses Supabase Realtime to subscribe to message changes
# Claims jobs when new PENDING messages arrive
```

### 1.4 Polling Fallback (Already Exists)
```typescript
// classfund/classfund/src/lib/polling.ts
// Long-polling /api/v1/messages?status=pending
// Used when Supabase realtime unavailable
```

---

## 2. Replacement Architecture: WebSocket + Redis Pub/Sub

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │◀───▶│  Backend    │◀───▶│   Redis     │
│  (WS Client)│     │  (WS Server)│     │  (Pub/Sub)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Database   │
                    │  (MySQL)    │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Worker     │
                    │  (WS/Poll)  │
                    └─────────────┘
```

### 2.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| WebSocket Server | FastAPI native WebSocket | No extra dependencies |
| Message Broker | Redis Pub/Sub | Scalable, supports multiple backend instances |
| Frontend Client | Native WebSocket API | No Supabase dependency |
| Worker Client | WebSocket or Polling | Flexible deployment |

### 2.2 Redis Channels

| Channel | Pattern | Publishers | Subscribers |
|---------|---------|------------|-------------|
| `messages:{conversation_id}` | `messages:*` | Backend (on message create/update) | Frontend, Worker |
| `worker_status` | `worker_status` | Backend (on worker heartbeat) | Admin dashboard, Worker |
| `system` | `system` | Backend (alerts) | All |

---

## 3. Backend WebSocket Implementation

### 3.1 Dependencies

```toml
# pyproject.toml - ADD
redis = ">=5.0"
websockets = ">=12.0"  # For client if needed
```

### 3.2 WebSocket Manager

```python
# app/services/realtime.py - CREATE NEW
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from redis.asyncio import Redis, ConnectionPool
import asyncio

class ConnectionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_pool = ConnectionPool.from_url(redis_url, decode_responses=True)
        self.redis = Redis(connection_pool=self.redis_pool)
        
        # Local connections: {channel: {websocket}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        
        # Subscribe to Redis channel if first local connection
        if len(self.active_connections[channel]) == 1:
            await self._subscribe_redis(channel)

    async def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                await self._unsubscribe_redis(channel)

    async def broadcast(self, channel: str, message: dict):
        """Broadcast to local connections AND publish to Redis."""
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
        await self.redis.publish(channel, json.dumps(message))

    async def _subscribe_redis(self, channel: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        
        async def listener():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._broadcast_local(channel, data)
        
        task = asyncio.create_task(listener())
        self._pubsub_tasks[channel] = task

    async def _unsubscribe_redis(self, channel: str):
        if channel in self._pubsub_tasks:
            self._pubsub_tasks[channel].cancel()
            del self._pubsub_tasks[channel]

    async def _broadcast_local(self, channel: str, message: dict):
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
        for task in self._pubsub_tasks.values():
            task.cancel()
        await self.redis.close()


# Global instance
manager = ConnectionManager()
```

### 3.3 WebSocket Endpoints

```python
# app/api/routes/realtime.py - CREATE NEW
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.realtime import manager
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ws", tags=["realtime"])

@router.websocket("/messages/{conversation_id}")
async def websocket_messages(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...),  # Access token as query param for WS
    db: Session = Depends(get_db)
):
    """WebSocket for real-time message updates in a conversation."""
    # Authenticate via token
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Verify user has access to conversation
    # (Implement conversation access check)
    
    channel = f"messages:{conversation_id}"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            # Keep connection alive, handle incoming messages if needed
            data = await websocket.receive_text()
            # Handle ping/pong or client messages
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception:
        await manager.disconnect(websocket, channel)

@router.websocket("/worker")
async def websocket_worker(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for worker status updates and job notifications."""
    # Authenticate as worker (special token or API key)
    # ...
    channel = "worker_status"
    await manager.connect(websocket, channel)
    # ... similar to above
```

### 3.4 Publishing Events (Integration Points)

```python
# app/services/realtime.py - ADD publish helpers
async def publish_message_update(conversation_id: str, message_data: dict):
    """Call when message is created/updated."""
    await manager.broadcast(f"messages:{conversation_id}", {
        "type": "message_update",
        "data": message_data
    })

async def publish_worker_status(worker_data: dict):
    """Call when worker status changes."""
    await manager.broadcast("worker_status", {
        "type": "worker_update",
        "data": worker_data
    })
```

### 3.5 Integration with Existing Code

```python
# messages.py - In create_message endpoint
from app.services.realtime import publish_message_update

@router.post("", response_model=MessageCreateResponse, status_code=201)
def create_message(...):
    # ... create message ...
    db.commit()
    
    # Publish realtime update
    await publish_message_update(message.conversation_id, {
        "message_id": message.id,
        "status": message.status,
        "content": message.content,
        # ... other fields
    })
    
    return response

# ledger.py - In post_transaction (when message posted)
from app.services.realtime import publish_message_update

# After successful post:
message.status = MessageStatus.POSTED.value
message.transaction_id = tx.id
db.commit()

await publish_message_update(message.conversation_id, {
    "message_id": message.id,
    "status": "posted",
    "transaction_id": tx.id,
})

# worker/main.py - In heartbeat/status update
from app.services.realtime import publish_worker_status

worker.status = "online"
worker.last_heartbeat = utcnow()
db.commit()

await publish_worker_status({
    "worker_id": worker.worker_id,
    "status": "online",
    "last_heartbeat": worker.last_heartbeat.isoformat(),
})
```

---

## 4. Frontend WebSocket Client

### 4.1 Replacement for RealtimeAdapter

```typescript
// classfund/classfund/src/lib/realtime.ts - REPLACE
type MessageUpdateCallback = (message: MessageStatusResponse) => void;
type ConnectionStatusCallback = (connected: boolean) => void;

interface RealtimeClientConfig {
  conversationId: string;
  onMessageUpdate: MessageUpdateCallback;
  onConnectionChange?: ConnectionStatusCallback;
  accessToken: string;
}

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private config: RealtimeClientConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;

  constructor(config: RealtimeClientConfig) {
    this.config = config;
  }

  async connect(): Promise<boolean> {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return true;
    }

    this.isConnecting = true;
    const wsUrl = this.getWsUrl();
    
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      return true;
    } catch (error) {
      this.isConnecting = false;
      this.config.onConnectionChange?.(false);
      return false;
    }
  }

  private getWsUrl(): string {
    const baseUrl = import.meta.env.VITE_WS_URL || 
      (import.meta.env.VITE_API_URL || '/api/v1').replace('/api/v1', '');
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${baseUrl.replace(/^https?:\/\//, '')}/ws/messages/${this.config.conversationId}?token=${this.config.accessToken}`;
  }

  private handleOpen() {
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.config.onConnectionChange?.(true);
    console.log('[Realtime] Connected');
  }

  private handleMessage(event: MessageEvent) {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'message_update') {
        this.config.onMessageUpdate(payload.data as MessageStatusResponse);
      }
    } catch (e) {
      console.warn('[Realtime] Invalid message:', e);
    }
  }

  private handleClose() {
    this.isConnecting = false;
    this.config.onConnectionChange?.(false);
    this.attemptReconnect();
  }

  private handleError(error: Event) {
    console.error('[Realtime] Error:', error);
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[Realtime] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`[Realtime] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => this.connect(), delay);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export function createRealtimeClient(config: RealtimeClientConfig): RealtimeClient {
  return new RealtimeClient(config);
}
```

### 4.2 Integration with useChat Hook

```typescript
// classfund/classfund/src/hooks/useChat.ts - UPDATE
import { createRealtimeClient } from '../lib/realtime';

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<MessageStatusResponse[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  
  const realtimeRef = useRef<RealtimeClient | null>(null);

  useEffect(() => {
    const tokens = authService.getStoredTokens();
    if (!tokens?.access_token) return;

    realtimeRef.current = createRealtimeClient({
      conversationId,
      accessToken: tokens.access_token,
      onMessageUpdate: (message) => {
        setMessages(prev => {
          const idx = prev.findIndex(m => m.message_id === message.message_id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = message;
            return updated;
          }
          return [message, ...prev];
        });
      },
      onConnectionChange: setIsConnected,
    });

    realtimeRef.current.connect();

    return () => {
      realtimeRef.current?.disconnect();
    };
  }, [conversationId]);

  // ... rest of hook
}
```

---

## 5. Worker Integration

### 5.1 WebSocket-Based Worker (Preferred)

```python
# worker/main.py - UPDATE
import asyncio
import websockets
import json

class WebSocketWorker:
    def __init__(self, worker_id: str, api_url: str, token: str):
        self.worker_id = worker_id
        self.ws_url = f"{api_url.replace('http', 'ws')}/ws/worker?token={token}"
        self.ws = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url)
        # Send initial status
        await self.ws.send(json.dumps({
            "type": "worker_status",
            "worker_id": self.worker_id,
            "status": "online"
        }))
        
        async for message in self.ws:
            data = json.loads(message)
            if data.get("type") == "job_available":
                await self.claim_job(data["message_id"])

    async def claim_job(self, message_id: str):
        # Claim via REST API
        pass

    async def heartbeat(self):
        while True:
            await asyncio.sleep(30)
            if self.ws:
                await self.ws.send(json.dumps({
                    "type": "heartbeat",
                    "worker_id": self.worker_id
                }))
```

### 5.2 Polling-Based Worker (Fallback/Alternative)

```python
# worker/main.py - KEEP AS ALTERNATIVE
async def poll_for_jobs(worker_id: str, db: Session):
    """Poll for pending messages (current implementation works)."""
    while True:
        message = db.execute(
            select(Message)
            .where(Message.status == MessageStatus.PENDING.value)
            .order_by(Message.created_at)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        
        if message:
            message.status = MessageStatus.PROCESSING.value
            message.worker_id = worker_id
            db.commit()
            # Process message...
        else:
            await asyncio.sleep(5)  # Poll interval
```

**Decision:** Support both. WebSocket for real-time, polling as fallback.

---

## 6. Redis Configuration

### 6.1 Docker Compose

```yaml
# docker-compose.yml - ADD
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - classfund_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  classfund_redis_data:
```

### 6.2 Redis Settings

```python
# app/core/config.py - ADD
redis_url: str = "redis://redis:6379"
```

---

## 7. Polling Fallback (Preserve Existing)

The existing `polling.ts` continues to work as fallback:

```typescript
// classfund/classfund/src/lib/polling.ts - KEEP
// Used when WebSocket fails or for workers that prefer polling
```

---

## 8. Migration Plan

### 8.1 Phase 1: Backend WebSocket Server
1. Create `app/services/realtime.py` with ConnectionManager
2. Create `app/api/routes/realtime.py` with WebSocket endpoints
3. Add Redis to docker-compose
4. Integrate publish calls in `messages.py`, `ledger.py`, `worker/main.py`

### 8.2 Phase 2: Frontend WebSocket Client
1. Replace `realtime.ts` with WebSocket implementation
2. Update `useChat.ts` to use new client
3. Add `VITE_WS_URL` environment variable

### 8.3 Phase 3: Worker Update
1. Update `worker/main.py` to use WebSocket or keep polling
2. Test worker job claiming via WebSocket

### 8.4 Phase 4: Remove Supabase Realtime
1. Delete `subscribe_to_messages`, `subscribe_to_worker_status` from `supabase_client.py`
2. Remove Supabase realtime config from frontend
3. Remove `@supabase/supabase-js` from package.json (if not removed in auth)

---

## 9. Testing

### 9.1 Unit Tests

```python
# tests/test_realtime.py
async def test_websocket_message_broadcast():
    # Test manager.broadcast delivers to local connections
    pass

async def test_redis_pubsub():
    # Test Redis pub/sub delivers across instances
    pass
```

### 9.2 Integration Tests

```python
async def test_frontend_receives_message_update():
    # 1. Connect frontend WebSocket
    # 2. Create message via REST API
    # 3. Verify frontend receives update
    pass

async def test_worker_receives_job_notification():
    # 1. Connect worker WebSocket
    # 2. Create pending message
    # 3. Verify worker notified
    pass
```

### 9.3 Load Test

```bash
# 1000 concurrent WebSocket connections
# Measure memory, CPU, latency
```

---

## 10. Verification Checklist

- [ ] WebSocket server accepts connections with JWT auth
- [ ] Message updates broadcast to conversation subscribers
- [ ] Worker status updates broadcast
- [ ] Frontend receives real-time updates
- [ ] Auto-reconnect works on disconnect
- [ ] Polling fallback still works
- [ ] Redis pub/sub works across backend instances
- [ ] Supabase realtime code removed
- [ ] No `@supabase/supabase-js` in package.json

---

**Status: REALTIME REPLACEMENT DESIGN COMPLETE - Ready for Docker Compose Design**