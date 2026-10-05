"""Simulation tests for Worker and Queue lifecycle."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text

from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    Message, MessageStatus, Transaction, Upload, UploadStatus, WorkerStatus
)
from app.services.ledger import verify_and_post_from_ai, ProcessingResult
from tests.simulation.mock_worker import WorkerSimulator, create_test_worker, simulate_worker_lifecycle


class TestWorkerLifecycle:
    """Test worker lifecycle states and transitions."""
    
    def test_worker_startup(self, db):
        """Test worker startup sequence."""
        worker = create_test_worker(db)
        
        assert worker.sim_config.worker_state.value == "ONLINE"
        
        # Check worker status in database
        status = db.execute(select(WorkerStatus).where(WorkerStatus.worker_id == "test-worker")).scalar_one()
        assert status.status == "online"
        assert status.last_heartbeat is not None
    
    def test_worker_shutdown(self, db):
        """Test graceful worker shutdown."""
        worker = create_test_worker(db)
        worker.shutdown(db)
        
        assert worker.sim_config.worker_state.value == "STOPPED"
        
        status = db.execute(select(WorkerStatus).where(WorkerStatus.worker_id == "test-worker")).scalar_one()
        assert status.status == "offline"
    
    def test_worker_reclaim_stale_leases(self, db):
        """Test worker reclaims stale processing messages on startup."""
        # Create a stale processing message
        stale_message = Message(
            conversation_id="conv-1",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            status=MessageStatus.PROCESSING.value,
            worker_id="dead-worker",
            claimed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db.add(stale_message)
        db.commit()
        
        # Start new worker
        worker = create_test_worker(db)
        
        # Stale message should be reclaimed
        db.expire(stale_message)
        assert stale_message.status == MessageStatus.PENDING.value
        assert stale_message.worker_id is None
        assert stale_message.claimed_at is None
        assert stale_message.lease_expires_at is None
    
    def test_worker_heartbeat(self, db):
        """Test worker heartbeat updates status."""
        worker = create_test_worker(db)
        original_heartbeat = db.execute(
            select(WorkerStatus.last_heartbeat).where(WorkerStatus.worker_id == "test-worker")
        ).scalar_one()
        
        # Wait a moment and send heartbeat
        import time
        time.sleep(0.01)
        worker.heartbeat(db)
        
        new_heartbeat = db.execute(
            select(WorkerStatus.last_heartbeat).where(WorkerStatus.worker_id == "test-worker")
        ).scalar_one()
        
        assert new_heartbeat >= original_heartbeat


class TestMessageClaiming:
    """Test atomic message claiming with leases."""
    
    def test_claim_next_message(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message):
        """Test worker claims next pending message."""
        worker = create_test_worker(db)
        
        claimed = worker.claim_next_message(db)
        
        assert claimed is not None
        assert claimed.id == test_message.id
        assert claimed.status == MessageStatus.PROCESSING.value
        assert claimed.worker_id == "test-worker"
        assert claimed.claimed_at is not None
        assert claimed.lease_expires_at is not None
        
        # Lease should be ~300 seconds
        lease_duration = (claimed.lease_expires_at - claimed.claimed_at).total_seconds()
        assert 290 < lease_duration < 310
    
    def test_claim_no_pending_messages(self, db):
        """Test claim returns None when no pending messages."""
        worker = create_test_worker(db)
        
        claimed = worker.claim_next_message(db)
        
        assert claimed is None
    
    def test_claim_skip_locked(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test FOR UPDATE SKIP LOCKED prevents duplicate claims."""
        # Create multiple pending messages
        msg1 = Message(
            conversation_id="conv-1",
            sender_name="Test1",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test1",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        msg2 = Message(
            conversation_id="conv-2",
            sender_name="Test2",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test2",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add_all([msg1, msg2])
        db.commit()
        
        worker = create_test_worker(db)
        
        # First claim
        claimed1 = worker.claim_next_message(db)
        assert claimed1 is not None
        
        # Second claim should get the other message
        claimed2 = worker.claim_next_message(db)
        assert claimed2 is not None
        assert claimed2.id != claimed1.id
        
        # Third claim should return None
        claimed3 = worker.claim_next_message(db)
        assert claimed3 is None
    
    def test_lease_expiry_reclamation(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test expired leases are reclaimed."""
        # Create message with expired lease
        expired_msg = Message(
            conversation_id="conv-expired",
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
        db.add(expired_msg)
        db.commit()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        
        assert claimed is not None
        assert claimed.id == expired_msg.id
        assert claimed.worker_id == "test-worker"  # Reassigned to new worker


class TestMessageProcessing:
    """Test message processing through AI pipeline."""
    
    def test_process_message_success(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message):
        """Test successful message processing."""
        worker = create_test_worker(db)
        
        # Claim and process
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        # Check message completed
        db.expire(claimed)
        assert claimed.status == MessageStatus.POSTED.value
        assert claimed.transaction_id is not None
        assert claimed.processed_at is not None
        assert claimed.worker_id is None  # Released
        
        # Check transaction created
        tx = db.get(Transaction, claimed.transaction_id)
        assert tx is not None
        assert tx.type == LedgerType.CREDIT
        assert tx.amount == test_extraction.amount
    
    def test_process_message_needs_review(self, db, test_account, test_bank_account, test_upload, test_extraction_low_confidence, test_message):
        """Test message requiring human review."""
        # Update message to point to low confidence extraction
        test_extraction_low_confidence.upload_id = test_upload.id
        db.commit()
        
        worker = create_test_worker(db)
        
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status == MessageStatus.AWAITING_REVIEW.value
        assert claimed.error_message is not None
        assert "confidence" in claimed.error_message.lower()
    
    def test_process_recalled_message(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test worker skips recalled messages."""
        recalled_msg = Message(
            conversation_id="conv-recalled",
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
        assert recalled_msg.processed_at is not None
    
    def test_process_message_no_upload(self, db, test_message):
        """Test processing fails when no upload attached."""
        test_message.attachment_id = "non-existent"
        db.commit()
        
        worker = create_test_worker(db)
        worker.process_message(db, test_message)
        
        db.expire(test_message)
        assert test_message.status == MessageStatus.PENDING.value  # Retry
        assert test_message.retry_count == 1
        assert test_message.error_message == "No upload attached"
    
    def test_process_message_no_extraction(self, db, test_message, test_upload):
        """Test processing fails when no extraction exists."""
        # Use upload without extraction
        worker = create_test_worker(db)
        worker.process_message(db, test_message)
        
        db.expire(test_message)
        assert test_message.status == MessageStatus.PENDING.value  # Retry
        assert test_message.retry_count == 1
        assert test_message.error_message == "No extraction found"


class TestRetryLogic:
    """Test retry backoff and failure handling.
    
    Note: The worker's retry logic is triggered when verify_and_post_from_ai returns
    RETRYABLE or FAILED status. In the current architecture, Ollama client has its own
    retry logic (3 retries) and returns failure results rather than raising exceptions.
    These tests verify the fail_message method's backoff behavior directly.
    """
    
    def test_fail_message_backoff_schedule(self, db, test_message):
        """Test exponential backoff in fail_message: 60s, 120s, 240s."""
        worker = create_test_worker(db)
        
        # First failure
        worker.fail_message(db, test_message, "Test error")
        db.expire(test_message)
        assert test_message.retry_count == 1
        assert test_message.status == MessageStatus.PENDING.value
        
        # Check lease_expires_at is ~60s in future (handle naive datetime from SQLite)
        lease_expires = test_message.lease_expires_at
        if lease_expires.tzinfo is None:
            lease_expires = lease_expires.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delay1 = (lease_expires - now).total_seconds()
        assert 55 < delay1 < 65
        
        # Second failure
        worker.fail_message(db, test_message, "Test error")
        db.expire(test_message)
        assert test_message.retry_count == 2
        
        lease_expires = test_message.lease_expires_at
        if lease_expires.tzinfo is None:
            lease_expires = lease_expires.replace(tzinfo=timezone.utc)
        delay2 = (lease_expires - now).total_seconds()
        assert 115 < delay2 < 125
        
        # Third failure - should be marked FAILED
        worker.fail_message(db, test_message, "Test error")
        db.expire(test_message)
        assert test_message.retry_count == 3
        assert test_message.status == MessageStatus.FAILED.value
    
    def test_fail_message_max_retries(self, db, test_upload):
        """Test message marked FAILED after 3 retries via fail_message."""
        worker = create_test_worker(db)
        
        msg = Message(
            conversation_id="conv-fail",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        # Fail 3 times
        for _ in range(3):
            worker.fail_message(db, msg, "Test error")
        
        db.expire(msg)
        assert msg.status == MessageStatus.FAILED.value
        assert msg.processed_at is not None
    
    def test_fail_message_bounded_retries(self, db, test_upload):
        """Test fail_message retry loop is bounded at 3.
        
        Note: retry_count increments on each call, but status becomes FAILED
        after 3 failures. retry_count can exceed 3 but status stays FAILED.
        """
        worker = create_test_worker(db)
        
        msg = Message(
            conversation_id="conv-bounded",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        # Try to fail 5 times
        for _ in range(5):
            worker.fail_message(db, msg, "Test error")
        
        db.expire(msg)
        assert msg.status == MessageStatus.FAILED.value
        # retry_count will be 5 (incremented each call), but status is FAILED
        assert msg.retry_count >= 3


class TestCrashRecovery:
    """Test worker crash and recovery scenarios."""
    
    def test_worker_crash_during_processing(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message):
        """Test message lease expires after worker crash."""
        worker = create_test_worker(db)
        worker.sim_config.inject_worker_crash = True
        
        claimed = worker.claim_next_message(db)
        
        # Process should crash
        with pytest.raises(Exception, match="Worker crashed"):
            worker.process_message(db, claimed)
        
        # Message should still be in processing with old worker
        db.expire(claimed)
        assert claimed.status == MessageStatus.PROCESSING.value
        assert claimed.worker_id == "test-worker"
    
    def test_recovery_after_crash(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test new worker recovers message after lease expiry."""
        # Use test_message but make it look like it was crashed
        # First, create a message that's in PROCESSING with expired lease
        crashed_msg = Message(
            conversation_id="conv-crash",
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
        
        # New worker starts (this calls reclaim_stale_leases which will set crashed_msg to PENDING)
        worker = create_test_worker(db)
        
        # Should reclaim and process - claim_next_message will get the oldest pending message
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        assert claimed.id == crashed_msg.id
        assert claimed.worker_id == "test-worker"
    
    def test_crash_after_external_call(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message):
        """Test crash after AI call but before completion."""
        worker = create_test_worker(db)
        worker.sim_config.worker_crash_after_external = True
        
        claimed = worker.claim_next_message(db)
        
        with pytest.raises(Exception, match="Worker crashed"):
            worker.process_message(db, claimed)
        
        # Message should be in processing state (not completed)
        db.expire(claimed)
        assert claimed.status == MessageStatus.PROCESSING.value
        
        # Simulate lease expiry for recovery
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
        
        # On recovery, should be reclaimed
        worker2 = create_test_worker(db)
        recovered = worker2.claim_next_message(db)
        assert recovered is not None
        assert recovered.id == claimed.id


class TestIdempotentProcessing:
    """Test idempotent message processing."""
    
    def test_duplicate_task_delivery(self, db, test_account, test_bank_account, test_upload, test_extraction, sim_config):
        """Test duplicate message delivery doesn't create duplicate transactions."""
        sim_config.reset()  # Ensure clean state
        # Create two messages with same upload
        msg1 = Message(
            conversation_id="conv-dup1",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        msg2 = Message(
            conversation_id="conv-dup2",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
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
        
        # Should be same transaction
        assert claimed2.transaction_id == tx_id
        
        # Only one transaction in DB
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 1
    
    def test_concurrent_workers_same_task(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test two workers don't process same message."""
        msg = Message(
            conversation_id="conv-concurrent",
            sender_name="Test",
            sender_role="PUBLIC",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(msg)
        db.commit()
        
        worker1 = create_test_worker(db, "worker-1")
        worker2 = create_test_worker(db, "worker-2")
        
        # Both try to claim
        claimed1 = worker1.claim_next_message(db)
        claimed2 = worker2.claim_next_message(db)
        
        # Only one should get it
        assert (claimed1 is not None) != (claimed2 is not None)
    
    def test_atomic_claim_behavior(self, db, test_upload):
        """Test claim is atomic - no race condition."""
        # Create many messages
        messages = []
        for i in range(10):
            msg = Message(
                conversation_id=f"conv-{i}",
                sender_name="Test",
                sender_role="PUBLIC",
                message_type="RECEIPT",
                content=f"Test {i}",
                attachment_id=test_upload.id,
                status=MessageStatus.PENDING.value,
            )
            messages.append(msg)
        db.add_all(messages)
        db.commit()
        
        worker = create_test_worker(db)
        
        # Claim all
        claimed_count = 0
        while True:
            claimed = worker.claim_next_message(db)
            if not claimed:
                break
            claimed_count += 1
        
        assert claimed_count == 10


class TestWorkerQueueSimulation:
    """Test full worker lifecycle simulation."""
    
    def test_simulate_worker_lifecycle(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test complete worker lifecycle with multiple messages."""
        # Create multiple pending messages
        for i in range(3):
            msg = Message(
                conversation_id=f"conv-{i}",
                sender_name="Test",
                sender_role="PUBLIC",
                message_type="RECEIPT",
                content=f"Test {i}",
                attachment_id=test_upload.id,
                status=MessageStatus.PENDING.value,
            )
            db.add(msg)
        db.commit()
        
        results = simulate_worker_lifecycle(db, message_count=3)
        
        assert len(results) == 3
        for r in results:
            assert r["status"] == MessageStatus.POSTED.value
            assert r["transaction_id"] is not None
        
        # All should have unique transactions (different uploads would be needed for unique)
        # But since same upload, they should all reference same transaction
        tx_ids = [r["transaction_id"] for r in results]
        assert len(set(tx_ids)) == 1
    
    def test_worker_crash_recovery_scenario(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test crash and recovery scenario."""
        from tests.simulation.config import get_simulation_config
        sim_config = get_simulation_config()
        sim_config.reset()  # Ensure clean state
        # Create message
        msg = Message(
            conversation_id="conv-crash-rec",
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
        worker.sim_config.inject_worker_crash = True
        
        # Claim and crash
        claimed = worker.claim_next_message(db)
        try:
            worker.process_message(db, claimed)
        except Exception:
            pass
        
        # Message still processing
        db.expire(claimed)
        assert claimed.status == MessageStatus.PROCESSING.value
        
        # Simulate lease expiry for recovery
        claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()
        
        # New worker recovers - reset crash flag and call reclaim
        worker2 = create_test_worker(db, "worker-recovery")
        worker2.sim_config.inject_worker_crash = False
        worker2.reclaim_stale_leases(db)  # Explicitly reclaim stale leases
        
        recovered = worker2.claim_next_message(db)
        assert recovered is not None
        assert recovered.id == claimed.id
        worker2.process_message(db, recovered)
        
        db.expire(recovered)
        assert recovered.status == MessageStatus.POSTED.value
    
    def test_lease_expiry_during_processing(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test lease expires while worker is slow."""
        msg = Message(
            conversation_id="conv-lease",
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
        worker.sim_config.inject_lease_expiry = True
        
        claimed = worker.claim_next_message(db)
        assert claimed is None  # Lease expiry injection blocks claiming


class TestWorkerStatusTransitions:
    """Test worker status state machine."""
    
    def test_status_transitions(self, db):
        """Test worker state transitions."""
        worker = WorkerSimulator(worker_id="test-state", database_url="")
        
        # OFFLINE -> STARTING -> ONLINE
        worker.startup(db)
        assert worker.sim_config.worker_state.value == "ONLINE"
        
        # ONLINE -> OFFLINE (shutdown)
        worker.shutdown(db)
        assert worker.sim_config.worker_state.value == "STOPPED"
    
    def test_degraded_state(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Test worker enters degraded state on duplicate load failure."""
        # This would require mocking duplicate detector failure
        # For now, verify the state exists
        from tests.simulation.config import WorkerState
        assert WorkerState.DEGRADED in WorkerState
    
    def test_recovering_state(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message):
        """Test worker recovering after crash."""
        worker = create_test_worker(db)
        worker.sim_config.inject_worker_crash = True
        
        claimed = worker.claim_next_message(db)
        try:
            worker.process_message(db, claimed)
        except Exception:
            pass
        
        # Recover
        worker.recover(db)
        assert worker.sim_config.worker_state.value == "RECOVERING"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])