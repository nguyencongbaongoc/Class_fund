from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    Account, CampaignMember, CampaignMemberStatus, CollectionCampaign, ExtractedTransaction,
    IdempotencyKey, LedgerEntry, LedgerSource, LedgerStatus, LedgerType,
    Message, MessageStatus, PaymentMatch, Transaction, Upload, UploadStatus,
)
from app.services.audit import write_audit
from app.services.activity import emit_activity


class ProcessingResult(StrEnum):
    SUCCESS = "SUCCESS"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    RETRYABLE = "RETRYABLE"
    AMBIGUOUS = "AMBIGUOUS"
    RECALLED = "RECALLED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class ErrorClassification(StrEnum):
    VALIDATION = "VALIDATION"
    BUSINESS_RULE = "BUSINESS_RULE"
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class ProcessingContext:
    message_id: str
    logical_operation_id: str
    attempt_id: str
    idempotency_key: str
    correlation_id: str
    upload_id: str | None = None


@dataclass
class PostTransactionResult:
    status: ProcessingResult
    transaction: Transaction | None
    error_message: str | None
    error_classification: ErrorClassification | None


@dataclass
class VerifyAndPostResult:
    status: ProcessingResult
    transaction: Transaction | None
    error_message: str | None
    error_classification: ErrorClassification | None


def calculate_balance(db: Session, account: Account) -> Decimal:
    entries = db.execute(
        select(LedgerEntry).join(Transaction, LedgerEntry.transaction_id == Transaction.id)
        .where(Transaction.account_id == account.id, LedgerEntry.status == LedgerStatus.VERIFIED)
        .order_by(LedgerEntry.effective_at, LedgerEntry.created_at)
    ).scalars().all()
    balance = Decimal(account.opening_balance)
    for entry in entries:
        if entry.type == LedgerType.CREDIT:
            balance += entry.amount
        elif entry.type == LedgerType.DEBIT:
            balance -= entry.amount
        elif entry.type == LedgerType.REVERT:
            if entry.note and entry.note.startswith("REVERSAL_OF:CREDIT"):
                balance -= entry.amount
            elif entry.note and entry.note.startswith("REVERSAL_OF:DEBIT"):
                balance += entry.amount
    return balance


def _make_request_fingerprint(parts: list[str]) -> str:
    return sha256("|".join(parts).encode()).hexdigest()


def _make_transaction_fingerprint(
    account_id: str,
    type_: LedgerType,
    amount: Decimal,
    currency: str,
    source: LedgerSource,
    transaction_code: str | None,
    bank_account_id: str | None,
    upload_id: str | None,
    message_id: str | None,
) -> str:
    """Create stable fingerprint including message_id for stable identity across retries."""
    return _make_request_fingerprint([
        account_id, type_.value, str(amount), currency, source.value,
        transaction_code or "", bank_account_id or "", upload_id or "",
        message_id or "",
    ])


def check_idempotency(db: Session, key: str | None, fingerprint: str) -> dict[str, Any] | None:
    if not key:
        return None
    existing = db.execute(select(IdempotencyKey).where(IdempotencyKey.key == key)).scalar_one_or_none()
    if not existing:
        return None
    if existing.request_fingerprint != fingerprint:
        raise HTTPException(status_code=409, detail="Idempotency key was reused with a different request")
    return existing.response_body


def save_idempotency(db: Session, key: str | None, fingerprint: str, status_code: int, body: dict[str, Any]) -> None:
    if key:
        db.add(IdempotencyKey(key=key, request_fingerprint=fingerprint, response_status=status_code, response_body=body))


def _recover_transaction_by_message(
    db: Session, message_id: str, bank_account_id: str | None, transaction_code: str | None
) -> Transaction | None:
    """Recover transaction when commit succeeded but response was lost.
    Looks up by message_id first, then by bank transaction identity."""
    if not message_id:
        return None
    # First try by message_id (direct link)
    tx = db.execute(select(Transaction).where(Transaction.message_id == message_id)).scalar_one_or_none()
    if tx:
        return tx
    # Fallback: if we have bank transaction identity, try that
    if bank_account_id and transaction_code:
        tx = db.execute(select(Transaction).where(
            Transaction.bank_account_id == bank_account_id,
            Transaction.transaction_code == transaction_code,
        )).scalar_one_or_none()
        if tx:
            return tx
    return None


def post_transaction(
    db: Session, *, account: Account, type_: LedgerType, amount: Decimal, currency: str,
    source: LedgerSource, transaction_code: str | None, bank_account_id: str | None,
    upload_id: str | None, created_by: str | None, effective_at, note: str | None,
    idempotency_key: str | None = None,
    message_id: str | None = None,
    logical_operation_id: str | None = None,
    attempt_id: str | None = None,
    audit_actor_id: str | None = None, commit: bool = True,
) -> PostTransactionResult:
    if amount <= 0:
        return PostTransactionResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message="Amount must be positive",
            error_classification=ErrorClassification.VALIDATION
        )
    if type_ == LedgerType.CREDIT and source == LedgerSource.IMAGE and (not transaction_code or not bank_account_id):
        return PostTransactionResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message="AI-posted credits require bank account and transaction code",
            error_classification=ErrorClassification.VALIDATION
        )

    fingerprint = _make_transaction_fingerprint(
        account_id=account.id,
        type_=type_,
        amount=amount,
        currency=currency,
        source=source,
        transaction_code=transaction_code,
        bank_account_id=bank_account_id,
        upload_id=upload_id,
        message_id=message_id,
    )
    try:
        existing_response = check_idempotency(db, idempotency_key, fingerprint)
    except HTTPException as e:
        # Fingerprint mismatch - key reused with different request
        return PostTransactionResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message=e.detail,
            error_classification=ErrorClassification.VALIDATION
        )
    
    if existing_response:
        existing_tx = db.get(Transaction, existing_response["transaction_id"])
        if existing_tx:
            return PostTransactionResult(
                status=ProcessingResult.DUPLICATE,
                transaction=existing_tx,
                error_message=None,
                error_classification=None
            )
        # Idempotency record exists but transaction not found - ambiguous commit
        recovered = _recover_transaction_by_message(db, message_id, bank_account_id, transaction_code)
        if recovered:
            # Update idempotency record with recovered transaction
            save_idempotency(db, idempotency_key, fingerprint, 200, {"transaction_id": recovered.id})
            return PostTransactionResult(
                status=ProcessingResult.SUCCESS,
                transaction=recovered,
                error_message="Recovered from ambiguous commit",
                error_classification=ErrorClassification.AMBIGUOUS
            )
        return PostTransactionResult(
            status=ProcessingResult.AMBIGUOUS,
            transaction=None,
            error_message="Idempotency record exists but transaction not recoverable",
            error_classification=ErrorClassification.AMBIGUOUS
        )

    if transaction_code and bank_account_id:
        existing = db.execute(select(Transaction).where(
            Transaction.bank_account_id == bank_account_id,
            Transaction.transaction_code == transaction_code,
        ).with_for_update()).scalar_one_or_none()
        if existing:
            # Check if this existing transaction belongs to the same message
            if message_id and existing.message_id == message_id:
                # Same message, same bank transaction - return existing
                if idempotency_key:
                    save_idempotency(db, idempotency_key, fingerprint, 200, {"transaction_id": existing.id})
                return PostTransactionResult(
                    status=ProcessingResult.DUPLICATE,
                    transaction=existing,
                    error_message=None,
                    error_classification=None
                )
            return PostTransactionResult(
                status=ProcessingResult.FAILED,
                transaction=None,
                error_message="Duplicate transaction code",
                error_classification=ErrorClassification.BUSINESS_RULE
            )

    tx = Transaction(
        account_id=account.id, bank_account_id=bank_account_id, transaction_code=transaction_code,
        type=type_, amount=amount, currency=currency, source=source, status=LedgerStatus.VERIFIED,
        upload_id=upload_id, created_by=created_by, effective_at=effective_at, note=note,
        message_id=message_id,
    )
    db.add(tx)
    db.flush()
    entry = LedgerEntry(
        transaction_id=tx.id, type=type_, amount=amount, currency=currency,
        transaction_code=transaction_code, source=source, status=LedgerStatus.VERIFIED,
        upload_id=upload_id, created_by=created_by, effective_at=effective_at, note=note,
    )
    db.add(entry)
    db.flush()
    write_audit(
        db, actor_id=audit_actor_id, action="LEDGER_POST", entity_type="TRANSACTION", entity_id=tx.id,
        after={"type": type_.value, "amount": str(amount), "transaction_code": transaction_code, "source": source.value, "message_id": message_id},
    )
    emit_activity(
        db, sender_id=audit_actor_id, sender_role="SYSTEM" if source == LedgerSource.IMAGE else "OWNER_TREASURER",
        message_type="TRANSACTION", content=f"{type_.value}: {amount} {currency}", ledger_entry_id=entry.id, attachment_id=upload_id,
    )
    if idempotency_key:
        save_idempotency(db, idempotency_key, fingerprint, 201, {"transaction_id": tx.id})
    if commit:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            # Try to recover in case of concurrent commit
            recovered = _recover_transaction_by_message(db, message_id, bank_account_id, transaction_code)
            if recovered:
                if idempotency_key:
                    save_idempotency(db, idempotency_key, fingerprint, 200, {"transaction_id": recovered.id})
                return PostTransactionResult(
                    status=ProcessingResult.SUCCESS,
                    transaction=recovered,
                    error_message="Recovered from concurrent commit",
                    error_classification=ErrorClassification.AMBIGUOUS
                )
            return PostTransactionResult(
                status=ProcessingResult.FAILED,
                transaction=None,
                error_message="Duplicate or conflicting financial mutation",
                error_classification=ErrorClassification.BUSINESS_RULE
            )
    return PostTransactionResult(
        status=ProcessingResult.SUCCESS,
        transaction=tx,
        error_message=None,
        error_classification=None
    )


def post_revert(db: Session, *, original: Transaction, actor_id: str, reason: str,
                idempotency_key: str | None = None,
                message_id: str | None = None) -> PostTransactionResult:
    fingerprint = _make_request_fingerprint(["revert", original.id, reason, message_id or ""])
    existing_response = check_idempotency(db, idempotency_key, fingerprint)
    if existing_response:
        existing_tx = db.get(Transaction, existing_response["transaction_id"])
        if existing_tx:
            return PostTransactionResult(
                status=ProcessingResult.DUPLICATE,
                transaction=existing_tx,
                error_message=None,
                error_classification=None
            )

    original = db.execute(select(Transaction).where(Transaction.id == original.id).with_for_update()).scalar_one()
    original_entry = db.execute(select(LedgerEntry).where(LedgerEntry.transaction_id == original.id).with_for_update()).scalar_one()
    if original.type == LedgerType.REVERT or original.source == LedgerSource.REVERT:
        return PostTransactionResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message="Cannot revert a reversal transaction",
            error_classification=ErrorClassification.BUSINESS_RULE
        )
    already = db.execute(select(LedgerEntry).where(
        LedgerEntry.original_entry_id == original_entry.id, LedgerEntry.type == LedgerType.REVERT,
    )).scalar_one_or_none()
    if already:
        return PostTransactionResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message="Transaction has already been reverted",
            error_classification=ErrorClassification.BUSINESS_RULE
        )

    tx = Transaction(
        account_id=original.account_id, bank_account_id=original.bank_account_id,
        transaction_code=f"REV-{original.id}", type=LedgerType.REVERT, amount=original.amount,
        currency=original.currency, source=LedgerSource.REVERT, status=LedgerStatus.VERIFIED,
        upload_id=original.upload_id, created_by=actor_id,
        note=f"REVERSAL_OF:{original.type.value};REASON:{reason}",
        message_id=message_id,
    )
    db.add(tx)
    db.flush()
    reversal = LedgerEntry(
        transaction_id=tx.id, type=LedgerType.REVERT, amount=original.amount, currency=original.currency,
        transaction_code=tx.transaction_code, source=LedgerSource.REVERT, status=LedgerStatus.VERIFIED,
        upload_id=original.upload_id, created_by=actor_id, original_entry_id=original_entry.id,
        note=f"REVERSAL_OF:{original.type.value};REASON:{reason}",
    )
    db.add(reversal)
    original.status = LedgerStatus.REVERTED
    write_audit(
        db, actor_id=actor_id, action="LEDGER_REVERT", entity_type="TRANSACTION", entity_id=original.id,
        before={"status": LedgerStatus.VERIFIED.value},
        after={"status": LedgerStatus.REVERTED.value, "reversal_transaction_id": tx.id, "reason": reason, "message_id": message_id},
    )
    if idempotency_key:
        save_idempotency(db, idempotency_key, fingerprint, 200, {"transaction_id": tx.id})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        return PostTransactionResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message="Conflicting revert",
            error_classification=ErrorClassification.BUSINESS_RULE
        )
    return PostTransactionResult(
        status=ProcessingResult.SUCCESS,
        transaction=tx,
        error_message=None,
        error_classification=None
    )


def verify_and_post_from_ai(db: Session, upload: Upload, result: ExtractedTransaction, *, account: Account,
                            actor_id: str | None, idempotency_key: str | None = None,
                            message_id: str | None = None,
                            logical_operation_id: str | None = None,
                            attempt_id: str | None = None) -> VerifyAndPostResult:
    from app.core.config import get_settings
    threshold = get_settings().ai_confidence_threshold

    existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == upload.id)).scalar_one_or_none()
    if existing_tx:
        return VerifyAndPostResult(
            status=ProcessingResult.DUPLICATE,
            transaction=existing_tx,
            error_message=None,
            error_classification=None
        )
    if upload.status in {UploadStatus.REJECTED, UploadStatus.DUPLICATE}:
        return VerifyAndPostResult(
            status=ProcessingResult.FAILED,
            transaction=None,
            error_message=f"Upload status is {upload.status.value}",
            error_classification=ErrorClassification.BUSINESS_RULE
        )

    if result.confidence is None or float(result.confidence) < threshold:
        upload.status = UploadStatus.NEEDS_REVIEW
        result.status = UploadStatus.NEEDS_REVIEW
        db.commit()
        return VerifyAndPostResult(
            status=ProcessingResult.NEEDS_HUMAN_REVIEW,
            transaction=None,
            error_message=f"Confidence {result.confidence} below threshold {threshold}",
            error_classification=ErrorClassification.BUSINESS_RULE
        )
    if not result.transaction_code or not result.amount or result.amount <= 0 or not result.bank_account_id:
        upload.status = UploadStatus.NEEDS_REVIEW
        result.status = UploadStatus.NEEDS_REVIEW
        db.commit()
        return VerifyAndPostResult(
            status=ProcessingResult.NEEDS_HUMAN_REVIEW,
            transaction=None,
            error_message="Missing required transaction fields",
            error_classification=ErrorClassification.VALIDATION
        )

    duplicate = db.execute(select(Transaction).where(
        Transaction.bank_account_id == result.bank_account_id,
        Transaction.transaction_code == result.transaction_code,
    ).with_for_update()).scalar_one_or_none()
    if duplicate:
        # Check if this is the same message (recovery case)
        if message_id and duplicate.message_id == message_id:
            return VerifyAndPostResult(
                status=ProcessingResult.DUPLICATE,
                transaction=duplicate,
                error_message=None,
                error_classification=None
            )
        upload.status = UploadStatus.DUPLICATE
        result.status = UploadStatus.DUPLICATE
        db.commit()
        return VerifyAndPostResult(
            status=ProcessingResult.DUPLICATE,
            transaction=None,
            error_message="Duplicate bank transaction",
            error_classification=ErrorClassification.BUSINESS_RULE
        )

    member = None
    if result.campaign_id:
        campaign = db.get(CollectionCampaign, result.campaign_id)
        if not campaign:
            upload.status = UploadStatus.NEEDS_REVIEW; result.status = UploadStatus.NEEDS_REVIEW; db.commit()
            return VerifyAndPostResult(
                status=ProcessingResult.NEEDS_HUMAN_REVIEW,
                transaction=None,
                error_message="Campaign not found",
                error_classification=ErrorClassification.VALIDATION
            )
        if Decimal(result.amount) != Decimal(campaign.expected_amount) or not result.student_id:
            upload.status = UploadStatus.NEEDS_REVIEW; result.status = UploadStatus.NEEDS_REVIEW; db.commit()
            return VerifyAndPostResult(
                status=ProcessingResult.NEEDS_HUMAN_REVIEW,
                transaction=None,
                error_message="Amount mismatch or missing student",
                error_classification=ErrorClassification.VALIDATION
            )
        member = db.execute(select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id, CampaignMember.student_id == result.student_id,
        ).with_for_update()).scalar_one_or_none()
        if not member or member.status == CampaignMemberStatus.PAID:
            upload.status = UploadStatus.NEEDS_REVIEW if member else UploadStatus.DUPLICATE
            result.status = upload.status
            db.commit()
            return VerifyAndPostResult(
                status=ProcessingResult.NEEDS_HUMAN_REVIEW if member else ProcessingResult.DUPLICATE,
                transaction=None,
                error_message="Member not found or already paid",
                error_classification=ErrorClassification.BUSINESS_RULE
            )

    post_result = post_transaction(
        db, account=account, type_=LedgerType.CREDIT, amount=Decimal(result.amount), currency=account.currency,
        source=LedgerSource.IMAGE, transaction_code=result.transaction_code, bank_account_id=result.bank_account_id,
        upload_id=upload.id, created_by=actor_id, effective_at=result.transaction_time or upload.created_at,
        note=f"AI_VERIFIED confidence={result.confidence}", audit_actor_id=actor_id,
        idempotency_key=idempotency_key, commit=False,
        message_id=message_id, logical_operation_id=logical_operation_id, attempt_id=attempt_id,
    )
    
    if post_result.status == ProcessingResult.SUCCESS:
        upload.status = UploadStatus.VERIFIED
        result.status = UploadStatus.VERIFIED
        if member and result.student_id and result.campaign_id:
            member.status = CampaignMemberStatus.PAID
            db.add(PaymentMatch(transaction_id=post_result.transaction.id, campaign_id=result.campaign_id, student_id=result.student_id,
                                confidence=result.confidence, matched_by="AI"))
        db.commit()
        return VerifyAndPostResult(
            status=ProcessingResult.SUCCESS,
            transaction=post_result.transaction,
            error_message=None,
            error_classification=None
        )
    elif post_result.status == ProcessingResult.DUPLICATE:
        upload.status = UploadStatus.VERIFIED
        result.status = UploadStatus.VERIFIED
        if member and result.student_id and result.campaign_id:
            member.status = CampaignMemberStatus.PAID
            db.add(PaymentMatch(transaction_id=post_result.transaction.id, campaign_id=result.campaign_id, student_id=result.student_id,
                                confidence=result.confidence, matched_by="AI"))
        db.commit()
        return VerifyAndPostResult(
            status=ProcessingResult.DUPLICATE,
            transaction=post_result.transaction,
            error_message=None,
            error_classification=None
        )
    else:
        # Failed or ambiguous
        db.rollback()
        upload = db.get(Upload, upload.id)
        if upload:
            upload.status = UploadStatus.DUPLICATE if post_result.status == ProcessingResult.FAILED and "Duplicate" in (post_result.error_message or "") else UploadStatus.NEEDS_REVIEW
            db.commit()
        return VerifyAndPostResult(
            status=post_result.status,
            transaction=post_result.transaction,
            error_message=post_result.error_message,
            error_classification=post_result.error_classification
        )
