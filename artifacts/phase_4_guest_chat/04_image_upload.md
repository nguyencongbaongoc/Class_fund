# 04_image_upload.md

## Image Upload Component Specification

### Overview
The ImageUploadArea handles drag-and-drop and click-to-upload for receipt images, with preview grid, progress tracking, and error handling.

### Component Structure
```
ImageUploadArea
├── DropZone/ClickArea
│   ├── Hidden File Input
│   ├── Empty State (icon + text)
│   └── Selected State (count + click to add more)
├── Upload Progress Summary (when uploading)
└── Preview Grid
    └── PreviewItem (repeated)
        ├── Image Preview
        ├── Status Overlay
        ├── Progress Bar
        └── Actions (Remove, Retry)
```

### Props Interface
```typescript
interface ImageUploadAreaProps {
  images: UploadState[];
  onChange: (images: UploadState[]) => void;
  onAddUpload: (file: File) => string;
  onRemoveUpload: (uploadId: string) => void;
  onRetryUpload: (uploadId: string) => void;
  maxFiles?: number; // default 5
  disabled?: boolean;
}
```

### Features

#### 1. Drop Zone / Click Area
- Click anywhere to open file dialog
- Drag & drop files onto zone
- Visual feedback on drag over (blue border, light bg)
- Shows "Chọn ảnh" text and upload icon
- Shows selected count when images exist
- Disabled state (opacity 50, no interactions)

#### 2. File Validation (Client-side)
- MIME types: image/jpeg, image/png, image/webp
- Max size: 5MB per file
- Max files: 5 (configurable)
- Invalid files skipped with console warning

#### 3. Preview Grid
- Responsive: 2 cols mobile, 3 tablet, 4 desktop
- Aspect ratio: 1:1 (square)
- Object-fit: cover for images
- Status overlay on hover:
  - Pending: Spinner + "Chờ tải..."
  - Uploading: Spinner + percentage
  - Completed: Checkmark + "Đã tải xong"
  - Error: Warning icon + error message + Retry button
- Bottom bar with filename (truncated)
- Actions on hover: Remove (always), Retry (on error)

#### 4. Progress Tracking
- Per-image progress (0-100%)
- Overall progress bar in drop zone
- Visual states:
  - Pending: Neutral border, gray spinner
  - Uploading: Sky blue ring, animated spinner
  - Completed: Emerald border, checkmark
  - Error: Rose border, warning icon

#### 5. Upload Integration
- Calls `onAddUpload(file)` for each valid file
- Returns uploadId for tracking
- UploadAdapter handles actual HTTP upload with XHR progress
- On complete: updates upload with upload_id, status=completed
- On error: updates upload with error message, status=error

#### 6. Retry Logic
- Retry button only on error state
- Calls `onRetryUpload(uploadId)`
- Re-uses same file, resets progress to 0
- Calls uploadAdapter again

#### 7. Remove Logic
- Remove button on hover (X icon)
- Revokes object URL to free memory
- Calls `onRemoveUpload(uploadId)`
- Cancels ongoing upload if in progress

### UploadState Interface
```typescript
interface UploadState {
  id: string;           // Client-side ID
  file: File;           // Original file
  preview_url: string;  // blob: URL for preview
  progress: number;     // 0-100
  status: 'pending' | 'uploading' | 'completed' | 'error';
  upload_id?: string;   // Backend upload ID
  error?: string;       // Error message if failed
}
```

### Accessibility
- Drop zone: role="button", tabindex=0, keyboard accessible
- File input: hidden but accessible via click
- Progress: role="progressbar" with aria-valuenow
- Status: role="status" with aria-live="polite"
- Actions: aria-labels for Remove/Retry
- Images: alt text from filename

### Testing Scenarios
1. Click drop zone → file dialog opens
2. Select valid image → preview appears, upload starts
3. Select 5 images → all show in grid
4. Select 6th image → ignored, warning logged
5. Select invalid file (PDF) → ignored, warning logged
6. Drag & drop files → same as click
7. Upload progresses → progress bar updates
8. Upload completes → checkmark, upload_id stored
9. Upload fails → error message, retry button
10. Click retry → upload restarts
11. Click remove → preview removed, upload cancelled
12. Disabled prop → no interactions possible

### Performance
- Object URLs revoked on remove
- Lazy loading for preview images
- Memoized PreviewItem components
- Virtualized grid for large lists (future)