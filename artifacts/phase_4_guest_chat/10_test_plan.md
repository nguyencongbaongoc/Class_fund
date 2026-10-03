# 10_test_plan.md

## Phase 4 Guest Chat - Test Plan

### Test Categories

| Category | Tests | Priority |
|----------|-------|----------|
| Unit Tests | Component logic, hooks, adapters | High |
| Integration Tests | Component interactions, API flows | High |
| E2E Tests | User journeys, realtime/polling | Medium |
| Accessibility Tests | WCAG AA compliance | High |
| Responsive Tests | Mobile/Tablet/Desktop | High |
| Security Tests | Recall token handling, XSS | High |

### Unit Test Cases

#### useChat Hook
- [ ] Initializes with correct default state
- [ ] loadMessages fetches and maps server messages
- [ ] sendMessage creates optimistic message
- [ ] sendMessage stores recall token in sessionStorage
- [ ] recallMessage calls adapter with correct params
- [ ] handleMessageUpdate merges realtime updates
- [ ] addUpload creates upload state with preview
- [ ] removeUpload revokes object URL
- [ ] retryUpload resets error state and re-uploads
- [ ] refreshMessages reloads from server

#### apiClient
- [ ] createMessage sends correct payload
- [ ] createMessage handles 201 response
- [ ] createMessage throws ApiError on 4xx/5xx
- [ ] recallMessage sends token in body
- [ ] recallMessage handles 403 (invalid token)
- [ ] recallMessage handles 409 (already recalled)
- [ ] getMessageStatus returns correct shape
- [ ] listMessages applies query params
- [ ] uploadWithProgress calls onProgress callback
- [ ] uploadWithProgress handles XHR abort

#### RecallAdapter
- [ ] canRecall returns true for pending/processing/awaiting_review/posted with token
- [ ] canRecall returns false for recalled/rejected/failed
- [ ] canRecall returns false when no token in sessionStorage
- [ ] recallMessage retrieves token from storage
- [ ] recallMessage removes token on success
- [ ] getDefaultRecallReason returns correct text per status

#### HybridAdapter
- [ ] Tries realtime first when credentials present
- [ ] Falls back to polling when realtime fails
- [ ] Switches back to realtime on reconnect
- [ ] Deduplicates messages from both sources
- [ ] Tracks message IDs for polling
- [ ] Stops polling for terminal statuses

#### UploadAdapter
- [ ] Validates file type and size
- [ ] Creates object URL for preview
- [ ] Calls onProgress during upload
- [ ] Calls onComplete with upload_id
- [ ] Calls onError on failure
- [ ] Cancels upload on abort

### Integration Test Cases

#### Message Creation Flow
- [ ] Guest enters name, types text, clicks send
- [ ] Guest enters name, attaches image, clicks send
- [ ] Guest attaches 5 images, all upload in parallel
- [ ] Guest attaches 6th image → ignored with warning
- [ ] Guest selects invalid file (PDF) → ignored
- [ ] Moderator toggles announcement → message_type=ANNOUNCEMENT
- [ ] Send during upload → button shows "Đang tải ảnh..."
- [ ] Network error → error toast, retry available

#### Message Display Flow
- [ ] Messages load on mount
- [ ] New message appears at top (optimistic)
- [ ] Status updates via realtime → badge updates
- [ ] Status updates via polling → badge updates
- [ ] Receipt message clickable → opens detail
- [ ] Public code displayed and copyable
- [ ] Pinned message at top with MOD badge
- [ ] Own messages right-aligned, others left

#### Recall Flow
- [ ] Guest sends message → recall token in sessionStorage
- [ ] Guest clicks "THU HỘI" on own pending message
- [ ] Confirmation modal shows correct description
- [ ] Guest confirms → recall API called with token
- [ ] Backend returns success → status "Đã thu hồi"
- [ ] Recall button hidden, status badge shown
- [ ] Guest tries recall again → button not shown
- [ ] Guest recalls posted message → reversal created
- [ ] Invalid token → error toast displayed
- [ ] Already recalled → error toast displayed

#### Image Upload Flow
- [ ] Click drop zone → file dialog opens
- [ ] Drag & drop → same as click
- [ ] Multiple files → all added to grid
- [ ] Upload progress → per-file progress bar
- [ ] Upload complete → checkmark, upload_id stored
- [ ] Upload fails → error message, retry button
- [ ] Click retry → upload restarts
- [ ] Click remove → preview removed, URL revoked
- [ ] Cancel upload → XHR aborted

### E2E Test Cases

#### Guest User Journey
1. Open /chat as PUBLIC user
2. See guest header with info
3. Enter name "Nguyễn Văn An"
4. Attach receipt image
5. See upload progress → complete
6. Click send
7. See optimistic message with "Đang chờ"
8. Wait for realtime update → "Đang xử lý"
9. Wait for completion → "Đã ghi sổ"
10. See public code CF-20261003-A1B2C3
11. Click copy → toast "Đã sao chép"
12. Click "THU HỘI" before posted
13. Confirm → message shows "Đã thu hồi"
14. Refresh page → token lost, cannot recall

#### Moderator Journey
1. Open /chat as MODERATOR
2. Toggle announcement checkbox
3. Type announcement text
4. Send → shows as announcement bubble
5. Pin message → shows at top with pin icon

#### Realtime/Polling
1. With Supabase credentials → realtime connected
2. Without credentials → polling active (5s)
3. Disconnect network → reconnect attempts
4. Reconnect → realtime resumes
5. Message posted → removed from polling

### Accessibility Test Cases

#### Keyboard Navigation
- [ ] Tab through: name input → textarea → attach → emoji → send
- [ ] Shift+Tab reverse order
- [ ] Enter in textarea → send (if valid)
- [ ] Shift+Enter → newline
- [ ] Escape in name input → blur
- [ ] Escape in recall modal → close
- [ ] Tab in modal → trap focus
- [ ] Focus visible on all elements

#### Screen Reader
- [ ] Message list announces "Đã ghi sổ" on status change
- [ ] Error toast announced immediately
- [ ] Form labels read: "Tên người gửi, required"
- [ ] Image alt: "Biên lai VCB8921734 from Nguyễn Văn An"
- [ ] Recall button: "Thu hồi yêu cầu, button"
- [ ] Modal: "Xác nhận thu hồi yêu cầu, dialog"

#### Color Contrast
- [ ] All text 4.5:1 on background
- [ ] Status badges with text + icon
- [ ] Focus ring 3:1 on background
- [ ] Disabled states distinguishable

#### Zoom & Responsive
- [ ] 200% zoom: no horizontal scroll
- [ ] 320px width: all content accessible
- [ ] Touch targets 44x44px
- [ ] No hover-only interactions

### Security Test Cases

#### Recall Token
- [ ] Token stored in sessionStorage only
- [ ] Token not in localStorage
- [ ] Token not in URL
- [ ] Token not in console logs
- [ ] Token cleared on successful recall
- [ ] Token not accessible after tab close
- [ ] Token required for recall API

#### Input Validation
- [ ] XSS in message content → escaped
- [ ] XSS in sender name → escaped
- [ ] File upload type validation
- [ ] File size limit enforced
- [ ] Max 5 files enforced

### Performance Test Cases
- [ ] 100 messages render without lag
- [ ] Virtualization works (if implemented)
- [ ] Scroll to bottom smooth
- [ ] Image previews lazy load
- [ ] Memory freed on image remove

### Test Execution Order

1. Unit tests (fast, isolated)
2. Integration tests (component + hook)
3. Accessibility audit (automated + manual)
4. Responsive visual regression
5. E2E critical paths
6. Security penetration
7. Performance benchmarks

### Test Environment
- Node.js 18+
- Vitest/Jest for unit/integration
- Playwright/Cypress for E2E
- axe-core for accessibility
- Chrome DevTools for performance

### CI/CD Integration
- Unit tests on every PR
- Integration tests on merge to main
- E2E tests on release candidate
- Accessibility gate on PR