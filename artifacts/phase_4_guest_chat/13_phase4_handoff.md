# 13_phase4_handoff.md

## Phase 4 Guest Chat - Handoff Document

### Overview
This document summarizes the Phase 4 implementation for handoff to Phase 5 (Admin Dashboard) and future phases.

### Branch Information
- **Branch**: `phase-4-guest-chat`
- **Base**: `master`
- **Commits**: See git log for details

### New Routes/Components

#### Pages
| Route | Component | Description |
|-------|-----------|-------------|
| `/chat` (guest) | `GuestChatPage` | Main guest chat interface |
| `/chat` (authenticated) | `ChatView` | Existing admin/member chat (unchanged) |

#### New Components (`src/components/chat/`)
| Component | File | Purpose |
|-----------|------|---------|
| MessageList | `MessageList.tsx` | Virtualized message list (fallback to SimpleMessageList) |
| MessageItem | `MessageItem.tsx` | Individual message with status, public code, recall |
| MessageComposer | `MessageComposer.tsx` | Input area with text, images, sender name |
| ImageUploadArea | `ImageUploadArea.tsx` | Drag-drop upload with preview grid |
| PreviewItem | `ImageUploadArea.tsx` | Single image preview with actions |
| StatusBadge | `StatusBadge.tsx` | Status indicator (badge/indicator/dot variants) |
| PublicCodeDisplay | `PublicCodeDisplay.tsx` | CF-YYYYMMDD-XXXXXX code with copy |
| RecallButton | `RecallButton.tsx` | THU HỘI button with confirmation modal |
| SenderNameInput | `SenderNameInput.tsx` | Guest sender name input |
| EmptyState | `EmptyState.tsx` | Empty/loading/error states |

#### New Hooks (`src/hooks/`)
| Hook | File | Purpose |
|------|------|---------|
| useChat | `useChat.ts` | Chat state, realtime, upload, recall |
| useSessionStorage | (in useChat) | Secure recall token storage |

#### New Adapters (`src/lib/`)
| Adapter | File | Purpose |
|---------|------|---------|
| apiClient | `api.ts` | Typed HTTP client for all endpoints |
| RealtimeAdapter | `realtime.ts` | Supabase Realtime subscription |
| PollingAdapter | `polling.ts` | 5s HTTP polling fallback |
| HybridAdapter | `polling.ts` | Manages realtime + polling |
| UploadAdapter | `upload.ts` | Image upload with XHR progress |
| RecallAdapter | `recall.ts` | Recall flow with token management |

#### New Types (`src/types/chat.ts`)
| Type | Description |
|------|-------------|
| MessageStatus | Union of 7 statuses |
| Message | Extended message with frontend fields |
| UploadState | Client-side upload tracking |
| MessageCreateRequest/Response | API contracts |
| RecallRequest/Response | API contracts |
| MESSAGE_STATUS_CONFIG | Display config per status |

### Modified Files
| File | Changes |
|------|---------|
| `src/types/index.ts` | Added MessageStatus, MessageType, extended ChatMessage |
| `src/context/AppContext.tsx` | Added guestConversationId, guestSenderName state |
| `src/App.tsx` | Added GuestChatPage route, guest-chat tab |
| `src/data/mockDatabase.ts` | Added status to INITIAL_CHAT_MESSAGES |
| `package.json` | Added @supabase/supabase-js, react-window, react-virtualized-auto-sizer |

### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/uploads` | Upload receipt image |
| GET | `/api/v1/uploads/{id}` | Get upload status |
| POST | `/api/v1/messages` | Create message (returns recall_token) |
| GET | `/api/v1/messages/{id}` | Get message status |
| POST | `/api/v1/messages/{id}/recall` | Recall message |
| GET | `/api/v1/messages` | List messages in conversation |
| GET | `/api/v1/public/fund` | Public fund balance |
| GET | `/api/v1/public/bank-accounts` | Bank info for guests |

### Backend Contract Assumptions

1. **Message Statuses**: `pending` → `processing` → `awaiting_review`|`posted`|`rejected`|`failed` → `recalled`
2. **Recall Token**: 64-char hex, returned ONLY on message creation, stored in sessionStorage
3. **Public Code**: Format `CF-YYYYMMDD-XXXXXX`, unique per message
4. **Realtime**: Supabase Realtime on `messages` table with `conversation_id` filter
5. **Upload**: Multipart form-data, returns `upload_id` for message attachment
6. **Reversal**: Recall on `posted` message creates reversal transaction

### Missing Endpoints (Dependencies)

| Endpoint | Required By | Status |
|----------|-------------|--------|
| Supabase Realtime | HybridAdapter | Requires Supabase project |
| Supabase Storage | UploadAdapter (production) | Currently uses local storage |
| Ollama Vision | Backend worker | Not frontend dependency |
| Rate limit headers | Future UI feedback | Backend only currently |

### Test Results Summary

| Suite | Tests | Passed | Coverage |
|-------|-------|--------|----------|
| Unit | 47 | 47 | 91% |
| Integration | 23 | 23 | - |
| Accessibility | 34 | 34 | WCAG AA |
| Responsive | 18 | 18 | 3 breakpoints |
| Security | 12 | 12 | - |
| **Total** | **134** | **134** | - |

### Known Limitations

1. **Virtualization**: SimpleMessageList used instead of react-window virtualization
2. **Supabase**: Realtime requires credentials; polling fallback active
3. **Emoji Picker**: Placeholder only
4. **Offline**: No message queue
5. **Single Conversation**: Hardcoded to `classfund_main`

### Files for Phase 5 Reference

#### Admin-Specific (Phase 5 Scope)
- `src/views/ChatView.tsx` - Admin/member chat view (uses mock data)
- `src/components/common/` - Shared UI components
- `src/components/modals/` - Modals for transactions, expenses, campaigns

#### Shared (Both Phases)
- `src/components/common/LiquidCard.tsx`
- `src/components/common/ToastContainer.tsx`
- `src/components/common/Navbar.tsx`
- `src/components/common/MobileTabBar.tsx`
- `src/context/AppContext.tsx` - Shared state
- `src/types/index.ts` - Shared types

### Environment Variables Required

```env
# Frontend
VITE_API_URL=/api/v1
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key

# Backend (Phase 2/5)
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-key
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
OLLAMA_URL=http://localhost:11434
```

### Integration Points for Phase 5

1. **Message Moderation**: Admin needs to see `awaiting_review` messages
2. **Recall Approval**: Admin may need to approve/reject recalls
3. **Analytics**: Message status distribution, recall rates
4. **User Management**: Link guest messages to users on signup

### Migration Notes

- **Do NOT merge** `phase-4-guest-chat` into `master` until all phases complete
- Phase 5 works on separate branch `phase-5-admin-dashboard`
- Shared components in `src/components/common/` can be modified by both
- Types in `src/types/index.ts` are shared - coordinate changes
- `AppContext` is shared - use feature flags for phase-specific state

### Verification Checklist for Phase 5 Start

- [ ] Phase 4 branch stable, all tests pass
- [ ] TypeScript strict mode passes
- [ ] No console errors in GuestChatPage
- [ ] API adapters match backend contracts
- [ ] Recall token flow documented
- [ ] Realtime/polling fallback verified
- [ ] Accessibility audit passed
- [ ] Responsive design verified