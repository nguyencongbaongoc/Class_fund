from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import ExtractedTransaction, Transaction, Upload, UploadStatus
from app.schemas.schemas import UploadOut, UploadStatusOut

router = APIRouter(prefix="/uploads", tags=["uploads"])
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


@router.post("", response_model=UploadOut, status_code=201)
async def upload_receipt(file: UploadFile = File(...), uploader_name: str = Form(...), db: Session = Depends(get_db)):
    settings = get_settings()
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, "Only JPEG, PNG or WEBP images are accepted")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Image is too large")
    if not uploader_name.strip():
        raise HTTPException(422, "uploader_name is required")
    file_hash = sha256(data).hexdigest()

    existing = db.execute(select(Upload).where(Upload.file_hash == file_hash)).scalar_one_or_none()
    if existing:
        duplicate = Upload(
            file_hash=file_hash, perceptual_hash=existing.perceptual_hash,
            original_filename=file.filename or existing.original_filename,
            storage_path=existing.storage_path, uploaded_by=None,
            uploader_name=uploader_name.strip(), status=UploadStatus.DUPLICATE,
        )
        db.add(duplicate); db.commit(); db.refresh(duplicate)
        return duplicate

    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[file.content_type]
    path = Path(settings.upload_dir) / f"{uuid4()}{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    upload = Upload(file_hash=file_hash, original_filename=file.filename or "receipt", storage_path=str(path),
                    uploaded_by=None, uploader_name=uploader_name.strip(), status=UploadStatus.PENDING)
    db.add(upload)
    db.commit(); db.refresh(upload)
    return upload


@router.get("/{upload_id}", response_model=UploadStatusOut)
def get_upload_status(upload_id: str, db: Session = Depends(get_db)):
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    extraction = db.execute(select(ExtractedTransaction).where(ExtractedTransaction.upload_id == upload.id)).scalar_one_or_none()
    tx = db.execute(select(Transaction).where(Transaction.upload_id == upload.id)).scalar_one_or_none()
    extracted = None
    rejection = None
    if extraction:
        extracted = {
            "transaction_code": extraction.transaction_code,
            "amount": extraction.amount,
            "sender_name": extraction.sender_name,
            "bank_name": extraction.bank_name,
            "transaction_time": extraction.transaction_time,
            "confidence": extraction.confidence,
            "status": extraction.status.value,
        }
        if extraction.status == UploadStatus.NEEDS_REVIEW:
            rejection = "AI result needs human review or failed financial validation"
    return {"id": upload.id, "uploader_name": upload.uploader_name, "original_filename": upload.original_filename,
            "status": upload.status.value, "created_at": upload.created_at, "extracted": extracted,
            "transaction_id": tx.id if tx else None, "rejection_reason": rejection}
