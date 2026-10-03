# 02_component_inventory.md

## Phase 4 Guest Chat - Component Inventory

### New Components (Phase 4 Scope)

| Component | File | Purpose | Dependencies |
|-----------|------|---------|--------------|
| **GuestChatPage** | `src/pages/GuestChatPage.tsx` | Main page component for guest chat route | All child components |
| **MessageList** | `src/components/chat/MessageList.tsx` | Renders list of messages with virtualization | MessageItem, EmptyState, LoadingState |
| **MessageItem** | `src/components/chat/MessageItem.tsx` | Single message bubble with status, public code, recall | StatusBadge, PublicCodeDisplay, RecallButton |
| **MessageComposer** | `src/components/chat/MessageComposer.tsx` | Input area with text, image upload, sender name | ImageUploadArea, SenderNameInput, SendButton |
| **ImageUploadArea** | `src/components/chat/ImageUploadArea.tsx` | Drag-drop/click upload with preview grid | PreviewItem, UploadAdapter |
| **PreviewItem** | `src/components/chat/PreviewItem.tsx` | Single image preview with progress, remove, retry | - |
| **StatusBadge** | `src/components/chat/StatusBadge.tsx` | Visual status indicator (icon + text) | - |
| **PublicCodeDisplay** | `src/components/chat/PublicCodeDisplay.tsx` | Shows CF-YYYYMMDD-XXXXXX code with copy button | - |
| **RecallButton** | `src/components/chat/RecallButton.tsx` | "THU HỘI" button with confirmation modal | RecallAdapter, ConfirmModal |
| **SenderNameInput** | `src/components/chat/SenderNameInput.tsx` | Input for guest sender name (required for PUBLIC) | - |
| **EmptyState** | `src/components/chat/EmptyState.tsx` | Empty chat illustration + CTA | - |
| **LoadingState** | `src/components/chat/LoadingState.tsx` | Skeleton loading for message list | - |

### Reused Components (Existing)

| Component | File | Usage in Phase 4 |
|-----------|------|------------------|
| **LiquidCard** | `src/components/common/LiquidCard.tsx` | Wrapper for MessageList, Composer |
| **ToastContainer** | `src/components/common/ToastContainer.tsx` | Global notifications |
| **Navbar** | `src/components/common/Navbar.tsx` | Navigation (unchanged) |
| **MobileTabBar** | `src/components/common/MobileTabBar.tsx` | Bottom nav on mobile (unchanged) |

### Modified Components (Existing)

| Component | File | Changes |
|-----------|------|---------|
| **ChatView** | `src/views/ChatView.tsx` | Refactor to use new components; add guest mode |
| **UploadReceiptView** | `src/views/UploadReceiptView.tsx` | Integrate with message creation flow |
| **AppContext** | `src/context/AppContext.tsx` | Add guest-specific state/actions |
| **types/index.ts** | `src/types/index.ts` | Add new Phase 4 types |

### New Hooks

| Hook | File | Purpose |
|------|------|---------|
| **useChat** | `src/hooks/useChat.ts` | ChatStore interface + realtime/polling |
| **useUpload** | `src/hooks/useUpload.ts` | UploadStore interface + upload logic |
| **useRecall** | `src/hooks/useRecall.ts` | RecallStore interface + recall logic |
| **useSessionStorage** | `src/hooks/useSessionStorage.ts` | Secure recall token storage |

### New Adapters (Integration Layer)

| Adapter | File | Purpose |
|---------|------|---------|
| **apiClient** | `src/lib/api.ts` | HTTP client with typed methods |
| **realtimeAdapter** | `src/lib/realtime.ts` | Supabase Realtime subscription |
| **pollingAdapter** | `src/lib/polling.ts` | Polling fallback for status updates |
| **uploadAdapter** | `src/lib/upload.ts` | Image upload with progress |
| **recallAdapter** | `src/lib/recall.ts` | Recall flow with token management |

### New Types

| Type | File | Description |
|------|------|-------------|
| **MessageStatus** | `src/types/chat.ts` | Union of all message statuses |
| **Message** | `src/types/chat.ts` | Extended message with frontend fields |
| **UploadState** | `src/types/chat.ts` | Client-side upload tracking |
| **MessageCreateRequest** | `src/types/chat.ts` | Request payload for create message |
| **MessageCreateResponse** | `src/types/chat.ts` | Response with recall_token |
| **RecallRequest/Response** | `src/types/chat.ts` | Recall API types |

### Component Specifications

#### 1. GuestChatPage
```tsx
// Route: /chat (public access)
// Props: none (reads conversation_id from URL or context)
// State: owns ChatStore, UploadStore, RecallStore
// Renders: MessageList + MessageComposer
```

#### 2. MessageList
```tsx
// Props: { messages: Message[], isLoading: boolean }
// Features:
// - Virtualized list (react-window) for performance
// - Auto-scroll to bottom on new messages
// - Sticky pinned message at top
// - EmptyState when messages.length === 0
// - LoadingState while initial fetch
```

#### 3. MessageItem
```tsx
// Props: { message: Message, isOwn: boolean }
// Layout:
// [SenderInfo] [StatusBadge] [PublicCodeDisplay]
// [MessageBubble]
// [RecallButton] (if isOwn && canRecall)
// Features:
// - Memoized to prevent re-render losses
// - Click receipt → navigate to detail
// - Long press → context menu (copy, recall)
```

#### 4. MessageComposer
```tsx
// Props: { onSend: (data: MessageCreateRequest) => void, isSending: boolean }
// State: local text, images[], senderName
// Validation:
// - Requires text OR images
// - Requires senderName if currentUser.role === 'PUBLIC'
// - Max 5 images, 5MB each, JPEG/PNG/WebP
// Features:
// - Debounced senderName save to localStorage
// - Enter to send, Shift+Enter for newline
// - Disabled while sending
```

#### 5. ImageUploadArea
```tsx
// Props: { images: UploadState[], onChange: (images: UploadState[]) => void, maxFiles: 5 }
// Features:
// - Click to open file dialog
// - Drag & drop zone
// - Preview grid (2 columns mobile, 4 desktop)
// - Upload progress per image
// - Remove button per image
// - Retry button on error
// - Shows total upload progress
```

#### 6. PreviewItem
```tsx
// Props: { upload: UploadState, onRemove: () => void, onRetry: () => void }
// States:
// - pending: shows file icon, "Waiting..."
// - uploading: progress bar, cancel button
// - completed: thumbnail, checkmark
// - error: warning icon, error message, retry button
```

#### 7. StatusBadge
```tsx
// Props: { status: MessageStatus }
// Mapping:
const STATUS_CONFIG = {
  pending: { label: 'Đang chờ', icon: Clock, color: 'neutral' },
  processing: { label: 'Đang xử lý', icon: Loader2, color: 'sky', animate: true },
  awaiting_review: { label: 'Cần duyệt', icon: AlertTriangle, color: 'amber' },
  posted: { label: 'Đã ghi sổ', icon: CheckCircle2, color: 'emerald' },
  rejected: { label: 'Từ chối', icon: XCircle, color: 'rose' },
  failed: { label: 'Lỗi', icon: AlertCircle, color: 'rose' },
  recalled: { label: 'Đã thu hồi', icon: RotateCcw, color: 'neutral' },
}
// Never shows "Thành công" or "Đã xác nhận" for non-posted states
```

#### 8. PublicCodeDisplay
```tsx
// Props: { code?: string }
// Shows: "Mã tham chiếu: CF-20261003-A1B2C3"
// Copy button → copies to clipboard, shows toast
// Only renders if code exists
```

#### 9. RecallButton
```tsx
// Props: { messageId: string, canRecall: boolean, onRecall: () => void }
// Logic:
// - Only renders if canRecall === true
// - canRecall = (status in {pending, processing, awaiting_review} || 
//                (status === 'posted' && has_reversal_capability)) 
//                && recall_token exists in sessionStorage
// - Click → ConfirmModal("Bạn có chắc muốn thu hồi tin nhắn này?")
// - Confirm → onRecall()
// - After success: hides permanently
```

#### 10. SenderNameInput
```tsx
// Props: { value: string, onChange: (v: string) => void, required: boolean }
// Features:
// - Prefilled from localStorage['guest_sender_name']
// - Required indicator (*)
// - Validation: min 2 chars, max 120 chars
// - Saves to localStorage on blur
```

### File Structure (New)

```
src/
├── lib/
│   ├── api.ts              # API client
│   ├── realtime.ts         # Realtime adapter
│   ├── polling.ts          # Polling adapter
│   ├── upload.ts           # Upload adapter
│   └── recall.ts           # Recall adapter
├── hooks/
│   ├── useChat.ts          # Chat state + realtime
│   ├── useUpload.ts        # Upload state + logic
│   ├── useRecall.ts        # Recall state + logic
│   └── useSessionStorage.ts # Secure storage
├── types/
│   └── chat.ts             # Phase 4 type definitions
├── components/
│   └── chat/
│       ├── MessageList.tsx
│       ├── MessageItem.tsx
│       ├── MessageComposer.tsx
│       ├── ImageUploadArea.tsx
│       ├── PreviewItem.tsx
│       ├── StatusBadge.tsx
│       ├── PublicCodeDisplay.tsx
│       ├── RecallButton.tsx
│       ├── SenderNameInput.tsx
│       ├── EmptyState.tsx
│       ├── LoadingState.tsx
│       └── index.ts        # Barrel export
├── pages/
│   └── GuestChatPage.tsx   # New route page
└── views/
    └── ChatView.tsx        # Modified (delegate to GuestChatPage)
```

### Migration Notes

1. **ChatView.tsx**: Keep as admin/member view, create GuestChatPage for PUBLIC role
2. **UploadReceiptView.tsx**: After successful upload, redirect to GuestChatPage with message_id for status tracking
3. **AppContext.tsx**: Add `guestConversationId`, `guestSenderName` state
4. **Routing**: Add `/chat` route for public, keep existing chat tab for authenticated users

### Testing Components

| Test File | Component Under Test |
|-----------|---------------------|
| `MessageList.test.tsx` | MessageList |
| `MessageItem.test.tsx` | MessageItem |
| `MessageComposer.test.tsx` | MessageComposer |
| `ImageUploadArea.test.tsx` | ImageUploadArea |
| `PreviewItem.test.tsx` | PreviewItem |
| `StatusBadge.test.tsx` | StatusBadge |
| `RecallButton.test.tsx` | RecallButton |
| `useChat.test.ts` | useChat hook |
| `useUpload.test.ts` | useUpload hook |
| `useRecall.test.ts` | useRecall hook |
| `apiClient.test.ts` | apiClient |
| `realtimeAdapter.test.ts` | realtimeAdapter |
| `pollingAdapter.test.ts` | pollingAdapter |