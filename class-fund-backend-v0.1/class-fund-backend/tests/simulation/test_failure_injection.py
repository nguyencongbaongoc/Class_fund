"""Failure injection simulation tests."""
from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    LedgerStatus, Message, MessageStatus, Transaction, Upload, UploadStatus, User, Role
)
from app.services.ledger import (
    verify_and_post_from_ai, ProcessingResult, post_revert, post_transaction, calculate_balance, ErrorClassification
)
from tests.simulation.mock_ollama import (
    create_vision_success_receipt,
    create_vision_low_confidence,
    create_vision_missing_fields,
    VISION_TIMEOUT,
    VISION_CONNECTION_REFUSED,
    VISION_INVALID_JSON,
    VISION_EMPTY_RESPONSE,
    VISION_MALFORMED_EXTRACTION,
    VISION_MODEL_UNAVAILABLE,
)
from tests.simulation.mock_worker import create_test_worker


# =============================================================================
# 6.1 AI Failure Injections
# =============================================================================

class TestAIFailureInjection:
    """Test AI failure injection scenarios."""
    
    def _setup_fresh_upload_and_message(self, db, test_account, test_bank_account):
        """Create a fresh upload and message without existing extraction."""
        upload = Upload(
            file_hash="fresh" * 10 + "abcd",
            original_filename="fresh_receipt.png",
            storage_path="uploads/fresh_receipt.png",
            uploaded_by="member-1",
            uploader_name="Test Member",
            status=UploadStatus.PENDING
        )
        db.add(upload)
        db.commit()
        
        msg = Message(
            conversation_id="conv-fresh",
            sender_name="Test",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test",
            attachment_id=upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        return upload, msg
    
    def test_ai_timeout_no_posting(self, db, test_account, test_bank_account, mock_ollama):
        """AI timeout → no financial posting, message needs review."""
        mock_ollama.sim_config.inject_ollama_timeout = True
        
        # Create fresh upload/message without existing extraction
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_connection_refused_no_posting(self, db, test_account, test_bank_account, mock_ollama):
        """AI connection refused → no financial posting."""
        mock_ollama.sim_config.inject_ollama_connection_refused = True
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_invalid_json_no_posting(self, db, test_account, test_bank_account, mock_ollama):
        """AI returns invalid JSON → no financial posting."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = VISION_INVALID_JSON
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_missing_fields_needs_review(self, db, test_account, test_bank_account, mock_ollama):
        """AI missing required fields → NEEDS_HUMAN_REVIEW (or PENDING for retry)."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_missing_fields()
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        # With no extraction found, message goes to PENDING for retry
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_invalid_amount_needs_review(self, db, test_account, test_bank_account, mock_ollama):
        """AI returns invalid amount → NEEDS_HUMAN_REVIEW (or PENDING for retry)."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = VISION_MALFORMED_EXTRACTION
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_low_confidence_needs_review(self, db, test_account, test_bank_account, mock_ollama):
        """AI confidence below threshold → NEEDS_HUMAN_REVIEW (or PENDING for retry)."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_low_confidence(confidence=0.5)
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_model_unavailable_needs_review(self, db, test_account, test_bank_account, mock_ollama):
        """AI model unavailable → NEEDS_HUMAN_REVIEW (or PENDING for retry)."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = VISION_MODEL_UNAVAILABLE
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_empty_response_needs_review(self, db, test_account, test_bank_account, mock_ollama):
        """AI empty response → NEEDS_HUMAN_REVIEW (or PENDING for retry)."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = VISION_EMPTY_RESPONSE
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_circuit_breaker_open_no_posting(self, db, test_account, test_bank_account, mock_ollama):
        """Circuit breaker OPEN → no financial posting."""
        from app.services.ollama_client import CircuitState
        mock_ollama.sim_config.circuit_state = CircuitState.OPEN
        mock_ollama.sim_config.ollama_available = True
        
        upload, msg = self._setup_fresh_upload_and_message(db, test_account, test_bank_account)
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
        
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_ai_retry_behavior_bounded(self, db, test_account, test_bank_account, test_upload, mock_ollama):
        """AI failure retry is bounded (max 3 retries)."""
        mock_ollama.sim_config.inject_ollama_timeout = True
        
        # Create fresh message
        msg = Message(
            conversation_id="conv-retry-bound",
            sender_name="Test",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        worker = create_test_worker(db)
        
        # Process 3 times - should hit max retries
        for _ in range(3):
            claimed = worker.claim_next_message(db)
            if claimed:
                worker.process_message(db, claimed)
        
        db.expire(msg)
        # After 3 failures, should be FAILED
        assert msg.status == MessageStatus.FAILED.value
        assert msg.retry_count >= 3


# =============================================================================
# 6.3 Worker Failure Injections
# =============================================================================

class TestWorkerFailureInjection:
    """Test worker failure injection scenarios."""
    
    def test_worker_crash_during_processing(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Worker crash during processing → message stays PROCESSING, recoverable."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        worker.sim_config.inject_worker_crash = True
        
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        
        with pytest.raises(Exception, match="Worker crashed"):
            worker.process_message(db, claimed)
        
        # Message should still be in processing
        db.expire(claimed)
        assert claimed.status == MessageStatus.PROCESSING.value
        assert claimed.worker_id == "test-worker"
    
    def test_recovery_after_crash(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """New worker recovers message after lease expiry."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Create crashed message state
        crashed_msg = Message(
            conversation_id="conv-crash-recovery",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PROCESSING.value,
            worker_id="crashed-worker",
            claimed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.add(crashed_msg)
        db.commit()
        
        # New worker starts
        worker = create_test_worker(db)
        
        # Should reclaim and process
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        assert claimed.id == crashed_msg.id
        assert claimed.worker_id == "test-worker"
        
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status == MessageStatus.POSTED.value
        assert claimed.transaction_id is not None
    
    def test_crash_after_external_call_recovery(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Crash after AI call but before completion → recoverable."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        worker.sim_config.worker_crash_after_external = True
        
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        
        with pytest.raises(Exception, match="Worker crashed"):
            worker.process_message(db, claimed)
        
        # Message in processing (not completed)
        db.expire(claimed)
        assert claimed.status == MessageStatus.PROCESSING.value
        
        # Simulate lease expiry
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
        
        # Recovery - new worker WITHOUT crash flag
        worker2 = create_test_worker(db)
        worker2.sim_config.worker_crash_after_external = False
        recovered = worker2.claim_next_message(db)
        assert recovered is not None
        assert recovered.id == claimed.id
        
        worker2.process_message(db, recovered)
        db.expire(recovered)
        assert recovered.status == MessageStatus.POSTED.value


# =============================================================================
# 6.4 Queue Failure Injections
# =============================================================================

class TestQueueFailureInjection:
    """Test queue/message failure injection scenarios."""
    
    def test_duplicate_message_no_double_post(self, db, test_account, test_bank_account, test_upload, test_extraction, sim_config):
        """Duplicate message delivery → no duplicate financial posting."""
        sim_config.reset()
        
        # Create two messages with same upload
        msg1 = Message(
            conversation_id="conv-dup1",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test 1",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        msg2 = Message(
            conversation_id="conv-dup2",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test 2",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add_all([msg1, msg2])
        db.commit()
        
        worker = create_test_worker(db)
        
        # Process first
        claimed1 = worker.claim_next_message(db)
        worker.process_message(db, claimed1)
        tx_id = claimed1.transaction_id
        
        # Process second
        claimed2 = worker.claim_next_message(db)
        worker.process_message(db, claimed2)
        
        # Same transaction
        assert claimed2.transaction_id == tx_id
        
        # Only one transaction
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 1
    
    def test_retry_exhaustion_terminal_failed(self, db, test_account, test_bank_account, test_upload, mock_ollama):
        """Retry exhaustion → message marked FAILED (terminal)."""
        mock_ollama.sim_config.inject_ollama_timeout = True
        
        msg = Message(
            conversation_id="conv-retry-exhaust",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        worker = create_test_worker(db)
        
        # Fail 5 times (more than max 3)
        for _ in range(5):
            claimed = worker.claim_next_message(db)
            if claimed:
                worker.process_message(db, claimed)
        
        db.expire(msg)
        assert msg.status == MessageStatus.FAILED.value
        assert msg.processed_at is not None
        assert msg.retry_count >= 3
    
    def test_stale_lease_recovery(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """Stale lease → reclaimed by new worker."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Message with expired lease
        stale_msg = Message(
            conversation_id="conv-stale",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PROCESSING.value,
            worker_id="old-worker",
            claimed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.add(stale_msg)
        db.commit()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        
        assert claimed is not None
        assert claimed.id == stale_msg.id
        assert claimed.worker_id == "test-worker"
    
    def test_invalid_payload_no_upload(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message):
        """Message with no upload → retry."""
        test_message.attachment_id = "non-existent"
        db.commit()
        
        worker = create_test_worker(db)
        worker.process_message(db, test_message)
        
        db.expire(test_message)
        assert test_message.status == MessageStatus.PENDING.value
        assert test_message.retry_count == 1
        assert test_message.error_message == "No upload attached"
    
    def test_invalid_payload_no_extraction(self, db, test_account, test_bank_account, test_upload, test_message):
        """Message with no extraction → retry."""
        worker = create_test_worker(db)
        worker.process_message(db, test_message)
        
        db.expire(test_message)
        assert test_message.status == MessageStatus.PENDING.value
        assert test_message.retry_count == 1
        assert test_message.error_message == "No extraction found"


# =============================================================================
# 6.5 API Failure Injections (Auth)
# =============================================================================

class TestAPIAuthFailureInjection:
    """Test API authentication/authorization failure scenarios."""
    
    def test_missing_token_rejected(self, test_client):
        """Missing Authorization header → 401/403."""
        response = test_client.get("/api/v1/admin/stats")
        assert response.status_code in (401, 403)
    
    def test_invalid_token_rejected(self, test_client):
        """Invalid token → 401/403."""
        response = test_client.get("/api/v1/admin/stats", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code in (401, 403)
    
    def test_expired_token_rejected(self, test_client):
        """Expired token → 401/403."""
        from tests.simulation.mock_supabase import create_mock_expired_token
        response = test_client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {create_mock_expired_token()}"})
        assert response.status_code in (401, 403)
    
    def test_malformed_token_rejected(self, test_client):
        """Malformed token → 401/403."""
        from tests.simulation.mock_supabase import create_mock_malformed_token
        response = test_client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {create_mock_malformed_token()}"})
        assert response.status_code in (401, 403)
    
    def test_member_cannot_access_admin(self, test_client):
        """MEMBER role → 401/403 on admin endpoints."""
        from tests.conftest import get_member_headers
        for endpoint in ["/api/v1/admin/stats", "/api/v1/admin/audit-logs", "/api/v1/admin/health"]:
            response = test_client.get(endpoint, headers=get_member_headers())
            assert response.status_code in (401, 403), f"Endpoint {endpoint}: got {response.status_code}"
    
    def test_public_cannot_access_admin(self, test_client):
        """PUBLIC role → 401/403 on admin endpoints."""
        from tests.conftest import get_public_headers
        for endpoint in ["/api/v1/admin/stats", "/api/v1/admin/audit-logs", "/api/v1/admin/health"]:
            response = test_client.get(endpoint, headers=get_public_headers())
            assert response.status_code in (401, 403), f"Endpoint {endpoint}: got {response.status_code}"


# =============================================================================
# 6.6 Recall/Reversal Failure Injections
# =============================================================================

class TestRecallReversalFailureInjection:
    """Test recall and reversal failure scenarios."""
    
    def test_worker_checks_recall_before_posting(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Worker checks message status before financial posting."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Create recalled message
        recalled_msg = Message(
            conversation_id="conv-recalled-check",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.RECALLED.value,
        )
        db.add(recalled_msg)
        db.commit()
        
        worker = create_test_worker(db)
        worker.process_message(db, recalled_msg)
        
        db.expire(recalled_msg)
        assert recalled_msg.status == MessageStatus.RECALLED.value
        assert recalled_msg.transaction_id is None
    
    def test_double_reversal_prevented(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Double reversal attempt → second fails."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Post transaction
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        original_tx = db.get(Transaction, claimed.transaction_id)
        
        # First reversal
        rev1 = post_revert(db, original=original_tx, actor_id="mod-1", reason="First revert")
        assert rev1.status == ProcessingResult.SUCCESS
        
        # Second reversal should fail
        rev2 = post_revert(db, original=original_tx, actor_id="mod-2", reason="Second revert")
        assert rev2.status == ProcessingResult.FAILED
        assert rev2.error_classification == ErrorClassification.BUSINESS_RULE
        assert "already been reverted" in rev2.error_message
    
    def test_original_entry_unchanged_after_reversal(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Original transaction unchanged after reversal."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        original_amount = original_tx.amount
        original_type = original_tx.type
        original_code = original_tx.transaction_code
        
        # Revert
        post_revert(db, original=original_tx, actor_id="mod-1", reason="Test revert")
        
        # Original unchanged
        db.expire(original_tx)
        assert original_tx.amount == original_amount
        assert original_tx.type == original_type
        assert original_tx.transaction_code == original_code
        assert original_tx.status == LedgerStatus.REVERTED
    
    def test_no_orphaned_reversal_relationship(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Reversal has valid original_entry_id link."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        
        from app.models.models import LedgerEntry
        original_entry = db.execute(
            select(LedgerEntry).where(LedgerEntry.transaction_id == original_tx.id)
        ).scalar_one()
        
        rev_result = post_revert(db, original=original_tx, actor_id="mod-1", reason="Test")
        rev_tx = rev_result.transaction
        
        rev_entry = db.execute(
            select(LedgerEntry).where(LedgerEntry.transaction_id == rev_tx.id)
        ).scalar_one()
        
        assert rev_entry.original_entry_id == original_entry.id
        assert rev_entry.type == LedgerType.REVERT


# =============================================================================
# Idempotency Key Mismatch (409)
# =============================================================================

class TestIdempotencyFailureInjection:
    """Test idempotency key conflict scenarios."""
    
    def test_same_key_different_payload_rejected(self, db, test_account, test_bank_account):
        """Same idempotency key, different payload → VALIDATION error."""
        from app.services.ledger import post_transaction
        
        # First request
        result1 = post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX1", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
            idempotency_key="same_key_test"
        )
        assert result1.status == ProcessingResult.SUCCESS
        
        # Second request, same key, different amount
        result2 = post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("60000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX1", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
            idempotency_key="same_key_test"
        )
        assert result2.status == ProcessingResult.FAILED
        assert result2.error_classification == ErrorClassification.VALIDATION
        assert "reused with a different request" in result2.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])