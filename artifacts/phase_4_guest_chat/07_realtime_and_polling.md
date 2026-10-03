# 07_realtime_and_polling.md

## Realtime and Polling Adapter Specification

### Overview
The HybridAdapter provides real-time message status updates with Supabase Realtime as primary and polling as fallback. This ensures status updates work even without Supabase credentials.

### Architecture

```
GuestChatPage
    ↓
useChat hook
    ↓
HybridAdapter (manages both)
    ├── RealtimeAdapter (Supabase Realtime)
    └── PollingAdapter (HTTP polling)
```

### RealtimeAdapter

#### Configuration
```typescript
interface RealtimeAdapterConfig {
  conversationId: string;
  onMessageUpdate: (message: MessageStatusResponse) => void;
  onConnectionChange?: (connected: boolean) => void;
  supabaseUrl?: string;
  supabaseAnonKey?: string;
}
```

#### Connection Flow
1. Check for Supabase credentials (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY)
2. If missing → return false, trigger polling fallback
3. Create Supabase client with anon key
4. Subscribe to `messages` table with filter: `conversation_id=eq.{conversationId}`
5. Listen for INSERT, UPDATE events
6. On event → call onMessageUpdate with new message data
7. On disconnect → exponential backoff reconnect (max 5 attempts)

#### Event Handling
```typescript
channel.on('postgres_changes', {
  event: '*',
  schema: 'public',
  table: 'messages',
  filter: `conversation_id=eq.${conversationId}`
}, (payload) => {
  if (payload.eventType === 'DELETE') return;
  
  const message = payload.new as MessageStatusResponse;
  
  // Only process relevant statuses
  const relevantStatuses = ['pending', 'processing', 'awaiting_review', 'posted', 'rejected', 'failed', 'recalled'];
  if (relevantStatuses.includes(message.status)) {
    onMessageUpdate(message);
  }
});
```

#### Reconnection Logic
- Attempt 1: 1s delay
- Attempt 2: 2s delay  
- Attempt 3: 4s delay
- Attempt 4: 8s delay
- Attempt 5: 16s delay
- After 5 failures → stop, polling takes over

### PollingAdapter

#### Configuration
```typescript
interface PollingAdapterConfig {
  conversationId: string;
  messageIds: string[];  // Messages to poll
  onUpdate: (messages: MessageStatusResponse[]) => void;
  interval?: number;     // Default 5000ms
  enabled?: boolean;
}
```

#### Polling Logic
1. Every 5 seconds (configurable):
   - For each messageId in messageIds:
     - GET /api/v1/messages/{messageId}
     - If status changed → add to updates
     - If terminal status (posted/rejected/failed/recalled) → remove from messageIds
   - If updates exist → call onUpdate
   - If messageIds empty → stop polling

#### Terminal Status Handling
- Once message reaches terminal state, stop polling for it
- Prevents unnecessary API calls
- Reduces server load

### HybridAdapter

#### Connection Strategy
```typescript
async connect() {
  const realtimeConnected = await this.realtime.connect();
  
  if (!realtimeConnected) {
    // No Supabase credentials or connection failed
    this.usePollingFallback = true;
    this.polling.setEnabled(true);
    this.config.onConnectionChange?.(true, 'polling');
  }
}
```

#### Event Deduplication
- Both adapters call `onMessageUpdate`
- useChat hook handles deduplication:
  - Compare message.id and processed_at
  - Ignore stale updates (older processed_at)
  - Update message in state

#### Connection State Reporting
```typescript
onConnectionChange: (connected: boolean, source: 'realtime' | 'polling') => {
  setIsConnected(connected);
  setConnectionSource(source);
}
```

### useChat Integration

```typescript
const hybridAdapterRef = useRef<HybridAdapter>();

useEffect(() => {
  hybridAdapterRef.current = createHybridAdapter({
    conversationId,
    onMessageUpdate: handleMessageUpdate,
    onConnectionChange: (connected, source) => {
      setIsConnected(connected);
      setConnectionSource(source);
    },
    supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
    supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY,
  });

  hybridAdapterRef.current.connect();

  // Load initial messages
  refreshMessages();

  return () => {
    hybridAdapterRef.current?.disconnect();
  };
}, [conversationId]);
```

### Adding/Removing Messages from Tracking
```typescript
// When optimistic message added
hybridAdapterRef.current?.addMessageId(messageId);

// When message reaches terminal state
hybridAdapterRef.current?.removeMessageId(messageId);
```

### Environment Variables
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=/api/v1  # Optional, defaults to /api/v1
```

### Testing Scenarios

1. **Supabase configured** → Realtime connects, instant updates
2. **Supabase not configured** → Polling starts automatically
3. **Realtime disconnects** → Polling fallback activates
4. **Realtime reconnects** → Polling stops, realtime resumes
5. **Message posted** → Removed from polling, realtime still works
6. **Multiple messages** → All tracked independently
7. **Network offline** → Reconnection attempts, polling continues
8. **Component unmount** → Both adapters disconnected

### Fallback Behavior
| Scenario | Realtime | Polling | Result |
|----------|----------|---------|--------|
| Credentials present | ✓ Connected | Standby | Realtime updates |
| Credentials missing | ✗ Failed | ✓ Active | 5s polling |
| Connected then lost | ✗ Reconnecting | ✓ Active | Polling until reconnect |
| Reconnects | ✓ Connected | ✗ Stopped | Realtime resumes |
| Terminal status | Still connected | Removed from list | Efficient |