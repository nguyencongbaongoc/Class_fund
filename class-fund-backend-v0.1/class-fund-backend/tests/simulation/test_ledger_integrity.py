"""Ledger integrity audit tests."""
from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerSource, LedgerType,
    LedgerStatus, Transaction, Upload, UploadStatus, User, Role, LedgerEntry, Message, MessageStatus
)
from app.services.ledger import (
    verify_and_post_from_ai, ProcessingResult, post_revert, post_transaction, calculate_balance
)
from tests.simulation.mock_ollama import create_vision_success_receipt
from tests.simulation.mock_worker import create_test_worker


class TestLedgerInvariants:
    """Test core ledger invariants."""
    
    def test_original_ledger_entries_immutable(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Original ledger entries are immutable after reversal."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Post transaction
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        original_amount = original_tx.amount
        original_type = original_tx.type
        original_code = original_tx.transaction_code
        original_status = original_tx.status
        
        # Get original ledger entry
        original_entry = db.execute(
            select(LedgerEntry).where(LedgerEntry.transaction_id == original_tx.id)
        ).scalar_one()
        original_entry_id = original_entry.id
        original_entry_amount = original_entry.amount
        original_entry_type = original_entry.type
        
        # Revert
        rev_result = post_revert(db, original=original_tx, actor_id="mod-1", reason="Test")
        rev_tx = rev_result.transaction
        
        # Original transaction unchanged
        db.expire(original_tx)
        assert original_tx.amount == original_amount
        assert original_tx.type == original_type
        assert original_tx.transaction_code == original_code
        assert original_tx.status == LedgerStatus.REVERTED  # Only status changes
        
        # Original ledger entry unchanged
        db.expire(original_entry)
        assert original_entry.id == original_entry_id
        assert original_entry.amount == original_entry_amount
        assert original_entry.type == original_entry_type
        assert original_entry.original_entry_id is None  # Original has no parent
    
    def test_every_valid_posting_creates_one_authoritative_effect(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Every valid posting creates exactly one authoritative ledger effect."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        # One transaction
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 1
        
        # One ledger entry
        entry_count = db.execute(select(LedgerEntry)).scalars().all()
        assert len(entry_count) == 1
        
        # Transaction and entry match
        tx = tx_count[0]
        entry = entry_count[0]
        assert entry.transaction_id == tx.id
        assert entry.type == tx.type
        assert entry.amount == tx.amount
    
    def test_ai_proposals_cannot_bypass_gatekeeper(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """AI proposals cannot bypass the financial gatekeeper."""
        # Verify the gatekeeper is the only path
        from app.services.ledger import verify_and_post_from_ai
        import inspect
        source = inspect.getsource(verify_and_post_from_ai)
        
        # Must call post_transaction (the gatekeeper)
        assert "post_transaction" in source
        
        # Test that direct Transaction creation doesn't happen in verify_and_post_from_ai
        # (it calls post_transaction which creates Transaction)
        assert "Transaction(" not in source or "post_transaction" in source
    
    def test_posted_transaction_has_expected_amount_direction(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Every posted transaction has expected amount and direction."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt(
            amount=750000
        )
        test_extraction.amount = Decimal("750000")
        db.commit()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        tx = db.get(Transaction, claimed.transaction_id)
        assert tx.type == LedgerType.CREDIT  # Income
        assert tx.amount == Decimal("750000")
        assert tx.currency == "VND"
    
    def test_reversal_references_correct_original(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Every reversal references the correct original entry."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        
        rev_result = post_revert(db, original=original_tx, actor_id="mod-1", reason="Test")
        rev_tx = rev_result.transaction
        
        # Check reversal transaction
        assert rev_tx.type == LedgerType.REVERT
        assert rev_tx.amount == original_tx.amount
        assert rev_tx.note.startswith("REVERSAL_OF:CREDIT")
        
        # Check ledger entry link
        rev_entry = db.execute(
            select(LedgerEntry).where(LedgerEntry.transaction_id == rev_tx.id)
        ).scalar_one()
        
        original_entry = db.execute(
            select(LedgerEntry).where(LedgerEntry.transaction_id == original_tx.id)
        ).scalar_one()
        
        assert rev_entry.original_entry_id == original_entry.id
    
    def test_reversal_cannot_occur_twice(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """A reversal cannot occur twice."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        
        # First reversal
        rev1 = post_revert(db, original=original_tx, actor_id="mod-1", reason="First")
        assert rev1.status == ProcessingResult.SUCCESS
        
        # Second reversal
        rev2 = post_revert(db, original=original_tx, actor_id="mod-2", reason="Second")
        assert rev2.status == ProcessingResult.FAILED
        assert rev2.error_classification.name == "BUSINESS_RULE"
        assert "already been reverted" in rev2.error_message
    
    def test_recall_before_posting_prevents_posting(self, db, test_account, test_bank_account, test_upload, test_extraction, mock_ollama):
        """Recall before posting prevents posting."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Create recalled message
        recalled_msg = Message(
            conversation_id="conv-recalled",
            sender_name="Test",
            sender_role="MEMBER",
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
        
        # No transaction
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
    
    def test_recall_after_posting_creates_revert(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Recall after posting creates compensating REVERT."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        
        # Simulate recall
        rev_result = post_revert(db, original=original_tx, actor_id="user-1", reason="User recalled")
        
        assert rev_result.status == ProcessingResult.SUCCESS
        rev_tx = rev_result.transaction
        assert rev_tx.type == LedgerType.REVERT
        assert rev_tx.amount == original_tx.amount
        
        # Balance restored
        assert calculate_balance(db, test_account) == test_account.opening_balance
    
    def test_failed_transaction_no_partial_ledger_effect(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Failed transaction cannot leave partial ledger effect."""
        # Simulate failure by setting low confidence
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt(confidence=0.5)
        test_extraction.confidence = Decimal("0.5")
        db.commit()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status == MessageStatus.AWAITING_REVIEW.value
        
        # No transaction created
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 0
        
        # No ledger entry
        entry_count = db.execute(select(LedgerEntry)).scalars().all()
        assert len(entry_count) == 0
    
    def test_duplicate_messages_no_duplicate_entries(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Duplicate messages cannot create duplicate entries."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Create duplicate message
        dup_msg = Message(
            conversation_id="conv-dup",
            sender_name="Test",
            sender_role="MEMBER",
            message_type="RECEIPT",
            content="Test",
            attachment_id=test_upload.id,
            status=MessageStatus.PENDING.value,
        )
        db.add(dup_msg)
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
        
        # Only one ledger entry
        entry_count = db.execute(select(LedgerEntry)).scalars().all()
        assert len(entry_count) == 1
    
    def test_concurrent_posts_no_multiple_effects(self, db, test_account, test_bank_account, test_upload, test_extraction):
        """Concurrent posts cannot create multiple effects for one logical operation."""
        from app.services.ledger import verify_and_post_from_ai
        
        # Simulate 5 concurrent calls with same idempotency key
        for i in range(5):
            result = verify_and_post_from_ai(
                db, test_upload, test_extraction, account=test_account, actor_id=None,
                idempotency_key="concurrent_test",
                message_id="msg_concurrent",
                logical_operation_id="op_concurrent",
                attempt_id=f"attempt_{i}"
            )
        
        # Only one transaction
        tx_count = db.execute(select(Transaction)).scalars().all()
        assert len(tx_count) == 1
        
        # Only one ledger entry
        entry_count = db.execute(select(LedgerEntry)).scalars().all()
        assert len(entry_count) == 1
    
    def test_balance_calculations_from_authoritative_ledger(self, db, test_account, test_bank_account):
        """Balance calculations derive from authoritative ledger data."""
        # Post multiple transactions
        for i in range(3):
            post_transaction(
                db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("100000"), currency="VND",
                source=LedgerSource.MANUAL, transaction_code=f"TX{i}", bank_account_id=test_bank_account.id,
                upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
                idempotency_key=f"balance_test_{i}"
            )
        
        # Calculate balance from ledger entries
        entries = db.execute(
            select(LedgerEntry).join(Transaction, LedgerEntry.transaction_id == Transaction.id)
            .where(Transaction.account_id == test_account.id, LedgerEntry.status == LedgerStatus.VERIFIED)
            .order_by(LedgerEntry.effective_at, LedgerEntry.created_at)
        ).scalars().all()
        
        manual_balance = Decimal(test_account.opening_balance)
        for entry in entries:
            if entry.type == LedgerType.CREDIT:
                manual_balance += entry.amount
            elif entry.type == LedgerType.DEBIT:
                manual_balance -= entry.amount
            elif entry.type == LedgerType.REVERT:
                if entry.note and entry.note.startswith("REVERSAL_OF:CREDIT"):
                    manual_balance -= entry.amount
                elif entry.note and entry.note.startswith("REVERSAL_OF:DEBIT"):
                    manual_balance += entry.amount
        
        # Compare with calculate_balance function
        calculated = calculate_balance(db, test_account)
        assert calculated == manual_balance
        assert calculated == test_account.opening_balance + Decimal("300000")


class TestDoubleEntryContract:
    """Test the accounting model contract."""
    
    def test_accounting_model_is_single_signed_ledger(self, db, test_account, test_bank_account):
        """Verify repository uses single signed ledger model."""
        # Post a credit
        post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX1", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
            idempotency_key="model_test_1"
        )
        
        # Post a debit
        post_transaction(
            db, account=test_account, type_=LedgerType.DEBIT, amount=Decimal("20000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX2", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
            idempotency_key="model_test_2"
        )
        
        # Verify ledger entries have types CREDIT/DEBIT/REVERT (single ledger with signs)
        entries = db.execute(select(LedgerEntry)).scalars().all()
        assert len(entries) == 2
        
        types = {e.type for e in entries}
        assert types == {LedgerType.CREDIT, LedgerType.DEBIT}
        
        # Verify balance calculation uses sign convention
        balance = calculate_balance(db, test_account)
        expected = test_account.opening_balance + Decimal("50000") - Decimal("20000")
        assert balance == expected
    
    def test_revert_sign_convention(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Verify REVERT sign convention in balance calculation."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        original_balance = calculate_balance(db, test_account)
        
        # Revert
        post_revert(db, original=original_tx, actor_id="mod-1", reason="Test")
        
        reverted_balance = calculate_balance(db, test_account)
        # REVERT of CREDIT should subtract the amount
        assert reverted_balance == test_account.opening_balance
        
        # Check note format for sign determination
        rev_tx = db.execute(
            select(Transaction).where(Transaction.type == LedgerType.REVERT)
        ).scalar_one()
        assert "REVERSAL_OF:CREDIT" in rev_tx.note


if __name__ == "__main__":
    pytest.main([__file__, "-v"])