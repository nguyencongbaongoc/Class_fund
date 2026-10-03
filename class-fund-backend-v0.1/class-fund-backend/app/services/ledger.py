from decimal import Decimal
from hashlib import sha256
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    Account, CampaignMember, CampaignMemberStatus, CollectionCampaign, ExtractedTransaction,
    IdempotencyKey, LedgerEntry, LedgerSource, LedgerStatus, LedgerType,
    PaymentMatch, Transaction, Upload, UploadStatus,
)
from app.services.audit import write_audit
from app.services.activity import emit_activity


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


def post_transaction(
    db: Session, *, account: Account, type_: LedgerType, amount: Decimal, currency: str,
    source: LedgerSource, transaction_code: str | None, bank_account_id: str | None,
    upload_id: str | None, created_by: str | None, effective_at, note: str | None,
    idempotency_key: str | None = None, audit_actor_id: str | None = None, commit: bool = True,
) -> Transaction:
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    if type_ == LedgerType.CREDIT and source == LedgerSource.IMAGE and (not transaction_code or not bank_account_id):
        raise HTTPException(status_code=422, detail="AI-posted credits require bank account and transaction code")

    fingerprint = _make_request_fingerprint([
        account.id, type_.value, str(amount), currency, source.value,
        transaction_code or "", bank_account_id or "", upload_id or "",
    ])
    existing_response = check_idempotency(db, idempotency_key, fingerprint)
    if existing_response:
        existing_tx = db.get(Transaction, existing_response["transaction_id"])
        if existing_tx:
            return existing_tx

    if transaction_code and bank_account_id:
        existing = db.execute(select(Transaction).where(
            Transaction.bank_account_id == bank_account_id,
            Transaction.transaction_code == transaction_code,
        ).with_for_update()).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Duplicate transaction code")

    tx = Transaction(
        account_id=account.id, bank_account_id=bank_account_id, transaction_code=transaction_code,
        type=type_, amount=amount, currency=currency, source=source, status=LedgerStatus.VERIFIED,
        upload_id=upload_id, created_by=created_by, effective_at=effective_at, note=note,
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
        after={"type": type_.value, "amount": str(amount), "transaction_code": transaction_code, "source": source.value},
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
            raise HTTPException(status_code=409, detail="Duplicate or conflicting financial mutation") from exc
    return tx


def post_revert(db: Session, *, original: Transaction, actor_id: str, reason: str,
                idempotency_key: str | None = None) -> Transaction:
    fingerprint = _make_request_fingerprint(["revert", original.id, reason])
    existing_response = check_idempotency(db, idempotency_key, fingerprint)
    if existing_response:
        existing_tx = db.get(Transaction, existing_response["transaction_id"])
        if existing_tx:
            return existing_tx

    original = db.execute(select(Transaction).where(Transaction.id == original.id).with_for_update()).scalar_one()
    original_entry = db.execute(select(LedgerEntry).where(LedgerEntry.transaction_id == original.id).with_for_update()).scalar_one()
    if original.type == LedgerType.REVERT or original.source == LedgerSource.REVERT:
        raise HTTPException(status_code=409, detail="Cannot revert a reversal transaction")
    already = db.execute(select(LedgerEntry).where(
        LedgerEntry.original_entry_id == original_entry.id, LedgerEntry.type == LedgerType.REVERT,
    )).scalar_one_or_none()
    if already:
        raise HTTPException(status_code=409, detail="Transaction has already been reverted")

    tx = Transaction(
        account_id=original.account_id, bank_account_id=original.bank_account_id,
        transaction_code=f"REV-{original.id}", type=LedgerType.REVERT, amount=original.amount,
        currency=original.currency, source=LedgerSource.REVERT, status=LedgerStatus.VERIFIED,
        upload_id=original.upload_id, created_by=actor_id,
        note=f"REVERSAL_OF:{original.type.value};REASON:{reason}",
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
        after={"status": LedgerStatus.REVERTED.value, "reversal_transaction_id": tx.id, "reason": reason},
    )
    if idempotency_key:
        save_idempotency(db, idempotency_key, fingerprint, 200, {"transaction_id": tx.id})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicting revert") from exc
    return tx


def verify_and_post_from_ai(db: Session, upload: Upload, result: ExtractedTransaction, *, account: Account,
                            actor_id: str | None, idempotency_key: str | None = None) -> Transaction | None:
    from app.core.config import get_settings
    threshold = get_settings().ai_confidence_threshold

    existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == upload.id)).scalar_one_or_none()
    if existing_tx:
        return existing_tx
    if upload.status in {UploadStatus.REJECTED, UploadStatus.DUPLICATE}:
        return None

    if result.confidence is None or float(result.confidence) < threshold:
        upload.status = UploadStatus.NEEDS_REVIEW
        result.status = UploadStatus.NEEDS_REVIEW
        db.commit()
        return None
    if not result.transaction_code or not result.amount or result.amount <= 0 or not result.bank_account_id:
        upload.status = UploadStatus.NEEDS_REVIEW
        result.status = UploadStatus.NEEDS_REVIEW
        db.commit()
        return None

    duplicate = db.execute(select(Transaction).where(
        Transaction.bank_account_id == result.bank_account_id,
        Transaction.transaction_code == result.transaction_code,
    ).with_for_update()).scalar_one_or_none()
    if duplicate:
        upload.status = UploadStatus.DUPLICATE
        result.status = UploadStatus.DUPLICATE
        db.commit()
        return None

    member = None
    if result.campaign_id:
        campaign = db.get(CollectionCampaign, result.campaign_id)
        if not campaign:
            upload.status = UploadStatus.NEEDS_REVIEW; result.status = UploadStatus.NEEDS_REVIEW; db.commit(); return None
        if Decimal(result.amount) != Decimal(campaign.expected_amount) or not result.student_id:
            upload.status = UploadStatus.NEEDS_REVIEW; result.status = UploadStatus.NEEDS_REVIEW; db.commit(); return None
        member = db.execute(select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id, CampaignMember.student_id == result.student_id,
        ).with_for_update()).scalar_one_or_none()
        if not member or member.status == CampaignMemberStatus.PAID:
            upload.status = UploadStatus.NEEDS_REVIEW if member else UploadStatus.DUPLICATE
            result.status = upload.status
            db.commit()
            return None

    try:
        tx = post_transaction(
            db, account=account, type_=LedgerType.CREDIT, amount=Decimal(result.amount), currency=account.currency,
            source=LedgerSource.IMAGE, transaction_code=result.transaction_code, bank_account_id=result.bank_account_id,
            upload_id=upload.id, created_by=actor_id, effective_at=result.transaction_time or upload.created_at,
            note=f"AI_VERIFIED confidence={result.confidence}", audit_actor_id=actor_id,
            idempotency_key=idempotency_key, commit=False,
        )
        upload.status = UploadStatus.VERIFIED
        result.status = UploadStatus.VERIFIED
        if member and result.student_id and result.campaign_id:
            member.status = CampaignMemberStatus.PAID
            db.add(PaymentMatch(transaction_id=tx.id, campaign_id=result.campaign_id, student_id=result.student_id,
                                confidence=result.confidence, matched_by="AI"))
        db.commit()
        return tx
    except IntegrityError:
        db.rollback()
        upload = db.get(Upload, upload.id)
        if upload:
            upload.status = UploadStatus.DUPLICATE
            db.commit()
        return None
