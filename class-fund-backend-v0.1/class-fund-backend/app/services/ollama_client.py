"""Ollama Vision Adapter for receipt extraction."""
import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field


class OllamaConfig:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.vision_model = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:3b")
        self.text_model = os.getenv("OLLAMA_TEXT_MODEL", "qwen3.5:4b")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("OLLAMA_RETRY_DELAY", "1.0"))


@dataclass
class VisionResult:
    transaction_code: Optional[str] = None
    amount: Optional[int] = None
    sender_name: Optional[str] = None
    bank_name: Optional[str] = None
    transaction_time: Optional[str] = None
    confidence: float = 0.0
    raw_text: Optional[str] = None
    needs_human_review: bool = False
    error: Optional[str] = None


class VisionExtractionSchema(BaseModel):
    """Expected JSON schema from vision model."""
    transaction_code: Optional[str] = None
    amount: Optional[int] = None
    sender_name: Optional[str] = None
    bank_name: Optional[str] = None
    transaction_time: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    raw_text: Optional[str] = None


class OllamaVisionClient:
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client = httpx.Client(timeout=self.config.timeout)
        
    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> list[str]:
        """List available models."""
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except Exception:
            return []
    
    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image to base64."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def _build_vision_prompt(self) -> str:
        """Build prompt for receipt extraction."""
        return """Extract the following information from this bank transfer receipt image. Return ONLY valid JSON with these fields:
{
  "transaction_code": "string or null",
  "amount": "integer (in VND) or null",
  "sender_name": "string or null",
  "bank_name": "string or null",
  "transaction_time": "ISO 8601 string or null",
  "confidence": "float 0-1",
  "raw_text": "string or null"
}

Look for:
- Transaction code/reference number (e.g., FT26277123456789, VCB123456789)
- Amount in VND (numbers only, no currency symbol)
- Sender/account holder name
- Bank name (e.g., Vietcombank, Techcombank, BIDV, MBBank)
- Transaction date/time

If any field is unclear or missing, use null. Set confidence based on clarity (0.0-1.0)."""
    
    def extract_from_image(self, image_bytes: bytes) -> VisionResult:
        """Extract receipt data from image using vision model."""
        if not self.is_available():
            return VisionResult(
                error="Ollama server not available",
                needs_human_review=True
            )
        
        # Check if vision model is available
        models = self.list_models()
        if self.config.vision_model not in models:
            return VisionResult(
                error=f"Vision model {self.config.vision_model} not available. Available: {models}",
                needs_human_review=True
            )
        
        image_b64 = self._encode_image(image_bytes)
        prompt = self._build_vision_prompt()
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.vision_model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9,
                        }
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").strip()
                    
                    # Parse JSON response
                    try:
                        extracted = json.loads(response_text)
                        schema = VisionExtractionSchema(**extracted)
                        
                        return VisionResult(
                            transaction_code=schema.transaction_code,
                            amount=schema.amount,
                            sender_name=schema.sender_name,
                            bank_name=schema.bank_name,
                            transaction_time=schema.transaction_time,
                            confidence=schema.confidence,
                            raw_text=schema.raw_text,
                            needs_human_review=schema.confidence < 0.7
                        )
                    except json.JSONDecodeError as e:
                        return VisionResult(
                            error=f"Failed to parse vision model output: {e}",
                            raw_text=response_text,
                            needs_human_review=True
                        )
                    except Exception as e:
                        return VisionResult(
                            error=f"Validation error: {e}",
                            raw_text=response_text,
                            needs_human_review=True
                        )
                else:
                    error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                    if attempt == self.config.max_retries - 1:
                        return VisionResult(error=error_msg, needs_human_review=True)
                        
            except httpx.TimeoutException:
                error_msg = f"Ollama request timeout (attempt {attempt + 1}/{self.config.max_retries})"
                if attempt == self.config.max_retries - 1:
                    return VisionResult(error=error_msg, needs_human_review=True)
            except Exception as e:
                error_msg = f"Ollama request failed: {e}"
                if attempt == self.config.max_retries - 1:
                    return VisionResult(error=error_msg, needs_human_review=True)
            
            # Wait before retry
            time.sleep(self.config.retry_delay * (attempt + 1))
        
        return VisionResult(
            error="Max retries exceeded",
            needs_human_review=True
        )
    
    def extract_with_text_fallback(self, image_bytes: bytes, ocr_text: str) -> VisionResult:
        """Use text model as fallback with OCR text."""
        if not self.is_available():
            return VisionResult(
                error="Ollama server not available",
                needs_human_review=True
            )
        
        models = self.list_models()
        if self.config.text_model not in models:
            return VisionResult(
                error=f"Text model {self.config.text_model} not available",
                needs_human_review=True
            )
        
        prompt = f"""Extract the following information from this OCR text of a bank transfer receipt. Return ONLY valid JSON:
{{
  "transaction_code": "string or null",
  "amount": "integer (in VND) or null",
  "sender_name": "string or null",
  "bank_name": "string or null",
  "transaction_time": "ISO 8601 string or null",
  "confidence": "float 0-1",
  "raw_text": "string"
}}

OCR Text:
{ocr_text}

If any field is unclear or missing, use null. Set confidence based on clarity (0.0-1.0)."""
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.text_model,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9,
                        }
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").strip()
                    
                    try:
                        extracted = json.loads(response_text)
                        schema = VisionExtractionSchema(**extracted)
                        
                        return VisionResult(
                            transaction_code=schema.transaction_code,
                            amount=schema.amount,
                            sender_name=schema.sender_name,
                            bank_name=schema.bank_name,
                            transaction_time=schema.transaction_time,
                            confidence=schema.confidence,
                            raw_text=schema.raw_text,
                            needs_human_review=schema.confidence < 0.7
                        )
                    except Exception as e:
                        if attempt == self.config.max_retries - 1:
                            return VisionResult(
                                error=f"Failed to parse text model output: {e}",
                                raw_text=response_text,
                                needs_human_review=True
                            )
                else:
                    if attempt == self.config.max_retries - 1:
                        return VisionResult(
                            error=f"Ollama API error: {response.status_code}",
                            needs_human_review=True
                        )
                        
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    return VisionResult(
                        error=f"Ollama request failed: {e}",
                        needs_human_review=True
                    )
            
            time.sleep(self.config.retry_delay * (attempt + 1))
        
        return VisionResult(
            error="Max retries exceeded",
            needs_human_review=True
        )
    
    def close(self):
        self.client.close()


# Global instance
_vision_client: Optional[OllamaVisionClient] = None


def get_vision_client() -> OllamaVisionClient:
    global _vision_client
    if _vision_client is None:
        _vision_client = OllamaVisionClient()
    return _vision_client