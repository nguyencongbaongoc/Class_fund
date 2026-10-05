# Phase 6 Storage Replacement Design

## Overview
This document designs the self-hosted file storage system to replace Supabase Storage, preserving all current functionality for private transaction image storage with authorized access control.

---

## 1. Current Storage Architecture

### 1.1 Supabase Storage Usage
| Operation | Current Implementation | Location |
|-----------|------------------------|----------|
| Upload receipt | `supabase_client.py:upload_receipt()` → Supabase bucket "receipts" | Backend |
| Download receipt | `supabase_client.py:download_receipt()` → Supabase | Backend (vision.py) |
| Delete receipt | `supabase_client.py:delete_receipt()` → Supabase | Not used |
| Public URL | `get_public_url()` returns public URL | Vision route fallback |
| Local fallback | `uploads.py` saves to `./storage/uploads/` | Primary upload |

### 1.2 Local Storage Already Primary
```python
# uploads.py:42-44 - ALREADY WORKING
ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[file.content_type]
path = Path(settings.upload_dir) / f"{uuid4()}{ext}"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(data)
upload = Upload(storage_path=str(path), ...)
```

### 1.3 Vision Route Fallback (Already Works)
```python
# vision.py:61-66
try:
    image_bytes = supabase.download_receipt(upload.storage_path)
except Exception:
    # Local fallback - ALREADY WORKS
    image_bytes = Path(upload.storage_path).read_bytes()
```

---

## 2. Storage Replacement Design

### 2.1 Architecture: Local Filesystem + Authenticated Serving

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Client    │────▶│  Backend    │────▶│  Local Filesystem │
│  (Upload)   │     │  (Validate) │     │  ./storage/uploads│
└─────────────┘     └─────────────┘     └──────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Database   │
                    │ (Upload rec)│
                    └─────────────┘
```

### 2.2 Upload Flow (Unchanged)
```python
# uploads.py - KEEP AS IS
@router.post("", response_model=UploadOut, status_code=201)
async def upload_receipt(file: UploadFile = File(...), uploader_name: str = Form(...), db: Session = Depends(get_db)):
    # 1. Validate MIME type (JPEG, PNG, WebP)
    # 2. Validate file size (max 10MB)
    # 3. Compute SHA256 hash
    # 4. Check duplicate (file_hash)
    # 5. Save to ./storage/uploads/{uuid}.{ext}
    # 6. Create Upload record with storage_path
    # 7. Return UploadOut
```

### 2.3 Authenticated File Serving (NEW)

```python
# app/api/routes/uploads.py - ADD
@router.get("/{upload_id}/file")
def serve_upload_file(upload_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Serve upload file with authorization."""
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    
    # Authorization: Owner, OWNER_TREASURER, MODERATOR can access
    if upload.uploaded_by != current_user.id and current_user.role not in (Role.OWNER_TREASURER, Role.MODERATOR):
        raise HTTPException(403, "Not authorized to access this file")
    
    file_path = Path(upload.storage_path)
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")
    
    # Determine media type
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(file_path.suffix.lower(), "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=upload.original_filename
    )
```

### 2.4 Vision Route Update (Remove Supabase)

```python
# vision.py - UPDATE
@router.post("/extract")
async def extract_receipt(upload_id: str, db: Session = Depends(get_db)):
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    
    # READ LOCAL FILE DIRECTLY - No Supabase
    file_path = Path(upload.storage_path)
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    image_bytes = file_path.read_bytes()
    
    # Call Ollama vision
    result = await vision_client.extract(image_bytes)
    
    # Save extraction...
    return result
```

### 2.5 Admin File Access (For Review)

```python
# app/api/routes/admin.py - ADD
@router.get("/uploads/{upload_id}/file")
def admin_serve_upload(upload_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_role(Role.OWNER_TREASURER, Role.MODERATOR))):
    """Admin access to any upload file for review."""
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    
    file_path = Path(upload.storage_path)
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    return FileResponse(path=file_path, filename=upload.original_filename)
```

---

## 3. File Validation and Security

### 3.1 Upload Validation (Already Implemented)
```python
# uploads.py - KEEP
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}

# Size limit from config
if len(data) > settings.max_upload_mb * 1024 * 1024:
    raise HTTPException(413, "Image is too large")

# MIME validation
if file.content_type not in ALLOWED_MIME:
    raise HTTPException(415, "Only JPEG, PNG or WEBP images are accepted")
```

### 3.2 Additional Security (RECOMMENDED)

```python
# app/services/storage.py - CREATE NEW
import magic  # python-magic for MIME detection

def validate_image_file(file_bytes: bytes) -> tuple[bool, str]:
    """Validate file is actually an image using magic bytes."""
    mime = magic.from_buffer(file_bytes, mime=True)
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if mime not in allowed:
        return False, f"Invalid file type: {mime}"
    
    # Check for embedded scripts/malware
    # Check image dimensions (max 10000x10000)
    return True, "OK"

def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename."""
    import re
    # Keep only alphanumeric, dots, hyphens, underscores
    return re.sub(r'[^a-zA-Z0-9._-]', '', filename)
```

---

## 4. Storage Configuration

### 4.1 Environment Variables

```bash
# .env.example
UPLOAD_DIR=./storage/uploads
MAX_UPLOAD_MB=10
```

### 4.2 Docker Volume Mount

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./storage/uploads:/app/storage/uploads  # Persistent storage
```

### 4.3 Directory Structure

```
storage/
└── uploads/
    ├── 2026/
    │   ├── 10/
    │   │   ├── 04/
    │   │   │   ├── abc123.jpg
    │   │   │   ├── def456.png
    │   │   │   └── ghi789.webp
    │   │   └── ...
    │   └── ...
    └── ...
```

**Optional:** Organize by date for easier management.

---

## 5. Backup and Recovery

### 5.1 File Backup

```bash
# Backup uploads directory
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz storage/uploads/

# Or rsync to backup server
rsync -av storage/uploads/ backup-server:/backups/classfund/uploads/
```

### 5.2 Database-File Consistency

```python
# Backup verification script
def verify_storage_integrity(db: Session):
    """Verify all upload records have corresponding files."""
    uploads = db.execute(select(Upload)).scalars().all()
    missing = []
    for upload in uploads:
        if not Path(upload.storage_path).exists():
            missing.append(upload.id)
    return missing
```

---

## 6. Frontend Integration

### 6.1 Upload Component (Unchanged)
```typescript
// classfund/classfund/src/lib/upload.ts - KEEP
// Already uses POST /api/v1/uploads
```

### 6.2 Image Display (Update URL)

```typescript
// classfund/classfund/src/lib/adminApi.ts - UPDATE
getImageUrl(uploadId: string): string {
    // OLD: Supabase public URL
    // NEW: Authenticated backend endpoint
    return `${API_BASE}/uploads/${uploadId}/file`;
}
```

### 6.3 Authenticated Image Display

```typescript
// For images in chat/review - need auth header
async function fetchImageWithAuth(uploadId: string): Promise<Blob> {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/uploads/${uploadId}/file`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new Error('Failed to load image');
    return response.blob();
}

// Usage in components:
const imageUrl = URL.createObjectURL(await fetchImageWithAuth(uploadId));
```

---

## 7. Scalability Considerations (Future)

### 7.1 S3-Compatible Storage (Phase 7+)
```python
# app/services/storage.py - ABSTRACT INTERFACE
class StorageBackend(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, filename: str) -> str:  # Returns storage key
    @abstractmethod
    def read(self, storage_key: str) -> bytes:
    @abstractmethod
    def delete(self, storage_key: str) -> bool:
    @abstractmethod
    def exists(self, storage_key: str) -> bool:

class LocalStorageBackend(StorageBackend):
    # Current implementation

class S3StorageBackend(StorageBackend):
    # Future: boto3 implementation
```

### 7.2 CDN Integration (Future)
- CloudFront / Cloudflare in front of file serving endpoint
- Cache-Control headers for public assets
- Signed URLs for private assets

---

## 8. Migration Plan

### 8.1 Phase 1: Remove Supabase Storage Code
1. Delete `upload_receipt`, `download_receipt`, `delete_receipt` from `supabase_client.py`
2. Update `vision.py` to read local files only
3. Remove Supabase storage config from `config.py`

### 8.2 Phase 2: Add Authenticated File Serving
1. Add `/uploads/{id}/file` endpoint with auth
2. Add admin file access endpoint
3. Update frontend `adminApi.getImageUrl()`

### 8.3 Phase 3: Testing
1. Test upload/download with auth
2. Test vision extraction reads local files
4. Test admin review image access
5. Test duplicate detection still works

---

## 9. Verification Checklist

- [ ] `supabase_client.py` has no storage methods
- [ ] `vision.py` reads local files directly
- [ ] `/uploads/{id}/file` endpoint works with auth
- [ ] Admin can access any upload for review
- [ ] Upload validation unchanged (MIME, size, hash)
- [ ] Duplicate detection works (file_hash)
- [ ] Frontend displays images via authenticated endpoint
- [ ] Docker volume persists uploads
- [ ] Backup script includes uploads directory

---

**Status: STORAGE REPLACEMENT DESIGN COMPLETE - Ready for Realtime Replacement Design**