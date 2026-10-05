"""Concurrency and race condition simulation tests.

Note: SQLite in-memory database does not support true concurrent writes.
These tests simulate concurrent scenarios by making sequential calls with
shared idempotency keys to verify the application-level concurrency handling.
For true database-level concurrency testing, PostgreSQL would be required.
"""
from __future__ import annotations

import threading
import time
from decimal import Decimal
from typing import List, Dict, Any
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    LedgerStatus, Message, MessageStatus, Transaction, Upload, UploadStatus, User, Role
)
from app.services.ledger import (
    verify_and_post_from_ai, ProcessingResult, post_revert, post_transaction, calculate_balance
)
from tests.simulation.mock_ollama import create_vision_success_receipt


# =============================================================================
# 5.1 Concurrent Posting Tests (Simulated via Sequential Idempotency)
# =============================================================================

def test_concurrent_posting_2_clients(db, test_account, test_bank_account, test_upload, test_extraction):
    """Test 2 concurrent post requests for same proposal (simulated)."""
    _run_concurrent_posting_test(db, test_account, test_bank_account, test_upload, test_extraction, 2)


def test_concurrent_posting_5_clients(db, test_account, test_bank_account, test_upload, test_extraction):
    """Test 5 concurrent post requests for same proposal (simulated)."""
    _run_concurrent_posting_test(db, test_account, test_bank_account, test_upload, test_extraction, 5)


def test_concurrent_posting_10_clients(db, test_account, test_bank_account, test_upload, test_extraction):
    """Test 10 concurrent post requests for same proposal (simulated)."""
    _run_concurrent_posting_test(db, test_account, test_bank_account, test_upload, test_extraction, 10)


def test_concurrent_posting_20_clients(db, test_account, test_bank_account, test_upload, test_extraction):
    """Test 20 concurrent post requests for same proposal (simulated)."""
    _run_concurrent_posting_test(db, test_account, test_bank_account, test_upload, test_extraction, 20)


def _run_concurrent_posting_test(db, test_account, test_bank_account, test_upload, test_extraction, num_clients: int):
    """Run concurrent posting test with specified number of clients.
    
    Since SQLite doesn't support true concurrent writes, we simulate by
    making sequential calls with the same idempotency key - which tests
    the application's idempotency logic that would handle concurrent requests.
    """
    from tests.simulation.config import get_simulation_config
    get_simulation_config().reset()
    
    # Ensure extraction is verified (high confidence)
    test_extraction.confidence = Decimal("0.95")
    test_extraction.status = UploadStatus.PROCESSING
    db.commit()
    
    results = []
    errors = []
    
    for i in range(num_clients):
        try:
            from app.services.ledger import verify_and_post_from_ai
            result = verify_and_post_from_ai(
                db, test_upload, test_extraction, account=test_account, actor_id=None,
                idempotency_key="concurrent_post_test",  # Same key for all
                message_id=f"msg_concurrent_{num_clients}",
                logical_operation_id=f"op_concurrent_{num_clients}",
                attempt_id=f"attempt_{i}"
            )
            
            results.append({
                "thread_id": i,
                "status": result.status.value,
                "transaction_id": result.transaction.id if result.transaction else None,
                "error": result.error_message
            })
        except Exception as e:
            errors.append({"thread_id": i, "error": str(e), "type": type(e).__name__})
    
    # Verify no errors
    assert len(errors) == 0, f"Errors occurred: {errors}"
    
    # Verify exactly one SUCCESS, rest DUPLICATE
    statuses = [r["status"] for r in results]
    success_count = statuses.count("SUCCESS")
    duplicate_count = statuses.count("DUPLICATE")
    
    assert success_count == 1, f"Expected 1 SUCCESS, got {success_count}"
    assert duplicate_count == num_clients - 1, f"Expected {num_clients - 1} DUPLICATE, got {duplicate_count}"
    
    # Verify all successful results point to same transaction
    transaction_ids = [r["transaction_id"] for r in results if r["transaction_id"]]
    assert len(set(transaction_ids)) == 1, f"Multiple transaction IDs: {transaction_ids}"
    
    # Verify only one transaction in DB
    tx_count = db.execute(select(Transaction)).scalars().all()
    assert len(tx_count) == 1, f"Expected 1 transaction in DB, got {len(tx_count)}"
    
    # Verify proposal state consistent
    db.expire(test_extraction)
    assert test_extraction.status == UploadStatus.VERIFIED
    db.expire(test_upload)
    assert test_upload.status == UploadStatus.VERIFIED


# =============================================================================
# 5.2 Concurrent Queue Claiming (Simulated)
# =============================================================================

def test_concurrent_queue_claiming(db, test_account, test_bank_account, test_upload, test_extraction, sim_config):
    """Test 5 workers concurrently claiming 20 pending messages (simulated)."""
    sim_config.reset()
    
    # Create 20 pending messages
    messages = []
    for i in range(20):
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
    message_ids = [m.id for m in messages]
    
    # Simulate 5 workers claiming sequentially (tests atomic claim logic)
    from tests.simulation.mock_worker import create_test_worker
    
    claimed_ids = []
    for i in range(5):
        worker = create_test_worker(db, f"worker-{i}")
        claimed = worker.claim_next_message(db)
        if claimed:
            claimed_ids.append(claimed.id)
    
    # Verify no duplicate claims
    assert len(claimed_ids) == len(set(claimed_ids)), "Duplicate claims detected"
    
    # Verify all claimed messages are in PROCESSING with correct worker
    for msg_id in claimed_ids:
        msg = db.get(Message, msg_id)
        assert msg.status == MessageStatus.PROCESSING.value
        assert msg.worker_id is not None
    
    # Verify total claimed = 5
    assert len(claimed_ids) == 5, f"Expected 5 claimed, got {len(claimed_ids)}"


# =============================================================================
# 5.3 Concurrent Approval (Simulated)
# =============================================================================

def test_concurrent_approval(db, test_account, test_bank_account, test_upload, test_extraction_low_confidence, sim_config):
    """Test two reviewers concurrently approving same proposal (simulated)."""
    sim_config.reset()
    
    # Set up low confidence extraction needing review
    test_extraction_low_confidence.status = UploadStatus.NEEDS_REVIEW
    test_upload.status = UploadStatus.NEEDS_REVIEW
    db.commit()
    
    # Simulate two concurrent approval attempts
    results = []
    for i in range(2):
        extraction = db.get(ExtractedTransaction, test_extraction_low_confidence.id)
        if extraction.status == UploadStatus.NEEDS_REVIEW:
            extraction.status = UploadStatus.VERIFIED
            extraction.reviewed_by = f"moderator-{i}"
            extraction.reviewed_at = datetime.now(timezone.utc)
            extraction.review_notes = "Approved"
            db.commit()
            
            # Now try to post
            from app.services.ledger import verify_and_post_from_ai
            result = verify_and_post_from_ai(
                db, test_upload, extraction, account=test_account, actor_id=f"moderator-{i}",
                idempotency_key="approve_concurrent_test",
                message_id="msg_approve_test"
            )
            
            results.append({
                "status": result.status.value,
                "transaction_id": result.transaction.id if result.transaction else None
            })
        else:
            results.append({
                "status": "ALREADY_PROCESSED",
                "transaction_id": None
            })
    
    # Verify at most one SUCCESS
    statuses = [r["status"] for r in results]
    success_count = statuses.count("SUCCESS")
    assert success_count <= 1, f"Multiple SUCCESS: {success_count}"
    
    # Verify no duplicate transactions
    tx_ids = [r["transaction_id"] for r in results if r["transaction_id"]]
    if tx_ids:
        assert len(set(tx_ids)) == 1, "Multiple transaction IDs"


# =============================================================================
# 5.4 Concurrent Recall (Simulated)
# =============================================================================

def test_concurrent_recall(db, test_account, test_bank_account, test_upload, test_extraction, sim_config):
    """Test 10 concurrent recall requests for same eligible proposal (simulated)."""
    sim_config.reset()
    
    # Create message that can be recalled (PENDING)
    msg = Message(
        conversation_id="conv-recall",
        sender_name="Test",
        sender_role="MEMBER",
        message_type="RECEIPT",
        content="Test",
        attachment_id=test_upload.id,
        status=MessageStatus.PENDING.value,
    )
    db.add(msg)
    db.commit()
    
    # Simulate 10 concurrent recall attempts
    results = []
    for i in range(10):
        message = db.get(Message, msg.id)
        if message.status == MessageStatus.PENDING.value:
            message.status = MessageStatus.RECALLED.value
            message.processed_at = datetime.now(timezone.utc)
            db.commit()
            results.append({"status": "RECALLED"})
        else:
            results.append({"status": message.status})
    
    # Verify exactly one RECALLED, rest see already recalled
    statuses = [r["status"] for r in results]
    recalled_count = statuses.count("RECALLED")
    assert recalled_count == 1, f"Expected 1 RECALLED, got {recalled_count}"
    
    # Verify no transaction created
    tx_count = db.execute(select(Transaction)).scalars().all()
    assert len(tx_count) == 0, "No transaction should be created for pre-post recall"


# =============================================================================
# 5.5 Concurrent Reversal (Simulated)
# =============================================================================

def test_concurrent_reversal(db, test_account, test_bank_account, test_upload, test_extraction, sim_config):
    """Test 10 concurrent reversal requests for same posted transaction (simulated)."""
    sim_config.reset()
    
    # First, post a transaction
    tx_result = post_transaction(
        db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX_CONCURRENT", bank_account_id=test_bank_account.id,
        upload_id=test_upload.id, created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key="concurrent_rev_test", message_id="msg_rev_test"
    )
    assert tx_result.status == ProcessingResult.SUCCESS
    original_tx = tx_result.transaction
    original_entry_id = None
    
    # Get the ledger entry
    from app.models.models import LedgerEntry
    original_entry = db.execute(
        select(LedgerEntry).where(LedgerEntry.transaction_id == original_tx.id)
    ).scalar_one()
    original_entry_id = original_entry.id
    
    # Simulate 10 concurrent reversal attempts
    results = []
    for i in range(10):
        rev_result = post_revert(
            db, original=original_tx, actor_id=f"moderator-{i}",
            reason=f"Concurrent revert {i}", idempotency_key=f"rev_concurrent_test_{i}",
            message_id="msg_rev_test"
        )
        
        results.append({
            "status": rev_result.status.value,
            "transaction_id": rev_result.transaction.id if rev_result.transaction else None
        })
    
    # Verify exactly one SUCCESS
    statuses = [r["status"] for r in results]
    success_count = statuses.count("SUCCESS")
    failed_count = statuses.count("FAILED")
    
    assert success_count == 1, f"Expected 1 SUCCESS, got {success_count}"
    assert failed_count == 9, f"Expected 9 FAILED, got {failed_count}"
    
    # Verify exactly one reversal transaction
    tx_count = db.execute(select(Transaction)).scalars().all()
    assert len(tx_count) == 2, f"Expected 2 transactions (original + 1 reversal), got {len(tx_count)}"
    
    # Verify original entry unchanged
    db.expire(original_tx)
    assert original_tx.status == LedgerStatus.REVERTED
    
    # Verify reversal has original_entry_id
    reversal_tx = [t for t in tx_count if t.type == LedgerType.REVERT][0]
    reversal_entry = db.execute(
        select(LedgerEntry).where(LedgerEntry.transaction_id == reversal_tx.id)
    ).scalar_one()
    assert reversal_entry.original_entry_id == original_entry_id


# =============================================================================
# 5.6 Concurrent Balance Reads and Writes (Simulated)
# =============================================================================

def test_concurrent_balance_reads_writes(db, test_account, test_bank_account, sim_config):
    """Test concurrent ledger writes and balance queries (simulated)."""
    sim_config.reset()
    
    # Write 5 transactions sequentially (simulating concurrent writes)
    writer_results = []
    for i in range(5):
        amount = Decimal("1000") * (i + 1)
        result = post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=amount, currency="VND",
            source=LedgerSource.MANUAL, transaction_code=f"WRITE_{i}", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=f"Writer {i}",
            idempotency_key=f"writer_{i}"
        )
        writer_results.append({"status": result.status.value, "amount": str(amount)})
    
    # Read balance multiple times (simulating concurrent reads)
    balances_read = []
    for _ in range(5):
        balance = calculate_balance(db, test_account)
        balances_read.append(balance)
    
    # Verify all writes succeeded
    assert len(writer_results) == 5
    for r in writer_results:
        assert r["status"] == "SUCCESS"
    
    # Verify balance reads are consistent
    expected_final = test_account.opening_balance + sum(Decimal("1000") * (i + 1) for i in range(5))
    final_balance = calculate_balance(db, test_account)
    assert final_balance == expected_final, f"Final balance mismatch: {final_balance} != {expected_final}"
    
    # All read balances should equal final (sequential simulation)
    for b in balances_read:
        assert b == expected_final, f"Invalid balance read: {b} != {expected_final}"


# =============================================================================
# 5.7 Concurrent Duplicate Delivery (Simulated)
# =============================================================================

def test_concurrent_duplicate_delivery(db, test_account, test_bank_account, test_upload, test_extraction, sim_config):
    """Test duplicate message delivery with same idempotency key (simulated)."""
    sim_config.reset()
    
    results = []
    for i in range(20):
        result = verify_and_post_from_ai(
            db, test_upload, test_extraction, account=test_account, actor_id=None,
            idempotency_key="duplicate_delivery_test",
            message_id="msg_duplicate_test",
            logical_operation_id="op_duplicate_test",
            attempt_id=f"attempt_{i}"
        )
        
        results.append({
            "status": result.status.value,
            "transaction_id": result.transaction.id if result.transaction else None
        })
    
    # All should be SUCCESS or DUPLICATE
    statuses = [r["status"] for r in results]
    for s in statuses:
        assert s in ("SUCCESS", "DUPLICATE"), f"Unexpected status: {s}"
    
    # Exactly one transaction
    tx_count = db.execute(select(Transaction)).scalars().all()
    assert len(tx_count) == 1, f"Expected 1 transaction, got {len(tx_count)}"
    
    # All transaction_ids same
    tx_ids = [r["transaction_id"] for r in results if r["transaction_id"]]
    assert len(set(tx_ids)) == 1


# =============================================================================
# 5.8 Idempotency Key Mismatch (Same Key, Different Payload)
# =============================================================================

def test_concurrent_idempotent_same_key_diff_payload(db, test_account, test_bank_account, sim_config):
    """Test concurrent requests with same idempotency key but different payloads (should fail validation)."""
    sim_config.reset()
    
    results = []
    for i in range(5):
        # Same key, different amount - should fail with VALIDATION
        amount = Decimal("50000") + Decimal(str(i * 1000))
        result = post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=amount, currency="VND",
            source=LedgerSource.MANUAL, transaction_code=f"TX_DIFF_{i}", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
            idempotency_key="same_key_diff_payload"  # Same key!
        )
        
        results.append({
            "status": result.status.value,
            "error_class": result.error_classification.value if result.error_classification else None
        })
    
    # First should succeed, rest should fail with VALIDATION
    statuses = [r["status"] for r in results]
    success_count = statuses.count("SUCCESS")
    failed_count = statuses.count("FAILED")
    
    assert success_count == 1, f"Expected 1 SUCCESS, got {success_count}"
    assert failed_count == 4, f"Expected 4 FAILED, got {failed_count}"
    
    # All failures should be VALIDATION
    for r in results:
        if r["status"] == "FAILED":
            assert r["error_class"] == "VALIDATION", f"Expected VALIDATION, got {r['error_class']}"


# =============================================================================
# 5.9 Stress Test (Reduced - Sequential Simulation)
# =============================================================================

def test_stress_simulation(db, test_account, test_bank_account, sim_config):
    """Stress simulation: 50 sequential operations across 3 rounds."""
    sim_config.reset()
    
    num_operations = 50
    num_rounds = 3
    
    for round_num in range(num_rounds):
        for i in range(num_operations):
            # Create unique upload for each operation
            upload = Upload(
                file_hash=f"{i}{round_num}" * 8,
                original_filename=f"receipt_{i}_{round_num}.png",
                storage_path=f"uploads/{i}_{round_num}.png",
                uploaded_by="member-1",
                uploader_name="Test Member",
                status=UploadStatus.PENDING
            )
            db.add(upload)
            db.flush()
            
            extraction = ExtractedTransaction(
                upload_id=upload.id,
                transaction_code=f"TX_{i}_{round_num}",
                amount=Decimal("1000"),
                sender_name="TEST SENDER",
                bank_name="Test Bank",
                bank_account_id=test_bank_account.id,
                transaction_time=datetime.now(timezone.utc),
                confidence=Decimal("0.95"),
                status=UploadStatus.PROCESSING,
                currency="VND"
            )
            db.add(extraction)
            db.commit()
            
            result = verify_and_post_from_ai(
                db, upload, extraction, account=test_account, actor_id=None,
                idempotency_key=f"stress_{i}_{round_num}",
                message_id=f"msg_stress_{i}_{round_num}"
            )
            
            assert result.status == ProcessingResult.SUCCESS, f"Round {round_num} op {i}: {result.status}"
        
        # Verify transaction count per round
        tx_count = db.execute(select(Transaction)).scalars().all()
        expected = (round_num + 1) * num_operations
        assert len(tx_count) == expected, f"Round {round_num}: expected {expected} transactions, got {len(tx_count)}"
    
    # Final balance check
    expected_balance = test_account.opening_balance + Decimal("1000") * num_operations * num_rounds
    final_balance = calculate_balance(db, test_account)
    assert final_balance == expected_balance, f"Final balance: {final_balance} != {expected_balance}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])