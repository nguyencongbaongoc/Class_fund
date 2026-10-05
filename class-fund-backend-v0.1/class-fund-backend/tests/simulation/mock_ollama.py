"""Mock Ollama Vision Client for simulation testing."""
from __future__ import annotations

import base64
import json
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from app.services.ollama_client import (
    CircuitState,
    OllamaConfig,
    OllamaVisionClient,
    VisionExtractionSchema,
    VisionResult,
)

from tests.simulation.config import get_simulation_config

logger = logging.getLogger(__name__)


class MockOllamaVisionClient:
    """Test-only mock Ollama client with deterministic responses."""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.sim_config = get_simulation_config()
        self._models_cache = self.sim_config.ollama_models
    
    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        return self.sim_config.ollama_available and not self.sim_config.inject_ollama_connection_refused
    
    def list_models(self) -> list[str]:
        """List available models."""
        return self._models_cache
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image to base64."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def _build_vision_prompt(self) -> str:
        """Build prompt for receipt extraction."""
        return "Mock vision prompt"
    
    def _build_text_fallback_prompt(self, ocr_text: str) -> str:
        """Build prompt for text fallback."""
        return f"Mock text fallback prompt with OCR: {ocr_text}"
    
    def _sanitize_for_prompt(self, text: str) -> str:
        """Sanitize text to prevent prompt injection."""
        return text[:5000]
    
    def extract_from_image(self, image_bytes: bytes, correlation_id: Optional[str] = None) -> VisionResult:
        """Extract receipt data from image using deterministic mock responses."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]
        
        logger.info(f"[{correlation_id}] Mock vision extraction")
        
        # Check circuit breaker first
        if self.sim_config.circuit_state == CircuitState.OPEN:
            return VisionResult(
                error="Circuit breaker OPEN - Ollama service unavailable (mock)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Check for failure injection
        if self.sim_config.inject_ollama_timeout:
            self.sim_config.circuit_state = CircuitState.OPEN
            return VisionResult(
                error="Ollama request timeout (injected)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        if self.sim_config.inject_ollama_connection_refused:
            self.sim_config.circuit_state = CircuitState.OPEN
            return VisionResult(
                error="Connection refused (injected)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Check if Ollama is available
        if not self.is_available():
            return VisionResult(
                error="Ollama server not available (mock)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Check if vision model is available
        if self.config.vision_model not in self._models_cache:
            return VisionResult(
                error=f"Vision model {self.config.vision_model} not available. Available: {self._models_cache}",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Generate a key based on image content for deterministic responses
        image_hash = hash(image_bytes) % 1000
        response_key = f"vision_{image_hash}"
        
        # Get deterministic response - try custom key first, then hash-based key
        # Check if there's a custom response set for this test
        result = None
        
        # First check if there's a single custom response set (for tests that set one)
        if len(self.sim_config.ollama_vision_responses) == 1:
            # Use the only response that was set
            result = list(self.sim_config.ollama_vision_responses.values())[0]
        else:
            # Otherwise use hash-based lookup
            result = self.sim_config.get_vision_response(response_key)
        
        if result is None:
            # Default successful response
            result = VisionResult(
                transaction_code="FT26277123456789",
                amount=500000,
                sender_name="NGUYEN VAN A",
                bank_name="Vietcombank",
                transaction_time="2026-10-04T10:30:00Z",
                confidence=0.95,
                raw_text="Mock OCR text from receipt",
                needs_human_review=False,
                correlation_id=correlation_id
            )
        
        # Ensure correlation_id is set
        result.correlation_id = correlation_id
        
        logger.info(f"[{correlation_id}] Mock vision result: confidence={result.confidence}, error={result.error}")
        return result
    
    def extract_with_text_fallback(self, image_bytes: bytes, ocr_text: str, correlation_id: Optional[str] = None) -> VisionResult:
        """Use text model as fallback with OCR text."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]
        
        logger.info(f"[{correlation_id}] Mock text fallback extraction")
        
        # Check circuit breaker first
        if self.sim_config.circuit_state == CircuitState.OPEN:
            return VisionResult(
                error="Circuit breaker OPEN - Ollama service unavailable (mock)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Check for failure injection (same as vision)
        if self.sim_config.inject_ollama_timeout:
            self.sim_config.circuit_state = CircuitState.OPEN
            return VisionResult(
                error="Ollama request timeout (injected)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        if self.sim_config.inject_ollama_connection_refused:
            self.sim_config.circuit_state = CircuitState.OPEN
            return VisionResult(
                error="Connection refused (injected)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Check if Ollama is available
        if not self.is_available():
            return VisionResult(
                error="Ollama server not available (mock)",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        if self.config.text_model not in self._models_cache:
            return VisionResult(
                error=f"Text model {self.config.text_model} not available",
                needs_human_review=True,
                correlation_id=correlation_id
            )
        
        # Get deterministic text fallback response
        text_hash = hash(ocr_text) % 1000
        response_key = f"text_{text_hash}"
        
        # First check if there's a single custom response set
        result = None
        if len(self.sim_config.ollama_text_responses) == 1:
            result = list(self.sim_config.ollama_text_responses.values())[0]
        else:
            result = self.sim_config.get_text_response(response_key)
        
        if result is None:
            # Default successful text fallback response
            result = VisionResult(
                transaction_code="FT26277123456789",
                amount=500000,
                sender_name="NGUYEN VAN A",
                bank_name="Vietcombank",
                transaction_time="2026-10-04T10:30:00Z",
                confidence=0.85,
                raw_text=ocr_text,
                needs_human_review=False,
                correlation_id=correlation_id
            )
        
        result.correlation_id = correlation_id
        logger.info(f"[{correlation_id}] Mock text fallback result: confidence={result.confidence}")
        return result
    
    def get_circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.sim_config.circuit_state
    
    def close(self):
        """Close the client."""
        pass


# Test fixtures for common scenarios
def create_vision_success_receipt(
    transaction_code: str = "FT26277123456789",
    amount: int = 500000,
    sender_name: str = "NGUYEN VAN A",
    bank_name: str = "Vietcombank",
    transaction_time: str = "2026-10-04T10:30:00Z",
    confidence: float = 0.95,
    raw_text: str = "Mock receipt text"
) -> VisionResult:
    """Create a successful vision extraction result."""
    return VisionResult(
        transaction_code=transaction_code,
        amount=amount,
        sender_name=sender_name,
        bank_name=bank_name,
        transaction_time=transaction_time,
        confidence=confidence,
        raw_text=raw_text,
        needs_human_review=confidence < 0.7,
        correlation_id=None
    )


def create_vision_low_confidence(
    confidence: float = 0.5,
    **kwargs
) -> VisionResult:
    """Create a low confidence vision result requiring human review."""
    result = create_vision_success_receipt(confidence=confidence, **kwargs)
    result.needs_human_review = True
    return result


def create_vision_missing_fields(
    transaction_code: Optional[str] = None,
    amount: Optional[int] = None,
    sender_name: Optional[str] = None,
    bank_name: Optional[str] = None,
    confidence: float = 0.6
) -> VisionResult:
    """Create a vision result with missing fields."""
    return VisionResult(
        transaction_code=transaction_code,
        amount=amount,
        sender_name=sender_name,
        bank_name=bank_name,
        transaction_time="2026-10-04T10:30:00Z",
        confidence=confidence,
        raw_text="Partial receipt text",
        needs_human_review=True,
        correlation_id=None
    )


def create_vision_multiple_transactions(
    transaction_codes: list[str],
    amounts: list[int],
    confidence: float = 0.8
) -> VisionResult:
    """Create a vision result indicating multiple transactions."""
    return VisionResult(
        transaction_code="MULTIPLE",
        amount=sum(amounts),
        sender_name="MULTIPLE SENDERS",
        bank_name="MULTIPLE BANKS",
        transaction_time="2026-10-04T10:30:00Z",
        confidence=confidence,
        raw_text=f"Multiple transactions: {list(zip(transaction_codes, amounts))}",
        needs_human_review=True,
        correlation_id=None
    )


def create_vision_vietnamese_text(
    transaction_code: str = "VCB20261004001",
    amount: int = 1000000,
    confidence: float = 0.88
) -> VisionResult:
    """Create a vision result with Vietnamese text."""
    return VisionResult(
        transaction_code=transaction_code,
        amount=amount,
        sender_name="TRẦN VẠN B",
        bank_name="Vietcombank",
        transaction_time="2026-10-04T14:22:00Z",
        confidence=confidence,
        raw_text="CHUYỂN KHOẢN - NGÂN HÀNG TMCP NGOẠI THƯƠNG VIỆT NAM - SỐ TIỀN: 1.000.000 VND",
        needs_human_review=confidence < 0.7,
        correlation_id=None
    )


# Failure fixtures
VISION_TIMEOUT = VisionResult(
    error="Ollama request timeout",
    needs_human_review=True,
    correlation_id=None
)

VISION_CONNECTION_REFUSED = VisionResult(
    error="Connection refused",
    needs_human_review=True,
    correlation_id=None
)

VISION_INVALID_JSON = VisionResult(
    error="Failed to parse model output: Invalid JSON",
    raw_text='{"transaction_code": "FT123", "amount": }',
    needs_human_review=True,
    correlation_id=None
)

VISION_MODEL_UNAVAILABLE = VisionResult(
    error="Vision model qwen2.5vl:3b not available",
    needs_human_review=True,
    correlation_id=None
)

VISION_EMPTY_RESPONSE = VisionResult(
    error="Empty response from model",
    raw_text="",
    needs_human_review=True,
    correlation_id=None
)

VISION_MALFORMED_EXTRACTION = VisionResult(
    error="Failed to validate extraction schema",
    raw_text='{"amount": "not_a_number"}',
    needs_human_review=True,
    correlation_id=None
)

# Text fallback fixtures
TEXT_FALLBACK_SUCCESS = VisionResult(
    transaction_code="FT26277123456789",
    amount=500000,
    sender_name="NGUYEN VAN A",
    bank_name="Vietcombank",
    transaction_time="2026-10-04T10:30:00Z",
    confidence=0.85,
    raw_text="OCR text from receipt",
    needs_human_review=False,
    correlation_id=None
)

TEXT_FALLBACK_INVALID_SCHEMA = VisionResult(
    error="Failed to validate extraction schema",
    raw_text='{"amount": "invalid"}',
    needs_human_review=True,
    correlation_id=None
)

TEXT_FALLBACK_BOTH_FAIL = VisionResult(
    error="Both vision and text models failed",
    needs_human_review=True,
    correlation_id=None
)

TEXT_FALLBACK_LOW_CONFIDENCE = VisionResult(
    transaction_code="FT26277123456789",
    amount=500000,
    sender_name="NGUYEN VAN A",
    bank_name="Vietcombank",
    transaction_time="2026-10-04T10:30:00Z",
    confidence=0.4,
    raw_text="OCR text",
    needs_human_review=True,
    correlation_id=None
)