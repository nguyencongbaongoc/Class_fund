# 03_message_composer.md

## Message Composer Component Specification

### Overview
The MessageComposer is the main input component for the Guest Chat. It handles text input, image attachments, sender name (for guests), and moderator announcements.

### Component Structure
```
MessageComposer
├── SenderNameInput (for PUBLIC role)
├── ModAnnouncementToggle (for MODERATOR/TREASURER)
├── ComposerInputArea
│   ├── ImageAttachButton
│   ├── Textarea
│   ├── EmojiButton
│   └── SendButton
├── ImageUploadArea (conditional, when images exist)
├── StatusIndicators (upload progress, errors)
└── EmojiPicker (placeholder)
```

### Props Interface
```typescript
interface MessageComposerProps {
  currentUser: {
    id: string;
    name: string;
    role: UserRole;
  };
  onSend: (data: Omit<MessageCreateRequest, 'conversation_id'>) => Promise<void>;
  isSending: boolean;
  uploads: Map<string, UploadState>;
  onAddUpload: (file: File) => string;
  onRemoveUpload: (uploadId: string) => void;
  onRetryUpload: (uploadId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}
```

### Features

#### 1. Sender Name Input (Guest Only)
- Required for PUBLIC role
- Pre-filled from localStorage (`guest_sender_name`)
- Auto-saves on blur
- Minimum 2 characters, maximum 120
- Visual required indicator (*)

#### 2. Moderator Announcement Toggle
- Only visible for MODERATOR/TREASURER roles
- Checkbox to switch between TEXT and ANNOUNCEMENT message types
- Visual indicator when active

#### 3. Text Input Area
- Auto-resizing textarea (min 44px, max 150px)
- Enter to send, Shift+Enter for newline
- Placeholder text based on mode
- Disabled during sending

#### 4. Image Attachment
- Click to open file dialog
- Accepts JPEG, PNG, WebP
- Max 5 files, 5MB each
- Triggers onAddUpload for each file

#### 5. Send Button States
- Default: "Gửi" with Send icon (enabled when valid)
- Sending: "Đang gửi..." with spinner
- Uploading: "Đang tải ảnh..." with spinner
- Disabled: opacity 40, not clickable

#### 6. Image Upload Area (conditional)
- Shows when `uploads.size > 0`
- Delegates to ImageUploadArea component
- Shows progress per image

#### 7. Status Indicators
- Shows processing badge when uploads in progress
- Shows error indicator when uploads fail
- Clickable retry for failed uploads

#### 8. Emoji Picker (placeholder)
- Toggle button with Smile icon
- Shows placeholder message
- Ready for future implementation

### Validation Rules
1. Must have text content OR at least one image
2. Guest users MUST provide sender name (min 2 chars)
3. Max 5 images total
4. Each image ≤ 5MB
5. Allowed MIME types: image/jpeg, image/png, image/webp
6. Disabled during send/upload

### Accessibility
- All buttons have aria-labels
- Input has aria-required when required
- Textarea has aria-describedby for hints
- Focus management on error
- Live region for status announcements

### Keyboard Shortcuts
- Enter: Send message (if valid)
- Shift+Enter: New line in textarea
- Escape: Blur sender name input

### Testing Scenarios
1. Guest opens chat → sees sender name input
2. Guest enters name → auto-saved to localStorage
3. Guest types message → send enabled
4. Guest clicks image button → file dialog opens
5. Guest selects 3 images → all uploaded, previews shown
6. Guest clicks send → onSend called with data
6. Moderator toggles announcement → message_type changes
7. Send during upload → button shows "Đang tải ảnh..."
8. Upload fails → retry button appears
9. Keyboard: Enter sends, Shift+Enter newlines