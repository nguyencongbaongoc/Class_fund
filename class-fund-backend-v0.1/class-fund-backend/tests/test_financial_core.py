import os
from datetime import datetime, timezone
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["AI_CONFIDENCE_THRESHOLD"] = "0.9"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.models import Account, BankAccount, ExtractedTransaction, LedgerStatus, Transaction, Upload, UploadStatus, User
from app.services.ledger import calculate_balance, post_revert, post_transaction, verify_and_post_from_ai, ProcessingResult
from app.models.models import LedgerSource, LedgerType, Role
from app.core.security import hash_password


def new_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_credit_debit_and_balance():
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("100000"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add_all([account, bank]); db.commit()

    result1 = post_transaction(db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
                     source=LedgerSource.MANUAL, transaction_code="M1", bank_account_id=bank.id,
                     upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
                     idempotency_key="credit-1")
    assert result1.status == ProcessingResult.SUCCESS
    
    result2 = post_transaction(db, account=account, type_=LedgerType.DEBIT, amount=Decimal("25000"), currency="VND",
                     source=LedgerSource.MANUAL, transaction_code="D1", bank_account_id=bank.id,
                     upload_id=None, created_by=None, effective_at=datetime.now(timezone.utc), note=None,
                     idempotency_key="debit-1")
    assert result2.status == ProcessingResult.SUCCESS
    assert calculate_balance(db, account) == Decimal("125000")


def test_revert_restores_balance_without_deleting_original():
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    user = User(name="Owner", email="owner@example.com", password_hash=hash_password("pw"), role=Role.OWNER_TREASURER)
    db.add_all([account, user]); db.commit()
    tx_result = post_transaction(db, account=account, type_=LedgerType.CREDIT, amount=Decimal("50000"), currency="VND",
                          source=LedgerSource.MANUAL, transaction_code=None, bank_account_id=None,
                          upload_id=None, created_by=user.id, effective_at=datetime.now(timezone.utc), note=None,
                          idempotency_key="credit-1")
    assert tx_result.status == ProcessingResult.SUCCESS
    tx = tx_result.transaction
    assert calculate_balance(db, account) == Decimal("50000")
    rev_result = post_revert(db, original=tx, actor_id=user.id, reason="wrong payment", idempotency_key="rev-1")
    assert rev_result.status == ProcessingResult.SUCCESS
    rev = rev_result.transaction
    assert rev.type == LedgerType.REVERT
    assert calculate_balance(db, account) == Decimal("0")
    assert db.get(Transaction, tx.id).status == LedgerStatus.REVERTED
    assert db.query(Transaction).count() == 2


def test_ai_low_confidence_does_not_post():
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    upload = Upload(file_hash="a" * 64, original_filename="a.png", storage_path="/tmp/a.png", uploader_name="Minh", status=UploadStatus.PENDING)
    db.add_all([account, bank, upload]); db.commit()
    extraction = ExtractedTransaction(upload_id=upload.id, transaction_code="ABC", amount=Decimal("50000"),
                                      sender_name="NGUYEN A", bank_name="Test", bank_account_id=bank.id,
                                      confidence=Decimal("0.5"), status=UploadStatus.PROCESSING)
    db.add(extraction); db.commit()
    result = verify_and_post_from_ai(db, upload, extraction, account=account, actor_id=None, idempotency_key="ai-1")
    assert result.status == ProcessingResult.NEEDS_HUMAN_REVIEW
    assert result.transaction is None
    assert upload.status == UploadStatus.NEEDS_REVIEW
    assert db.query(Transaction).count() == 0


def test_ai_retry_same_upload_does_not_double_post():
    db = new_db()
    account = Account(name="Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    bank = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    upload = Upload(file_hash="b" * 64, original_filename="b.png", storage_path="/tmp/b.png", uploader_name="Minh", status=UploadStatus.PENDING)
    db.add_all([account, bank, upload]); db.flush()
    extraction = ExtractedTransaction(upload_id=upload.id, transaction_code="ABC", amount=Decimal("50000"),
                                      sender_name="NGUYEN A", bank_name="Test", bank_account_id=bank.id,
                                      confidence=Decimal("0.98"), status=UploadStatus.PROCESSING)
    db.add(extraction); db.commit()
    first = verify_and_post_from_ai(db, upload, extraction, account=account, actor_id=None, idempotency_key="ai-1")
    second = verify_and_post_from_ai(db, upload, extraction, account=account, actor_id=None, idempotency_key="ai-2")
    assert first.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)
    assert second.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE)
    assert first.transaction is not None
    assert second.transaction is not None
    assert first.transaction.id == second.transaction.id
    assert db.query(Transaction).count() == 1
    assert calculate_balance(db, account) == Decimal("50000")
