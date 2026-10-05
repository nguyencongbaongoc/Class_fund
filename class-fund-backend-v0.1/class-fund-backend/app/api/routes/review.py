"""Human Review API endpoints for AI pipeline."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import (
    ExtractedTransaction, Message, MessageStatus, Transaction, Upload, UploadStatus, User, Role
)
from app.services.ledger import verify_and_post_from_ai, ProcessingResult


router = APIRouter(prefix="/internal/review", tags=["review-internal"], dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))])


class ReviewListItem(BaseModel):
    extraction_id: str
    upload_id: str
    transaction_code: Optional[str]
    amount: Optional[int]
    sender_name: Optional[str]
    bank_name: Optional[str]
    transaction_time: Optional[str]
    confidence: Optional[float]
    status: str
    created_at: datetime
    uploader_name: str
    message_id: Optional[str]


class ReviewDetail(BaseModel):
    extraction_id: str
    upload_id: str
    transaction_code: Optional[str]
    amount: Optional[int]
    sender_name: Optional[str]
    bank_name: Optional[str]
    transaction_time: Optional[str]
    confidence: Optional[float]
    raw_ocr: Optional[str]
    field_confidences: Optional[dict]
    extraction_method: Optional[str]
    currency: Optional[str]
    status: str
    created_at: datetime
    upload: dict
    message: Optional[dict]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]


class ReviewApproveRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true to approve")


class ReviewRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class ReviewResponse(BaseModel):
    extraction_id: str
    status: str
    reviewed_by: str
    reviewed_at: datetime
    review_notes: Optional[str]
    transaction_id: Optional[str] = None


@router.get("", response_model=list[ReviewListItem])
def list_pending_reviews(
    status: str = Query("NEEDS_REVIEW", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List extraction records pending review."""
    # Only allow NEEDS_REVIEW status for security
    if status != "NEEDS_REVIEW":
        raise HTTPException(400, "Only NEEDS_REVIEW status can be listed")
    
    query = select(ExtractedTransaction).where(
        ExtractedTransaction.status == UploadStatus.NEEDS_REVIEW
    ).order_by(ExtractedTransaction.created_at.desc()).limit(limit).offset(offset)
    
    extractions = db.execute(query).scalars().all()
    
    result = []
    for ext in extractions:
        # Get associated upload
        upload = db.get(Upload, ext.upload_id)
        # Get associated message if exists
        message = None
        if ext.upload_id:
            message = db.execute(
                select(Message).where(Message.attachment_id == ext.upload_id)
            ).scalar_one_or_none()
        
        result.append(ReviewListItem(
            extraction_id=ext.id,
            upload_id=ext.upload_id,
            transaction_code=ext.transaction_code,
            amount=int(ext.amount) if ext.amount else None,
            sender_name=ext.sender_name,
            bank_name=ext.bank_name,
            transaction_time=ext.transaction_time.isoformat() if ext.transaction_time else None,
            confidence=float(ext.confidence) if ext.confidence else None,
            status=ext.status.value,
            created_at=ext.created_at,
            uploader_name=upload.uploader_name if upload else "Unknown",
            message_id=message.id if message else None
        ))
    
    return result


@router.get("/{extraction_id}", response_model=ReviewDetail)
def get_review_detail(
    extraction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed review information for an extraction."""
    extraction = db.get(ExtractedTransaction, extraction_id)
    if not extraction:
        raise HTTPException(404, "Extraction not found")
    
    if extraction.status != UploadStatus.NEEDS_REVIEW:
        raise HTTPException(409, f"Extraction is not in NEEDS_REVIEW status (current: {extraction.status.value})")
    
    upload = db.get(Upload, extraction.upload_id)
    message = None
    if extraction.upload_id:
        message = db.execute(
            select(Message).where(Message.attachment_id == extraction.upload_id)
        ).scalar_one_or_none()
    
    return ReviewDetail(
        extraction_id=extraction.id,
        upload_id=extraction.upload_id,
        transaction_code=extraction.transaction_code,
        amount=int(extraction.amount) if extraction.amount else None,
        sender_name=extraction.sender_name,
        bank_name=extraction.bank_name,
        transaction_time=extraction.transaction_time.isoformat() if extraction.transaction_time else None,
        confidence=float(extraction.confidence) if extraction.confidence else None,
        raw_ocr=extraction.raw_ocr,
        field_confidences=extraction.field_confidences,
        extraction_method=extraction.extraction_method,
        currency=extraction.currency,
        status=extraction.status.value,
        created_at=extraction.created_at,
        upload={
            "id": upload.id,
            "original_filename": upload.original_filename,
            "uploader_name": upload.uploader_name,
            "storage_path": upload.storage_path,
            "created_at": upload.created_at,
        } if upload else None,
        message={
            "id": message.id,
            "content": message.content,
            "sender_name": message.sender_name,
            "public_code": message.public_code,
        } if message else None,
        reviewed_by=extraction.reviewed_by,
        reviewed_at=extraction.reviewed_at,
        review_notes=extraction.review_notes,
    )


@router.post("/{extraction_id}/approve", response_model=ReviewResponse)
def approve_extraction(
    extraction_id: str,
    body: ReviewApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve an extraction and proceed to financial posting."""
    if not body.confirm:
        raise HTTPException(400, "Confirmation required to approve")
    
    extraction = db.get(ExtractedTransaction, extraction_id)
    if not extraction:
        raise HTTPException(404, "Extraction not found")
    
    if extraction.status != UploadStatus.NEEDS_REVIEW:
        raise HTTPException(409, f"Extraction is not in NEEDS_REVIEW status (current: {extraction.status.value})")
    
    # Check if already posted
    existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == extraction.upload_id)).scalar_one_or_none()
    if existing_tx:
        raise HTTPException(409, "Transaction already posted")
    
    # Get upload
    upload = db.get(Upload, extraction.upload_id)
    if not upload:
        raise HTTPException(404, "Associated upload not found")
    
    # Get default account
    account = db.execute(
        select(Account).where(Account.active.is_(True)).order_by(Account.created_at)
    ).scalars().first()
    if not account:
        raise HTTPException(500, "No active fund account configured")
    
    # Update extraction with review info
    extraction.reviewed_by = current_user.id
    extraction.reviewed_at = datetime.now(timezone.utc)
    extraction.review_notes = "Approved by reviewer"
    extraction.status = UploadStatus.PROCESSING
    upload.status = UploadStatus.PROCESSING
    
    # Get message for idempotency
    message = db.execute(
        select(Message).where(Message.attachment_id == extraction.upload_id)
    ).scalar_one_or_none()
    message_id = message.id if message else None
    logical_operation_id = f"msg_{message_id}" if message_id else None
    attempt_id = f"attempt_{message.retry_count + 1}" if message else "attempt_1"
    
    # Generate idempotency key
    import hashlib
    payload = f"{extraction.transaction_code}|{extraction.amount}|{extraction.bank_account_id}"
    content_version = hashlib.sha256(payload.encode()).hexdigest()[:8]
    idempotency_key = f"msg_{message_id}_v{content_version}" if message_id else f"review_{extraction_id}_v{content_version}"
    
    # Post through authoritative financial gatekeeper
    result = verify_and_post_from_ai(
        db, upload, extraction, account=account, actor_id=current_user.id,
        idempotency_key=idempotency_key,
        message_id=message_id,
        logical_operation_id=logical_operation_id,
        attempt_id=attempt_id
    )
    
    transaction_id = None
    if result.status in (ProcessingResult.SUCCESS, ProcessingResult.DUPLICATE):
        extraction.status = UploadStatus.VERIFIED
        upload.status = UploadStatus.VERIFIED
        transaction_id = result.transaction.id if result.transaction else None
        
        if message:
            message.status = MessageStatus.POSTED.value
            message.transaction_id = transaction_id
            message.processed_at = datetime.now(timezone.utc)
    elif result.status == ProcessingResult.NEEDS_HUMAN_REVIEW:
        extraction.status = UploadStatus.NEEDS_REVIEW
        upload.status = UploadStatus.NEEDS_REVIEW
    else:
        extraction.status = UploadStatus.NEEDS_REVIEW
        upload.status = UploadStatus.NEEDS_REVIEW
    
    db.commit()
    
    return ReviewResponse(
        extraction_id=extraction.id,
        status=extraction.status.value,
        reviewed_by=current_user.id,
        reviewed_at=extraction.reviewed_at,
        review_notes=extraction.review_notes,
        transaction_id=transaction_id
    )


@router.post("/{extraction_id}/reject", response_model=ReviewResponse)
def reject_extraction(
    extraction_id: str,
    body: ReviewRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an extraction with a reason."""
    extraction = db.get(ExtractedTransaction, extraction_id)
    if not extraction:
        raise HTTPException(404, "Extraction not found")
    
    if extraction.status != UploadStatus.NEEDS_REVIEW:
        raise HTTPException(409, f"Extraction is not in NEEDS_REVIEW status (current: {extraction.status.value})")
    
    # Check if already posted
    existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == extraction.upload_id)).scalar_one_or_none()
    if existing_tx:
        raise HTTPException(409, "Transaction already posted - cannot reject")
    
    upload = db.get(Upload, extraction.upload_id)
    
    # Update extraction with review info
    extraction.reviewed_by = current_user.id
    extraction.reviewed_at = datetime.now(timezone.utc)
    extraction.review_notes = f"Rejected: {body.reason}"
    extraction.status = UploadStatus.REJECTED
    if upload:
        upload.status = UploadStatus.REJECTED
    
    db.commit()
    
    return ReviewResponse(
        extraction_id=extraction.id,
        status=extraction.status.value,
        reviewed_by=current_user.id,
        reviewed_at=extraction.reviewed_at,
        review_notes=extraction.review_notes,
        transaction_id=None
    )