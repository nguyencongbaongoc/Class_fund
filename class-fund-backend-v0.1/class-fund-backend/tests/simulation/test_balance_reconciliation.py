"""Balance reconciliation tests."""
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


class TestBalanceReconciliation:
    """Test balance reconciliation across multiple scenarios."""
    
    def test_independent_expected_balance_calculation(self, db, test_account, test_bank_account):
        """Calculate expected balance independently from ledger records."""
        # Create known transactions
        post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("500000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX1", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Income 1",
            idempotency_key="recon_1"
        )
        
        post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("300000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX2", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Income 2",
            idempotency_key="recon_2"
        )
        
        post_transaction(
            db, account=test_account, type_=LedgerType.DEBIT, amount=Decimal("200000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX3", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Expense 1",
            idempotency_key="recon_3"
        )
        
        # Independent calculation: opening + credits - debits
        expected = test_account.opening_balance + Decimal("500000") + Decimal("300000") - Decimal("200000")
        
        # Backend calculated balance
        backend_balance = calculate_balance(db, test_account)
        
        assert backend_balance == expected
        assert backend_balance == test_account.opening_balance + Decimal("600000")
    
    def test_balance_with_reversed_transactions(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Balance with reversed transactions."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Post transaction via worker
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        original_tx = db.get(Transaction, claimed.transaction_id)
        balance_after_post = calculate_balance(db, test_account)
        
        # Revert
        post_revert(db, original=original_tx, actor_id="mod-1", reason="Test revert")
        
        balance_after_revert = calculate_balance(db, test_account)
        
        # Should be back to opening balance
        assert balance_after_revert == test_account.opening_balance
        assert balance_after_post == test_account.opening_balance + original_tx.amount
    
    def test_balance_with_rejected_proposals(self, db, test_account, test_bank_account, test_upload, test_message, mock_ollama):
        """Rejected proposals don't affect balance."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt(confidence=0.5)
        
        # Create extraction with low confidence
        extraction = ExtractedTransaction(
            upload_id=test_upload.id,
            transaction_code="TX_LOW",
            amount=Decimal("100000"),
            sender_name="TEST",
            bank_name="Test Bank",
            bank_account_id=test_bank_account.id,
            transaction_time=datetime.now(timezone.utc),
            confidence=Decimal("0.5"),
            status=UploadStatus.PROCESSING,
            currency="VND"
        )
        db.add(extraction)
        db.commit()
        
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        assert claimed is not None
        worker.process_message(db, claimed)
        
        db.expire(claimed)
        assert claimed.status == MessageStatus.AWAITING_REVIEW.value
        
        # Balance unchanged
        balance = calculate_balance(db, test_account)
        assert balance == test_account.opening_balance
    
    def test_balance_with_duplicate_message_attempts(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Duplicate message attempts don't affect balance."""
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
        
        # Process both
        claimed1 = worker.claim_next_message(db)
        worker.process_message(db, claimed1)
        claimed2 = worker.claim_next_message(db)
        worker.process_message(db, claimed2)
        
        # Balance should only reflect one transaction
        balance = calculate_balance(db, test_account)
        expected = test_account.opening_balance + test_extraction.amount
        assert balance == expected
    
    def test_balance_with_failed_transactions(self, db, test_account, test_bank_account, test_upload, mock_ollama):
        """Failed transactions don't affect balance."""
        mock_ollama.sim_config.inject_ollama_timeout = True
        
        msg = Message(
            conversation_id="conv-fail",
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
        
        # Process 3 times (max retries)
        for _ in range(3):
            claimed = worker.claim_next_message(db)
            if claimed:
                worker.process_message(db, claimed)
        
        db.expire(msg)
        assert msg.status == MessageStatus.FAILED.value
        
        # Balance unchanged
        balance = calculate_balance(db, test_account)
        assert balance == test_account.opening_balance
    
    def test_comprehensive_scenario_reconciliation(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama):
        """Comprehensive scenario with all transaction types."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt(amount=100000)
        test_extraction.amount = Decimal("100000")
        db.commit()
        
        # 1. Initial balance
        assert calculate_balance(db, test_account) == test_account.opening_balance
        
        # 2. Manual credit
        post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("500000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="MANUAL1", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Manual income",
            idempotency_key="manual_1"
        )
        
        # 3. Manual debit
        post_transaction(
            db, account=test_account, type_=LedgerType.DEBIT, amount=Decimal("200000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="MANUAL2", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Manual expense",
            idempotency_key="manual_2"
        )
        
        # 4. AI-verified income (via worker)
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        # 5. Revert the AI transaction
        ai_tx = db.get(Transaction, claimed.transaction_id)
        post_revert(db, original=ai_tx, actor_id="mod-1", reason="Revert AI")
        
        # 6. Another manual credit
        post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("300000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="MANUAL3", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note="Manual income 2",
            idempotency_key="manual_3"
        )
        
        # Independent calculation
        expected = (
            test_account.opening_balance
            + Decimal("500000")  # manual credit
            - Decimal("200000")  # manual debit
            + Decimal("100000")  # AI credit
            - Decimal("100000")  # AI revert
            + Decimal("300000")  # manual credit 2
        )
        
        actual = calculate_balance(db, test_account)
        assert actual == expected
        
        # Verify ledger entries count
        entries = db.execute(select(LedgerEntry)).scalars().all()
        # 5 transactions = 5 ledger entries (3 manual + 1 AI + 1 revert)
        assert len(entries) == 5


class TestBalanceConsistencyAcrossSources:
    """Test balance consistency across different query paths."""
    
    def test_backend_vs_api_vs_dashboard_balance(self, db, test_account, test_bank_account, test_upload, test_extraction, test_message, mock_ollama, test_client, test_user_owner):
        """Backend, API, and dashboard should report same balance."""
        mock_ollama.sim_config.ollama_vision_responses.clear()
        mock_ollama.sim_config.ollama_vision_responses["test"] = create_vision_success_receipt()
        
        # Post via worker
        worker = create_test_worker(db)
        claimed = worker.claim_next_message(db)
        worker.process_message(db, claimed)
        
        backend_balance = calculate_balance(db, test_account)
        
        # API balance (via admin stats) - use owner fixture
        from tests.conftest import get_owner_headers
        response = test_client.get("/api/v1/admin/stats", headers=get_owner_headers())
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        api_balance = Decimal(str(response.json()["current_balance"]))
        
        assert backend_balance == api_balance
    
    def test_ledger_entry_based_balance(self, db, test_account, test_bank_account):
        """Balance calculated directly from ledger entries."""
        # Create transactions
        post_transaction(
            db, account=test_account, type_=LedgerType.CREDIT, amount=Decimal("100000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX1", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
            idempotency_key="ledger_1"
        )
        
        post_transaction(
            db, account=test_account, type_=LedgerType.DEBIT, amount=Decimal("30000"), currency="VND",
            source=LedgerSource.MANUAL, transaction_code="TX2", bank_account_id=test_bank_account.id,
            upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
            idempotency_key="ledger_2"
        )
        
        # Direct ledger entry query
        entries = db.execute(
            select(LedgerEntry).join(Transaction, LedgerEntry.transaction_id == Transaction.id)
            .where(Transaction.account_id == test_account.id, LedgerEntry.status == LedgerStatus.VERIFIED)
            .order_by(LedgerEntry.effective_at, LedgerEntry.created_at)
        ).scalars().all()
        
        manual_calc = Decimal(test_account.opening_balance)
        for entry in entries:
            if entry.type == LedgerType.CREDIT:
                manual_calc += entry.amount
            elif entry.type == LedgerType.DEBIT:
                manual_calc -= entry.amount
            elif entry.type == LedgerType.REVERT:
                if entry.note and entry.note.startswith("REVERSAL_OF:CREDIT"):
                    manual_calc -= entry.amount
                elif entry.note and entry.note.startswith("REVERSAL_OF:DEBIT"):
                    manual_calc += entry.amount
        
        backend_balance = calculate_balance(db, test_account)
        assert backend_balance == manual_calc


if __name__ == "__main__":
    pytest.main([__file__, "-v"])