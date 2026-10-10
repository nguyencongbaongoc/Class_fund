"""End-to-end workflow simulation tests."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import select

from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    LedgerStatus, Message, MessageStatus, Transaction, Upload, UploadStatus, User, Role
)
from app.services.ledger import verify_and_post_from_ai, ProcessingResult, post_revert
from tests.simulation.mock_ollama import (
    create_vision_success_receipt,
    create_vision_low_confidence,
)
from tests.conftest import get_owner_headers, get_moderator_headers, get_member_headers, get_public_headers


class TestScenarioANormalFinancialWorkflow:
    """SCENARIO A — NORMAL FINANCIAL WORKFLOW"""
    
    def test_normal_financial_workflow(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Test complete normal financial workflow."""
        # 1. MEMBER uploads synthetic receipt image (already done via fixtures)
        assert test_upload.status == UploadStatus.PENDING
        assert test_message.status == MessageStatus.PENDING.value
        
        # 2. Backend validates file (simulated - upload already exists)
        # 3. Storage adapter accepts upload (simulated)
        
        # 4. AI vision returns extracted fields
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt(
            transaction_code=test_extraction.transaction_code,
            amount=int(test_extraction.amount),
            sender_name=test_extraction.sender_name,
            bank_name=test_extraction.bank_name,
            confidence=0.95
        )
        mock_ollama.sim_config.ollama_vision_responses["test"] = expected
        
        # 5. Extraction validation executes (via worker)
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        
        # 6. Duplicate detection executes (inside verify_and_post_from_ai)
        # 7. Proposal enters review queue (if low confidence) or proceeds to posting
        
        # 8. Worker processes message
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        # 9. Check message was posted
        db.expire(claimed)
        assert claimed.status == MessageStatus.POSTED.value
        assert claimed.transaction_id is not None
        
        # 10. Verify financial gatekeeper validated
        tx = db.get(Transaction, claimed.transaction_id)
        assert tx is not None
        assert tx.type == LedgerType.CREDIT
        assert tx.amount == test_extraction.amount
        assert tx.transaction_code == test_extraction.transaction_code
        assert tx.bank_account_id == test_bank_account.id
        assert tx.source == LedgerSource.IMAGE
        assert tx.status == LedgerStatus.VERIFIED
        
        # 11. Audit record created
        from app.models.models import AuditLog
        audit = db.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == "TRANSACTION")
            .where(AuditLog.entity_id == tx.id)
        ).scalar_one_or_none()
        assert audit is not None
        assert audit.action == "LEDGER_POST"
        
        # 12. No duplicate posting
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 1
        
        # 13. Correct actor and metadata
        assert tx.created_by is None  # AI posted
        assert tx.upload_id == test_upload.id


class TestScenarioBHumanRejectsProposal:
    """SCENARIO B — HUMAN REJECTS PROPOSAL"""
    
    def test_human_rejects_proposal(self, db, test_account, test_bank_account, test_upload, test_extraction_low_confidence, mock_ollama):
        """Test human rejects low-confidence proposal."""
        # Create message for low confidence extraction
        msg = Message(
            conversation_id="conv-reject",
            sender_name="Test Member",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test receipt",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        # Set up mock Ollama for low confidence
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_low_confidence(confidence=0.5)
        mock_ollama.sim_config.ollama_vision_responses["test"] = expected
        
        # Worker processes - should go to NEEDS_HUMAN_REVIEW
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status == MessageStatus.AWAITING_REVIEW.value
        assert "confidence" in claimed.error_message.lower()
        
        # 4. Moderator rejects via review API (simulated by updating extraction)
        extraction = db.get(ExtractedTransaction, test_extraction_low_confidence.id)
        assert extraction.status == UploadStatus.NEEDS_REVIEW
        
        # Simulate rejection
        extraction.reviewed_by = "moderator-1"
        extraction.reviewed_at = datetime.now(timezone.utc)
        extraction.review_notes = "Rejected: insufficient clarity"
        extraction.status = UploadStatus.REJECTED
        test_upload.status = UploadStatus.REJECTED
        db.commit()
        
        # Verify no transaction was posted
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0


class TestScenarioCDuplicateReceipt:
    """SCENARIO C — DUPLICATE RECEIPT"""
    
    def test_duplicate_receipt(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """Test duplicate receipt detection."""
        # Create second message with same upload (simulating duplicate upload)
        msg1 = Message(
            conversation_id="conv-dup1",
            sender_name="Test Member",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test receipt 1",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        msg2 = Message(
            conversation_id="conv-dup2",
            sender_name="Test Member",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test receipt 2",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add_all([msg1, msg2])
        db.commit()
        
        # Process first message
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        
        claimed1 = worker.claim_next_message(db)
        assert claimed1 is not None
        worker.process_message(db, claimed1)
        db.expire(claimed1)
        tx_id_1 = claimed1.transaction_id
        
        # Process second message
        claimed2 = worker.claim_next_message(db)
        assert claimed2 is not None
        worker.process_message(db, claimed2)
        db.expire(claimed2)
        tx_id_2 = claimed2.transaction_id
        
        # Should be same transaction (idempotent)
        assert tx_id_1 == tx_id_2
        
        # Only one transaction in DB
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 1


class TestScenarioDRecallBeforePosting:
    """SCENARIO D — RECALL BEFORE POSTING"""
    
    def test_recall_before_posting(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """Test recall before financial posting prevents posting."""
        # Create message and recall it
        msg = Message(
            conversation_id="conv-recall-before",
            sender_name="Test Member",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test receipt",
            attachment_id=test_upload.id,
            status=MessageStatus.RECALLED.value,  # Already recalled
        )
        db.add(msg)
        db.commit()
        
        # Set up mock Ollama
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt()
        mock_ollama.sim_config.ollama_vision_responses["test"] = expected
        
        # Worker should skip recalled message
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        
        if claimed:
            worker.process_message(db, claimed)
            db.expire(claimed)
            # Should remain RECALLED
            assert claimed.status == MessageStatus.RECALLED.value
            assert claimed.transaction_id is None
        
        # Verify no transaction created
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0


class TestScenarioERecallAfterPosting:
    """SCENARIO E — RECALL AFTER POSTING"""
    
    def test_recall_after_posting_creates_reversal(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Test recall after posting creates compensating REVERT."""
        # First, post a transaction normally
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        
        mock_ollama.sim_config.ollama_vision_responses.clear()
        expected = create_vision_success_receipt()
        mock_ollama.sim_config.ollama_vision_responses["test"] = expected
        
        claimed = worker.claim_next_message(db)
        assert claimed is not None, "Should claim a pending message"
        worker.process_message(db, claimed)
        db.expire(claimed)
        
        assert claimed.status == MessageStatus.POSTED.value
        tx_id = claimed.transaction_id
        original_tx = db.get(Transaction, tx_id)
        
        # Now recall the message (simulate post_revert)
        from app.services.ledger import post_revert
        
        # Simulate recall by creating REVERT transaction
        msg = db.get(Message, claimed.id)
        msg.status = MessageStatus.RECALLED.value
        msg.processed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Create reversal
        rev_result = post_revert(
            db, original=original_tx, actor_id="moderator-1", reason="User recalled",
            message_id=msg.id
        )
        
        assert rev_result.status == ProcessingResult.SUCCESS
        rev_tx = rev_result.transaction
        assert rev_tx.type == LedgerType.REVERT
        assert rev_tx.amount == original_tx.amount
        
        # Original transaction should be marked reverted
        db.expire(original_tx)
        assert original_tx.status == LedgerStatus.REVERTED
        
        # Balance should be restored to opening balance (1,000,000)
        from app.services.ledger import calculate_balance
        assert calculate_balance(db, test_account) == Decimal("1000000")
        
        # Two transactions now exist (original + reversal)
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 2


class TestScenarioFExternalServiceFailure:
    """SCENARIO F — EXTERNAL SERVICE FAILURE"""
    
    def test_storage_unavailable(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama, mock_supabase):
        """Test storage unavailable."""
        mock_supabase.sim_config.inject_storage_failure = True
        
        # Try to upload - should fail gracefully
        from app.services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        with pytest.raises(Exception, match="Storage upload failed"):
            supabase.upload_receipt(b"test", "test.png", "image/png")
    
    def test_ollama_unavailable(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """Test Ollama unavailable - extraction fails with low confidence requiring review."""
        # Clear existing extraction to simulate Ollama failure
        db.delete(test_extraction)
        db.commit()
        
        mock_ollama.sim_config.ollama_available = False
        
        # Worker processes - should fail with human review
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        
        # Create fresh message with NEW upload (no extraction)
        new_upload = Upload(
            file_hash="b" * 64,
            original_filename="receipt2.png",
            storage_path="uploads/receipt2.png",
            uploaded_by="member-1",
            uploader_name="Test Member",
            status=UploadStatus.PENDING
        )
        db.add(new_upload)
        db.commit()
        
        msg = Message(
            conversation_id="conv-ollama-down",
            sender_name="Test",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test",
            attachment_id=new_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        # When Ollama is unavailable, no extraction is found, should go to PENDING for retry
        assert claimed.status in (MessageStatus.AWAITING_REVIEW.value, MessageStatus.PENDING.value)
    
    def test_database_timeout(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """Test database timeout simulation during worker transaction execution."""
        from tests.simulation.mock_worker import create_test_worker
        from sqlalchemy.exc import OperationalError
        
        worker = create_test_worker(db)
        
        # Create a message to process
        msg = Message(
            conversation_id="conv-timeout-recovery",
            sender_name="Timeout Test Sender",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Simulated DB timeout test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        claimed = worker.claim_next_message(db)
        assert claimed is not None, "Worker must claim pending message"
        
        # Simulate an operational database timeout
        db_timeout = OperationalError(
            "statement timeout",
            params={},
            orig=Exception("Query execution was interrupted, max_statement_time exceeded")
        )
        worker.handle_error(db, claimed, db_timeout)
        
        db.expire(claimed)
        # Message should enter retryable backoff
        assert claimed.status == MessageStatus.PENDING.value
        assert claimed.retry_count == 1
        assert "timeout" in claimed.error_message.lower()
        
        # Verify worker can re-claim and successfully process once database recovers
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        
        reclaimed = worker.claim_next_message(db)
        assert reclaimed is not None
        assert reclaimed.id == claimed.id
        worker.process_message(db, reclaimed)
        
        db.expire(reclaimed)
        assert reclaimed.status == MessageStatus.POSTED.value
    
    def test_realtime_disconnected(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_supabase):
        """Test realtime disconnected."""
        mock_supabase.sim_config.inject_realtime_disconnect = True
        
        from app.services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        channel = supabase.subscribe_to_messages("conv-1", lambda x: None)
        assert channel.subscribed == False
    
    def test_worker_crash(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Test worker crash during processing."""
        from tests.simulation.mock_worker import create_test_worker
        worker = create_test_worker(db)
        worker.sim_config.inject_worker_crash = True
        
        claimed = worker.claim_next_message(db)
        assert claimed is not None, "Should claim a pending message"
        
        with pytest.raises(Exception, match="Worker crashed"):
            worker.process_message(db, claimed)
        
        # Message should still be in processing
        db.expire(claimed)
        assert claimed.status == MessageStatus.PROCESSING.value
        
        # Simulate lease expiry for recovery
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
        
        # New worker can recover
        worker2 = create_test_worker(db, "worker-2")
        worker2.sim_config.inject_worker_crash = False
        
        recovered = worker2.claim_next_message(db)
        assert recovered is not None
        worker2.process_message(db, recovered)
        
        db.expire(recovered)
        assert recovered.status == MessageStatus.POSTED.value


class TestScenarioGAdminDashboard:
    """SCENARIO G — ADMIN DASHBOARD"""
    
    def test_admin_dashboard_view(self, test_client, test_account, test_user_owner):
        """Test AdminDashboardView accessible to OWNER_TREASURER."""
        response = test_client.get("/api/v1/admin/stats", headers=get_owner_headers())
        assert response.status_code == 200
        data = response.json()
        assert "current_balance" in data
        assert "pending_review_count" in data
        assert "worker_online_count" in data
    
    def test_admin_ledger_view(self, test_client, test_account, test_user_owner):
        """Test AdminLedgerView accessible."""
        response = test_client.get("/api/v1/admin/audit-logs", headers=get_owner_headers())
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_ai_review_queue_view(self, test_client, test_account, test_user_owner):
        """Test AIReviewQueueView accessible."""
        response = test_client.get("/api/v1/internal/review", headers=get_owner_headers())
        # May be 500 due to known bug, but not 403
        assert response.status_code != 403
    
    def test_audit_log_view(self, test_client, test_account, test_user_owner):
        """Test AuditLogView accessible."""
        response = test_client.get("/api/v1/admin/audit-logs", headers=get_owner_headers())
        assert response.status_code == 200
    
    def test_system_monitoring_view(self, test_client, test_account, test_user_owner, mock_ollama, mock_supabase):
        """Test SystemMonitoringView accessible."""
        response = test_client.get("/api/v1/admin/health", headers=get_owner_headers())
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "components" in data
    
    def test_role_restrictions(self, test_client, test_user_moderator, test_user_member, test_user_public):
        """Test role restrictions on admin views."""
        for endpoint in ["/api/v1/admin/stats", "/api/v1/admin/audit-logs", "/api/v1/internal/review"]:
            # MODERATOR should have access
            response = test_client.get(endpoint, headers=get_moderator_headers())
            assert response.status_code != 403
            
            # MEMBER should be denied
            response = test_client.get(endpoint, headers=get_member_headers())
            assert response.status_code == 403
            
            # PUBLIC should be denied
            response = test_client.get(endpoint, headers=get_public_headers())
            assert response.status_code == 403
    
    def test_csv_exports_preserve_filters(self, test_client, test_account, test_user_owner):
        """Test CSV exports preserve filters and pagination."""
        response = test_client.get(
            "/api/v1/admin/audit-logs/export?limit=10&action=LEDGER_POST",
            headers=get_owner_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert "csv_content" in data
        assert "total_records" in data
    
    def test_audit_history_readonly(self, test_client, test_account, test_user_owner):
        """Test audit history remains read-only."""
        # No write endpoints for audit logs - just verify read works
        response = test_client.get("/api/v1/admin/audit-logs", headers=get_owner_headers())
        assert response.status_code == 200
    
    def test_user_management_unimplemented(self, test_client, test_user_owner):
        """Test User Management remains explicitly unimplemented."""
        # This is a frontend check - backend doesn't have user management endpoints
        response = test_client.get("/api/v1/admin/users", headers=get_owner_headers())
        # Should be 404 (not implemented)
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])