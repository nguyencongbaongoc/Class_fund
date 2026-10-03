# 08_DUPLICATE_CANDIDATE_DETECTION.md

## Phase 3 AI Pipeline — Duplicate Candidate Detection

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

The Duplicate Candidate Detector identifies **potential duplicate receipts/transactions** at the AI layer. It produces **candidates only** — the final duplicate decision is made by the Backend Financial Gatekeeper (Phase 2) using database constraints and idempotency keys.

### 1.1 Key Principles

- **Propose, Don't Decide**: AI flags candidates; Backend makes final decision
- **Multi-Layer Defense**: Four independent detection layers
- **Persisted State**: Hashes stored in Supabase for cross-worker, cross-restart detection
- **Configurable Thresholds**: All thresholds tunable via config
- **Audit Trail**: Every detection logged with evidence

### 1.2 Four Detection Layers

```
┌─────────────────────────────────────────────────────────────────┐
│              DUPLICATE CANDIDATE DETECTION LAYERS               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LAYER 1: FILE HASH (Exact Duplicate)                          │
│  ─────────────────────────────────────                          │
│  • SHA-256 of raw image bytes                                   │
│  • Confidence: 1.0 (cryptographic certainty)                   │
│  • Detects: Exact re-upload of same file                        │
│  • Storage: Supabase `file_hashes` table                        │
│                                                                 │
│  LAYER 2: PERCEPTUAL HASH (Near Duplicate)                     │
│  ─────────────────────────────────────                          │
│  • DCT-based pHash (32x32 → 8x8 DCT → 64-bit)                 │
│  • Hamming distance ≤ threshold (default 10)                   │
│  • Confidence: 1.0 - distance/64                               │
│  • Detects: Re-compressed, cropped, rotated versions           │
│  • Storage: Supabase `perceptual_hashes` table                 │
│                                                                 │
│  LAYER 3: TRANSACTION IDENTITY (Business Duplicate)            │
│  ─────────────────────────────────────                          │
│  • Key: bank_name + transaction_code                           │
│  • Confidence: 1.0 (exact match)                               │
│  • Detects: Same transaction submitted via different images    │
│  • Storage: Supabase `transaction_identities` table            │
│                                                                 │
│  LAYER 4: FUZZY TRANSACTION (Suspicious Similarity)            │
│  ─────────────────────────────────────                          │
│  • Amount + date + sender + bank fuzzy match                   │
│  • Threshold: 0.85 combined similarity                         │
│  • Confidence: Combined similarity score                       │
│  • Detects: Potential fraud, data entry errors                 │
│  • Storage: Query-time (no persistence needed)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Models

### 2.1 Duplicate Candidate

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from enum import StrEnum

class DuplicateLayer(StrEnum):
    FILE_HASH = "file_hash"
    PERCEPTUAL_HASH = "perceptual_hash"
    TRANSACTION_IDENTITY = "transaction_identity"
    FUZZY_TRANSACTION = "fuzzy_transaction"

class DuplicateCandidate(BaseModel):
    """A potential duplicate detected by AI."""
    candidate_id: UUID = Field(default_factory=uuid4)
    layer: DuplicateLayer
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Matched upload
    matched_upload_id: UUID
    matched_upload_created_at: datetime
    
    # Evidence
    details: dict[str, Any] = Field(default_factory=dict)
    
    # For Layer 1
    file_hash: Optional[str] = None
    
    # For Layer 2
    perceptual_hash: Optional[str] = None
    hamming_distance: Optional[int] = None
    phash_threshold: Optional[int] = None
    
    # For Layer 3
    transaction_code: Optional[str] = None
    bank_name: Optional[str] = None
    identity_key: Optional[str] = None
    
    # For Layer 4
    similarity_breakdown: Optional[dict[str, float]] = None
    
    # Timestamp
    detected_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.2 Storage Schema (Supabase)

```sql
-- Layer 1: Exact file hashes
CREATE TABLE file_hashes (
    hash CHAR(64) PRIMARY KEY,           -- SHA-256 hex
    upload_id UUID NOT NULL REFERENCES uploads(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_file_hashes_upload ON file_hashes(upload_id);

-- Layer 2: Perceptual hashes
CREATE TABLE perceptual_hashes (
    phash CHAR(16) PRIMARY KEY,          -- 16-char hex (64-bit)
    upload_id UUID NOT NULL REFERENCES uploads(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_perceptual_hashes_upload ON perceptual_hashes(upload_id);

-- Layer 3: Transaction identities
CREATE TABLE transaction_identities (
    identity_key TEXT PRIMARY KEY,       -- "bank_name|transaction_code"
    upload_id UUID NOT NULL REFERENCES uploads(id),
    bank_name TEXT NOT NULL,
    transaction_code TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transaction_identities_upload ON transaction_identities(upload_id);
CREATE INDEX idx_transaction_identities_bank ON transaction_identities(bank_name);
```

---

## 3. Detection Algorithms

### 3.1 Layer 1: File Hash (Exact)

```python
class FileHashDetector:
    def __init__(self, supabase: SupabaseClient):
        self.supabase = supabase
    
    async def check(self, file_hash: str) -> Optional[DuplicateCandidate]:
        """Check if exact file hash exists."""
        result = await self.supabase.table("file_hashes") \
            .select("upload_id, created_at") \
            .eq("hash", file_hash) \
            .execute()
        
        if result.data:
            row = result.data[0]
            return DuplicateCandidate(
                layer=DuplicateLayer.FILE_HASH,
                confidence=1.0,
                matched_upload_id=UUID(row["upload_id"]),
                matched_upload_created_at=row["created_at"],
                details={"hash": file_hash},
                file_hash=file_hash,
            )
        return None
    
    async def register(self, file_hash: str, upload_id: UUID) -> None:
        """Register new file hash."""
        await self.supabase.table("file_hashes").insert({
            "hash": file_hash,
            "upload_id": str(upload_id),
        }).execute()
```

### 3.2 Layer 2: Perceptual Hash (Near-Duplicate)

```python
class PerceptualHashDetector:
    def __init__(self, supabase: SupabaseClient, threshold: int = 10):
        self.supabase = supabase
        self.threshold = threshold
    
    def compute_phash(self, image_bytes: bytes) -> str:
        """Compute DCT-based perceptual hash (64-bit → 16-char hex)."""
        from PIL import Image
        import cv2
        import numpy as np
        from io import BytesIO
        
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
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """Hamming distance between two 16-char hex strings."""
        x = int(hash1, 16) ^ int(hash2, 16)
        return bin(x).count("1")
    
    async def check(self, phash: str) -> Optional[DuplicateCandidate]:
        """Find near-duplicates within Hamming threshold."""
        # Get all stored hashes (consider pagination for large datasets)
        result = await self.supabase.table("perceptual_hashes") \
            .select("phash, upload_id, created_at") \
            .execute()
        
        best_match = None
        best_distance = self.threshold + 1
        
        for row in result.data:
            distance = self.hamming_distance(phash, row["phash"])
            if distance <= self.threshold and distance < best_distance:
                best_distance = distance
                best_match = row
        
        if best_match:
            confidence = 1.0 - (best_distance / 64.0)
            return DuplicateCandidate(
                layer=DuplicateLayer.PERCEPTUAL_HASH,
                confidence=confidence,
                matched_upload_id=UUID(best_match["upload_id"]),
                matched_upload_created_at=best_match["created_at"],
                details={
                    "phash": phash,
                    "matched_phash": best_match["phash"],
                    "hamming_distance": best_distance,
                    "threshold": self.threshold,
                },
                perceptual_hash=phash,
                hamming_distance=best_distance,
                phash_threshold=self.threshold,
            )
        return None
    
    async def register(self, phash: str, upload_id: UUID) -> None:
        await self.supabase.table("perceptual_hashes").insert({
            "phash": phash,
            "upload_id": str(upload_id),
        }).execute()
```

### 3.3 Layer 3: Transaction Identity (Business Key)

```python
class TransactionIdentityDetector:
    def __init__(self, supabase: SupabaseClient):
        self.supabase = supabase
    
    def build_identity_key(self, bank_name: str, transaction_code: str) -> str:
        """Build normalized identity key."""
        bank_norm = bank_name.strip().upper() if bank_name else "UNKNOWN"
        code_norm = transaction_code.strip().upper() if transaction_code else ""
        return f"{bank_norm}|{code_norm}"
    
    async def check(
        self, 
        bank_name: Optional[str], 
        transaction_code: Optional[str]
    ) -> Optional[DuplicateCandidate]:
        """Check if transaction identity already exists."""
        if not transaction_code:
            return None
        
        identity_key = self.build_identity_key(bank_name or "UNKNOWN", transaction_code)
        
        result = await self.supabase.table("transaction_identities") \
            .select("upload_id, created_at, bank_name, transaction_code") \
            .eq("identity_key", identity_key) \
            .execute()
        
        if result.data:
            row = result.data[0]
            return DuplicateCandidate(
                layer=DuplicateLayer.TRANSACTION_IDENTITY,
                confidence=1.0,
                matched_upload_id=UUID(row["upload_id"]),
                matched_upload_created_at=row["created_at"],
                details={
                    "identity_key": identity_key,
                    "transaction_code": transaction_code,
                    "bank_name": bank_name,
                },
                transaction_code=transaction_code,
                bank_name=bank_name,
                identity_key=identity_key,
            )
        return None
    
    async def register(
        self, 
        bank_name: Optional[str], 
        transaction_code: Optional[str], 
        upload_id: UUID
    ) -> None:
        if not transaction_code:
            return
        
        identity_key = self.build_identity_key(bank_name or "UNKNOWN", transaction_code)
        
        await self.supabase.table("transaction_identities").insert({
            "identity_key": identity_key,
            "upload_id": str(upload_id),
            "bank_name": bank_name or "UNKNOWN",
            "transaction_code": transaction_code,
        }).execute()
```

### 3.4 Layer 4: Fuzzy Transaction (Similarity)

```python
class FuzzyTransactionDetector:
    def __init__(self, supabase: SupabaseClient, threshold: float = 0.85):
        self.supabase = supabase
        self.threshold = threshold
    
    def compute_similarity(
        self, 
        extraction1: UnifiedExtractionResult,
        extraction2: UnifiedExtractionResult
    ) -> dict[str, float]:
        """Compute field-level similarity scores."""
        from rapidfuzz import fuzz
        
        scores = {}
        
        # Amount similarity (exact or very close)
        if extraction1.amount and extraction1.amount.value and \
           extraction2.amount and extraction2.amount.value:
            diff = abs(extraction1.amount.value - extraction2.amount.value)
            max_amt = max(extraction1.amount.value, extraction2.amount.value)
            scores["amount"] = 1.0 - (diff / max_amt) if max_amt > 0 else 1.0
        else:
            scores["amount"] = 0.0
        
        # Date similarity (same day = 1.0)
        if extraction1.transaction_date and extraction1.transaction_date.value and \
           extraction2.transaction_date and extraction2.transaction_date.value:
            if extraction1.transaction_date.value.date() == extraction2.transaction_date.value.date():
                scores["date"] = 1.0
            else:
                days_diff = abs((extraction1.transaction_date.value - extraction2.transaction_date.value).days)
                scores["date"] = max(0.0, 1.0 - days_diff / 30.0)
        else:
            scores["date"] = 0.0
        
        # Sender name similarity (fuzzy)
        if extraction1.sender_name and extraction1.sender_name.value and \
           extraction2.sender_name and extraction2.sender_name.value:
            scores["sender"] = fuzz.ratio(
                extraction1.sender_name.value, 
                extraction2.sender_name.value
            ) / 100.0
        else:
            scores["sender"] = 0.0
        
        # Bank name similarity
        if extraction1.bank_name and extraction1.bank_name.value and \
           extraction2.bank_name and extraction2.bank_name.value:
            scores["bank"] = 1.0 if extraction1.bank_name.value == extraction2.bank_name.value else 0.0
        else:
            scores["bank"] = 0.0
        
        return scores
    
    def combined_similarity(self, scores: dict[str, float]) -> float:
        """Weighted combination of field similarities."""
        weights = {
            "amount": 0.40,
            "date": 0.25,
            "sender": 0.20,
            "bank": 0.15,
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for field, weight in weights.items():
            if field in scores:
                weighted_sum += scores[field] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    async def check(
        self, 
        extraction: UnifiedExtractionResult
    ) -> Optional[DuplicateCandidate]:
        """Find fuzzy duplicates among recent uploads."""
        # Query recent uploads (last 30 days) with similar amounts
        if not extraction.amount or not extraction.amount.value:
            return None
        
        amount = extraction.amount.value
        amount_range = (amount * 0.95, amount * 1.05)  # ±5%
        
        # This would need a more sophisticated query in production
        # For now, simplified: check uploads with same amount ±5%
        result = await self.supabase.table("uploads") \
            .select("id, created_at, extracted_transactions(*)") \
            .gte("created_at", (datetime.utcnow() - timedelta(days=30)).isoformat()) \
            .execute()
        
        best_match = None
        best_score = self.threshold
        
        for row in result.data:
            # Parse extraction from stored data
            # This is simplified - real impl would use ExtractedTransaction table
            pass
        
        return None  # Placeholder - full impl needs DB query optimization
```

---

## 4. Unified Detector

```python
class DuplicateCandidateDetector:
    def __init__(
        self,
        supabase: SupabaseClient,
        config: DuplicateDetectorConfig,
    ):
        self.config = config
        self.file_hash_detector = FileHashDetector(supabase)
        self.perceptual_hash_detector = PerceptualHashDetector(
            supabase, config.phash_threshold
        )
        self.transaction_identity_detector = TransactionIdentityDetector(supabase)
        self.fuzzy_detector = FuzzyTransactionDetector(
            supabase, config.fuzzy_threshold
        )
    
    async def check_candidates(
        self,
        validated_image: ValidatedImage,
        extraction: UnifiedExtractionResult,
    ) -> list[DuplicateCandidate]:
        """Run all detection layers in parallel."""
        candidates = []
        
        # Layer 1: File hash
        if self.config.enable_file_hash:
            candidate = await self.file_hash_detector.check(validated_image.file_hash)
            if candidate:
                candidates.append(candidate)
        
        # Layer 2: Perceptual hash
        if self.config.enable_perceptual_hash:
            candidate = await self.perceptual_hash_detector.check(validated_image.perceptual_hash)
            if candidate:
                candidates.append(candidate)
        
        # Layer 3: Transaction identity
        if self.config.enable_transaction_identity:
            candidate = await self.transaction_identity_detector.check(
                extraction.bank_name.value if extraction.bank_name else None,
                extraction.transaction_code.value if extraction.transaction_code else None,
            )
            if candidate:
                candidates.append(candidate)
        
        # Layer 4: Fuzzy (optional, more expensive)
        if self.config.enable_fuzzy:
            candidate = await self.fuzzy_detector.check(extraction)
            if candidate:
                candidates.append(candidate)
        
        return candidates
    
    async def register(
        self,
        validated_image: ValidatedImage,
        extraction: UnifiedExtractionResult,
        upload_id: UUID,
    ) -> None:
        """Register all hashes/identities for future detection."""
        # Run in parallel
        await asyncio.gather(
            self.file_hash_detector.register(validated_image.file_hash, upload_id),
            self.perceptual_hash_detector.register(validated_image.perceptual_hash, upload_id),
            self.transaction_identity_detector.register(
                extraction.bank_name.value if extraction.bank_name else None,
                extraction.transaction_code.value if extraction.transaction_code else None,
                upload_id
            ),
        )
    
    async def load_existing(self, upload_id: UUID) -> None:
        """Not needed - detectors query Supabase directly."""
        pass
```

---

## 5. Configuration

```python
@dataclass
class DuplicateDetectorConfig:
    # Layer toggles
    enable_file_hash: bool = True
    enable_perceptual_hash: bool = True
    enable_transaction_identity: bool = True
    enable_fuzzy: bool = False  # Expensive, enable after evaluation
    
    # Thresholds
    phash_threshold: int = 10              # Hamming distance (0-64)
    fuzzy_threshold: float = 0.85          # Combined similarity (0-1)
    
    # Fuzzy query limits
    fuzzy_lookback_days: int = 30
    fuzzy_max_candidates: int = 100
    
    # Performance
    parallel_detection: bool = True
    cache_ttl_seconds: int = 300           # Cache recent checks
```

---

## 6. Integration with Verification Engine

```python
# In UnifiedVerificationEngine.verify()

# Step 7: Duplicate detection
duplicate_candidates = await self.duplicate_detector.check_candidates(
    validated_image, extraction
)

if duplicate_candidates:
    risk_flags.append(RiskFlag.DUPLICATE_RECEIPT)
    # Add details to risk_details
    risk_details["duplicate_candidates"] = [
        {
            "layer": c.layer.value,
            "confidence": c.confidence,
            "matched_upload_id": str(c.matched_upload_id),
            "details": c.details,
        }
        for c in duplicate_candidates
    ]

# After verification, register if not duplicate
if verification.status != VerificationStatus.DUPLICATE:
    await self.duplicate_detector.register(
        validated_image, extraction, upload_id
    )
```

---

## 7. Backend Integration (Phase 2)

### 7.1 Backend Duplicate Decision

The Backend Financial Gatekeeper makes the **final** duplicate decision using:

1. **Database Unique Constraint**: `(bank_account_id, transaction_code)` unique index
2. **Idempotency Key**: `msg_{message_id}_v{content_version}`
3. **AI Duplicate Candidates**: As additional evidence

```python
# In ledger.py verify_and_post_from_ai()

# Check database-level duplicate (authoritative)
duplicate = db.execute(select(Transaction).where(
    Transaction.bank_account_id == result.bank_account_id,
    Transaction.transaction_code == result.transaction_code,
)).scalar_one_or_none()

if duplicate:
    # Check if same message (recovery case)
    if message_id and duplicate.message_id == message_id:
        return VerifyAndPostResult(status=ProcessingResult.DUPLICATE, ...)
    
    # Different message, same bank transaction = BUSINESS_RULE violation
    upload.status = UploadStatus.DUPLICATE
    db.commit()
    return VerifyAndPostResult(
        status=ProcessingResult.DUPLICATE,
        error_message="Duplicate bank transaction",
        error_classification=ErrorClassification.BUSINESS_RULE
    )
```

### 7.2 AI Duplicate Candidates as Evidence

```python
# AI duplicate candidates included in AIResultIn.evidence
# Backend can log them for audit but doesn't rely on them for decision
```

---

## 8. Testing Requirements

### 8.1 Unit Tests

| Test | Description |
|------|-------------|
| File hash exact match | Same bytes → candidate with confidence 1.0 |
| File hash no match | Different bytes → no candidate |
| pHash exact match | Same image → distance 0, confidence 1.0 |
| pHash near match | Re-compressed → distance ≤10, confidence >0.8 |
| pHash no match | Different image → distance >10, no candidate |
| Transaction identity match | Same bank+code → candidate confidence 1.0 |
| Transaction identity no match | Different code → no candidate |
| Fuzzy similarity | Same amount, date, sender, bank → high score |
| Fuzzy no match | Different amount/date/sender → low score |

### 8.2 Integration Tests

| Test | Description |
|------|-------------|
| Exact re-upload detected | Upload same file twice → FILE_HASH candidate |
| Near-duplicate detected | Compress same image → PERCEPTUAL_HASH candidate |
| Cross-image same transaction | Two photos of same receipt → TRANSACTION_IDENTITY candidate |
| Fuzzy detection | Similar but not identical transactions → FUZZY candidate |
| Registration persistence | Restart detector → existing hashes loaded |
| Concurrent detection | Parallel uploads → no race conditions |

### 8.3 Performance Tests

| Metric | Target |
|--------|--------|
| File hash check | < 10ms |
| pHash check (10k hashes) | < 50ms |
| Transaction identity check | < 10ms |
| Full detection (4 layers) | < 100ms |
| Registration | < 50ms |

---

## 9. Monitoring & Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `duplicate_check_total` | Counter | layer, result (match, no_match) |
| `duplicate_check_latency_ms` | Histogram | layer |
| `duplicate_candidates_found` | Counter | layer |
| `duplicate_hamming_distances` | Histogram | - |
| `duplicate_fuzzy_scores` | Histogram | - |
| `duplicate_registration_total` | Counter | layer |

---

## 10. Implementation Location

```
ai/
├── duplicate/
│   ├── __init__.py
│   ├── detector.py              # DuplicateCandidateDetector
│   ├── file_hash.py             # FileHashDetector
│   ├── perceptual_hash.py       # PerceptualHashDetector
│   ├── transaction_identity.py  # TransactionIdentityDetector
│   ├── fuzzy.py                 # FuzzyTransactionDetector
│   ├── config.py                # DuplicateDetectorConfig
│   └── models.py                # DuplicateCandidate, DuplicateLayer
```

---

## 11. Migration from Current System

| Current (`ai/duplicate/service.py`) | New |
|-------------------------------------|-----|
| In-memory only (`seen_hashes` dict) | Persisted to Supabase |
| 3 layers | 4 layers (adds fuzzy) |
| `DuplicateCheckResult` | `DuplicateCandidate` with richer evidence |
| `DuplicateDetector.check_all()` sync | `DuplicateCandidateDetector.check_candidates()` async |
| `DuplicateDetector.register()` sync | `DuplicateCandidateDetector.register()` async |
| No config | Full `DuplicateDetectorConfig` |
| Hamming threshold hardcoded (10) | Configurable |
| No fuzzy layer | Added (optional) |

---

## 12. Security Considerations

1. **Hash Privacy**: File hashes and pHashes are not PII but could reveal upload patterns
2. **Rate Limiting**: Detection endpoints rate-limited to prevent enumeration
3. **SQL Injection**: Use parameterized queries (Supabase client handles)
4. **Storage Growth**: Implement TTL cleanup for old hashes (e.g., 1 year)
5. **Index Maintenance**: Monitor index size on `perceptual_hashes` table

---

*End of Duplicate Candidate Detection Design*