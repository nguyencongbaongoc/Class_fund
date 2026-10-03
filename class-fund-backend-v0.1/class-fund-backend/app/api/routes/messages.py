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
    Message, MessageStatus, RecallToken, Transaction, Upload, UploadStatus
)
from app.schemas.schemas import UploadOut
from app.services.ledger import post_revert, ProcessingResult


router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreate(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    sender_name: str = Field(..., min_length=1, max_length=120)
    sender_photo: Optional[str] = Field(None, max_length=500)
    message_type: str = Field(default="TEXT", pattern="^(TEXT|RECEIPT|IMAGE)$")
    content: str = Field(..., min_length=1)
    attachment_id: Optional[str] = None


class MessageCreateResponse(BaseModel):
    message_id: str
    public_code: str
    recall_token: str  # Only returned once!
    status: str
    created_at: datetime


class RecallRequest(BaseModel):
    recall_token: str = Field(..., min_length=64, max_length=64)
    reason: str = Field(default="User recalled", min_length=1, max_length=500)


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
    # Verify upload exists if attachment provided
    if body.attachment_id:
        upload = db.get(Upload, body.attachment_id)
        if not upload:
            raise HTTPException(404, "Upload not found")
        if upload.status not in (UploadStatus.PENDING, UploadStatus.PROCESSING):
            raise HTTPException(409, "Upload already processed")
    
    # Generate recall token
    recall_token, token_hash = generate_recall_token()
    
    # Generate public code
    public_code = generate_public_code()
    # Ensure uniqueness (retry if collision)
    while db.execute(select(Message).where(Message.public_code == public_code)).scalar_one_or_none():
        public_code = generate_public_code()
    
    # Create message
    message = Message(
        conversation_id=body.conversation_id,
        sender_id=None,  # Guest
        sender_name=body.sender_name.strip(),
        sender_photo=body.sender_photo,
        sender_role="PUBLIC",
        message_type=body.message_type,
        content=body.content.strip(),
        attachment_id=body.attachment_id,
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


@router.get("/{message_id}", response_model=MessageStatusResponse)
def get_message_status(
    message_id: str,
    db: Session = Depends(get_db)
):
    """Get message status (public, no authorization needed)."""
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(404, "Message not found")
    
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
    
    return [
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
        )
        for m in messages
    ]