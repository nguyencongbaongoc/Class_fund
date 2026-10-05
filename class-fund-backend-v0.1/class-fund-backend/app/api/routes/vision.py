"""Vision processing endpoint for AI worker."""
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import require_ai_service
from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import ExtractedTransaction, Upload, UploadStatus, Message, Transaction, Account
from app.schemas.schemas import AIResultIn
from app.services.ledger import verify_and_post_from_ai, VerifyAndPostResult, ProcessingResult
from app.services.ollama_client import get_vision_client, VisionResult
from ai.duplicate.service import DuplicateDetector


router = APIRouter(prefix="/internal/vision", tags=["vision-internal"], dependencies=[Depends(require_ai_service)])


class VisionProcessRequest(BaseModel):
    upload_id: str
    image_data_hex: str  # Image as hex string
    idempotency_key: str = Header(..., alias="Idempotency-Key")


class VisionProcessResponse(BaseModel):
    upload_id: str
    status: str
    extraction: dict | None = None
    field_confidences: dict | None = None
    processing_status: str
    error: str | None = None
    correlation_id: str | None = None


@router.post("/process", response_model=VisionProcessResponse)
def process_receipt_vision(
    body: VisionProcessRequest,
    db: Session = Depends(get_db)
):
    """Process receipt image through vision model and return extraction."""
    correlation_id = str(uuid.uuid4())[:8]
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
            error=None,
            correlation_id=correlation_id
        )
    
    # Get image from local storage
    try:
        file_path = Path(upload.storage_path)
        if not file_path.exists():
            raise HTTPException(404, f"Image file not found: {upload.storage_path}")
        image_bytes = file_path.read_bytes()
    except Exception as e:
        raise HTTPException(500, f"Failed to retrieve image: {e}")
    
    # Compute perceptual hash for duplicate detection
    from ai.ocr.service import compute_perceptual_hash
    perceptual_hash = compute_perceptual_hash(image_bytes)
    upload.perceptual_hash = perceptual_hash
    
    # Process with vision model
    vision_client = get_vision_client()
    vision_result: VisionResult = vision_client.extract_from_image(image_bytes, correlation_id)
    
    # Create/update extraction record
    extraction = db.execute(
        select(ExtractedTransaction).where(ExtractedTransaction.upload_id == upload.id)
    ).scalar_one_or_none()
    
    if vision_result.error:
        # Vision failed - try text fallback with OCR
        from ai.ocr.service import OCRService
        ocr_service = OCRService()
        try:
            ocr_result = ocr_service.process(image_bytes)
            vision_result = vision_client.extract_with_text_fallback(image_bytes, ocr_result.raw_text, correlation_id)
        except Exception as ocr_error:
            # Both vision and OCR failed
            upload.status = UploadStatus.NEEDS_REVIEW
            if extraction:
                extraction.status = UploadStatus.NEEDS_REVIEW
            db.commit()
            
            return VisionProcessResponse(
                upload_id=upload.id,
                status=upload.status.value,
                extraction=None,
                processing_status="needs_human_review",
                error=f"Vision: {vision_result.error}; OCR: {ocr_error}",
                correlation_id=correlation_id
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
    
    # Build field-level confidences (simplified - in practice would come from structured extraction)
    field_confidences = {
        "transaction_code": 0.9 if vision_result.transaction_code else 0.0,
        "amount": 0.9 if vision_result.amount else 0.0,
        "sender_name": 0.8 if vision_result.sender_name else 0.0,
        "bank_name": 0.8 if vision_result.bank_name else 0.0,
        "transaction_time": 0.7 if vision_result.transaction_time else 0.0,
    }
    
    if extraction:
        for key, value in extraction_data.items():
            setattr(extraction, key, value)
        extraction.field_confidences = field_confidences
        extraction.extraction_method = "vision"
        extraction.source_image_id = upload.id
        extraction.currency = "VND"
        extraction.status = UploadStatus.PROCESSING
    else:
        extraction = ExtractedTransaction(
            upload_id=upload.id,
            field_confidences=field_confidences,
            extraction_method="vision",
            source_image_id=upload.id,
            currency="VND",
            **extraction_data,
            status=UploadStatus.PROCESSING
        )
        db.add(extraction)
    
    db.flush()
    
    # If confidence is high enough, proceed to verification
    if vision_result.needs_human_review or vision_result.confidence < 0.7:
        upload.status = UploadStatus.NEEDS_REVIEW
        extraction.status = UploadStatus.NEEDS_REVIEW
        db.commit()
    else:
        # Persist duplicate detection data for successful extractions
        detector = DuplicateDetector()
        detector.persist_duplicate_data(db, image_bytes, extraction)
        db.commit()
        
        return VisionProcessResponse(
            upload_id=upload.id,
            status=upload.status.value,
            extraction=extraction_data,
            field_confidences=field_confidences,
            processing_status="needs_human_review",
            error="Low confidence - requires human review",
            correlation_id=correlation_id
        )
    
    # High confidence - proceed to AI verification
    upload.status = UploadStatus.PROCESSING
    
    # Get default account
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
        field_confidences=field_confidences,
        processing_status=result.status.value,
        correlation_id=correlation_id
    )
    if result.error_message:
        response.error = result.error_message
    
    return response


from pydantic import BaseModel