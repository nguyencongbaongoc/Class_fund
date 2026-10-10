# Phase 7 WebSocket & Redis Pub/Sub Real-Time Integration

## Overview
Complete real-time communication layer replacing Supabase Realtime with native WebSocket + Redis Pub/Sub.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │◀───▶│  Backend    │◀───▶│   Redis     │
│  (WebSocket)│     │  (FastAPI)  │     │  (Pub/Sub)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Worker    │
                    │  (Pub/Sub)  │
                    └─────────────┘
```

## Components

### 1. Connection Manager (`app/core/websocket.py`)

**Features:**
- Multi-channel support (chat, transactions, admin, system)
- User-based connection tracking
- Redis Pub/Sub listener for cross-instance events
- Automatic reconnection handling
- Heartbeat/ping-pong keepalive
- Role-based broadcast filtering

**Channels:**
- `chat:{conversation_id}` - Per-conversation messages
- `transactions` - Transaction updates (MEMBER+)
- `admin` - Admin dashboard events (OWNER_TREASURER)
- `system` - System-wide alerts (all)

### 2. WebSocket Endpoints (`app/api/routes/realtime.py`)

| Endpoint | Auth Required | Roles | Purpose |
|----------|--------------|-------|---------|
| `/ws/chat/{conversation_id}` | Yes | All | Chat messages |
| `/ws/transactions` | Yes | MEMBER+ | Transaction updates |
| `/ws/admin` | Yes | OWNER_TREASURER | Admin dashboard |
| `/ws/health` | No | - | Health check |

### 3. Worker Event Publishing (`worker/main.py`)

Worker publishes events to Redis channels:

```python
# Message received
await _publish_event("chat:events", "MESSAGE_RECEIVED", {
    "message_id": msg.id,
    "conversation_id": msg.conversation_id
})

# AI extraction complete
await _publish_event("chat:events", "AI_EXTRACTED", {
    "message_id": msg.id,
    "status": "needs_review" | "approved"
})

# Ledger committed
await _publish_event("tx:updates", "LEDGER_COMMITTED", {
    "message_id": msg.id,
    "transaction_id": tx.id,
    "amount": "50000"
})

# Transaction reversed
await _publish_event("tx:updates", "TRANSACTION_REVERSED", {
    "message_id": msg.id,
    "original_tx_id": orig_tx.id,
    "revert_tx_id": revert_tx.id
})
```

### 4. Frontend Integration

**WebSocket Client Hook:**
```typescript
// Auto-reconnect with exponential backoff
// Fallback to 5s polling on disconnect
// Event deduplication
```

## Redis Configuration

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 128mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD}
  ports: ["6379:6379"]
```

**Security:**
- Password authentication required
- AOF persistence enabled
- Max memory limit with LRU eviction
- Dangerous commands disabled (FLUSHALL, CONFIG)

## Event Flow Examples

### 1. New Message Received
```
User sends message → POST /api/v1/messages
    → Worker claims message
    → Worker publishes MESSAGE_RECEIVED to chat:{conversation_id}
    → All connected clients in conversation receive event
```

### 2. AI Extraction Complete
```
Worker extracts receipt → verify_and_post_from_ai()
    → If approved: publishes LEDGER_COMMITTED to tx:updates
    → If needs review: publishes AI_EXTRACTED to chat:{conversation_id}
    → Frontend updates UI in real-time
```

### 3. Transaction Reversal (Recall)
```
User recalls message → POST /api/v1/messages/{id}/recall
    → post_revert() creates REVERT transaction
    → Worker publishes TRANSACTION_REVERSED to tx:updates
    → Frontend updates balance and message status
```

### 4. Admin Dashboard
```
Admin connects to /ws/admin
    → Receives system alerts, worker status, queue metrics
    → Real-time worker health updates
```

## Connection Manager Features

### Connection Lifecycle
```python
# Connect
await manager.connect(websocket, channel, user_id)

# Disconnect (auto-cleanup)
await manager.disconnect(websocket, channel, user_id)

# Broadcast with filters
await manager.broadcast(channel, event, 
    exclude_user=user_id,  # Don't send to sender
    role_filter="MEMBER")  # Role-based filtering

# Personal message
await manager.send_personal(user_id, event)
```

### Redis Pub/Sub Integration
```python
# Subscribe to channel
await manager._subscribe_redis("chat:events")

# Publish to channel (cross-instance)
await manager._redis.publish("chat:events", json.dumps(event))

# Local broadcast from Redis message
await manager._broadcast_local(channel, data)
```

## Security

### Authentication
- JWT token in query parameter: `?token=<jwt>`
- Validated via `decode_access_token()`
- User object retrieved from database

### Authorization
- Channel-level: `role_filter` parameter
- Personal: `send_personal(user_id, event)`
- Admin: `role_filter="OWNER_TREASURER"`

### Connection Limits
- Max connections per user per channel: 5
- Heartbeat: 30s ping/pong
- Stale connection cleanup: 60s timeout

## Testing

### Redis Pub/Sub Test
```bash
pytest tests/test_mysql_qualification.py::test_12_redis_pubsub_realtime -v
```

**Result:** PASSED
- Native Redis on port 6379
- Fallback to WSL Ubuntu Redis if native unavailable

### WebSocket Health Check
```bash
curl http://localhost:8000/ws/health
```

### Manual WebSocket Test
```bash
# Connect
wscat -c "ws://localhost:8000/ws/chat/test-conversation?token=<jwt>"

# Send ping
{"type": "ping"}

# Receive pong
{"type": "pong", "timestamp": "2026-10-10T14:30:00Z"}
```

## Event Types Reference

| Event Type | Channel | Payload |
|------------|---------|---------|
| `MESSAGE_RECEIVED` | `chat:{id}` | `{message_id, conversation_id, sender_name}` |
| `MESSAGE_UPDATED` | `chat:{id}` | `{message_id, status, content}` |
| `MESSAGE_RECALLED` | `chat:{id}` | `{message_id, conversation_id}` |
| `USER_TYPING` | `chat:{id}` | `{user_id, user_name}` |
| `LEDGER_COMMITTED` | `tx:updates` | `{message_id, transaction_id, amount}` |
| `TRANSACTION_REVERSED` | `tx:updates` | `{message_id, original_tx_id, revert_tx_id}` |
| `AI_EXTRACTED` | `chat:{id}` | `{message_id, status, confidence}` |
| `WORKER_STATUS` | `admin` | `{worker_id, status, last_heartbeat}` |
| `SYSTEM_ALERT` | `system` | `{level, message}` |

## Frontend Reconnection Logic

```typescript
// Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
// Max reconnect attempts: 10
// Fallback: 5s polling after max retries
// Event deduplication by message_id
```

## Monitoring

### Health Endpoint
```json
GET /ws/health
{
  "status": "healthy",
  "service": "websocket",
  "active_connections": 42,
  "channels": ["chat:abc123", "transactions", "admin"]
}
```

### Metrics
- Active connections per channel
- Messages per second
- Redis Pub/Sub latency
- Connection errors