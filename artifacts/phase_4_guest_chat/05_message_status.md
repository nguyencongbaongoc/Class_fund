# 05_message_status.md

## Message Status Component Specification

### Overview
The message status system displays the current processing state of each message in the Guest Chat. Statuses are driven entirely by backend responses - the frontend never assumes or auto-transitions statuses.

### Status Types
```typescript
type MessageStatus = 
  | 'pending'           // Just created, not yet processed
  | 'processing'        // Worker picked up, running vision/verification
  | 'awaiting_review'   // Low confidence, needs human review
  | 'posted'            // Successfully posted to ledger
  | 'rejected'          // Failed validation (duplicate, etc.)
  | 'failed'            // Processing error
  | 'recalled';         // User recalled
```

### Status Display Configuration
| Status | Label | Icon | Color | Animation | Description |
|--------|-------|------|-------|-----------|-------------|
| pending | Đang chờ | Clock | neutral | - | Tin nhắn vừa được gửi, chờ hệ thống xử lý |
| processing | Đang xử lý | Loader2 | sky | spin | AI đang đọc biên lai và đối soát |
| awaiting_review | Cần duyệt | AlertTriangle | amber | - | Cần thủ quỹ kiểm tra thủ công |
| posted | Đã ghi sổ | CheckCircle2 | emerald | - | Đã xác thực và ghi vào sổ cái quỹ |
| rejected | Từ chối | XCircle | rose | - | Không hợp lệ (trùng lặp, sai thông tin...) |
| failed | Lỗi | AlertCircle | rose | - | Có lỗi xảy ra khi xử lý |
| recalled | Đã thu hồi | RotateCcw | neutral | - | Người gửi đã thu hồi yêu cầu này |

### Components

#### 1. StatusBadge
Full badge with icon, label, and border.
```tsx
<StatusBadge status={message.status} size="md" showLabel showIcon />
```
Sizes: sm (text-[10px]), md (text-xs), lg (text-sm)

#### 2. StatusIndicator
Inline indicator with icon and label.
```tsx
<StatusIndicator status={message.status} />
```

#### 3. StatusDot
Minimal dot with label.
```tsx
<StatusDot status={message.status} />
```

### Integration in MessageItem

#### Receipt Messages
Status shown in card header with colored badge:
```tsx
<span className="text-emerald-400 font-medium">
  <CheckCircle2 /> Đã xác minh AI
</span>
```

#### Text/Announcement Messages
Status badge in sender info row:
```tsx
<StatusBadge status={message.status} size="sm" />
```

#### Public Code Display
Shown alongside status for all message types:
```tsx
<PublicCodeDisplay code={message.public_code} size="sm" />
```

### Realtime/Polling Updates
- HybridAdapter receives status updates via Supabase Realtime or polling
- Updates applied via `handleMessageUpdate()` in useChat hook
- Status compared to prevent stale updates (using processed_at)
- Terminal states (posted, rejected, failed, recalled) stop polling

### Important Rules
1. **Never auto-transition** processing → posted
2. **Only display backend-provided status**
3. **No "Thành công" or "Đã xác nhận" for non-posted states**
4. **Color + Icon + Text** - never rely on color alone
5. **Animation only for processing** (spinner)
6. **Error messages** shown below message when present

### Testing Scenarios
1. Message created → shows "Đang chờ"
2. Worker picks up → shows "Đang xử lý" with spinner
3. Low confidence → shows "Cần duyệt" (amber)
4. Verified → shows "Đã ghi sổ" (emerald)
5. Duplicate → shows "Từ chối" (rose)
6. Processing error → shows "Lỗi" (rose)
7. User recalls → shows "Đã thu hồi" (neutral)
8. Status updates via realtime → UI updates without reload
9. Colorblind test: icons + text convey meaning without color