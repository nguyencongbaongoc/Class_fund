# 03_OLLAMA_MODEL_CONFIGURATION.md

## Phase 3 AI Pipeline — Ollama Model Configuration & Management

**Version**: 1.0  
**Schema Version**: 1.0.0  
**Date**: 2026-10-03  
**Status**: DESIGN PHASE

---

## 1. Overview

This document specifies the configuration, management, and operational procedures for Ollama models used in the AI pipeline. The pipeline uses two models:

| Model | Type | Role | Size |
|-------|------|------|------|
| `qwen2.5vl:3b` | Vision-Language | Primary receipt OCR & extraction | 3.2 GB |
| `qwen3.5:4b` | Text-only | Fallback classification, text normalization | 3.4 GB |

**Critical**: Both models run locally at `http://127.0.0.1:11434`. No external API calls permitted.

---

## 2. Model Configuration

### 2.1 Environment Variables

```bash
# Ollama Server
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Model Names (must match `ollama list` output exactly)
OLLAMA_VISION_MODEL=qwen2.5vl:3b
OLLAMA_TEXT_MODEL=qwen3.5:4b

# Timeouts & Retries
OLLAMA_TIMEOUT=60                    # Seconds per request
OLLAMA_MAX_RETRIES=3                 # Retry attempts
OLLAMA_RETRY_DELAY=1.0               # Base delay (exponential backoff)
OLLAMA_CONNECT_TIMEOUT=10            # Connection establishment
OLLAMA_KEEP_ALIVE=5m                 # Model keep-alive duration

# Model Options
OLLAMA_TEMPERATURE=0.1               # Low for deterministic extraction
OLLAMA_TOP_P=0.9
OLLAMA_NUM_CTX=4096                  # Context window
OLLAMA_NUM_PREDICT=1024              # Max output tokens

# Health Checks
OLLAMA_HEALTH_CHECK_INTERVAL=30      # Seconds
OLLAMA_WARMUP_ON_START=true          # Preload models at startup

# Circuit Breaker
OLLAMA_CIRCUIT_BREAKER_THRESHOLD=5   # Failures before OPEN
OLLAMA_CIRCUIT_BREAKER_TIMEOUT=60    # Seconds before HALF_OPEN
```

### 2.2 Configuration Class

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class OllamaConfig:
    # Server
    base_url: str = "http://127.0.0.1:11434"
    
    # Models
    vision_model: str = "qwen2.5vl:3b"
    text_model: str = "qwen3.5:4b"
    
    # Timeouts
    timeout: int = 60
    connect_timeout: int = 10
    keep_alive: str = "5m"
    
    # Retry Policy
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_multiplier: float = 2.0
    
    # Generation Options
    temperature: float = 0.1
    top_p: float = 0.9
    num_ctx: int = 4096
    num_predict: int = 1024
    
    # Structured Output
    json_schema_enforcement: bool = True
    
    # Health & Warmup
    health_check_interval: int = 30
    warmup_on_start: bool = True
    
    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    
    @classmethod
    def from_env(cls) -> "OllamaConfig":
        import os
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", cls.base_url),
            vision_model=os.getenv("OLLAMA_VISION_MODEL", cls.vision_model),
            text_model=os.getenv("OLLAMA_TEXT_MODEL", cls.text_model),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", cls.timeout)),
            connect_timeout=int(os.getenv("OLLAMA_CONNECT_TIMEOUT", cls.connect_timeout)),
            keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", cls.keep_alive),
            max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", cls.max_retries)),
            retry_delay=float(os.getenv("OLLAMA_RETRY_DELAY", cls.retry_delay)),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", cls.temperature)),
            top_p=float(os.getenv("OLLAMA_TOP_P", cls.top_p)),
            num_ctx=int(os.getenv("OLLAMA_NUM_CTX", cls.num_ctx)),
            num_predict=int(os.getenv("OLLAMA_NUM_PREDICT", cls.num_predict)),
            health_check_interval=int(os.getenv("OLLAMA_HEALTH_CHECK_INTERVAL", cls.health_check_interval)),
            warmup_on_start=os.getenv("OLLAMA_WARMUP_ON_START", "true").lower() == "true",
            circuit_breaker_threshold=int(os.getenv("OLLAMA_CIRCUIT_BREAKER_THRESHOLD", cls.circuit_breaker_threshold)),
            circuit_breaker_timeout=int(os.getenv("OLLAMA_CIRCUIT_BREAKER_TIMEOUT", cls.circuit_breaker_timeout)),
        )
```

---

## 3. Model Manager Service

### 3.1 Responsibilities

- **Health Monitoring**: Continuous server + model availability checks
- **Model Lifecycle**: Warmup, keep-alive, graceful degradation
- **Request Routing**: Vision vs text model selection
- **Circuit Breaker**: Prevent cascade failures
- **Metrics Collection**: Latency, error rates, model performance

### 3.2 Interface

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import httpx

class ModelStatus(Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

@dataclass
class ModelHealth:
    model_name: str
    status: ModelStatus
    last_check: datetime
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    memory_usage_mb: Optional[int] = None

@dataclass
class ServerHealth:
    reachable: bool
    version: Optional[str] = None
    models: list[ModelHealth] = field(default_factory=list)
    total_memory_mb: Optional[int] = None
    free_memory_mb: Optional[int] = None

class OllamaModelManager:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.connect_timeout, read=config.timeout)
        )
        self._circuit_breaker = CircuitBreaker(
            threshold=config.circuit_breaker_threshold,
            timeout=config.circuit_breaker_timeout
        )
        self._vision_warmed = False
        self._text_warmed = False
    
    async def health_check(self) -> ServerHealth:
        """Comprehensive server + model health check."""
        pass
    
    async def ensure_model_available(self, model: str) -> bool:
        """Check model exists, pull if missing (requires admin), warmup."""
        pass
    
    async def warmup_models(self) -> None:
        """Preload both models to avoid cold-start latency."""
        pass
    
    async def extract_vision(
        self, 
        image_bytes: bytes, 
        schema: dict
    ) -> OllamaExtraction:
        """Call vision model with structured output enforcement."""
        pass
    
    async def extract_text_fallback(
        self, 
        ocr_text: str, 
        schema: dict
    ) -> OllamaExtraction:
        """Call text model with OCR text as input."""
        pass
    
    def get_vision_model_name(self) -> str:
        return self.config.vision_model
    
    def get_text_model_name(self) -> str:
        return self.config.text_model
    
    async def close(self):
        await self.client.aclose()
```

### 3.3 Circuit Breaker Implementation

```python
import time
from enum import Enum
from threading import Lock

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.state = CircuitState.CLOSED
        self._lock = Lock()
        self.half_open_successes = 0
        self.half_open_max_calls = 3
    
    def record_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.half_open_successes = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.threshold:
                self.state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_successes = 0
                    return True
                return False
            # HALF_OPEN
            return self.half_open_successes < self.half_open_max_calls
    
    def get_state(self) -> CircuitState:
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_successes = 0
            return self.state
```

---

## 4. Vision Extraction Prompt Engineering

### 4.1 Primary Vision Prompt (Structured Output)

```python
VISION_SYSTEM_PROMPT = """You are a Vietnamese bank transfer receipt analyzer.
Extract the following information from the receipt image.
Return ONLY valid JSON matching the provided schema exactly.

Fields:
- transaction_code: string or null (bank reference number, e.g., FT26277123456789, VCB123456789, MBVCB123456789)
- amount: integer or null (amount in VND, no currency symbol, no separators)
- sender_name: string or null (account holder name who sent money)
- bank_name: string or null (bank name: Vietcombank, Techcombank, BIDV, MBBank, VPBank, ACB, SHB, Sacombank, VietinBank, Agribank, SeABank, NAPAS, or other)
- transaction_time: string or null (ISO 8601 format: YYYY-MM-DDTHH:MM:SS)
- confidence: float 0-1 (overall confidence in extraction)
- raw_text: string or null (full OCR text for reference)

Rules:
- If a field is unclear, missing, or ambiguous, use null
- Do NOT guess or infer values
- Amount must be integer VND (e.g., 500000 not "500,000" or "500.000")
- Transaction code must be exact as shown on receipt
- Bank name must be standard Vietnamese bank name
- Date/time must be parsable ISO 8601
- Confidence should reflect actual certainty (0.0-1.0)"""

VISION_USER_PROMPT = "Analyze this Vietnamese bank transfer receipt image and extract the required fields."
```

### 4.2 Text Fallback Prompt

```python
TEXT_FALLBACK_SYSTEM_PROMPT = """You are a Vietnamese bank transfer receipt text analyzer.
Extract the following information from the OCR text provided.
Return ONLY valid JSON matching the provided schema exactly.

Fields: (same as vision prompt)

OCR Text will be provided after this prompt.
Rules: (same as vision prompt)"""

TEXT_FALLBACK_USER_PROMPT_TEMPLATE = """OCR Text:
{ocr_text}

Extract the required fields from the above OCR text."""
```

### 4.3 JSON Schema for Structured Output

```python
VISION_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "transaction_code": {"type": ["string", "null"]},
        "amount": {"type": ["integer", "null"], "minimum": 1, "maximum": 1000000000},
        "sender_name": {"type": ["string", "null"]},
        "bank_name": {"type": ["string", "null"]},
        "transaction_time": {"type": ["string", "null"], "format": "date-time"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "raw_text": {"type": ["string", "null"]}
    },
    "required": ["transaction_code", "amount", "sender_name", "bank_name", "transaction_time", "confidence", "raw_text"],
    "additionalProperties": False
}
```

---

## 5. Request/Response Handling

### 5.1 Vision Request Payload

```python
async def _call_vision_model(
    self, 
    image_bytes: bytes, 
    schema: dict
) -> dict:
    """Call Ollama /api/chat with vision model."""
    import base64
    
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "model": self.config.vision_model,
        "messages": [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user", 
                "content": VISION_USER_PROMPT,
                "images": [image_b64]
            }
        ],
        "format": "json",
        "options": {
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "num_ctx": self.config.num_ctx,
            "num_predict": self.config.num_predict,
            "keep_alive": self.config.keep_alive
        },
        "stream": False
    }
    
    response = await self.client.post("/api/chat", json=payload)
    response.raise_for_status()
    return response.json()
```

### 5.2 Response Parsing

```python
def _parse_vision_response(self, response: dict) -> OllamaExtraction:
    """Parse and validate Ollama vision response."""
    content = response.get("message", {}).get("content", "").strip()
    
    try:
        extracted = json.loads(content)
        # Validate against schema
        validated = VisionExtractionSchema(**extracted)
        return OllamaExtraction(
            transaction_code=validated.transaction_code,
            amount=validated.amount,
            sender_name=validated.sender_name,
            bank_name=validated.bank_name,
            transaction_time=validated.transaction_time,
            confidence=validated.confidence,
            raw_text=validated.raw_text,
            model=self.config.vision_model,
            processing_time_ms=response.get("total_duration", 0) // 1_000_000
        )
    except json.JSONDecodeError as e:
        raise OllamaResponseError(f"Invalid JSON from model: {e}")
    except ValidationError as e:
        raise OllamaResponseError(f"Schema validation failed: {e}")
```

---

## 6. Fallback Strategy

### 6.1 Fallback Decision Tree

```
                    ┌─────────────────┐
                    │ Vision Request  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────────┐ ┌──────────┐
        │ Success │   │ Timeout/    │ │ Circuit  │
        │         │   │ Error       │ │ OPEN     │
        └────┬────┘   └──────┬──────┘ └────┬─────┘
           │                 │             │
           ▼                 ▼             ▼
      Return result    ┌─────────┐   ┌──────────┐
                       │ Retry   │   │ Fallback │
                       │ (3x)    │   │ to       │
                       └────┬────┘   │ Tesseract│
                          │         └────┬─────┘
                   ┌──────┴──────┐       │
                   ▼             ▼       ▼
              ┌─────────┐   ┌─────────┐  ┌────────────┐
              │ Success │   │ All     │  │ Text       │
              │         │   │ Failed  │  │ Fallback   │
              └────┬────┘   └────┬────┘  └──────┬─────┘
                   │             │             │
                   ▼             ▼             ▼
              Return      Return Error   ┌─────────┐
              Result      + Needs HR     │ OCR +   │
                                        │ LLM Text│
                                        └────┬────┘
                                             │
                                      ┌──────┴──────┐
                                      ▼             ▼
                                 ┌─────────┐  ┌──────────┐
                                 │ Success │  │ Failed   │
                                 └────┬────┘  └────┬─────┘
                                      │            │
                                      ▼            ▼
                                 Return      Return Error
                                 Result      + Needs HR
```

### 6.2 Fallback Conditions

| Condition | Action |
|-----------|--------|
| Ollama server unreachable | Immediate fallback to Tesseract |
| Vision model not loaded | Attempt load → fallback if failed |
| Vision request timeout | Retry 3x → fallback |
| Circuit breaker OPEN | Immediate fallback |
| JSON parse failure | Retry 1x → fallback |
| Schema validation failure | Retry 1x → fallback |
| Confidence < 0.3 | Fallback (model likely confused) |

---

## 7. Warmup Strategy

### 7.1 Startup Warmup

```python
async def warmup_models(self) -> None:
    """Warm up both models with dummy requests."""
    if not self.config.warmup_on_start:
        return
    
    # Warmup vision model with minimal image (1x1 pixel)
    dummy_image = base64.b64encode(b"\x89PNG\r\n\x1a\n...").decode()  # 1x1 PNG
    
    vision_payload = {
        "model": self.config.vision_model,
        "messages": [
            {"role": "user", "content": "test", "images": [dummy_image]}
        ],
        "options": {"num_predict": 1, "keep_alive": self.config.keep_alive},
        "stream": False
    }
    
    await self.client.post("/api/chat", json=vision_payload, timeout=30)
    
    # Warmup text model
    text_payload = {
        "model": self.config.text_model,
        "messages": [{"role": "user", "content": "test"}],
        "options": {"num_predict": 1, "keep_alive": self.config.keep_alive},
        "stream": False
    }
    
    await self.client.post("/api/chat", json=text_payload, timeout=30)
    
    self._vision_warmed = True
    self._text_warmed = True
```

### 7.2 Keep-Alive Management

- Models stay loaded for `OLLAMA_KEEP_ALIVE` (default 5m) after last request
- Worker should send periodic "heartbeat" requests if idle > 4m
- On worker shutdown, no explicit unload needed (Ollama manages)

---

## 8. Model Versioning & Updates

### 8.1 Version Pinning

```python
# Pin exact model digests for reproducibility
MODEL_PINS = {
    "qwen2.5vl:3b": "sha256:fb90415cde1e...",  # From `ollama list --verbose`
    "qwen3.5:4b": "sha256:2a654d98e6fb...",
}
```

### 8.2 Update Procedure

1. Test new model version in staging with evaluation dataset
2. Compare metrics (accuracy, latency, confidence calibration)
3. If improved: update `OLLAMA_VISION_MODEL` env var
4. Deploy with rolling restart
5. Monitor for 24h before declaring stable

### 8.3 Rollback

- Keep previous model tag available (`ollama pull qwen2.5vl:3b-old`)
- Revert env var and restart workers
- No data migration needed (stateless)

---

## 9. Monitoring & Observability

### 9.1 Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `ollama_requests_total` | Counter | By model, endpoint, status |
| `ollama_request_latency_ms` | Histogram | Per model, per operation |
| `ollama_circuit_breaker_state` | Gauge | 0=closed, 1=half_open, 2=open |
| `ollama_model_loaded` | Gauge | 1 if model in memory |
| `ollama_fallback_rate` | Counter | Vision → Tesseract fallbacks |
| `ollama_json_parse_errors` | Counter | By model |
| `ollama_schema_validation_errors` | Counter | By model |

### 9.2 Health Check Endpoint

```python
async def get_health_status(self) -> dict:
    return {
        "server": await self.health_check(),
        "circuit_breaker": self._circuit_breaker.get_state().value,
        "vision_warmed": self._vision_warmed,
        "text_warmed": self._text_warmed,
        "config": {
            "vision_model": self.config.vision_model,
            "text_model": self.config.text_model,
            "timeout": self.config.timeout,
        }
    }
```

---

## 10. Error Types

```python
class OllamaError(Exception):
    """Base Ollama error."""

class OllamaConnectionError(OllamaError):
    """Cannot connect to Ollama server."""

class OllamaModelNotFoundError(OllamaError):
    """Requested model not available."""

class OllamaTimeoutError(OllamaError):
    """Request timed out."""

class OllamaResponseError(OllamaError):
    """Response parsing/validation failed."""

class OllamaCircuitOpenError(OllamaError):
    """Circuit breaker is open."""
```

---

## 11. Testing Requirements

### 11.1 Unit Tests

| Test | Description |
|------|-------------|
| Config from env | All env vars correctly parsed |
| Health check success | Returns server + model status |
| Health check failure | Handles connection error |
| Circuit breaker | Opens after threshold failures |
| Circuit breaker recovery | Half-open → closed on success |
| Vision request | Valid image → structured output |
| Text fallback | OCR text → structured output |
| JSON parse failure | Raises OllamaResponseError |
| Schema validation failure | Raises OllamaResponseError |
| Model not found | Raises OllamaModelNotFoundError |
| Warmup | Both models respond to dummy request |

### 11.2 Integration Tests (Require Ollama Running)

| Test | Description |
|------|-------------|
| Vision extraction | Real receipt image → valid extraction |
| Text fallback | Real OCR text → valid extraction |
| Fallback chain | Vision fail → Tesseract success |
| Concurrent requests | Multiple parallel requests handled |
| Long request | 55s request completes (within timeout) |
| Model switching | Vision → text model calls work |

---

## 12. Security

1. **Localhost Only**: `base_url` must be `127.0.0.1` or `localhost`
2. **No Auth**: Ollama has no auth; rely on network isolation
3. **Input Validation**: Image bytes validated before sending
4. **Output Sanitization**: Model output validated against strict JSON schema
5. **No PII in Logs**: Don't log raw OCR text or extracted fields in production
6. **Resource Limits**: Timeout prevents resource exhaustion

---

## 13. Implementation Location

```
ai/
├── ollama/
│   ├── __init__.py
│   ├── config.py              # OllamaConfig
│   ├── manager.py             # OllamaModelManager
│   ├── circuit_breaker.py     # CircuitBreaker
│   ├── prompts.py             # Prompt templates
│   ├── schemas.py             # VisionExtractionSchema, OllamaExtraction
│   ├── client.py              # Low-level HTTP client
│   └── errors.py              # Exception hierarchy
```

---

## 14. Migration from Current `ollama_client.py`

| Current | New |
|---------|-----|
| `OllamaConfig` (sync) | `OllamaConfig` (async-ready) |
| `OllamaVisionClient` (sync httpx) | `OllamaModelManager` (async httpx) |
| `extract_from_image()` | `extract_vision()` |
| `extract_with_text_fallback()` | `extract_text_fallback()` |
| `VisionResult` (dataclass) | `OllamaExtraction` (Pydantic) |
| `VisionExtractionSchema` | Extended with more fields |
| Hardcoded 0.7 threshold | Configurable via `ThresholdConfig` |
| No circuit breaker | Circuit breaker included |
| No warmup | Startup warmup |
| No metrics | Structured metrics |

---

*End of Ollama Model Configuration*