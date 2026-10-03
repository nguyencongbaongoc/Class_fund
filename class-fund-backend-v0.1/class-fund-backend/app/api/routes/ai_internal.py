from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_ai_service
from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import Account, ExtractedTransaction, Transaction, Upload, UploadStatus
from app.schemas.schemas import AIResultIn
from app.services.ledger import verify_and_post_from_ai

router = APIRouter(prefix="/internal/ai", tags=["ai-internal"], dependencies=[Depends(require_ai_service)])


@router.get("/uploads/{upload_id}/file")
def get_upload_file(upload_id: str, db: Session = Depends(get_db)):
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    return FileResponse(upload.storage_path, filename=upload.original_filename, media_type="application/octet-stream")


@router.post("/uploads/{upload_id}/result")
def receive_ai_result(upload_id: str, body: AIResultIn, idempotency_key: str = Header(..., alias="Idempotency-Key"),
                     db: Session = Depends(get_db)):
    upload = db.get(Upload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    existing_tx = db.execute(select(Transaction).where(Transaction.upload_id == upload.id)).scalar_one_or_none()
    if existing_tx:
        return {"upload_id": upload.id, "status": upload.status.value, "transaction_id": existing_tx.id, "posted": True}

    upload.status = UploadStatus.PROCESSING
    extraction = db.execute(select(ExtractedTransaction).where(ExtractedTransaction.upload_id == upload.id)).scalar_one_or_none()
    data = body.model_dump()
    account_id = data.pop("account_id", None)
    if extraction:
        for key, value in data.items():
            setattr(extraction, key, value)
    else:
        extraction = ExtractedTransaction(upload_id=upload.id, **data, status=UploadStatus.PROCESSING)
        db.add(extraction)
        db.flush()

    account = db.get(Account, account_id) if account_id else None
    if not account:
        account = db.execute(select(Account).where(Account.active.is_(True)).order_by(Account.created_at)).scalars().first()
    if not account:
        raise HTTPException(500, "No active fund account configured")

    tx = verify_and_post_from_ai(db, upload, extraction, account=account, actor_id=None, idempotency_key=idempotency_key)
    return {"upload_id": upload.id, "status": upload.status.value, "transaction_id": tx.id if tx else None, "posted": tx is not None}
