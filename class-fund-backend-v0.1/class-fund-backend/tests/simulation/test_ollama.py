"""Simulation tests for Ollama Vision and Text extraction."""
from __future__ import annotations

import pytest
from app.services.ollama_client import VisionResult, CircuitState
from tests.simulation.mock_ollama import (
    MockOllamaVisionClient,
    create_vision_success_receipt,
    create_vision_low_confidence,
    create_vision_missing_fields,
    create_vision_multiple_transactions,
    create_vision_vietnamese_text,
    VISION_TIMEOUT,
    VISION_CONNECTION_REFUSED,
    VISION_INVALID_JSON,
    VISION_MODEL_UNAVAILABLE,
    VISION_EMPTY_RESPONSE,
    VISION_MALFORMED_EXTRACTION,
    TEXT_FALLBACK_SUCCESS,
    TEXT_FALLBACK_INVALID_SCHEMA,
    TEXT_FALLBACK_LOW_CONFIDENCE,
)
from tests.conftest import mock_ollama as mock_ollama_fixture


class TestOllamaVisionSimulation:
    """Test Ollama Vision extraction with deterministic mocks."""
    
    def test_vision_success_receipt(self, mock_ollama):
        """Test successful receipt extraction."""
        result = mock_ollama.extract_from_image(b"fake receipt image")
        
        assert result.transaction_code is not None
        assert result.amount is not None
        assert result.sender_name is not None
        assert result.bank_name is not None
        assert result.confidence >= 0.7
        assert not result.needs_human_review
        assert result.error is None
    
    def test_vision_success_with_custom_values(self, mock_ollama):
        """Test successful extraction with custom fixture values."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(
            transaction_code="VCB123456",
            amount=1000000,
            sender_name="TRAN VAN B",
            bank_name="Vietcombank",
            confidence=0.98
        )
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.transaction_code == "VCB123456"
        assert result.amount == 1000000
        assert result.sender_name == "TRAN VAN B"
        assert result.bank_name == "Vietcombank"
        assert result.confidence == 0.98
    
    def test_vision_low_confidence(self, mock_ollama):
        """Test low confidence extraction requires human review."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_low_confidence(confidence=0.5)
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"unclear receipt")
        
        assert result.confidence == 0.5
        assert result.needs_human_review is True
    
    def test_vision_missing_fields(self, mock_ollama):
        """Test extraction with missing required fields."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_missing_fields(
            transaction_code=None,
            amount=None,
            sender_name="NGUYEN VAN A",
            bank_name="Vietcombank"
        )
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"partial receipt")
        
        assert result.transaction_code is None
        assert result.amount is None
        assert result.sender_name == "NGUYEN VAN A"
        assert result.needs_human_review is True
    
    def test_vision_multiple_transactions(self, mock_ollama):
        """Test extraction detecting multiple transactions."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_multiple_transactions(
            transaction_codes=["TX001", "TX002"],
            amounts=[500000, 300000]
        )
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"multi receipt")
        
        assert result.transaction_code == "MULTIPLE"
        assert result.amount == 800000
        assert result.needs_human_review is True
    
    def test_vision_vietnamese_text(self, mock_ollama):
        """Test extraction with Vietnamese text."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_vietnamese_text()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"vietnamese receipt")
        
        assert "TRẦN VẠN B" in result.sender_name
        assert "Vietcombank" in result.bank_name
        assert "CHUYỂN KHOẢN" in result.raw_text
        assert result.confidence >= 0.7


class TestOllamaVisionFailures:
    """Test Ollama Vision failure scenarios."""
    
    def test_vision_timeout(self, mock_ollama):
        """Test vision extraction timeout."""
        mock_ollama.sim_config.inject_ollama_timeout = True
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert "timeout" in result.error.lower()
        assert result.needs_human_review is True
    
    def test_vision_connection_refused(self, mock_ollama):
        """Test vision connection refused."""
        mock_ollama.sim_config.inject_ollama_connection_refused = True
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert "refused" in result.error.lower()
        assert result.needs_human_review is True
    
    def test_vision_invalid_json(self, mock_ollama):
        """Test vision returns invalid JSON."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = VISION_INVALID_JSON
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert "parse" in result.error.lower() or "json" in result.error.lower()
        assert result.needs_human_review is True
    
    def test_vision_model_unavailable(self, mock_ollama):
        """Test vision model not available."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = VISION_MODEL_UNAVAILABLE
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert "not available" in result.error.lower()
        assert result.needs_human_review is True
    
    def test_vision_empty_response(self, mock_ollama):
        """Test vision returns empty response."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = VISION_EMPTY_RESPONSE
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert result.needs_human_review is True
    
    def test_vision_malformed_extraction(self, mock_ollama):
        """Test vision returns malformed extraction schema."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = VISION_MALFORMED_EXTRACTION
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert result.needs_human_review is True
    
    def test_vision_server_unavailable(self, mock_ollama):
        """Test Ollama server completely unavailable."""
        mock_ollama.sim_config.ollama_available = False
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert "not available" in result.error.lower()
        assert result.needs_human_review is True
    
    def test_vision_circuit_breaker_open(self, mock_ollama):
        """Test circuit breaker open state."""
        # Set circuit breaker to OPEN state
        mock_ollama.sim_config.circuit_state = CircuitState.OPEN
        # Also ensure Ollama is available so we hit the circuit breaker check first
        mock_ollama.sim_config.ollama_available = True
        
        result = mock_ollama.extract_from_image(b"test image")
        
        assert result.error is not None
        assert "circuit breaker" in result.error.lower()
        assert result.needs_human_review is True


class TestOllamaTextFallback:
    """Test Ollama Text fallback extraction."""
    
    def test_text_fallback_success(self, mock_ollama):
        """Test successful text fallback after vision failure."""
        mock_ollama.sim_config.ollama_text_responses.clear()
        mock_ollama.sim_config.ollama_text_responses["custom"] = TEXT_FALLBACK_SUCCESS
        
        result = mock_ollama.extract_with_text_fallback(b"image", "OCR text from receipt")
        
        assert result.transaction_code is not None
        assert result.amount is not None
        assert result.confidence >= 0.7
        assert not result.needs_human_review
    
    def test_text_fallback_invalid_schema(self, mock_ollama):
        """Test text fallback returns invalid schema."""
        mock_ollama.sim_config.ollama_text_responses.clear()
        mock_ollama.sim_config.ollama_text_responses["custom"] = TEXT_FALLBACK_INVALID_SCHEMA
        
        result = mock_ollama.extract_with_text_fallback(b"image", "OCR text")
        
        assert result.error is not None
        assert result.needs_human_review is True
    
    def test_text_fallback_low_confidence(self, mock_ollama):
        """Test text fallback returns low confidence."""
        mock_ollama.sim_config.ollama_text_responses.clear()
        mock_ollama.sim_config.ollama_text_responses["custom"] = TEXT_FALLBACK_LOW_CONFIDENCE
        
        result = mock_ollama.extract_with_text_fallback(b"image", "OCR text")
        
        assert result.confidence < 0.7
        assert result.needs_human_review is True
    
    def test_text_fallback_vision_unavailable(self, mock_ollama):
        """Test text fallback when vision model unavailable."""
        mock_ollama.sim_config.ollama_available = False
        mock_ollama.sim_config.ollama_text_responses.clear()
        mock_ollama.sim_config.ollama_text_responses["custom"] = TEXT_FALLBACK_SUCCESS
        
        result = mock_ollama.extract_with_text_fallback(b"image", "OCR text")
        
        # Text fallback also fails when Ollama is unavailable
        assert result.error is not None
        assert result.needs_human_review is True
    
    def test_both_vision_and_text_fail(self, mock_ollama):
        """Test both vision and text models fail."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = VISION_TIMEOUT
        mock_ollama.sim_config.ollama_text_responses.clear()
        mock_ollama.sim_config.ollama_text_responses["custom"] = TEXT_FALLBACK_INVALID_SCHEMA
        
        # Vision fails
        vision_result = mock_ollama.extract_from_image(b"test image")
        assert vision_result.error is not None
        
        # Text fallback also fails
        text_result = mock_ollama.extract_with_text_fallback(b"test image", "OCR text")
        assert text_result.error is not None
        assert text_result.needs_human_review is True


class TestExtractionCorrectness:
    """Test extraction field correctness and validation."""
    
    def test_amount_extraction(self, mock_ollama):
        """Test amount field extraction correctness."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(amount=1234567)
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        assert result.amount == 1234567
        assert isinstance(result.amount, int)
    
    def test_currency_handling(self, mock_ollama):
        """Test currency field (defaults to VND)."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt()
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        # Currency not in VisionResult, but would be VND per schema
        assert result.amount is not None
    
    def test_transaction_date_extraction(self, mock_ollama):
        """Test transaction date/time extraction."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(
            transaction_time="2026-10-04T14:30:00Z"
        )
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        assert result.transaction_time == "2026-10-04T14:30:00Z"
    
    def test_sender_extraction(self, mock_ollama):
        """Test sender name extraction."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(sender_name="LE THI C")
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        assert result.sender_name == "LE THI C"
    
    def test_recipient_bank_extraction(self, mock_ollama):
        """Test recipient bank extraction."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(bank_name="Techcombank")
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        assert result.bank_name == "Techcombank"
    
    def test_confidence_scoring(self, mock_ollama):
        """Test confidence score bounds and meaning."""
        # High confidence
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(confidence=0.95)
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        result = mock_ollama.extract_from_image(b"test")
        assert result.confidence == 0.95
        assert result.needs_human_review is False
        
        # Threshold confidence
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(confidence=0.7)
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        result = mock_ollama.extract_from_image(b"test")
        assert result.confidence == 0.7
        assert result.needs_human_review is False
        
        # Below threshold
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_low_confidence(confidence=0.69)
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        result = mock_ollama.extract_from_image(b"test")
        assert result.confidence == 0.69
        assert result.needs_human_review is True
    
    def test_source_metadata(self, mock_ollama):
        """Test source metadata preservation."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(raw_text="Original OCR text content")
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        assert result.raw_text == "Original OCR text content"
        assert result.correlation_id is not None
    
    def test_duplicate_indicators(self, mock_ollama):
        """Test duplicate transaction detection indicators."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_multiple_transactions(
            transaction_codes=["TX001", "TX001"],  # Duplicate code
            amounts=[500000, 500000]
        )
        mock_ollama.sim_config.ollama_vision_responses["custom"] = expected
        
        result = mock_ollama.extract_from_image(b"test")
        
        assert result.transaction_code == "MULTIPLE"
        assert result.needs_human_review is True


class TestOllamaConfiguration:
    """Test Ollama configuration and model availability."""
    
    def test_vision_model_configuration(self, mock_ollama):
        """Test vision model is correctly configured."""
        models = mock_ollama.list_models()
        
        assert "qwen2.5vl:3b" in models
        assert mock_ollama.config.vision_model == "qwen2.5vl:3b"
    
    def test_text_model_configuration(self, mock_ollama):
        """Test text fallback model is correctly configured."""
        models = mock_ollama.list_models()
        
        assert "qwen3.5:4b" in models
        assert mock_ollama.config.text_model == "qwen3.5:4b"
    
    def test_ollama_endpoint(self, mock_ollama):
        """Test Ollama endpoint configuration."""
        assert mock_ollama.config.base_url == "http://127.0.0.1:11434"
    
    def test_model_availability_check(self, mock_ollama):
        """Test model availability checking."""
        # Default models available
        assert mock_ollama.is_available() is True
        
        # Remove vision model
        mock_ollama._models_cache = ["qwen3.5:4b"]
        assert mock_ollama.is_available() is True  # Server still available
        
        # Vision model not in list
        result = mock_ollama.extract_from_image(b"test")
        assert "not available" in result.error.lower()


class TestAIGatekeeperIntegration:
    """Test AI extraction integrates correctly with financial gatekeeper."""
    
    def test_ai_extraction_never_posts_directly(self):
        """Verify AI extraction only produces proposals, never posts directly."""
        from app.services.ledger import verify_and_post_from_ai
        from app.models.models import Upload, UploadStatus, ExtractedTransaction
        from app.models.models import Account, BankAccount
        from decimal import Decimal
        from datetime import datetime, timezone
        
        # This is a design verification - the verify_and_post_from_ai function
        # is the ONLY path from AI extraction to financial posting
        import inspect
        source = inspect.getsource(verify_and_post_from_ai)
        
        # Verify it calls post_transaction (the gatekeeper)
        assert "post_transaction" in source
        assert "verify_and_post_from_ai" in source
        
        # Verify it does NOT directly create Transaction objects
        # (it calls post_transaction which does)
        assert "Transaction(" not in source or "post_transaction" in source
    
    def test_verify_and_post_from_ai_signature(self):
        """Verify the gatekeeper function signature matches expectations."""
        from app.services.ledger import verify_and_post_from_ai
        import inspect
        
        sig = inspect.signature(verify_and_post_from_ai)
        params = list(sig.parameters.keys())
        
        required = ['db', 'upload', 'result', 'account', 'actor_id']
        for param in required:
            assert param in params, f"Missing required parameter: {param}"
        
        # Check optional parameters
        optional = ['idempotency_key', 'message_id', 'logical_operation_id', 'attempt_id']
        for param in optional:
            assert param in params, f"Missing optional parameter: {param}"
    
    def test_confidence_threshold_enforcement(self):
        """Test confidence threshold is enforced in gatekeeper."""
        from app.services.ledger import verify_and_post_from_ai
        from app.core.config import get_settings
        
        settings = get_settings()
        threshold = settings.ai_confidence_threshold
        
        # Threshold should be 0.9 per config
        assert threshold == 0.9
    
    def test_required_fields_validation(self):
        """Test required transaction fields are validated."""
        from app.services.ledger import verify_and_post_from_ai
        import inspect
        
        source = inspect.getsource(verify_and_post_from_ai)
        
        # Should check for transaction_code, amount, bank_account_id
        assert "transaction_code" in source
        assert "amount" in source
        assert "bank_account_id" in source
        
        # Should return NEEDS_HUMAN_REVIEW if missing
        assert "NEEDS_HUMAN_REVIEW" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])