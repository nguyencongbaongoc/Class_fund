# PHASE 0 ADDENDUM B — GUEST CHAT PHOTO MESSAGE RECALL AUDIT

## Executive Summary
**Status: PARTIALLY_COMPATIBLE** — The frontend has a sophisticated chat UI with photo upload and mock message sending, but **zero backend integration**. No guest authentication, no message persistence, no recall tokens, no financial transaction linkage. The mock implementation simulates the desired flow but lacks all security and persistence mechanisms.

---

## 1. EXISTING GUEST CHAT IMPLEMENTATION

### Frontend ChatView (`src/views/ChatView.tsx`)

**Current Flow (Mock Only)**:
```typescript
// Lines 19-30: handleSend
const handleSend = (e: React.FormEvent) => {
  e.preventDefault();
  if (!inputText.trim()) return;
  sendChatMessage(inputText, isModAnnouncement ? 'ANNOUNCEMENT' : 'TEXT', isModAnnouncement);
  setInputText('');
  setIsModAnnouncement(false);
}
```

**Message Creation** (`AppContext.tsx:447-464`):
```typescript
const sendChatMessage = (content: string, type: 'TEXT' | 'ANNOUNCEMENT' = 'TEXT', isPinned: boolean = false) => {
  const newMsg: ChatMessage = {
    id: 'msg_' + Date.now(),           // ⚠️ Timestamp-based, not UUID
    sender_id: currentUser.id,         // Mock user ID
    sender_name: currentUser.name,     // Mock user name
    sender_role: currentUser.role,     // Mock role
    message_type: currentUser.role === 'MODERATOR' || currentUser.role === 'TREASURER' ? type : 'TEXT',
    content: content.trim(),
    is_pinned: isPinned,
    created_at: timeStr,               // "HH:mm" only, no date
  };
  setChatMessages((prev) => [newMsg, ...prev]);
};
```

### Guest Sender Model: **NOT IMPLEMENTED**

| Requirement | Current State | Gap |
|-------------|---------------|-----|
| No registration/login | ❌ Only mock role switching | Complete gap |
| Photo + full name as identity | ❌ Photo only in receipt upload, not chat | Complete gap |
| Sender identifier | ❌ Mock `currentUser.id` | Complete gap |
| Message ownership | ❌ Mock `sender_id` | Complete gap |
| Conversation identity | ❌ Single global chat | Complete gap |
| Uploaded image | ❌ Only in receipt upload, not chat | Complete gap |
| Timestamp | ⚠️ "HH:mm" only | No date, no ISO format |

### Evidence: ChatView Photo Button (Lines 190-197)
```tsx
<button
  type="button"
  onClick={() => setCurrentTab('upload')}
  className="..."
  title="Đính kèm ảnh biên lai"
>
  <ImageIcon className="w-4 h-4" />
</button>
```
**Finding**: Photo attachment navigates to Upload tab — **no inline photo capture in chat**.

---

## 2. EXISTING PHOTO UPLOAD IMPLEMENTATION

### UploadReceiptView (`src/views/UploadReceiptView.tsx`)

**Current Flow**:
1. Drag-drop or file input → `handleFileChange` (Lines 66-75)
2. Preview via `URL.createObjectURL()` (Line 70)
3. Enter uploader name (Line 276-282)
4. Simulated 4-step AI pipeline (Lines 77-181)
5. Creates local `LedgerEntry` via `addLedgerEntry` (Lines 129-172)

**Photo Storage**: **Local only** — `URL.createObjectURL()` creates blob URL, no persistence.

**File Validation** (Lines 21-27):
```typescript
const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (file) {
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  }
};
```
- No file type check in frontend (backend allows: JPEG, PNG, WebP)
- No file size check in frontend (backend: 10MB)
- No EXIF handling
- No Supabase Storage integration

### Backend Upload Endpoint (`app/api/routes/uploads.py:18-49`)

```python
@router.post("", response_model=UploadOut, status_code=201)
async def upload_receipt(file: UploadFile = File(...), uploader_name: str = Form(...), db: Session = Depends(get_db)):
    # Validates MIME: image/jpeg, image/png, image/webp
    # Validates size: MAX_UPLOAD_MB (10MB)
    # SHA-256 file hash for duplicate detection
    # Stores to local filesystem: ./storage/uploads/{uuid}.{ext}
    # Returns UploadOut with id, uploader_name, filename, status, created_at
```

**Gap**: Frontend doesn't call this endpoint. No Supabase Storage.

---

## 3. EXISTING FULL-NAME CAPTURE

### ChatView: **NO FULL NAME INPUT**
- Uses `currentUser.name` from mock role switching
- No input field for guest name in chat

### UploadReceiptView: **HAS FULL NAME INPUT** (Lines 276-282)
```tsx
<label>Tên người nộp / chuyển khoản *</label>
<input
  type="text"
  value={uploaderName}
  onChange={(e) => setUploaderName(e.target.value)}
  placeholder="VD: Nguyễn Văn An"
/>
```
**Finding**: Full name captured only in receipt upload, not in chat messages.

---

## 4. EXISTING MESSAGE ID MECHANISM

### Frontend (`AppContext.tsx:452`)
```typescript
const newMsg: ChatMessage = {
  id: 'msg_' + Date.now(),  // ⚠️ NOT UUID, NOT CRYPTOGRAPHICALLY SAFE
  // ...
};
```

### Backend ChatMessage Model (`app/models/models.py:236-245`)
```python
class ChatMessage(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    sender_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sender_role: Mapped[str] = mapped_column(String(40))
    message_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    attachment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ledger_entry_id: Mapped[str | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

**Finding**: Backend uses UUID (`uuid4_str`), frontend uses timestamp. **Mismatch**.

### Message ID Traceability: **NOT IMPLEMENTED**
- No `message_id` → `transaction_id` linkage in mock
- Backend has `ledger_entry_id` FK on `chat_messages` but unused in mock

---

## 5. EXISTING PUBLIC MESSAGE CODE MECHANISM

### Frontend: **NONE**
- No human-readable code displayed
- Mock `transaction_code` exists in `LedgerEntry` (e.g., "VCB8921734") but not for chat messages

### Backend: **NONE FOR CHAT**
- `transactions` have `transaction_code` (bank transaction code)
- `chat_messages` have no public code field

**Gap**: No `public_code` like `CF-20261003-A8F42C` for messages.

---

## 6. EXISTING QWEN PROCESSING LINKAGE

### Current AI Pipeline: **TESSERACT ONLY** (No Qwen/Ollama)

**Frontend Simulation** (`UploadReceiptView.tsx:77-181`):
```typescript
const startProcessing = () => {
  // Simulates 4 steps with timeouts
  // Step 1: Upload (800ms)
  // Step 2: AI OCR (1000ms)
  // Step 3: Anti-Duplicate (1000ms)
  // Step 4: Result
  
  // Duplicate check against LOCAL ledgerEntries
  const isDuplicate = ledgerEntries.some(...);
  
  // Creates local LedgerEntry with ai_confidence
  addLedgerEntry({ ai_confidence: 99.4, ... });
};
```

**Backend AI Internal Endpoint** (`app/api/routes/ai_internal.py:24-52`):
```python
@router.post("/uploads/{upload_id}/result")
def receive_ai_result(upload_id: str, body: AIResultIn, idempotency_key: str = Header(...), db: Session = Depends(get_db)):
    # Calls verify_and_post_from_ai()
    # Returns {posted, transaction_id}
```

**Qwen Integration**: **ZERO** — No Ollama client, no vision model calls.

**Message ID Retention**: **NOT IMPLEMENTED** — No `message_id` field in `AIResultIn` or `VerificationResult`.

---

## 7. EXISTING FINANCIAL TRANSACTION LINKAGE

### Backend Relationships (Verified in Models)

| Relationship | Implementation |
|--------------|----------------|
| `ChatMessage.ledger_entry_id` → `LedgerEntry.id` | FK, nullable (Line 244) |
| `LedgerEntry.transaction_id` → `Transaction.id` | FK, Unique (Line 187) |
| `Transaction.id` → `LedgerEntry.transaction_id` | 1:1 (Line 187) |
| `Transaction.upload_id` → `Upload.id` | FK, nullable (Line 174) |
| `Upload.id` → `ExtractedTransaction.upload_id` | Unique (Line 149) |

### Frontend Mock Linkage (`AppContext.tsx:279-303`)
```typescript
if (fullEntry.source === 'IMAGE') {
  setChatMessages((prev) => [{
    receipt_data: {
      entry_id: entryId,           // Links to ledger entry
      amount: fullEntry.amount,
      transaction_code: fullEntry.transaction_code,
      image_url: fullEntry.image_url,
      status: fullEntry.status,
      // ...
    },
    // ...
  }, ...prev]);
}
```

**Finding**: Backend schema supports `ChatMessage ↔ LedgerEntry ↔ Transaction` linkage. **Frontend mock simulates this but no persistence**.

---

## 8. EXISTING RECALL/REVERT FUNCTIONALITY

### Frontend Recall (`AppContext.tsx:310-422`)
```typescript
const revertTransaction = (transactionId: string, reason: string): boolean => {
  // 1. Finds original entry
  // 2. Creates REVERT LedgerEntry with original_entry_id linkage
  // 3. Marks original status = REVERTED
  // 4. Updates student roster (unmarks paid)
  // 5. Updates campaign stats
  // 6. Adds audit log
  // 7. Adds system chat message
  // 8. Returns true
};
```

**Implementation Quality**: **EXCELLENT** — Proper reversal with immutable original, audit trail, cascade updates.

### Backend Reversal (`app/services/ledger.py:121-169`)
```python
def post_revert(db: Session, *, original: Transaction, actor_id: str, reason: str, idempotency_key: str | None = None):
    # FOR UPDATE locks on original transaction + ledger entry
    # Prevents reverting REVERT transactions
    # Prevents double-revert (checks original_entry_id)
    # Creates REVERT transaction + ledger entry
    # Marks original status = REVERTED
    # Audit log
```

**Critical Gap**: **FRONTEND RECALL ONLY WORKS ON MOCK DATA** — No API call to backend `/fund/transactions/{id}/revert`.

### Recall Button UI (`LedgerView.tsx:306-311`, `DashboardView.tsx` — not visible in mock)
- `LedgerView` shows "Chi tiết ›" but no revert button in mock
- `TransactionDetailModal` likely has revert (not read)

---

## 9. RECALL AFTER QWEN PROCESSED (POSTED)

### Current Behavior (Mock)
- `revertTransaction` works on any `VERIFIED` entry
- Creates reversal, restores balance, updates all dependent state

### Backend Behavior (Verified)
- `post_revert` requires `OWNER_TREASURER` role
- Idempotency key required
- Reverses balance correctly via `LedgerEntry.REVERT` type

**Gap**: No guest user can call this — requires authentication.

---

## 10. RECALL BEFORE QWEN PROCESSING (PENDING)

### Current State: **NOT IMPLEMENTED**
- No `PENDING`/`PROCESSING` message states in chat
- Upload has `UploadStatus.PENDING`/`PROCESSING` but not linked to chat messages
- Worker would need to check message status before posting

### Required Logic (Not Present):
```python
# Before financial posting
if message.status == 'RECALLED':
    return  # Don't post
```

---

## 11. RECALL DURING PROCESSING (RACE CONDITION)

### Current: **NO PROTECTION**
- No lease mechanism
- No atomic state check before posting
- Celery worker has no recall awareness

### Required (Hybrid Architecture):
```sql
-- Atomic check before posting
UPDATE messages
SET status = 'processing'
WHERE id = $1 AND status = 'pending' AND recall_token IS NULL
RETURNING *;
```

---

## 12. RECALL AFTER POSTING (COMPENSATING TRANSACTION)

### Current: **SUPPORTED IN BACKEND, NOT IN FRONTEND/CHAT**
- Backend `post_revert` creates proper reversal
- Frontend `revertTransaction` simulates it
- **No chat message → transaction linkage for guest users**

---

## 13. MULTIPLE RECALL ATTEMPTS

### Backend: **PROTECTED**
```python
# ledger.py:134-138
already = db.execute(select(LedgerEntry).where(
    LedgerEntry.original_entry_id == original_entry.id,
    LedgerEntry.type == LedgerType.REVERT,
)).scalar_one_or_none()
if already:
    raise HTTPException(409, "Transaction has already been reverted")
```

### Frontend: **PROTECTED IN MOCK**
```typescript
if (original.status === 'REVERTED') {
  addToast({ type: 'warning', title: 'Cảnh báo', description: 'Giao dịch này đã được thu hồi trước đó.' });
  return false;
}
```

---

## 14. MESSAGE STATUS MODEL

### Frontend (`src/types/index.ts:13`)
```typescript
export type TransactionStatus = 'PENDING' | 'VERIFIED' | 'NEEDS_REVIEW' | 'DUPLICATE' | 'REJECTED' | 'REVERTED';
```
**Used for**: Ledger entries and receipt status.

### Chat Messages: **NO STATUS FIELD**
```typescript
// ChatMessage type (Line 65-84)
export interface ChatMessage {
  // No status field!
  id, sender_id, sender_name, sender_role, message_type, content, receipt_data?, is_pinned?, created_at
}
```

### Upload Status (Backend): **COMPLETE**
```python
class UploadStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
```

**Gap**: Chat messages need status field matching upload/processing states.

---

## 15. WHO CAN RECALL? (GUEST OWNERSHIP MODEL)

### Current: **NO SECURE MECHANISM**

| Mechanism | Implemented? | Evidence |
|-----------|--------------|----------|
| User account/login | ❌ | Mock role switching only |
| Session-based ownership | ❌ | `currentUser` is global mock |
| Recall token | ❌ | Not exist |
| Browser fingerprint | ❌ | Not implemented |
| Message ID only | ❌ | Would allow anyone to revert |

### Frontend Recall (`AppContext.tsx:310-315`)
```typescript
const revertTransaction = (transactionId: string, reason: string): boolean => {
  const original = ledgerEntries.find((e) => e.id === transactionId);
  // No ownership check! Any role can revert in mock.
```

**Critical Finding**: **ZERO AUTHORIZATION** for recall in current implementation.

---

## 16. RECALL TOKEN

### Current: **NOT IMPLEMENTED**

| Component | Exists? |
|-----------|---------|
| Private recall token per message | ❌ |
| Token stored in frontend | ❌ |
| Token validated on recall | ❌ |
| Token separate from public code | ❌ |

---

## 17. UI REQUIREMENTS AUDIT

### Current Chat UI (`ChatView.tsx`)

**Has**:
- ✅ Message input with send button
- ✅ Photo button (navigates to Upload tab)
- ✅ MOD announcement toggle (role-gated)
- ✅ Message bubbles with receipt preview
- ✅ Pinned announcements
- ✅ Sender name, role badge, timestamp

**Missing for Guest Flow**:
- ❌ Photo capture/selection inline
- ❌ Full name input field
- ❌ Message status display (pending/processing/posted)
- ❌ Public message code display
- ❌ Recall/THU HỒI button on own messages
- ❌ Ownership verification for recall

### Current Upload UI (`UploadReceiptView.tsx`)

**Has for Receipt**:
- ✅ Photo drag-drop + preview
- ✅ Full name input
- ✅ Transaction code display (AI extracted)
- ✅ Status badges (VERIFIED/NEEDS_REVIEW/DUPLICATE)
- ✅ Simulated AI pipeline steps

**Missing**:
- ❌ Integration with chat message
- ❌ Recall button
- ❌ Guest identity persistence

---

## 18. PUBLIC CHAT VS ADMIN CHAT

### Current Separation: **ROLE-BASED UI ONLY**

| Feature | Guest/Member | Moderator/Treasurer | Admin (Not Implemented) |
|---------|--------------|---------------------|------------------------|
| Send TEXT | ✅ | ✅ | ✅ |
| Send ANNOUNCEMENT | ❌ | ✅ | ✅ |
| Send RECEIPT | ✅ (via Upload) | ✅ | ✅ |
| View all messages | ✅ | ✅ | ✅ |
| View AI extraction | ❌ | ❌ | ❌ |
| Pending queue | ❌ | ❌ | ❌ |
| Financial transactions | ❌ | ✅ (fund tab) | ✅ |
| Recall/Revert | ❌ (mock only) | ✅ (mock only) | ❌ |
| Audit logs | ❌ | ❌ | ❌ |
| Worker status | ❌ | ❌ | ❌ |
| Member management | ❌ | ✅ (campaign) | ✅ |

**Finding**: No true admin interface — only role-gated UI elements in mock.

---

## 19. DATABASE AUDIT: MISSING RELATIONSHIPS

### Current Schema vs. Required

| Required | Current | Gap |
|----------|---------|-----|
| `messages.sender_name` | ❌ `ChatMessage.sender_name` exists | OK but nullable |
| `messages.sender_photo` | ❌ | Missing |
| `messages.message_id` | ⚠️ `ChatMessage.id` UUID | OK type, but no chat integration |
| `messages.public_code` | ❌ | Missing |
| `messages.status` | ❌ | Missing |
| `messages.recall_status` | ❌ | Missing |
| `messages.recall_token_hash` | ❌ | Missing |
| `messages.transaction_id` | ⚠️ `ChatMessage.ledger_entry_id` → LedgerEntry | Indirect |
| `financial_transactions.message_id` | ❌ | Missing |
| `financial_transactions.reversal_transaction_id` | ⚠️ `LedgerEntry.original_entry_id` | On ledger, not transaction |
| `ledger_entries.balance_before` | ❌ | Missing (computed) |
| `ledger_entries.balance_after` | ❌ | Missing (computed) |

**Finding**: Backend has strong financial linkage (`Transaction ↔ LedgerEntry ↔ ChatMessage` via `ledger_entry_id`) but **missing guest message fields and direct message→transaction link**.

---

## 20. IDEMPOTENCY REQUIREMENT

### Current Backend: **STRONG**
- `IdempotencyKey` table with request fingerprint
- `verify_and_post_from_ai` checks existing transaction by `upload_id`
- Unique constraint on `(bank_account_id, transaction_code)`

### Current Frontend: **NONE**
- No idempotency key generation for chat messages
- Mock `addLedgerEntry` uses timestamp-based ID

### Gap: Guest message needs idempotency key
```typescript
// Required: Generate on message creation
const idempotencyKey = `msg_${messageId}_${Date.now()}`;
```

---

## 21. AUDIT LOG REQUIREMENT

### Current Backend: **COMPREHENSIVE** (`app/services/audit.py`)
```python
def write_audit(db, actor_id, action, entity_type, entity_id, before, after, ip):
    db.add(AuditLog(...))
```

**Logged Actions** (from code):
- `LOGIN`, `LOGIN_FAILED`, `LOGOUT`
- `OPENING_BALANCE_UPDATE`
- `BANK_ACCOUNT_CREATE`
- `LEDGER_POST` (every transaction)
- `LEDGER_REVERT` (every reversal)
- `STUDENT_CREATE`, `ROSTER_IMPORT`
- `CAMPAIGN_CREATE`, `CAMPAIGN_UPDATE`
- `STUDENT_CREATE`, `ROSTER_IMPORT`

### Missing for Guest Chat:
- `MESSAGE_CREATED` (guest)
- `AI_PROCESSING_STARTED`
- `AI_EXTRACTION_COMPLETED`
- `TRANSACTION_CREATED` (from message)
- `RECALL_REQUESTED` (guest)
- `TRANSACTION_REVERSED` (from message recall)
- `MESSAGE_RECALLED`

### Actor Distinction: **NOT IMPLEMENTED**
- No `guest_sender` actor type
- `actor_id` nullable but always user ID or NULL

---

## 22. MISSING CAPABILITIES SUMMARY

| Capability | Status | Effort |
|------------|--------|--------|
| Guest authentication (photo + name) | ❌ Missing | High |
| Inline photo capture in chat | ❌ Missing | Medium |
| UUID message IDs | ❌ Missing | Low |
| Public message codes (CF-...) | ❌ Missing | Low |
| Message status states | ❌ Missing | Medium |
| Recall token generation | ❌ Missing | High |
| Recall authorization | ❌ Missing | Critical |
| Recall before/during/after processing logic | ❌ Missing | High |
| Guest message → transaction linkage | ❌ Missing | High |
| Idempotency for guest messages | ❌ Missing | Medium |
| Audit logs for guest actions | ❌ Missing | Medium |
| Admin review queue UI | ❌ Missing | High |
| Worker recall awareness | ❌ Missing | High |
| Supabase Storage for photos | ❌ Missing | Medium |
| Realtime status updates | ❌ Missing | Medium |

---

## 23. CRITICAL RISKS

| Risk | Severity | Evidence |
|------|----------|----------|
| **Anyone can revert any transaction** | CRITICAL | `revertTransaction` has no ownership check (AppContext.tsx:310) |
| **Message ID not cryptographically unique** | HIGH | `'msg_' + Date.now()` (AppContext.tsx:452) |
| **No guest recall authorization** | CRITICAL | No token, no session, no ownership |
| **Race condition: recall during processing** | HIGH | No lease, no atomic state check |
| **AI output directly modifies balance in mock** | HIGH | `addLedgerEntry` called directly from simulated AI |
| **No idempotency for guest messages** | HIGH | Timestamp-based IDs, no deduplication |
| **Photo not persisted** | MEDIUM | `URL.createObjectURL()` only |
| **Audit log missing guest actions** | MEDIUM | No `MESSAGE_CREATED`, `RECALL_REQUESTED` |
| **Message status not tracked** | MEDIUM | ChatMessage type lacks status field |

---

## 24. EVIDENCE MAP (Exact Files/Lines)

| Feature | File | Lines |
|---------|------|-------|
| Chat message send | `src/views/ChatView.tsx` | 19-30 |
| Mock message creation | `src/context/AppContext.tsx` | 447-464 |
| Mock revert transaction | `src/context/AppContext.tsx` | 310-422 |
| Receipt upload UI | `src/views/UploadReceiptView.tsx` | 1-393 |
| Simulated AI pipeline | `src/views/UploadReceiptView.tsx` | 77-181 |
| Photo upload handling | `src/views/UploadReceiptView.tsx` | 66-75 |
| Full name input (upload) | `src/views/UploadReceiptView.tsx` | 276-282 |
| Photo button in chat | `src/views/ChatView.tsx` | 190-197 |
| Message ID generation | `src/context/AppContext.tsx` | 452 |
| ChatMessage type | `src/types/index.ts` | 65-84 |
| TransactionStatus type | `src/types/index.ts` | 13 |
| Backend ChatMessage model | `app/models/models.py` | 236-245 |
| Backend Upload model | `app/models/models.py` | 104-115 |
| Backend Transaction model | `app/models/models.py` | 163-181 |
| Backend LedgerEntry model | `app/models/models.py` | 184-199 |
| Backend revert logic | `app/services/ledger.py` | 121-169 |
| Backend AI internal endpoint | `app/api/routes/ai_internal.py` | 24-52 |
| Backend upload endpoint | `app/api/routes/uploads.py` | 18-49 |
| Backend fund revert endpoint | `app/api/routes/fund.py` | 97-103 |
| AI VerificationService | `ai/verification/service.py` | 32-109 |
| AI OCR service | `ai/ocr/service.py` | 167-220 |
| AI Worker queue | `ai/worker/queue.py` | 160-211 |

---

## 25. RECOMMENDED IMPLEMENTATION SEQUENCE

### Phase 1: Foundation (Guest Identity & Message Persistence)
1. Add `sender_photo`, `status`, `public_code`, `recall_token_hash`, `transaction_id` to `messages` table
2. Create `recall_tokens` table (or add to messages)
3. Implement guest message insert with token generation
4. Frontend: Inline photo capture + name input in ChatView

### Phase 2: Message ID & Codes
1. Frontend: Generate UUID v4 for `message_id` (not timestamp)
2. Backend: Generate `public_code` = `CF-{YYYYMMDD}-{short_uuid}`
2. Display code in message bubble

### Phase 3: Status & Realtime
1. Add status enum: `pending` | `processing` | `extracted` | `awaiting_review` | `posted` | `recalled` | `rejected` | `failed`
2. Supabase Realtime subscription for status changes
3. Frontend status badges in ChatView

### Phase 4: Recall Token & Authorization
1. Generate cryptographically secure recall token per message (32 bytes)
2. Store hash in DB (`recall_token_hash` = SHA-256(token))
3. Return token to sender only (in message response)
4. Frontend: Store token in sessionStorage (per-message)
5. Recall endpoint: `POST /messages/{id}/recall` with token in header/body

### Phase 5: Worker Integration
1. Worker claims message: atomic `UPDATE ... FOR UPDATE SKIP LOCKED`
2. Before financial posting: re-check `status != 'recalled'`
3. Pass `message_id` through AI → backend validation
4. On recall during processing: worker checks status, aborts if recalled

### Phase 6: Financial Linkage
1. Backend: Add `message_id` to `transactions` table
2. `verify_and_post_from_ai` accepts `message_id`, sets on transaction
3. `ChatMessage.ledger_entry_id` populated on post
4. Recall endpoint calls `post_revert` with idempotency key

### Phase 7: Double-Recall Protection
1. Backend `post_revert` already prevents double-revert
2. Frontend: Disable recall button if `recall_status = 'recalled'`
3. Message status `recalled` prevents further actions

### Phase 8: Admin Interface
1. Admin chat view: all messages, filter by status
2. AI extraction display for `awaiting_review`
3. Manual approve/reject buttons
4. Worker status dashboard

---

## 26. CONFIDENCE ASSESSMENT

- **Verified**: All frontend mock implementations, backend schemas, reversal logic, AI pipeline structure
- **Partially Verified**: Database linkage capabilities (schema supports but not wired)
- **Assumed**: Supabase Realtime can handle message status updates
- **Not Verified**: Actual guest recall token security, race condition handling under load, Ollama vision accuracy for Vietnamese receipts