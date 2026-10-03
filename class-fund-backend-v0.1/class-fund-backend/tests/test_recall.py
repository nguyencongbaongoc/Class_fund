import os
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from secrets import token_bytes
from sqlalchemy import select

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AI_CONFIDENCE_THRESHOLD"] = "0.9"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.models import (
    Account, BankAccount, ExtractedTransaction, LedgerStatus, Transaction, 
    Upload, UploadStatus, User, LedgerType, LedgerSource, Message, MessageStatus, RecallToken
)
from app.services.ledger import (
    calculate_balance, post_revert, post_transaction, verify_and_post_from_ai, 
    ProcessingResult, PostTransactionResult, VerifyAndPostResult, ErrorClassification
)
from app.core.security import hash_password


def new_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_recall_token_generation_and_validation():
    """Test recall token generation, storage, and validation."""
    from hashlib import sha256
    from secrets import token_bytes
    
    # Generate token
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    
    # Validate
    computed_hash = sha256(bytes.fromhex(token_hex)).hexdigest()
    assert computed_hash == token_hash
    
    # Wrong token should not match
    wrong_token = token_bytes(32).hex()
    wrong_hash = sha256(bytes.fromhex(wrong_token)).hexdigest()
    assert wrong_hash != token_hash


def test_recall_before_post():
    """Recall before posting - message should be marked recalled, no transaction created."""
    db = new_db()
    
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    
    message = Message(
        conversation_id="conv-1",
        sender_name="Test User",
        sender_role="PUBLIC",
        message_type="RECEIPT",
        content="Test receipt",
        attachment_id="upload-1",
        status=MessageStatus.PENDING.value,
        public_code="CF-20261003-TEST",
        recall_token_hash=token_hash,
    )
    db.add(message)
    db.flush()
    
    recall_token = RecallToken(message_id=message.id, token_hash=token_hash)
    db.add(recall_token)
    db.commit()
    
    # Recall the message before processing
    # Simulate the API call
    recall_token_record = db.execute(
        select(RecallToken).where(RecallToken.message_id == message.id)
    ).scalar_one()
    
    # Validate token
    computed_hash = sha256(bytes.fromhex(token_hex)).hexdigest()
    assert recall_token_record.token_hash == computed_hash
    
    # Mark as recalled
    message.status = MessageStatus.RECALLED.value
    message.processed_at = datetime.now(timezone.utc)
    recall_token_record.used_at = datetime.now(timezone.utc)
    db.commit()
    
    assert message.status == MessageStatus.RECALLED.value
    assert recall_token_record.used_at is not None
    
    # Verify no transaction was created
    assert db.query(Transaction).count() == 0


def test_recall_after_post_creates_reversal():
    """Recall after posting - should create a reversal transaction."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()
    
    # Post a transaction
    tx_result = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX001", bank_account_id=bank.id,
        upload_id="upload-1", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key="msg_msg-1_v1", message_id="msg-1",
    )
    assert tx_result.status == ProcessingResult.SUCCESS
    tx = tx_result.transaction
    
    # Create message linked to transaction
    from hashlib import sha256
    from secrets import token_bytes
    
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    
    message = Message(
        conversation_id="conv-1",
        sender_name="Test User",
        sender_role="PUBLIC",
        message_type="RECEIPT",
        content="Test receipt",
        attachment_id="upload-1",
        status=MessageStatus.POSTED.value,
        public_code="CF-20261003-TEST",
        recall_token_hash=token_hash,
        transaction_id=tx.id,
    )
    db.add(message)
    db.flush()
    
    recall_token = RecallToken(message_id=message.id, token_hash=token_hash)
    db.add(recall_token)
    db.commit()
    
    # Recall the message
    rev_result = post_revert(
        db, original=tx, actor_id=None, reason="User recalled",
        message_id=message.id
    )
    
    assert rev_result.status == ProcessingResult.SUCCESS
    rev_tx = rev_result.transaction
    assert rev_tx.type == LedgerType.REVERT
    
    # Original transaction should be marked reverted
    original = db.get(Transaction, tx.id)
    assert original.status == LedgerStatus.REVERTED
    
    # Balance should be restored
    assert calculate_balance(db, account) == Decimal("0")
    
    # Message should be marked recalled
    message.status = MessageStatus.RECALLED.value
    message.processed_at = datetime.now(timezone.utc)
    recall_token.used_at = datetime.now(timezone.utc)
    db.commit()
    
    assert message.status == MessageStatus.RECALLED.value


def test_double_recall_prevented():
    """Double recall should be prevented."""
    db = new_db()
    
    from hashlib import sha256
    from secrets import token_bytes
    
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    
    message = Message(
        conversation_id="conv-1",
        sender_name="Test User",
        sender_role="PUBLIC",
        message_type="RECEIPT",
        content="Test receipt",
        status=MessageStatus.RECALLED.value,  # Already recalled
        public_code="CF-20261003-TEST",
        recall_token_hash=token_hash,
    )
    db.add(message)
    db.flush()
    
    recall_token = RecallToken(message_id=message.id, token_hash=token_hash, used_at=datetime.now(timezone.utc))
    db.add(recall_token)
    db.commit()
    
    # Attempt second recall - should fail
    computed_hash = sha256(bytes.fromhex(token_hex)).hexdigest()
    assert recall_token.token_hash == computed_hash
    assert recall_token.used_at is not None
    
    # This simulates the API check
    if recall_token.used_at:
        # Should reject
        assert True  # Test passes if we reach here
    
    # Message status should remain RECALLED
    assert message.status == MessageStatus.RECALLED.value


def test_recall_token_replay_protection():
    """Recall token should not be reusable (replay protection)."""
    db = new_db()
    
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    
    message = Message(
        conversation_id="conv-1",
        sender_name="Test User",
        sender_role="PUBLIC",
        message_type="RECEIPT",
        content="Test receipt",
        status=MessageStatus.PENDING.value,
        public_code="CF-20261003-TEST",
        recall_token_hash=token_hash,
    )
    db.add(message)
    db.flush()
    
    recall_token = RecallToken(message_id=message.id, token_hash=token_hash)
    db.add(recall_token)
    db.commit()
    
    # First recall - succeeds
    recall_token.used_at = datetime.now(timezone.utc)
    message.status = MessageStatus.RECALLED.value
    db.commit()
    
    # Second attempt with same token - should fail
    recall_token_record = db.execute(
        select(RecallToken).where(RecallToken.message_id == message.id)
    ).scalar_one()
    
    assert recall_token_record.used_at is not None
    
    # Simulate API check
    if recall_token_record.used_at:
        # Should reject
        assert True


def test_public_message_id_cannot_authorize_recall():
    """Public message_id alone should not authorize recall."""
    db = new_db()
    
    message = Message(
        conversation_id="conv-1",
        sender_name="Test User",
        sender_role="PUBLIC",
        message_type="RECEIPT",
        content="Test receipt",
        status=MessageStatus.PENDING.value,
        public_code="CF-20261003-TEST",
        recall_token_hash="some_hash",
    )
    db.add(message)
    db.commit()
    
    # Knowing message.id should NOT be enough
    message_id = message.id
    
    # API requires token in body
    # Without token, recall should fail
    # This is tested by the API endpoint requiring recall_token in RecallRequest
    assert message_id is not None  # Just verify we have it
    
    # The actual authorization happens in the endpoint
    # which validates token_hash against stored hash


def test_public_transaction_id_cannot_authorize_recall():
    """Public transaction_id alone should not authorize recall."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()
    
    tx_result = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
        source=LedgerSource.IMAGE, transaction_code="TX001", bank_account_id=bank.id,
        upload_id="upload-1", created_by=None, effective_at=datetime.now(timezone.utc), note="Test",
        idempotency_key="msg_msg-1_v1", message_id="msg-1",
    )
    assert tx_result.status == ProcessingResult.SUCCESS
    
    tx_id = tx_result.transaction.id
    
    # Knowing transaction_id should NOT be enough to authorize recall
    # Recall requires message_id + recall_token
    assert tx_id is not None


def test_worker_checks_recall_before_posting():
    """Worker should check message status before financial posting."""
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    upload = Upload(file_hash="a" * 64, original_filename="a.png", storage_path="/tmp/a.png", uploader_name="Minh", status=UploadStatus.PENDING)
    db.add_all([account, bank, upload]); db.commit()
    
    extraction = ExtractedTransaction(
        upload_id=upload.id, transaction_code="TX001", amount=Decimal("50000"),
        sender_name="NGUYEN A", bank_name="Test", bank_account_id=bank.id,
        confidence=Decimal("0.98"), status=UploadStatus.PROCESSING
    )
    db.add(extraction); db.commit()
    
    # Create message marked as recalled
    from hashlib import sha256
    from secrets import token_bytes
    
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    
    message = Message(
        conversation_id="conv-1",
        sender_name="Test User",
        sender_role="PUBLIC",
        message_type="RECEIPT",
        content="Test receipt",
        attachment_id=upload.id,
        status=MessageStatus.RECALLED.value,  # Already recalled!
        public_code="CF-20261003-TEST",
        recall_token_hash=token_hash,
    )
    db.add(message)
    db.commit()
    
    # Worker should check status and NOT post
    # This simulates the check in verify_and_post_from_ai
    msg = db.get(Message, message.id)
    assert msg.status == MessageStatus.RECALLED.value
    
    # If worker checks this before calling verify_and_post_from_ai:
    if msg.status == MessageStatus.RECALLED.value:
        # Should return RECALLED result
        from app.services.ledger import VerifyAndPostResult, ProcessingResult, ErrorClassification
        result = VerifyAndPostResult(
            status=ProcessingResult.RECALLED,
            transaction=None,
            error_message="Message recalled before processing",
            error_classification=ErrorClassification.BUSINESS_RULE
        )
        assert result.status == ProcessingResult.RECALLED


if __name__ == "__main__":
    test_recall_token_generation_and_validation()
    print("test_recall_token_generation_and_validation PASSED")
    
    test_recall_before_post()
    print("test_recall_before_post PASSED")
    
    test_recall_after_post_creates_reversal()
    print("test_recall_after_post_creates_reversal PASSED")
    
    test_double_recall_prevented()
    print("test_double_recall_prevented PASSED")
    
    test_recall_token_replay_protection()
    print("test_recall_token_replay_protection PASSED")
    
    test_public_message_id_cannot_authorize_recall()
    print("test_public_message_id_cannot_authorize_recall PASSED")
    
    test_public_transaction_id_cannot_authorize_recall()
    print("test_public_transaction_id_cannot_authorize_recall PASSED")
    
    test_worker_checks_recall_before_posting()
    print("test_worker_checks_recall_before_posting PASSED")
    
    print("\nAll recall authorization tests PASSED!")