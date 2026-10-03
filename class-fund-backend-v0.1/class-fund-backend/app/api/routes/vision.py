"""Vision processing endpoint for AI worker."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_ai_service
from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import ExtractedTransaction, Upload, UploadStatus
from app.schemas.schemas import AIResultIn
from app.services.ledger import verify_and_post_from_ai, VerifyAndPostResult, ProcessingResult
from app.services.ollama_client import get_vision_client, VisionResult


router = APIRouter(prefix="/internal/vision", tags=["vision-internal"], dependencies=[Depends(require_ai_service)])


class VisionProcessRequest(BaseModel):
    upload_id: str
    image_data_hex: str  # Image as hex string
    idempotency_key: str = Header(..., alias="Idempotency-Key")


class VisionProcessResponse(BaseModel):
    upload_id: str
    status: str
    extraction: dict | None = None
    processing_status: str
    error: str | None = None


@router.post("/process", response_model=VisionProcessResponse)
def process_receipt_vision(
    body: VisionProcessRequest,
    db: Session = Depends(get_db)
):
    """Process receipt image through vision model and return extraction."""
    upload = db.get(Upload, body.upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    
    # Check if already processed
    existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == upload.id)).scalar_one_or_none()
    if existing_tx:
        return VisionProcessResponse(
            upload_id=upload.id,
            status=upload.status.value,
            extraction=None,
            processing_status="already_processed",
            error=None
        )
    
    # Get image from storage (Supabase or local)
    from app.services.supabase_client import get_supabase_client
    
    supabase = get_supabase_client()
    try:
        if upload.storage_path.startswith("uploads/"):
            # Supabase storage
            image_bytes = supabase.download_receipt(upload.storage_path)
        else:
            # Local storage
            with open(upload.storage_path, "rb") as f:
                image_bytes = f.read()
    except Exception as e:
        raise HTTPException(500, f"Failed to retrieve image: {e}")
    
    # Process with vision model
    vision_client = get_vision_client()
    vision_result: VisionResult = vision_client.extract_from_image(image_bytes)
    
    # Create/update extraction record
    extraction = db.execute(
        select(ExtractedTransaction).where(ExtractedTransaction.upload_id == upload.id)
    ).scalar_one_or_none()
    
    if vision_result.error:
        # Vision failed - mark for human review
        upload.status = UploadStatus.NEEDS_REVIEW
        if extraction:
            extraction.status = UploadStatus.NEEDS_REVIEW
        db.commit()
        
        return VisionProcessResponse(
            upload_id=upload.id,
            status=upload.status.value,
            extraction=None,
            processing_status="needs_human_review",
            error=vision_result.error
        )
    
    # Build extraction data
    extraction_data = {
        "transaction_code": vision_result.transaction_code,
        "amount": vision_result.amount,
        "sender_name": vision_result.sender_name,
        "bank_name": vision_result.bank_name,
        "transaction_time": vision_result.transaction_time,
        "confidence": vision_result.confidence,
        "raw_ocr": vision_result.raw_text,
    }
    
    if extraction:
        for key, value in extraction_data.items():
            setattr(extraction, key, value)
        extraction.status = UploadStatus.PROCESSING
    else:
        extraction = ExtractedTransaction(upload_id=upload.id, **extraction_data, status=UploadStatus.PROCESSING)
        db.add(extraction)
    
    db.flush()
    
    # If confidence is high enough, proceed to verification
    if vision_result.needs_human_review or vision_result.confidence < 0.7:
        upload.status = UploadStatus.NEEDS_REVIEW
        extraction.status = UploadStatus.NEEDS_REVIEW
        db.commit()
        
        return VisionProcessResponse(
            upload_id=upload.id,
            status=upload.status.value,
            extraction=extraction_data,
            processing_status="needs_human_review",
            error="Low confidence - requires human review"
        )
    
    # High confidence - proceed to AI verification
    upload.status = UploadStatus.PROCESSING
    
    # Get default account
    from app.models.models import Account
    account = db.execute(
        select(Account).where(Account.active.is_(True)).order_by(Account.created_at)
    ).scalars().first()
    
    if not account:
        raise HTTPException(500, "No active fund account configured")
    
    # Verify and post
    message = db.execute(select(Message).where(Message.attachment_id == upload.id)).scalar_one_or_none()
    message_id = message.id if message else None
    logical_operation_id = f"msg_{message_id}" if message_id else None
    attempt_id = f"attempt_{message.retry_count + 1}" if message else "attempt_1"
    
    result = verify_and_post_from_ai(
        db, upload, extraction, account=account, actor_id=None,
        idempotency_key=body.idempotency_key,
        message_id=message_id,
        logical_operation_id=logical_operation_id,
        attempt_id=attempt_id
    )
    
    response = VisionProcessResponse(
        upload_id=upload.id,
        status=upload.status.value,
        extraction=extraction_data,
        processing_status=result.status.value,
    )
    if result.error_message:
        response.error = result.error_message
    
    return response


# Need to import Message for the vision endpoint
from app.models.models import Message, Transaction
from pydantic import BaseModel