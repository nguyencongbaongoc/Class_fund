# 11_FRONTEND_INTEGRATION.md

## Workstream I: Frontend Integration

### Current State Analysis

**Problem**: Frontend (`classfund/classfund/src/`) is entirely mock-based:
- `AppContext.tsx` manages all state in memory
- `ChatView.tsx` simulates message sending
- `UploadReceiptView.tsx` simulates AI pipeline
- No API integration with backend

**Solution**: Integrate React/TypeScript frontend with backend contracts:
- Replace mock state with API calls
- Add message status polling/realtime
- Implement recall flow with token
- Preserve existing UI components

### Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| API client | ⏳ PENDING | Need to create `src/lib/api.ts` |
| Message creation | ⏳ PENDING | `ChatView.tsx` integration |
| Status polling | ⏳ PENDING | Supabase Realtime or polling |
| Recall button | ⏳ PENDING | `ChatView.tsx` + token storage |
| Upload integration | ⏳ PENDING | `UploadReceiptView.tsx` → chat message |
| Public code display | ⏳ PENDING | Message bubble component |

### Required Frontend Changes

#### 1. API Client (`src/lib/api.ts`)
```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export async function createMessage(data: MessageCreate): Promise<MessageCreateResponse> {
  const res = await fetch(`${API_BASE}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function recallMessage(messageId: string, recallToken: string, reason: string): Promise<RecallResponse> {
  const res = await fetch(`${API_BASE}/messages/${messageId}/recall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recall_token: recallToken, reason }),
  });
  return res.json();
}

export async function getMessageStatus(messageId: string): Promise<MessageStatusResponse> {
  const res = await fetch(`${API_BASE}/messages/${messageId}`);
  return res.json();
}
```

#### 2. ChatView Integration
- Add inline photo capture (camera/file input)
- Add sender name input for guests
- Display message status badges (pending/processing/posted/recalled)
- Show public code (CF-YYYYMMDD-XXXXXX)
- Add "THU HỘI" button with recall token from sessionStorage

#### 3. UploadReceiptView Integration
- After upload, create message via API
- Link attachment_id to message
- Navigate back to chat with status updates

#### 4. Realtime Status
- Supabase Realtime subscription on `messages` table
- Or polling fallback (5s interval)

### Preserved UI Components
- `Navbar.tsx`, `MobileTabBar.tsx` - Navigation
- `LiquidGlassCard.tsx`, `LiquidCard.tsx` - Cards
- `ToastContainer.tsx` - Notifications
- `TransactionDetailModal.tsx` - Transaction details
- All liquidglass shaders/rendering

### Backend Contract Compliance
- Message lifecycle: `pending` → `processing` → `posted`/`awaiting_review`/`recalled`/`failed`
- Recall token stored in `sessionStorage` per message
- No direct financial posting from frontend
- Balance displayed from `/api/v1/public/fund`

### Status

| Task | Status | Evidence |
|------|--------|----------|
| API client | ⏳ PENDING | |
| Message creation flow | ⏳ PENDING | |
| Status display | ⏳ PENDING | |
| Recall button + token | ⏳ PENDING | |
| Upload → message link | ⏳ PENDING | |
| Realtime/polling | ⏳ PENDING | |
| UI preservation | ✅ VERIFIED | Existing components intact |