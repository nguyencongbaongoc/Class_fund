# 12_known_limitations.md

## Phase 4 Guest Chat - Known Limitations

### Current Limitations

#### 1. Virtualized Message List
**Issue**: `react-window` types conflict with `react-virtualized-auto-sizer`
**Impact**: Using `SimpleMessageList` (non-virtualized) instead of `MessageList`
**Workaround**: Works for < 200 messages; virtualization needed for scale
**Fix**: Resolve type definitions or use alternative virtualization library

#### 2. Supabase Realtime Dependency
**Issue**: Realtime updates require Supabase project with credentials
**Impact**: Without credentials, falls back to 5-second polling
**Status**: Expected behavior; polling is functional fallback
**Required**: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY environment variables

#### 3. Emoji Picker Placeholder
**Issue**: Emoji button shows placeholder message only
**Impact**: Users cannot insert emojis via picker
**Workaround**: Users can use system emoji picker (Win+., Cmd+Ctrl+Space)
**Future**: Implement emoji-mart or similar library

#### 4. No Offline Message Queue
**Issue**: Messages sent offline are lost
**Impact**: Guest must be online to send messages
**Future**: Implement IndexedDB queue with background sync

#### 5. Single Conversation
**Issue**: Hardcoded to `classfund_main` conversation
**Impact**: Cannot support multiple chat rooms/channels
**Future**: Add conversation selector, URL-based routing

#### 6. No Message Editing
**Issue**: Users cannot edit sent messages
**Impact**: Typos require recall + resend
**Future**: Add edit capability with edit history

#### 7. No Threaded Replies
**Issue**: Flat message list only
**Impact**: Conversations can become hard to follow
**Future**: Add reply-to-message threading

#### 8. Limited File Preview
**Issue**: Only images supported; no PDF/document preview
**Impact**: Users cannot preview non-image attachments
**Future**: Add file type icons, generic preview for documents

#### 9. No Push Notifications
**Issue**: No browser push notifications for status changes
**Impact**: Users must keep tab open for updates
**Future**: Implement Web Push API with service worker

#### 10. No Message Search
**Issue**: Cannot search message history
**Impact**: Hard to find old messages
**Future**: Add search with backend indexing

#### 11. No Read Receipts
**Issue**: No indication if others have seen messages
**Impact**: Unclear if message was viewed
**Future**: Add read status with privacy controls

#### 12. No Message Translation
**Issue**: Messages only in Vietnamese
**Impact**: Non-Vietnamese speakers cannot understand
**Future**: Integrate translation API

#### 13. Recall Token in sessionStorage Only
**Issue**: Token lost when tab closed
**Impact**: Cannot recall messages after browser restart
**Security**: Intentional - prevents token theft
**Future**: Option to save token securely (encrypted localStorage)

#### 14. No Rate Limiting UI
**Issue**: No client-side rate limit indicators
**Impact**: Users may hit backend rate limits unexpectedly
**Future**: Add rate limit headers parsing, retry-after display

#### 15. No Rich Text Formatting
**Issue**: Plain text only, no markdown/rich text
**Impact**: Limited formatting options
**Future**: Add TipTap or similar editor

### Environment Dependencies

#### Required for Full Functionality
| Dependency | Status | Required For |
|------------|--------|--------------|
| Supabase Project | ❌ Not configured | Realtime updates, Storage |
| Ollama Server | ❌ Not running | AI vision processing |
| Backend API | ❌ Not deployed | All API calls |
| PostgreSQL | ❌ Not connected | Message persistence |

#### Current Development Mode
- All API calls go to `/api/v1` (Vite proxy or relative)
- Mock data in `AppContext` still used for non-chat views
- `ChatView` (admin/member) still uses mock data
- `GuestChatPage` uses new API adapters (will fail without backend)

### Browser Compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome 100+ | ✅ Supported | Full functionality |
| Firefox 95+ | ✅ Supported | Full functionality |
| Safari 15+ | ✅ Supported | Full functionality |
| Edge 100+ | ✅ Supported | Full functionality |
| IE 11 | ❌ Not supported | Modern JS features used |

### Performance Considerations

| Metric | Current | Target |
|--------|---------|--------|
| Initial load | ~200KB gzipped | < 150KB |
| Message render (100) | ~50ms | < 16ms |
| Scroll performance | Good (non-virtualized) | 60fps |
| Memory (100 messages + images) | ~50MB | < 30MB |
| Upload progress latency | ~100ms | < 50ms |

### Accessibility Gaps

| Feature | Status | Notes |
|---------|--------|-------|
| ARIA live regions | ✅ Implemented | Message list, errors |
| Keyboard navigation | ✅ Implemented | All interactive elements |
| Focus management | ✅ Implemented | Modals, forms |
| Screen reader labels | ✅ Implemented | All buttons, inputs |
| Color contrast | ✅ Verified | WCAG AA |
| Reduced motion | ⚠️ Partial | CSS only, no JS hook |
| High contrast mode | ❌ Not tested | |
| Zoom 200% | ✅ Works | Text reflows |
| Zoom 400% | ⚠️ Minor issues | Some overflow |

### Security Considerations

| Aspect | Status | Notes |
|--------|--------|-------|
| Recall token storage | ✅ sessionStorage | Cleared on tab close |
| XSS prevention | ✅ React default | No dangerouslySetInnerHTML |
| File upload validation | ✅ Client + server | MIME, size, count |
| HTTPS enforcement | ⚠️ Dev only | Production requires HTTPS |
| CSP headers | ❌ Not configured | |
| Rate limiting | ❌ Backend only | No UI feedback |
| Token expiry | ❌ No expiry | Tokens live forever |

### Migration Path for Phase 5+

1. **Admin Dashboard** (Phase 5) will need:
   - Message moderation interface
   - Recall approval workflow
   - Analytics on message statuses

2. **Phase 6+ Integration** will need:
   - Webhook for message status changes
   - Batch message operations
   - Advanced search API

3. **Production Deployment** requires:
   - Supabase project with Realtime enabled
   - Ollama server with vision models
   - Backend API deployed with proper CORS
   - CDN for image storage
   - Monitoring/alerting for worker health

### Recommended Next Steps

1. **Immediate** (before production):
   - Configure Supabase project
   - Deploy backend API
   - Set up environment variables
   - Run E2E tests against live backend

2. **Short-term** (Phase 5):
   - Add virtualization for message list
   - Implement emoji picker
   - Add conversation support

3. **Medium-term** (Phase 6):
   - Offline message queue
   - Push notifications
   - Message search

4. **Long-term** (Phase 7+):
   - Threaded replies
   - Rich text editing
   - Translation support