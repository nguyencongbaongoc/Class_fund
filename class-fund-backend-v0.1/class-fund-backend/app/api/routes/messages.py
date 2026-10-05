"""Message API routes for guest chat and recall."""
from datetime import datetime, timezone
from hashlib import sha256
from secrets import token_bytes
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import (
    Message, MessageStatus, RecallToken, Transaction, Upload, UploadStatus, ExtractedTransaction
)
from app.schemas.schemas import UploadOut, ExtractionData
from app.services.ledger import post_revert, ProcessingResult


router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreate(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    sender_name: str = Field(..., min_length=1, max_length=120)
    sender_photo: Optional[str] = Field(None, max_length=500)
    message_type: str = Field(default="TEXT", pattern="^(TEXT|RECEIPT|IMAGE|ANNOUNCEMENT|SYSTEM)$")
    content: str = Field(..., min_length=1)
    attachment_id: Optional[str] = None
    attachment_ids: Optional[list[str]] = Field(default=None, max_length=5)


class MessageCreateResponse(BaseModel):
    message_id: str
    public_code: str
    recall_token: str  # Only returned once!
    status: str
    created_at: datetime


class RecallRequest(BaseModel):
    recall_token: str = Field(..., min_length=64, max_length=64)
    reason: str = Field(default="User recalled", min_length=1, max_length=500)


class RecallEligibilityResponse(BaseModel):
    eligible: bool
    message_id: str
    status: str
    reason: Optional[str] = None
    can_recall_before_post: bool = False
    can_recall_after_post: bool = False
    has_token: bool = False
    token_expired: bool = False
    token_used: bool = False
    token_revoked: bool = False
    already_recalled: bool = False
    transaction_posted: bool = False


class RecallResponse(BaseModel):
    message_id: str
    status: str
    recalled_at: datetime
    reversal_transaction_id: Optional[str] = None


class MessageStatusResponse(BaseModel):
    message_id: str
    conversation_id: str
    sender_name: str
    sender_role: str
    message_type: str
    content: str
    status: str
    public_code: Optional[str]
    transaction_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    attachment_ids: Optional[list[str]] = None
    extraction: Optional[ExtractionData] = None


def generate_public_code() -> str:
    """Generate human-readable public code: CF-YYYYMMDD-XXXXXX"""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = token_bytes(3).hex().upper()
    return f"CF-{date_part}-{random_part}"


def generate_recall_token() -> tuple[str, str]:
    """Generate recall token and its hash.
    Returns: (token_hex, token_hash_hex)
    """
    token = token_bytes(32)
    token_hex = token.hex()
    token_hash = sha256(token).hexdigest()
    return token_hex, token_hash


@router.post("", response_model=MessageCreateResponse, status_code=201)
def create_message(
    body: MessageCreate,
    db: Session = Depends(get_db)
):
    """Create a new guest message with recall token."""
    # Verify uploads exist if attachments provided
    attachment_ids = body.attachment_ids or ([body.attachment_id] if body.attachment_id else [])
    for attachment_id in attachment_ids:
        upload = db.get(Upload, attachment_id)
        if not upload:
            raise HTTPException(404, f"Upload {attachment_id} not found")
        if upload.status not in (UploadStatus.PENDING, UploadStatus.PROCESSING):
            raise HTTPException(409, f"Upload {attachment_id} already processed")
    
    # Generate recall token
    recall_token, token_hash = generate_recall_token()
    
    # Generate public code
    public_code = generate_public_code()
    # Ensure uniqueness (retry if collision)
    while db.execute(select(Message).where(Message.public_code == public_code)).scalar_one_or_none():
        public_code = generate_public_code()
    
    # Create message - store first attachment_id for backward compatibility
    first_attachment_id = attachment_ids[0] if attachment_ids else None
    message = Message(
        conversation_id=body.conversation_id,
        sender_id=None,  # Guest
        sender_name=body.sender_name.strip(),
        sender_photo=body.sender_photo,
        sender_role="PUBLIC",
        message_type=body.message_type,
        content=body.content.strip(),
        attachment_id=first_attachment_id,
        attachment_ids=attachment_ids if attachment_ids else None,
        status=MessageStatus.PENDING.value,
        public_code=public_code,
        recall_token_hash=token_hash,
    )
    db.add(message)
    db.flush()
    
    # Store recall token
    recall_token_record = RecallToken(
        message_id=message.id,
        token_hash=token_hash,
        expires_at=None,  # No expiry by default
    )
    db.add(recall_token_record)
    db.commit()
    db.refresh(message)
    
    return MessageCreateResponse(
        message_id=message.id,
        public_code=message.public_code,
        recall_token=recall_token,  # ONLY TIME THIS IS RETURNED!
        status=message.status,
        created_at=message.created_at,
    )


@router.post("/{message_id}/recall", response_model=RecallResponse)
def recall_message(
    message_id: str,
    body: RecallRequest,
    db: Session = Depends(get_db)
):
    """Recall a message using the private recall token."""
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(404, "Message not found")
    
    # Validate recall token
    token_hash = sha256(bytes.fromhex(body.recall_token)).hexdigest()
    recall_token = db.execute(
        select(RecallToken).where(RecallToken.message_id == message_id)
    ).scalar_one_or_none()
    
    if not recall_token:
        raise HTTPException(403, "Recall not authorized: no token found")
    
    if recall_token.token_hash != token_hash:
        raise HTTPException(403, "Recall not authorized: invalid token")
    
    if recall_token.used_at:
        raise HTTPException(409, "Recall token already used")
    
    if recall_token.revoked_at:
        raise HTTPException(403, "Recall token revoked")
    
    if recall_token.expires_at and recall_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(403, "Recall token expired")
    
    # Check current message status
    if message.status == MessageStatus.RECALLED.value:
        raise HTTPException(409, "Message already recalled")
    
    # If message already posted (has transaction), create reversal
    reversal_transaction_id = None
    if message.transaction_id and message.status == MessageStatus.POSTED.value:
        original_tx = db.get(Transaction, message.transaction_id)
        if original_tx:
            rev_result = post_revert(
                db, original=original_tx, actor_id=None,  # System actor
                reason=body.reason,
                message_id=message_id
            )
            if rev_result.status == ProcessingResult.SUCCESS:
                reversal_transaction_id = rev_result.transaction.id
            else:
                raise HTTPException(500, f"Failed to create reversal: {rev_result.error_message}")
    
    # Mark message as recalled
    message.status = MessageStatus.RECALLED.value
    message.processed_at = datetime.now(timezone.utc)
    message.error_message = body.reason
    
    # Mark recall token as used
    recall_token.used_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return RecallResponse(
        message_id=message.id,
        status=message.status,
        recalled_at=message.processed_at,
        reversal_transaction_id=reversal_transaction_id,
    )


@router.get("/{message_id}/recall-eligibility", response_model=RecallEligibilityResponse)
def check_recall_eligibility(
    message_id: str,
    db: Session = Depends(get_db)
):
    """Check if a message is eligible for recall without consuming the token.
    This endpoint provides server-authoritative eligibility information.
    """
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(404, "Message not found")
    
    # Check recall token existence
    recall_token = db.execute(
        select(RecallToken).where(RecallToken.message_id == message_id)
    ).scalar_one_or_none()
    
    has_token = recall_token is not None
    token_expired = False
    token_used = False
    token_revoked = False
    
    if recall_token:
        token_expired = recall_token.expires_at and recall_token.expires_at < datetime.now(timezone.utc)
        token_used = recall_token.used_at is not None
        token_revoked = recall_token.revoked_at is not None
    
    already_recalled = message.status == MessageStatus.RECALLED.value
    transaction_posted = message.transaction_id is not None and message.status == MessageStatus.POSTED.value
    
    # Determine eligibility
    eligible = True
    reasons = []
    
    if not has_token:
        eligible = False
        reasons.append("No recall token found")
    
    if token_expired:
        eligible = False
        reasons.append("Recall token expired")
    
    if token_used:
        eligible = False
        reasons.append("Recall token already used")
    
    if token_revoked:
        eligible = False
        reasons.append("Recall token revoked")
    
    if already_recalled:
        eligible = False
        reasons.append("Message already recalled")
    
    can_recall_before_post = (
        eligible and 
        message.status in [MessageStatus.PENDING.value, MessageStatus.PROCESSING.value, MessageStatus.AWAITING_REVIEW.value]
    )
    
    can_recall_after_post = (
        eligible and 
        transaction_posted
    )
    
    reason = "; ".join(reasons) if reasons else "Eligible for recall"
    
    return RecallEligibilityResponse(
        eligible=eligible,
        message_id=message.id,
        status=message.status,
        reason=reason,
        can_recall_before_post=can_recall_before_post,
        can_recall_after_post=can_recall_after_post,
        has_token=has_token,
        token_expired=token_expired,
        token_used=token_used,
        token_revoked=token_revoked,
        already_recalled=already_recalled,
        transaction_posted=transaction_posted,
    )


@router.get("/{message_id}", response_model=MessageStatusResponse)
def get_message_status(
    message_id: str,
    db: Session = Depends(get_db)
):
    """Get message status (public, no authorization needed)."""
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(404, "Message not found")
    
    # Get extraction data if exists
    extraction = None
    if message.attachment_ids:
        for attachment_id in message.attachment_ids:
            ext = db.execute(
                select(ExtractedTransaction).where(ExtractedTransaction.upload_id == attachment_id)
            ).scalar_one_or_none()
            if ext:
                extraction = ExtractionData(
                    transaction_code=ext.transaction_code,
                    amount=int(ext.amount) if ext.amount else None,
                    sender_name=ext.sender_name,
                    bank_name=ext.bank_name,
                    transaction_time=ext.transaction_time.isoformat() if ext.transaction_time else None,
                    confidence=float(ext.confidence) if ext.confidence else None,
                    raw_ocr=ext.raw_ocr,
                    status=ext.status.value if ext.status else None,
                    field_confidences=ext.field_confidences,
                )
                break
    elif message.attachment_id:
        ext = db.execute(
            select(ExtractedTransaction).where(ExtractedTransaction.upload_id == message.attachment_id)
        ).scalar_one_or_none()
        if ext:
            extraction = ExtractionData(
                transaction_code=ext.transaction_code,
                amount=int(ext.amount) if ext.amount else None,
                sender_name=ext.sender_name,
                bank_name=ext.bank_name,
                transaction_time=ext.transaction_time.isoformat() if ext.transaction_time else None,
                confidence=float(ext.confidence) if ext.confidence else None,
                raw_ocr=ext.raw_ocr,
                status=ext.status.value if ext.status else None,
                field_confidences=ext.field_confidences,
            )
    
    return MessageStatusResponse(
        message_id=message.id,
        conversation_id=message.conversation_id,
        sender_name=message.sender_name,
        sender_role=message.sender_role,
        message_type=message.message_type,
        content=message.content,
        status=message.status,
        public_code=message.public_code,
        transaction_id=message.transaction_id,
        error_message=message.error_message,
        created_at=message.created_at,
        processed_at=message.processed_at,
        attachment_ids=message.attachment_ids,
        extraction=extraction,
    )


@router.get("", response_model=list[MessageStatusResponse])
def list_messages(
    conversation_id: str = Query(...),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List messages in a conversation."""
    query = select(Message).where(Message.conversation_id == conversation_id)
    if status:
        query = query.where(Message.status == status)
    query = query.order_by(Message.created_at.desc()).limit(limit).offset(offset)
    
    messages = db.execute(query).scalars().all()
    
    result = []
    for m in messages:
        # Get extraction data if exists
        extraction = None
        attachment_ids = m.attachment_ids or ([m.attachment_id] if m.attachment_id else [])
        for attachment_id in attachment_ids:
            ext = db.execute(
                select(ExtractedTransaction).where(ExtractedTransaction.upload_id == attachment_id)
            ).scalar_one_or_none()
            if ext:
                extraction = ExtractionData(
                    transaction_code=ext.transaction_code,
                    amount=int(ext.amount) if ext.amount else None,
                    sender_name=ext.sender_name,
                    bank_name=ext.bank_name,
                    transaction_time=ext.transaction_time.isoformat() if ext.transaction_time else None,
                    confidence=float(ext.confidence) if ext.confidence else None,
                    raw_ocr=ext.raw_ocr,
                    status=ext.status.value if ext.status else None,
                    field_confidences=ext.field_confidences,
                )
                break
        
        result.append(
            MessageStatusResponse(
                message_id=m.id,
                conversation_id=m.conversation_id,
                sender_name=m.sender_name,
                sender_role=m.sender_role,
                message_type=m.message_type,
                content=m.content,
                status=m.status,
                public_code=m.public_code,
                transaction_id=m.transaction_id,
                error_message=m.error_message,
                created_at=m.created_at,
                processed_at=m.processed_at,
                attachment_ids=m.attachment_ids,
                extraction=extraction,
            )
        )
    
    return result