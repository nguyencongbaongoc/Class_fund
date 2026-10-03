import os
from datetime import datetime, timezone
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AI_CONFIDENCE_THRESHOLD"] = "0.9"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerStatus, Transaction, 
    Upload, UploadStatus, User, LedgerType, LedgerSource
)
from app.services.ledger import (
    calculate_balance, post_revert, post_transaction, verify_and_post_from_ai, 
    ProcessingResult, PostTransactionResult, VerifyAndPostResult
)
from app.core.security import hash_password


def new_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_idempotent_same_key_same_payload():
    """Same message, same payload, repeated request returns original transaction."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    message_id = "msg-test-1"
    idempotency_key = f"msg_{message_id}_v1"
    
    result1 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX001", bank_account_id=bank.id,
        upload_id="upload-1", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    result2 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX001", bank_account_id=bank.id,
        upload_id="upload-1", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    assert result1.status == ProcessingResult.SUCCESS
    assert result2.status == ProcessingResult.DUPLICATE
    assert result1.transaction.id == result2.transaction.id
    assert db.query(Transaction).count() == 1


def test_idempotent_different_retry_count_same_payload():
    """Same message, different retry count (but same payload) returns original transaction.
    This is the key fix: retry count does NOT change the key."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    message_id = "msg-test-2"
    # Same key regardless of retry count
    idempotency_key = f"msg_{message_id}_v1"
    
    result1 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX002", bank_account_id=bank.id,
        upload_id="upload-2", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    # Simulate retry with different attempt_id but same key
    result2 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX002", bank_account_id=bank.id,
        upload_id="upload-2", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id, attempt_id="attempt-2",
    )
    
    assert result1.status == ProcessingResult.SUCCESS
    assert result2.status == ProcessingResult.DUPLICATE
    assert result1.transaction.id == result2.transaction.id
    assert db.query(Transaction).count() == 1


def test_idempotent_same_message_modified_amount_rejected():
    """Same message, modified amount - should reject with different fingerprint."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    message_id = "msg-test-3"
    idempotency_key = f"msg_{message_id}_v1"
    
    result1 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX003", bank_account_id=bank.id,
        upload_id="upload-3", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    # Same key, different amount -> fingerprint mismatch -> FAILED with VALIDATION error
    result2 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("60000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX003", bank_account_id=bank.id,
        upload_id="upload-3", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    assert result1.status == ProcessingResult.SUCCESS
    assert result2.status == ProcessingResult.FAILED
    assert result2.error_classification.name == "VALIDATION"


def test_different_message_same_bank_transaction():
    """Different message with same bank transaction code - DB constraint prevents duplicate."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    # First message
    result1 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX004", bank_account_id=bank.id,
        upload_id="upload-4a", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key="msg_msg-1_v1", message_id="msg-1",
    )
    
    # Second message, same bank transaction code - should FAIL with BUSINESS_RULE
    result2 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX004", bank_account_id=bank.id,
        upload_id="upload-4b", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key="msg_msg-2_v1", message_id="msg-2",
    )
    
    assert result1.status == ProcessingResult.SUCCESS
    assert result2.status == ProcessingResult.FAILED
    assert result2.error_classification.name == "BUSINESS_RULE"
    assert "Duplicate transaction code" in result2.error_message


def test_concurrent_requests_no_double_post():
    """Concurrent requests with same idempotency key - only one succeeds.
    Simulates concurrent behavior by making multiple sequential calls with the same key."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    message_id = "msg-concurrent"
    idempotency_key = f"msg_{message_id}_v1"
    results = []

    # Simulate 5 concurrent requests sequentially (same effect for idempotency test)
    for i in range(5):
        result = post_transaction(
            db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
            source=LedgerSource.IMAGE, transaction_code="TX005", bank_account_id=bank.id,
            upload_id="upload-5", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
            idempotency_key=idempotency_key, message_id=message_id,
        )
        results.append(result)
    
    # All successful requests should return the same transaction ID
    successful = [r for r in results if r.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)]
    assert len(successful) >= 1
    assert all(r.transaction.id == successful[0].transaction.id for r in successful)
    # Only one transaction should exist in DB
    assert db.query(Transaction).count() == 1


def test_ambiguous_commit_recovery():
    """Commit succeeded but response lost - recovery via message_id."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    message_id = "msg-recovery-1"
    idempotency_key = f"msg_{message_id}_v1"
    
    # First post - succeeds
    result1 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX006", bank_account_id=bank.id,
        upload_id="upload-6", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    original_id = result1.transaction.id
    
    # Simulate: idempotency record exists but we query with a NEW session that doesn't have the transaction loaded
    # In real scenario, this would be a new request with same idempotency_key
    # The check_idempotency will find the key but the transaction might not be in the identity map
    # Our _recover_transaction_by_message should find it
    
    # Manually simulate by expiring and querying
    db.expire_all()
    
    result2 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX006", bank_account_id=bank.id,
        upload_id="upload-6", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    assert result2.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)
    assert result2.transaction.id == original_id
    assert db.query(Transaction).count() == 1


def test_worker_crash_after_commit_recovery():
    """Worker crashes immediately after commit - recovery on restart via message_id."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    message_id = "msg-crash-recovery"
    idempotency_key = f"msg_{message_id}_v1"
    
    # Post transaction (simulates worker completing commit)
    result1 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX007", bank_account_id=bank.id,
        upload_id="upload-7", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    original_id = result1.transaction.id
    
    # Simulate worker restart - new database session
    # In reality this would be a completely new process
    # The idempotency key and message_id are persisted
    db.expire_all()
    
    # New request with same message_id and idempotency_key should recover
    result2 = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX007", bank_account_id=bank.id,
        upload_id="upload-7", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key=idempotency_key, message_id=message_id,
    )
    
    assert result2.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)
    assert result2.transaction.id == original_id
    assert db.query(Transaction).count() == 1


def test_verify_and_post_from_ai_idempotent():
    """verify_and_post_from_ai with message_id is idempotent."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    upload = Upload(file_hash="a" * 64, original_filename="a.png", storage_path="/tmp/a.png", uploader_name="Minh", status=UploadStatus.PENDING)
    db.add_all([account, bank, upload]); db.commit()
    
    extraction = ExtractedTransaction(
        upload_id=upload.id, transaction_code="TX008", amount=Decimal("50000"),
        sender_name="NGUYEN A", bank_name="Test", bank_account_id=bank.id,
        confidence=Decimal("0.98"), status=UploadStatus.PROCESSING
    )
    db.add(extraction); db.commit()
    
    message_id = "msg-ai-1"
    idempotency_key = f"msg_{message_id}_v1"
    
    result1 = verify_and_post_from_ai(
        db, upload, extraction, account=account, actor_id=None, 
        idempotency_key=idempotency_key, message_id=message_id
    )
    
    result2 = verify_and_post_from_ai(
        db, upload, extraction, account=account, actor_id=None, 
        idempotency_key=idempotency_key, message_id=message_id
    )
    
    assert result1.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)
    assert result2.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)
    assert result1.transaction is not None
    assert result2.transaction is not None
    assert result1.transaction.id == result2.transaction.id
    assert db.query(Transaction).count() == 1


if __name__ == "__main__":
    test_idempotent_same_key_same_payload()
    print("test_idempotent_same_key_same_payload PASSED")
    
    test_idempotent_different_retry_count_same_payload()
    print("test_idempotent_different_retry_count_same_payload PASSED")
    
    test_idempotent_same_message_modified_amount_rejected()
    print("test_idempotent_same_message_modified_amount_rejected PASSED")
    
    test_different_message_same_bank_transaction()
    print("test_different_message_same_bank_transaction PASSED")
    
    test_concurrent_requests_no_double_post()
    print("test_concurrent_requests_no_double_post PASSED")
    
    test_ambiguous_commit_recovery()
    print("test_ambiguous_commit_recovery PASSED")
    
    test_worker_crash_after_commit_recovery()
    print("test_worker_crash_after_commit_recovery PASSED")
    
    test_verify_and_post_from_ai_idempotent()
    print("test_verify_and_post_from_ai_idempotent PASSED")
    
    print("\nAll idempotency tests PASSED!")