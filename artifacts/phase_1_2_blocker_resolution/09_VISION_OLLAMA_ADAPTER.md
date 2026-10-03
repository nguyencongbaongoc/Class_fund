# 09_VISION_OLLAMA_ADAPTER.md

## Workstream G: Vision and Ollama Adapter

### Current State Analysis

**Problem**: No vision model integration. Current AI pipeline uses Tesseract OCR only (`ai/ocr/service.py`).

**Solution**: Ollama Vision Adapter with local models:
- Configured endpoint: `http://127.0.0.1:11434`
- Available models: `qwen2.5vl:3b` (vision), `qwen3.5:4b` (text fallback)
- JSON schema validation for structured output
- Timeout and bounded retries
- Human review fallback for low confidence

### Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Ollama client config | ✅ IMPLEMENTED | `app/services/ollama_client.py` |
| Vision extraction | ✅ IMPLEMENTED | `ollama_client.py:OllamaVisionClient.extract_from_image` |
| Text fallback | ✅ IMPLEMENTED | `ollama_client.py:extract_with_text_fallback` |
| JSON schema validation | ✅ IMPLEMENTED | `VisionExtractionSchema` Pydantic model |
| Vision endpoint | ✅ IMPLEMENTED | `app/api/routes/vision.py` |
| Human review trigger | ✅ IMPLEMENTED | Confidence < 0.7 → NEEDS_HUMAN_REVIEW |
| Offline handling | ✅ IMPLEMENTED | Returns error, triggers review |

### Key Features

1. **Structured Output**: Pydantic schema validates model response
2. **Model Verification**: Checks model availability before calling
3. **Bounded Retries**: 3 attempts with exponential backoff
4. **Timeout**: 60s default, configurable
5. **Fallback**: Text model with OCR text if vision fails
6. **No Direct Financial Write**: Returns extraction only, gatekeeper handles posting

### API Endpoint

`POST /api/v1/internal/vision/process`
- Input: `upload_id`, `image_data_hex`, `Idempotency-Key`
- Output: Extraction data + processing status

### Testing

- Unit tests needed for vision client
- Integration test requires Ollama running
- Marked as UNVERIFIED for model accuracy (no measured dataset)

### Status

| Task | Status | Evidence |
|------|--------|----------|
| Ollama client | ✅ IMPLEMENTED | `app/services/ollama_client.py` |
| Vision extraction | ✅ IMPLEMENTED | `OllamaVisionClient.extract_from_image` |
| Text fallback | ✅ IMPLEMENTED | `extract_with_text_fallback` |
| Schema validation | ✅ IMPLEMENTED | `VisionExtractionSchema` |
| Vision endpoint | ✅ IMPLEMENTED | `app/api/routes/vision.py` |
| Human review trigger | ✅ IMPLEMENTED | `vision.py` lines 80-95 |
| Offline handling | ✅ IMPLEMENTED | `is_available()` check |
| Unit tests | ⏳ PENDING | Requires Ollama running |
| Model accuracy verification | ⏳ UNVERIFIED | No measured dataset |