# 02_IMAGE_INGESTION.md

## Phase 3 AI Pipeline — Image Ingestion Pipeline

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

The Image Ingestion Pipeline is the **first stage** of the AI pipeline. It receives raw image bytes from the Guest Chat (Phase 4) or direct API uploads and performs comprehensive validation, normalization, and metadata extraction before passing to the extraction engine.

### 1.1 Responsibilities

- **Validate**: MIME type, file size, dimensions, corruption, format support
- **Analyze**: Orientation (EXIF), blur, resolution, color space
- **Hash**: Compute file hash (SHA-256) and perceptual hash (pHash) for duplicate detection
- **Normalize**: Auto-rotate, convert to standard format (RGB), optional resize
- **Metadata**: Extract and preserve all relevant metadata for downstream stages

### 1.2 Non-Responsibilities

- ❌ OCR or text extraction
- ❌ Business logic (amount parsing, transaction codes)
- ❌ Financial validation
- ❌ Duplicate decision (only computes hashes for detection)

---

## 2. Input Contract

### 2.1 From Guest Chat (Phase 4)

```python
class GuestChatImageUpload:
    image_bytes: bytes
    filename: str                    # Original filename from client
    content_type: str                # Client-provided MIME (UNTRUSTED)
    uploaded_by: str                 # Guest session ID or user ID
    conversation_id: UUID            # Chat conversation reference
    message_id: UUID                 # Message reference for idempotency
```

### 2.2 From Direct API (Phase 2 Backend)

```python
class DirectImageUpload:
    image_bytes: bytes
    filename: str
    upload_id: UUID                  # Pre-created upload record
    storage_path: str                # Supabase Storage path
```

---

## 3. Validation Pipeline

### 3.1 Stage 1: MIME Type Verification

**Critical**: Do NOT trust client-provided `content_type`. Use `python-magic` (libmagic) for actual content detection.

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/heic": [".heic", ".heif"],
    "image/tiff": [".tiff", ".tif"],
}

def detect_mime_type(image_bytes: bytes) -> str:
    """Use python-magic to detect actual MIME type from file signature."""
    import magic
    mime = magic.Magic(mime=True)
    return mime.from_buffer(image_bytes)
```

**Rejection Criteria**:
- MIME not in `ALLOWED_MIME_TYPES` → `INVALID_MIME_TYPE`
- MIME mismatch with extension → `MIME_EXTENSION_MISMATCH` (warning, not block)

### 3.2 Stage 2: File Size Limits

```python
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def check_file_size(image_bytes: bytes) -> ValidationResult:
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        return ValidationResult(
            valid=False,
            error_code="FILE_TOO_LARGE",
            details={"size_mb": len(image_bytes) / 1024 / 1024, "max_mb": MAX_FILE_SIZE_MB}
        )
    return ValidationResult(valid=True)
```

### 3.3 Stage 3: Image Decoding & Corruption Check

```python
from PIL import Image, UnidentifiedImageError

def decode_and_verify(image_bytes: bytes) -> Image.Image:
    """Decode and verify image is not corrupted."""
    try:
        img = Image.open(BytesIO(image_bytes))
        img.verify()  # Verify integrity without loading pixels
        # Re-open for actual use (verify() consumes the stream)
        img = Image.open(BytesIO(image_bytes))
        img.load()  # Force load to catch truncated files
        return img
    except UnidentifiedImageError:
        raise ValidationError("CORRUPT_IMAGE", "Cannot identify image format")
    except Exception as e:
        raise ValidationError("CORRUPT_IMAGE", f"Image decode failed: {e}")
```

### 3.4 Stage 4: Dimension Validation

```python
MIN_DIMENSIONS = (400, 300)      # Minimum for receipt readability
MAX_DIMENSIONS = (4000, 4000)    # Prevent OOM on huge images

def check_dimensions(img: Image.Image) -> ValidationResult:
    w, h = img.size
    if w < MIN_DIMENSIONS[0] or h < MIN_DIMENSIONS[1]:
        return ValidationResult(
            valid=False,
            error_code="RESOLUTION_TOO_LOW",
            details={"width": w, "height": h, "min": MIN_DIMENSIONS}
        )
    if w > MAX_DIMENSIONS[0] or h > MAX_DIMENSIONS[1]:
        return ValidationResult(
            valid=False,
            error_code="RESOLUTION_TOO_HIGH",
            details={"width": w, "height": h, "max": MAX_DIMENSIONS}
        )
    return ValidationResult(valid=True)
```

### 3.5 Stage 5: Orientation Correction (EXIF)

```python
def auto_rotate(img: Image.Image) -> Image.Image:
    """Rotate based on EXIF orientation tag."""
    try:
        exif = img._getexif()
        if exif:
            orientation = exif.get(274)  # 274 = Orientation tag
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except Exception:
        pass  # No EXIF or error - proceed as-is
    return img
```

### 3.6 Stage 6: Blur Detection

```python
import cv2
import numpy as np

def compute_blur_score(image_bytes: bytes) -> float:
    """Compute Laplacian variance as blur metric. Higher = sharper."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    laplacian = cv2.Laplacian(img, cv2.CV_64F)
    return laplacian.var()

MIN_BLUR_SCORE = 100.0  # Empirical threshold for receipt images

def check_blur(image_bytes: bytes) -> ValidationResult:
    score = compute_blur_score(image_bytes)
    if score < MIN_BLUR_SCORE:
        return ValidationResult(
            valid=False,
            error_code="IMAGE_BLURRY",
            details={"blur_score": score, "threshold": MIN_BLUR_SCORE}
        )
    return ValidationResult(valid=True, metadata={"blur_score": score})
```

### 3.7 Stage 7: Color Space & Format Normalization

```python
def normalize_image(img: Image.Image) -> Image.Image:
    """Convert to standard RGB format for downstream processing."""
    # Handle palette modes (P), transparency (LA, PA), CMYK
    if img.mode in ("P", "LA", "PA"):
        img = img.convert("RGBA")
    if img.mode == "RGBA":
        # Composite on white background for OCR
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode == "CMYK":
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img
```

---

## 4. Hash Computation

### 4.1 File Hash (SHA-256)

```python
import hashlib

def compute_file_hash(image_bytes: bytes) -> str:
    """SHA-256 of raw bytes for exact duplicate detection."""
    return hashlib.sha256(image_bytes).hexdigest()
```

### 4.2 Perceptual Hash (pHash)

```python
def compute_perceptual_hash(image_bytes: bytes) -> str:
    """DCT-based pHash for near-duplicate detection."""
    from PIL import Image
    import cv2
    import numpy as np
    
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    pixels = np.array(img, dtype=np.float64)
    dct = cv2.dct(pixels)
    dct_low = dct[:8, :8]
    median = np.median(dct_low)
    hash_bits = (dct_low > median).flatten()
    hash_int = 0
    for bit in hash_bits:
        hash_int = (hash_int << 1) | int(bit)
    return f"{hash_int:016x}"
```

### 4.3 Hamming Distance for pHash Comparison

```python
def hamming_distance(hash1: str, hash2: str) -> int:
    """Hamming distance between two hex pHash strings."""
    x = int(hash1, 16) ^ int(hash2, 16)
    return bin(x).count("1")

PHASH_DUPLICATE_THRESHOLD = 10  # Hamming distance ≤ 10 = near duplicate
```

---

## 5. Output Contract

### 5.1 ValidatedImage Dataclass

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID
from PIL import Image

@dataclass
class ValidatedImage:
    # Original data
    image_bytes: bytes
    original_filename: str
    client_content_type: str          # Untrusted, for reference only
    
    # Validated properties
    mime_type: str                    # Verified by python-magic
    file_size: int                    # Bytes
    width: int
    height: int
    format: str                       # PIL format (JPEG, PNG, etc.)
    mode: str                         # Color mode (RGB, RGBA, etc.)
    
    # EXIF / Metadata
    orientation_applied: bool         # Whether auto-rotation was applied
    exif_data: dict | None            # Preserved EXIF (GPS stripped)
    
    # Quality metrics
    blur_score: float                 # Laplacian variance
    
    # Hashes for duplicate detection
    file_hash: str                    # SHA-256
    perceptual_hash: str              # pHash (16-char hex)
    
    # Processing metadata
    validated_at: datetime
    validation_warnings: list[str]    # Non-blocking issues
    
    # Optional: normalized image bytes (if resized/converted)
    normalized_bytes: bytes | None = None
    
    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0.0
```

### 5.2 ValidationResult

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationResult:
    valid: bool
    error_code: Optional[str] = None
    details: dict = None
    metadata: dict = None
    warnings: list[str] = None
```

### 5.3 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_MIME_TYPE` | 400 | File type not supported |
| `MIME_EXTENSION_MISMATCH` | 400 (warn) | Extension doesn't match content |
| `FILE_TOO_LARGE` | 413 | Exceeds max file size |
| `CORRUPT_IMAGE` | 400 | Cannot decode or truncated |
| `RESOLUTION_TOO_LOW` | 400 | Below minimum dimensions |
| `RESOLUTION_TOO_HIGH` | 400 | Above maximum dimensions |
| `IMAGE_BLURRY` | 400 | Blur score below threshold |
| `UNSUPPORTED_FORMAT` | 400 | Format not processable (e.g., animated GIF) |

---

## 6. Configuration

```python
@dataclass
class IngestionConfig:
    # File validation
    allowed_mime_types: list[str] = field(default_factory=lambda: [
        "image/jpeg", "image/png", "image/webp", "image/heic", "image/tiff"
    ])
    max_file_size_mb: int = 10
    min_dimensions: tuple[int, int] = (400, 300)
    max_dimensions: tuple[int, int] = (4000, 4000)
    
    # Quality thresholds
    min_blur_score: float = 100.0
    
    # Processing
    auto_rotate: bool = True
    normalize_to_rgb: bool = True
    strip_exif_gps: bool = True  # Privacy
    
    # Output
    compute_file_hash: bool = True
    compute_perceptual_hash: bool = True
    
    # Optional: resize large images for faster OCR
    max_ocr_dimension: int = 2000  # Resize if larger, preserve aspect ratio
```

**Environment Overrides**:
```bash
AI_INGESTION_MAX_FILE_SIZE_MB=10
AI_INGESTION_MIN_BLUR_SCORE=100.0
AI_INGESTION_MAX_DIMENSION=4000
```

---

## 7. Integration Points

### 7.1 Downstream: Extraction Engine

```python
# ExtractionEngine.extract(validated_image: ValidatedImage) -> UnifiedExtractionResult
```

The `ValidatedImage` provides:
- `image_bytes` or `normalized_bytes` for OCR/vision
- `file_hash` and `perceptual_hash` for duplicate detection
- `blur_score` for confidence adjustment
- `width`, `height` for DPI estimation

### 7.2 Downstream: Duplicate Detector

```python
# DuplicateCandidateDetector.check_candidates(validated_image, verification)
```

Uses `file_hash` and `perceptual_hash` from `ValidatedImage`.

### 7.3 Upstream: Vision API Endpoint

```python
# app/api/routes/vision.py:process_receipt_vision()
# Receives image as hex string, converts to bytes, calls ingestion
```

---

## 8. Testing Requirements

### 8.1 Unit Tests

| Test Case | Expected Result |
|-----------|-----------------|
| Valid JPEG receipt | ✅ ValidatedImage with all fields |
| Valid PNG receipt | ✅ ValidatedImage |
| Valid WebP receipt | ✅ ValidatedImage |
| HEIC receipt | ✅ ValidatedImage (if libheif available) |
| Corrupt JPEG (truncated) | ❌ CORRUPT_IMAGE |
| Non-image file (PDF renamed .jpg) | ❌ INVALID_MIME_TYPE |
| 50MB image | ❌ FILE_TOO_LARGE |
| 200x150 image | ❌ RESOLUTION_TOO_LOW |
| 5000x5000 image | ❌ RESOLUTION_TOO_HIGH |
| Blurry receipt (score < 100) | ❌ IMAGE_BLURRY |
| Rotated EXIF (orientation 6) | ✅ Auto-rotated, orientation_applied=true |
| PNG with transparency | ✅ Composited on white |
| CMYK TIFF | ✅ Converted to RGB |
| Animated GIF | ❌ UNSUPPORTED_FORMAT |

### 8.2 Property-Based Tests

- Hash determinism: Same bytes → same file_hash
- pHash stability: Minor compression → small Hamming distance
- Orientation: Known EXIF orientations produce correct rotation

### 8.3 Integration Tests

- Full pipeline: Upload → Ingestion → Extraction → Verification
- Duplicate detection: Same image twice → file_hash match
- Near duplicate: Slightly compressed → pHash match

---

## 9. Performance Targets

| Metric | Target |
|--------|--------|
| Validation latency (typical 2MB JPEG) | < 200ms |
| Blur detection latency | < 100ms |
| Hash computation | < 50ms |
| Memory peak (4000x4000) | < 500MB |
| Throughput | > 10 images/sec (single worker) |

---

## 10. Security Considerations

1. **No Trust in Client Input**: MIME, filename, size all verified server-side
2. **Memory Safety**: Stream processing where possible; limit concurrent large images
3. **EXIF Privacy**: Strip GPS coordinates from EXIF before storage
4. **Decompression Bombs**: PIL `Image.MAX_IMAGE_PIXELS` limit (default 89M pixels)
5. **Timeout**: Overall ingestion timeout (configurable, default 30s)

```python
# Protect against decompression bombs
Image.MAX_IMAGE_PIXELS = 50_000_000  # 50MP limit
```

---

## 11. Implementation Location

```
ai/
├── ingestion/
│   ├── __init__.py
│   ├── image_validator.py      # Main service
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── mime_validator.py
│   │   ├── size_validator.py
│   │   ├── dimension_validator.py
│   │   ├── corruption_validator.py
│   │   ├── blur_validator.py
│   │   └── format_validator.py
│   ├── hashing.py              # File hash + pHash
│   ├── normalization.py        # Orientation, color space
│   └── config.py               # IngestionConfig
```

---

*End of Image Ingestion Pipeline Design*