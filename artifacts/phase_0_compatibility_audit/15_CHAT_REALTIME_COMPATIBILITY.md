# PHASE 0 ADDENDUM — CHAT REALTIME COMPATIBILITY AUDIT

## Executive Summary
**Status: PARTIALLY_COMPATIBLE** — The frontend has a complete chat UI with mock data but zero realtime capability. Supabase Realtime can provide the needed infrastructure with minimal frontend adapter changes.

---

## 1. CURRENT CHAT IMPLEMENTATION

### Frontend ChatView (`src/views/ChatView.tsx`)

**Features Implemented (Mock Only):**
- Message list with types: `TEXT`, `RECEIPT`, `ANNOUNCEMENT`, `SYSTEM`
- Pinned moderator announcements
- Receipt message cards with image preview, amount, transaction code
- Sender name, role badge (MOD), timestamp
- Message input with MOD announcement toggle
- Attach receipt button (navigates to Upload tab)
- Auto-scroll to bottom (via `flex-col-reverse`)

**Data Source:** `AppContext.chatMessages` from `mockDatabase.ts`

**No Network Code:** Zero `fetch`, `WebSocket`, or subscription logic.

### Mock Message Structure (`src/types/index.ts:65-84`)
```typescript
ChatMessage = {
  id: string,
  sender_id: string,
  sender_name: string,
  sender_role: UserRole,
  message_type: 'TEXT' | 'RECEIPT' | 'ANNOUNCEMENT' | 'SYSTEM',
  content: string,
  receipt_data?: {
    entry_id: string,
    amount: number,
    transaction_code: string,
    image_url: string,
    status: TransactionStatus,
    sender_name: string,
    uploader_name: string,
    time: string,
  },
  is_pinned?: boolean,
  created_at: string,  // "HH:mm" format only
}
```

### Backend Chat Endpoints (`app/api/routes/chat.py`)
```python
GET /api/v1/chat/messages?limit=50&offset=0 → list[ChatMessageOut]
POST /api/v1/chat/messages (ChatMessageIn) → ChatMessageOut
```

**Backend Model** (`app/models/models.py:236-245`):
```python
class ChatMessage(Base):
    id, sender_id (FK users), sender_role, message_type,
    content, attachment_id, ledger_entry_id, created_at
```

**Gaps vs Frontend:**
- No `conversation_id` (single global chat)
- No `is_pinned` column
- No `receipt_data` JSON — frontend expects embedded receipt preview
- `created_at` is full timestamp; frontend shows only time

---

## 2. SUPABASE REALTIME CAPABILITIES

### What Supabase Realtime Provides
- PostgreSQL `NOTIFY`/`LISTEN` via websockets
- Row-level changes: `INSERT`, `UPDATE`, `DELETE`
- Filter by table, schema, event type, column values
- Presence (who's online)
- Broadcast (custom events)

### Required Tables for Realtime

| Table | Events Needed | Frontend Subscription |
|-------|---------------|----------------------|
| `messages` (new) | INSERT, UPDATE (status) | Live message feed, status changes |
| `ledger_entries` | INSERT | Live balance/ledger updates |
| `campaign_members` | UPDATE (status) | Live campaign progress |
| `uploads` | UPDATE (status) | Upload processing status |
| `chat_messages` (legacy) | INSERT | Backward compatibility |

### Publication Setup
```sql
-- Enable realtime for required tables
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE ledger_entries;
ALTER PUBLICATION supabase_realtime ADD TABLE campaign_members;
ALTER PUBLICATION supabase_realtime ADD TABLE uploads;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
```

---

## 3. FRONTEND REALTIME INTEGRATION DESIGN

### New Hook: `useRealtimeMessages`

```typescript
// src/hooks/useRealtimeMessages.ts
import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { ChatMessage } from '../types'

export function useRealtimeMessages(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // 1. Initial fetch
    supabase
      .from('messages')
      .select('*')
      .eq('conversation_id', conversationId)
      .order('created_at', { ascending: true })
      .then(({ data }) => {
        setMessages(data || [])
        setLoading(false)
      })

    // 2. Subscribe to changes
    const channel = supabase
      .channel(`messages:${conversationId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `conversation_id=eq.${conversationId}`,
        },
        (payload) => {
          setMessages(prev => [...prev, payload.new as ChatMessage])
        }
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'messages',
          filter: `conversation_id=eq.${conversationId}`,
        },
        (payload) => {
          setMessages(prev => 
            prev.map(m => m.id === payload.new.id ? payload.new as ChatMessage : m)
          )
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [conversationId])

  return { messages, loading }
}
```

### Updated ChatView Integration
```typescript
// ChatView.tsx - replace mock usage
const { messages, loading } = useRealtimeMessages(currentConversationId)

const handleSend = async (e: React.FormEvent) => {
  e.preventDefault()
  if (!inputText.trim()) return

  // Optimistic UI
  const tempId = `temp_${Date.now()}`
  setMessages(prev => [...prev, {
    id: tempId,
    sender_id: currentUser.id,
    sender_name: currentUser.name,
    sender_role: currentUser.role,
    message_type: isModAnnouncement ? 'ANNOUNCEMENT' : 'TEXT',
    content: inputText,
    created_at: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    is_pinned: isModAnnouncement,
  }])
  setInputText('')

  // Actual insert (RLS enforces sender_id = auth.uid())
  const { error } = await supabase.from('messages').insert({
    conversation_id: currentConversationId,
    content: inputText,
    message_type: isModAnnouncement ? 'ANNOUNCEMENT' : 'TEXT',
    is_pinned: isModAnnouncement,
  })
  
  if (error) {
    // Rollback optimistic update
    setMessages(prev => prev.filter(m => m.id !== tempId))
    addToast({ type: 'error', title: 'Gửi thất bại', description: error.message })
  }
}
```

---

## 4. MESSAGE STATE MACHINE (REALTIME)

### Frontend Message States

| State | Visual | Description |
|-------|--------|-------------|
| `sending` | Spinner | Optimistic insert, awaiting server confirmation |
| `sent` | Checkmark | Server confirmed (INSERT returned) |
| `processing` | AI sparkle | Worker claimed message, running AI |
| `awaiting_admin` | Warning badge | AI needs human review |
| `processed` | Green check | AI verified, ledger posted |
| `failed` | Red alert | Error, retry available |

### Realtime Status Transitions
```typescript
// Backend/worker updates message status
// Frontend receives UPDATE via realtime

// payload.new = { id, status: 'processing', ... }
setMessages(prev => prev.map(m => 
  m.id === payload.new.id 
    ? { ...m, status: payload.new.status, ai_result: payload.new.ai_result }
    : m
))
```

### Visual Indicators (Add to ChatView)
```tsx
{message.status === 'processing' && (
  <span className="inline-flex items-center gap-1 text-xs text-sky-400">
    <Loader2 className="w-3 h-3 animate-spin" />
    <span>AI đang xử lý...</span>
  </span>
)}
{message.status === 'awaiting_admin' && (
  <span className="inline-flex items-center gap-1 text-xs text-amber-400">
    <AlertTriangle className="w-3 h-3" />
    <span>Chờ duyệt thủ quỹ</span>
  </span>
)}
{message.status === 'failed' && (
  <button className="text-xs text-rose-400 underline" onClick={() => retryMessage(message.id)}>
    Thử lại
  </button>
)}
```

---

## 5. DELIVERY STATE TRACKING

### Current: None
### Required: Message Receipts

```sql
-- Add to messages table
message_state varchar(20) DEFAULT 'sent',  -- sent, delivered, read
delivered_at timestamptz,
read_at timestamptz

-- Or separate receipts table for granular tracking
CREATE TABLE message_receipts (
  message_id uuid REFERENCES messages(id),
  user_id uuid REFERENCES auth.users(id),
  state varchar(20) NOT NULL,  -- delivered, read
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (message_id, user_id)
);
```

### Frontend Delivery Hook
```typescript
// Mark delivered when message enters viewport
useEffect(() => {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        supabase.from('message_receipts').upsert({
          message_id: entry.target.dataset.messageId,
          user_id: currentUser.id,
          state: 'delivered',
        })
      }
    })
  }, { threshold: 0.5 })
  
  messages.forEach(m => observer.observe(document.getElementById(m.id)))
  return () => observer.disconnect()
}, [messages])
```

---

## 6. ADMIN REVIEW NOTIFICATIONS

### Worker Sets `status = 'awaiting_admin'`
- AI confidence below threshold
- Missing transaction code/amount
- Sender mismatch
- Duplicate detected

### Frontend Admin Badge
```tsx
{message.status === 'awaiting_admin' && currentUser.role === 'MODERATOR' && (
  <button 
    className="text-xs px-2 py-1 bg-amber-500/20 text-amber-300 rounded"
    onClick={() => openReviewModal(message.id)}
  >
    Xem xét ngay
  </button>
)}
```

### Review Modal
- Shows original message + AI extraction (`ai_result`)
- Buttons: Approve (→ `processed`), Reject (→ `failed`), Request more info

---

## 7. WORKER OFFLINE INDICATION

### Worker Status via Realtime
```sql
-- worker_status table changes
ALTER PUBLICATION supabase_realtime ADD TABLE worker_status;
```

### Frontend Worker Indicator
```typescript
// src/hooks/useWorkerStatus.ts
export function useWorkerStatus() {
  const [status, setStatus] = useState<'online' | 'offline' | 'processing'>('offline')

  useEffect(() => {
    const channel = supabase
      .channel('worker_status')
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'worker_status',
      }, payload => {
        const worker = payload.new
        if (worker.status === 'online' && worker.last_heartbeat > Date.now() - 30000) {
          setStatus(worker.current_job_id ? 'processing' : 'online')
        } else {
          setStatus('offline')
        }
      })
      .subscribe()

    return () => supabase.removeChannel(channel)
  }, [])

  return status
}

// In Navbar or ChatView header
const workerStatus = useWorkerStatus()
return (
  <span className={`w-2 h-2 rounded-full ${
    workerStatus === 'online' ? 'bg-emerald-400' :
    workerStatus === 'processing' ? 'bg-sky-400 animate-pulse' :
    'bg-rose-400'
  }`} />
)
```

---

## 8. RECONNECTION HANDLING

### Supabase Client Auto-Reconnect
```typescript
// supabase-js handles reconnection automatically
// But we need to resubscribe channels

supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'TOKEN_REFRESHED') {
    // Resubscribe channels with new token
    Object.values(channels).forEach(ch => ch.subscribe())
  }
})
```

### Custom Reconnection Logic
```typescript
function useRealtimeWithReconnect(channelName: string, config: RealtimeConfig) {
  const [connected, setConnected] = useState(false)
  
  useEffect(() => {
    const channel = supabase.channel(channelName)
    
    channel
      .on('system', {}, () => setConnected(true))
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') setConnected(true)
        if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') setConnected(false)
      })
    
    return () => supabase.removeChannel(channel)
  }, [channelName])
  
  return connected
}
```

---

## 9. DUPLICATE EVENT HANDLING

### Risk: Realtime May Deliver Duplicate Events
- Network reconnection
- Multiple subscriptions
- Server-side retries

### Deduplication Strategy
```typescript
// Track processed event IDs
const processedEventIds = useRef<Set<string>>(new Set())

channel.on('postgres_changes', { ... }, payload => {
  const eventId = `${payload.eventType}:${payload.new.id}:${payload.commit_timestamp}`
  
  if (processedEventIds.current.has(eventId)) return
  processedEventIds.current.add(eventId)
  
  // Keep set bounded
  if (processedEventIds.current.size > 1000) {
    const first = processedEventIds.current.values().next().value
    processedEventIds.current.delete(first)
  }
  
  // Process event
})
```

---

## 10. COMPATIBILITY MATRIX

| Feature | Current Frontend | Supabase Realtime | Effort |
|---------|------------------|-------------------|--------|
| Message list | Mock array | `useRealtimeMessages` hook | Low |
| Send message | `sendChatMessage()` local | `supabase.from('messages').insert()` | Low |
| Receipt preview | Mock `receipt_data` | `ai_result` JSON in message | Medium |
| Pinned announcements | `is_pinned` filter | Same + realtime | Low |
| MOD badge | `sender_role` check | Same | Low |
| Typing indicator | None | Presence + broadcast | Medium |
| Delivery receipts | None | `message_receipts` table | Medium |
| Admin review queue | None | `status='awaiting_admin'` filter | Low |
| Worker status | None | `worker_status` table | Low |
| Reconnection | None | Supabase auto + resubscribe | Low |
| Duplicate handling | None | Event ID deduplication | Low |

---

## 11. IS A NEW CHAT UI NECESSARY?

**NO** — The existing `ChatView.tsx` is feature-complete for mock data. Required changes:
1. Replace `useApp()` chat messages with `useRealtimeMessages()` hook
2. Replace `sendChatMessage()` with Supabase insert
3. Add status badges for `processing`/`awaiting_admin`/`failed`
4. Add worker status indicator
5. Add retry button for failed messages

**Estimated effort**: ~200 lines of new hook + ~50 lines of component changes.

---

## 12. CONVERSATION MODEL

### Current: Single Global Chat
- All messages in one list
- No conversation separation

### Hybrid: Conversation-Per-Campaign/Topic
```sql
CREATE TABLE conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title varchar(200),
  type varchar(30),  -- 'campaign', 'general', 'announcements'
  campaign_id uuid REFERENCES collection_campaigns(id),
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE conversation_participants (
  conversation_id uuid REFERENCES conversations(id),
  user_id uuid REFERENCES auth.users(id),
  role varchar(20),  -- 'member', 'moderator'
  joined_at timestamptz DEFAULT now(),
  PRIMARY KEY (conversation_id, user_id)
);
```

### Frontend Conversation List
```tsx
// New ConversationList component in Navbar or sidebar
const { data: conversations } = useRealtimeConversations()

return (
  <div className="space-y-1">
    {conversations.map(c => (
      <button key={c.id} onClick={() => setCurrentConversation(c.id)}>
        {c.title} ({c.unread_count})
      </button>
    ))}
  </div>
)
```

---

## 13. CONFIDENCE ASSESSMENT

- **Verified**: Frontend chat code, Supabase Realtime API, PostgreSQL publication syntax
- **Partially Verified**: Integration complexity (standard patterns)
- **Assumed**: Supabase Realtime scales for expected message volume
- **Not Verified**: Actual reconnection behavior under poor network, presence scaling