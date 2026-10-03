# 01_guest_chat_architecture.md

## Phase 4 Guest Chat Architecture

### Overview
This document describes the frontend architecture for the Guest Chat feature in Phase 4. The architecture follows a clean separation of concerns between UI components, API layer, state management, and realtime adapters.

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + TS)                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  UI Layer    │  │  State Layer │  │  Integration Layer   │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤  │
│  │ • MessageList│  │ • ChatStore  │  │ • ApiClient          │  │
│  │ • Composer   │  │ • UploadStore│  │ • RealtimeAdapter    │  │
│  │ • ImageUpload│  │ • RecallStore│  │ • PollingFallback    │  │
│  │ • StatusBadge│  └──────────────┘  │ • UploadAdapter      │  │
│  │ • RecallBtn  │                    │ • RecallAdapter      │  │
│  └──────────────┘                    └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    HTTP / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend API (FastAPI)                    │
├─────────────────────────────────────────────────────────────────┤
│  POST   /api/v1/uploads          → Upload receipt image        │
│  POST   /api/v1/messages         → Create message (w/ token)   │
│  GET    /api/v1/messages/:id     → Get message status          │
│  POST   /api/v1/messages/:id/recall → Recall message           │
│  GET    /api/v1/messages         → List messages (conversation)│
│  GET    /api/v1/public/fund      → Public fund balance         │
│  GET    /api/v1/public/bank-accounts → Bank info for guests    │
└─────────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
GuestChatPage (Route: /chat)
├── MessageList
│   ├── PinnedMessage (optional)
│   ├── MessageItem (repeated)
│   │   ├── SenderInfo
│   │   ├── MessageBubble
│   │   │   ├── TextContent
│   │   │   ├── ReceiptContent
│   │   │   └── AnnouncementContent
│   │   ├── StatusBadge
│   │   ├── PublicCodeDisplay
│   │   └── RecallButton (conditional)
│   └── EmptyState / LoadingState
├── MessageComposer
│   ├── SenderNameInput (for PUBLIC role)
│   ├── TextInput
│   ├── ImageUploadArea
│   │   ├── FileInput (hidden)
│   │   ├── PreviewGrid
│   │   │   ├── PreviewItem
│   │   │   │   ├── ImagePreview
│   │   │   │   ├── ProgressBar
│   │   │   │   ├── RemoveButton
│   │   │   │   └── RetryButton (on error)
│   │   └── DropZone / ClickToUpload
│   ├── SendButton (with loading state)
│   └── ErrorToast (inline)
└── ToastContainer (global)
```

### Data Flow

#### Message Creation Flow
```
User Input (text + optional images)
       │
       ▼
MessageComposer.validate()
       │
       ├── Images? → UploadAdapter.uploadImages() → attachment_ids[]
       │
       ▼
ApiClient.createMessage({ content, sender_name, attachment_ids })
       │
       ▼
Backend returns: { message_id, public_code, recall_token, status }
       │
       ├── Store recall_token in sessionStorage[message_id]
       ├── Add optimistic message to ChatStore (status: PENDING)
       │
       ▼
Subscribe to realtime updates for message_id
       │
       ▼
On status change → Update ChatStore message status
```

#### Image Upload Flow
```
User selects file(s)
       │
       ▼
ImageUpload.validate(file) → Check MIME, size
       │
       ▼
Create preview URLs (objectURL)
       │
       ▼
For each file:
  UploadAdapter.upload(file) 
       │
       ├── POST /api/v1/uploads → { upload_id, status }
       ├── Show progress (via XHR upload progress)
       ├── On success → Store upload_id
       ├── On error → Show retry button
       │
       ▼
Return array of upload_ids for message creation
```

#### Recall Flow
```
User clicks "THU HỘI" on own message
       │
       ▼
RecallAdapter.canRecall(message) → Check status, token exists
       │
       ▼
Show confirmation modal
       │
       ▼
User confirms
       │
       ▼
Retrieve recall_token from sessionStorage[message_id]
       │
       ▼
ApiClient.recallMessage(message_id, recall_token, reason)
       │
       ▼
Backend validates token, updates status to RECALLED
       │
       ▼
Realtime/Polling receives update
       │
       ▼
Update ChatStore: message.status = RECALLED
       │
       ▼
Clear sessionStorage[message_id]
       │
       ▼
Disable recall button permanently
```

#### Status Polling / Realtime Flow
```
On mount (GuestChatPage):
  1. Try Supabase Realtime subscription
  2. If fails or not configured → Start polling (5s interval)
  3. On each poll/event:
     - Fetch message status for visible messages
     - Update ChatStore with latest status
     - Deduplicate: ignore stale events (compare processed_at)
```

### State Management

#### ChatStore (Zustand-like pattern)
```typescript
interface ChatStore {
  messages: Message[];
  conversationId: string;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessageStatus: (messageId: string, status: MessageStatus, extra?: Partial<Message>) => void;
  removeMessage: (messageId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}
```

#### UploadStore
```typescript
interface UploadStore {
  uploads: Map<string, UploadState>; // key: upload_id
  
  // Actions
  addUpload: (file: File) => string; // returns upload_id
  updateProgress: (uploadId: string, progress: number) => void;
  setUploadResult: (uploadId: string, result: UploadResult) => void;
  setUploadError: (uploadId: string, error: string) => void;
  removeUpload: (uploadId: string) => void;
  retryUpload: (uploadId: string) => void;
}
```

#### RecallStore
```typescript
interface RecallStore {
  pendingRecalls: Set<string>; // message_ids being recalled
  
  // Actions
  startRecall: (messageId: string) => void;
  completeRecall: (messageId: string, success: boolean) => void;
  isRecalling: (messageId: string) => boolean;
}
```

### Type Definitions (Frontend)

```typescript
// Extended from backend contracts
type MessageStatus = 
  | 'pending'           // Just created, not yet processed
  | 'processing'        // Worker picked up, running vision/verification
  | 'awaiting_review'   // Low confidence, needs human review
  | 'posted'            // Successfully posted to ledger
  | 'rejected'          // Failed validation (duplicate, etc.)
  | 'failed'            // Processing error
  | 'recalled';         // User recalled

interface Message {
  id: string;
  conversation_id: string;
  sender_name: string;
  sender_role: 'PUBLIC' | 'MEMBER' | 'MODERATOR' | 'TREASURER';
  message_type: 'TEXT' | 'RECEIPT' | 'IMAGE';
  content: string;
  attachment_id?: string;
  status: MessageStatus;
  public_code?: string;      // CF-YYYYMMDD-XXXXXX
  transaction_id?: string;   // Linked ledger transaction
  error_message?: string;
  created_at: string;
  processed_at?: string;
  // Frontend-only
  recall_token?: string;     // Stored in sessionStorage only
  is_optimistic?: boolean;   // Not yet confirmed by backend
  upload_progress?: number;  // For images being uploaded
}

interface UploadState {
  id: string;
  file: File;
  preview_url: string;
  progress: number;      // 0-100
  status: 'pending' | 'uploading' | 'completed' | 'error';
  upload_id?: string;    // Backend upload ID
  error?: string;
}

interface MessageCreateRequest {
  conversation_id: string;
  sender_name: string;
  message_type: 'TEXT' | 'RECEIPT' | 'IMAGE';
  content: string;
  attachment_ids?: string[];
}

interface MessageCreateResponse {
  message_id: string;
  public_code: string;
  recall_token: string;    // ONLY returned once!
  status: MessageStatus;
  created_at: string;
}

interface RecallRequest {
  recall_token: string;
  reason: string;
}

interface RecallResponse {
  message_id: string;
  status: MessageStatus;
  recalled_at: string;
  reversal_transaction_id?: string;
}
```

### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/uploads` | Upload receipt image(s) |
| POST | `/api/v1/messages` | Create guest message |
| GET | `/api/v1/messages/:id` | Get message status |
| POST | `/api/v1/messages/:id/recall` | Recall message |
| GET | `/api/v1/messages` | List messages in conversation |
| GET | `/api/v1/public/fund` | Get public fund balance |
| GET | `/api/v1/public/bank-accounts` | Get bank info for guests |

### Realtime Strategy

1. **Primary**: Supabase Realtime subscription on `messages` table
   - Filter by `conversation_id`
   - Events: INSERT, UPDATE
   - On UPDATE: Compare `processed_at` to avoid stale updates

2. **Fallback**: Polling every 5 seconds
   - Fetch status for messages with status in {pending, processing, awaiting_review}
   - Stop polling for messages in terminal states (posted, rejected, failed, recalled)

3. **Hybrid**: Use both simultaneously with deduplication
   - Realtime for instant updates
   - Polling as safety net for missed events

### Security Considerations

1. **Recall Token**: 
   - Stored ONLY in `sessionStorage` (cleared on tab close)
   - Never in localStorage, URL, or logs
   - Sent only in recall request body (HTTPS)

2. **Authorization**:
   - Public message ID ≠ recall permission
   - Only sender (same session) has recall_token
   - Backend validates token hash

3. **File Upload**:
   - Validate MIME type and size client-side
   - Backend re-validates
   - No service role keys in frontend

4. **Message Status**:
   - Never auto-transition processing → posted
   - Display only backend-provided status
   - Show "Đang xử lý..." not "Đã ghi sổ"

### Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Stack composer vertically, full-width bubbles |
| Tablet | 640-1024px | Side-by-side sender info + bubble |
| Desktop | > 1024px | Max-width container, comfortable reading width |

### Accessibility Requirements

- All interactive elements: keyboard focusable, visible focus ring
- Status changes: announced via aria-live region
- Images: alt text from sender_name + "receipt image"
- Color: Not sole indicator of status (use icons + text)
- Form labels: Proper `<label for>` associations
- Error messages: Associated with inputs via aria-describedby