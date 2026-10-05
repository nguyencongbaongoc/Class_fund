from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from starlette.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import csv
import io
import httpx

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import (
    Account, Transaction, LedgerType, Upload, UploadStatus,
    ExtractedTransaction, User, Role, AuditLog, WorkerStatus, Message, MessageStatus
)
from app.schemas.admin import (
    AdminStatsResponse, PaginatedAuditLogsResponse, AuditLogItemResponse,
    WorkerStatusResponse, SystemHealthResponse, ComponentHealth, QueueStatusResponse,
    AuditLogExportRequest, AuditLogExportResponse
)
from app.services.ledger import calculate_balance
from app.services.ollama_client import OllamaClient

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles(Role.OWNER_TREASURER, Role.MODERATOR))])


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get aggregated dashboard statistics."""
    account = db.execute(select(Account).where(Account.active.is_(True)).order_by(Account.created_at)).scalars().first()
    if not account:
        raise HTTPException(404, "No active fund account")
    
    balance = calculate_balance(db, account)
    
    total_income = db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.account_id == account.id, Transaction.type == LedgerType.CREDIT)
    ).scalar() or Decimal("0")
    
    total_expense = db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.account_id == account.id, Transaction.type.in_([LedgerType.DEBIT, LedgerType.REVERT]))
    ).scalar() or Decimal("0")
    
    transaction_count = db.execute(
        select(func.count(Transaction.id)).where(Transaction.account_id == account.id)
    ).scalar() or 0
    
    last_tx = db.execute(
        select(Transaction.effective_at)
        .where(Transaction.account_id == account.id)
        .order_by(Transaction.effective_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    
    pending_review_count = db.execute(
        select(func.count(ExtractedTransaction.id)).where(ExtractedTransaction.status == UploadStatus.NEEDS_REVIEW)
    ).scalar() or 0
    
    processing_review_count = db.execute(
        select(func.count(ExtractedTransaction.id)).where(ExtractedTransaction.status == UploadStatus.PROCESSING)
    ).scalar() or 0
    
    last_review = db.execute(
        select(ExtractedTransaction.reviewed_at)
        .where(ExtractedTransaction.reviewed_at.is_not(None))
        .order_by(ExtractedTransaction.reviewed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    
    workers = db.execute(select(WorkerStatus)).scalars().all()
    worker_total_count = len(workers)
    now = datetime.now(timezone.utc)
    worker_online_count = sum(
        1 for w in workers 
        if w.last_heartbeat and (now - w.last_heartbeat).total_seconds() < 30
    )
    
    queue_pending_count = db.execute(
        select(func.count(Message.id)).where(Message.status == MessageStatus.PENDING.value)
    ).scalar() or 0
    
    queue_processing_count = db.execute(
        select(func.count(Message.id)).where(Message.status == MessageStatus.PROCESSING.value)
    ).scalar() or 0
    
    return AdminStatsResponse(
        current_balance=balance,
        opening_balance=account.opening_balance,
        total_income=total_income,
        total_expense=total_expense,
        transaction_count=transaction_count,
        pending_review_count=pending_review_count,
        processing_review_count=processing_review_count,
        worker_online_count=worker_online_count,
        worker_total_count=worker_total_count,
        queue_pending_count=queue_pending_count,
        queue_processing_count=queue_processing_count,
        last_transaction_at=last_tx,
        last_review_at=last_review,
    )


@router.get("/audit-logs", response_model=PaginatedAuditLogsResponse)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="Filter logs created after this date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter logs created before this date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated audit logs with filters."""
    from sqlalchemy import select, func
    from app.models.models import AuditLog
    
    # Handle FastAPI Query objects when called directly (not through FastAPI)
    def extract_int(val):
        if hasattr(val, '__class__') and 'Query' in val.__class__.__name__:
            return val.default
        return val
    
    limit = extract_int(limit)
    offset = extract_int(offset)
    
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    
    def parse_date(date_val):
        if date_val is None:
            return None
        # Handle FastAPI Query object
        if hasattr(date_val, '__class__') and 'Query' in date_val.__class__.__name__:
            return None
        try:
            return datetime.fromisoformat(date_val.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    dt_from = parse_date(date_from)
    dt_to = parse_date(date_to)
    
    if dt_from:
        query = query.where(AuditLog.created_at >= dt_from)
    if dt_to:
        query = query.where(AuditLog.created_at <= dt_to)
    
    # Count total with same filters
    count_query = select(func.count(AuditLog.id))
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if entity_type:
        count_query = count_query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        count_query = count_query.where(AuditLog.entity_id == entity_id)
    if actor_id:
        count_query = count_query.where(AuditLog.actor_id == actor_id)
    if dt_from:
        count_query = count_query.where(AuditLog.created_at >= dt_from)
    if dt_to:
        count_query = count_query.where(AuditLog.created_at <= dt_to)
    
    total = db.execute(count_query).scalar() or 0
    
    items = db.execute(query.limit(limit).offset(offset)).scalars().all()
    
    result_items = []
    for log in items:
        actor_name = None
        actor_role = None
        if log.actor_id:
            user = db.get(User, log.actor_id)
            if user:
                actor_name = user.name
                actor_role = user.role.value
        
        result_items.append(AuditLogItemResponse(
            id=log.id,
            actor_id=log.actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            before_data=log.before_data,
            after_data=log.after_data,
            ip=log.ip,
            created_at=log.created_at,
        ))
    
    return PaginatedAuditLogsResponse(
        items=result_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-logs/export", response_model=AuditLogExportResponse)
def export_audit_logs(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="Filter logs created after this date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter logs created before this date (ISO format)"),
    limit: Optional[int] = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export audit logs as CSV."""
    from sqlalchemy import select, func
    from app.models.models import AuditLog
    
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.where(AuditLog.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.where(AuditLog.created_at <= dt_to)
        except ValueError:
            pass
    
    # Count total with same filters
    count_query = select(func.count(AuditLog.id))
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if entity_type:
        count_query = count_query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        count_query = count_query.where(AuditLog.entity_id == entity_id)
    if actor_id:
        count_query = count_query.where(AuditLog.actor_id == actor_id)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            count_query = count_query.where(AuditLog.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            count_query = count_query.where(AuditLog.created_at <= dt_to)
        except ValueError:
            pass
    
    total = db.execute(count_query).scalar() or 0
    
    # Apply limit
    query = query.limit(limit)
    
    items = db.execute(query).scalars().all()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Thời gian', 'Hành động', 'Loại thực thể', 'ID thực thể',
        'Người thực hiện', 'Vai trò', 'IP', 'Trước', 'Sau'
    ])
    
    # Data rows
    for log in items:
        actor_name = None
        actor_role = None
        if log.actor_id:
            user = db.get(User, log.actor_id)
            if user:
                actor_name = user.name
                actor_role = user.role.value
        
        before_str = ''
        if log.before_data:
            import json
            before_str = json.dumps(log.before_data, ensure_ascii=False)
        
        after_str = ''
        if log.after_data:
            import json
            after_str = json.dumps(log.after_data, ensure_ascii=False)
        
        writer.writerow([
            log.id,
            log.created_at.isoformat() if log.created_at else '',
            log.action,
            log.entity_type,
            log.entity_id or '',
            actor_name or '',
            actor_role or '',
            log.ip or '',
            before_str,
            after_str,
        ])
    
    csv_content = output.getvalue()
    
    return AuditLogExportResponse(
        csv_content=csv_content,
        total_records=total,
        filename=f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    )


@router.get("/workers", response_model=list[WorkerStatusResponse])
def get_workers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all worker statuses with health computation."""
    workers = db.execute(select(WorkerStatus)).scalars().all()
    now = datetime.now(timezone.utc)
    
    result = []
    for w in workers:
        seconds_since_heartbeat = None
        health: Literal["ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN"] = "UNKNOWN"
        
        if w.last_heartbeat:
            # Ensure both datetimes are timezone-aware for comparison
            heartbeat = w.last_heartbeat
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
            now_aware = datetime.now(timezone.utc)
            seconds_since_heartbeat = int((now_aware - heartbeat).total_seconds())
            if seconds_since_heartbeat < 30:
                health = "ONLINE"
            elif seconds_since_heartbeat < 300:
                health = "DEGRADED"
            else:
                health = "OFFLINE"
        
        result.append(WorkerStatusResponse(
            worker_id=w.worker_id,
            status=w.status,
            model_name=w.model_name,
            last_heartbeat=w.last_heartbeat,
            last_processed_at=w.last_processed_at,
            current_job_id=w.current_job_id,
            metadata=w.worker_metadata or {},
            health=health,
            seconds_since_heartbeat=seconds_since_heartbeat,
        ))
    
    return result


@router.get("/health", response_model=SystemHealthResponse)
def get_system_health(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get system component health checks."""
    components = []
    checked_at = datetime.now(timezone.utc)
    
    # 1. Database check
    db_start = datetime.now(timezone.utc)
    try:
        db.execute(select(1))
        db_latency = int((datetime.now(timezone.utc) - db_start).total_seconds() * 1000)
        components.append(ComponentHealth(
            name="Database",
            status="HEALTHY",
            last_check=checked_at,
            details="MySQL connection successful",
            latency_ms=db_latency,
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="Database",
            status="DOWN",
            last_check=checked_at,
            details=f"Connection failed: {str(e)}",
            latency_ms=None,
        ))
    
    # 2. AI Service check (Ollama)
    ai_start = datetime.now(timezone.utc)
    try:
        from app.services.ollama_client import OllamaClient
        from app.core.config import get_settings
        settings = get_settings()
        
        # Check if Ollama is configured
        if not settings.ollama_base_url:
            components.append(ComponentHealth(
                name="AI Service (Ollama)",
                status="NOT_CONFIGURED",
                last_check=checked_at,
                details="Ollama base URL not configured",
                latency_ms=None,
            ))
        else:
            client = OllamaClient(settings.ollama_base_url)
            try:
                if client.is_available():
                    ai_latency = int((datetime.now(timezone.utc) - ai_start).total_seconds() * 1000)
                    models = client.list_models()
                    components.append(ComponentHealth(
                        name="AI Service (Ollama)",
                        status="HEALTHY",
                        last_check=checked_at,
                        details=f"Ollama API responding. Models: {', '.join(models) if models else 'none'}",
                        latency_ms=ai_latency,
                    ))
                else:
                    components.append(ComponentHealth(
                        name="AI Service (Ollama)",
                        status="DOWN",
                        last_check=checked_at,
                        details="Ollama API not responding",
                        latency_ms=None,
                    ))
            finally:
                client.close()
    except Exception as e:
        components.append(ComponentHealth(
            name="AI Service (Ollama)",
            status="DOWN",
            last_check=checked_at,
            details=f"Connection failed: {str(e)}",
            latency_ms=None,
        ))
    
    # 3. Storage check (Local filesystem)
    storage_start = datetime.now(timezone.utc)
    try:
        from app.core.config import get_settings
        settings = get_settings()
        upload_dir = Path(settings.upload_dir)
        if upload_dir.exists() and upload_dir.is_dir():
            # Test write/read
            test_file = upload_dir / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            storage_latency = int((datetime.now(timezone.utc) - storage_start).total_seconds() * 1000)
            components.append(ComponentHealth(
                name="Storage (Local)",
                status="HEALTHY",
                last_check=checked_at,
                details=f"Local filesystem accessible at {upload_dir}",
                latency_ms=storage_latency,
            ))
        else:
            components.append(ComponentHealth(
                name="Storage (Local)",
                status="DOWN",
                last_check=checked_at,
                details=f"Upload directory not found: {upload_dir}",
                latency_ms=None,
            ))
    except Exception as e:
        components.append(ComponentHealth(
            name="Storage (Local)",
            status="DOWN",
            last_check=checked_at,
            details=f"Check failed: {str(e)}",
            latency_ms=None,
        ))
    
    # 4. Message Queue check
    queue_start = datetime.now(timezone.utc)
    try:
        pending = db.execute(select(func.count(Message.id)).where(Message.status == MessageStatus.PENDING.value)).scalar() or 0
        processing = db.execute(select(func.count(Message.id)).where(Message.status == MessageStatus.PROCESSING.value)).scalar() or 0
        queue_latency = int((datetime.now(timezone.utc) - queue_start).total_seconds() * 1000)
        components.append(ComponentHealth(
            name="Message Queue",
            status="HEALTHY" if pending < 100 else "DEGRADED",
            last_check=checked_at,
            details=f"Pending: {pending}, Processing: {processing}",
            latency_ms=queue_latency,
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="Message Queue",
            status="DOWN",
            last_check=checked_at,
            details=f"Query failed: {str(e)}",
            latency_ms=None,
        ))
    
    # 5. Worker Pool check
    worker_start = datetime.now(timezone.utc)
    try:
        workers = db.execute(select(WorkerStatus)).scalars().all()
        if not workers:
            components.append(ComponentHealth(
                name="Worker Pool",
                status="NOT_CONFIGURED",
                last_check=checked_at,
                details="No workers registered",
                latency_ms=None,
            ))
        else:
            online = sum(1 for w in workers if w.last_heartbeat and (checked_at - w.last_heartbeat).total_seconds() < 30)
            worker_latency = int((datetime.now(timezone.utc) - worker_start).total_seconds() * 1000)
            components.append(ComponentHealth(
                name="Worker Pool",
                status="HEALTHY" if online > 0 else "DEGRADED",
                last_check=checked_at,
                details=f"Online: {online}/{len(workers)}",
                latency_ms=worker_latency,
            ))
    except Exception as e:
        components.append(ComponentHealth(
            name="Worker Pool",
            status="DOWN",
            last_check=checked_at,
            details=f"Query failed: {str(e)}",
            latency_ms=None,
        ))
    
    # Required components for core system operation
    required_components = {"Database", "AI Service (Ollama)", "Message Queue"}
    
    has_down = any(c.status == "DOWN" for c in components)
    has_required_down = any(c.status == "DOWN" and c.name in required_components for c in components)
    has_degraded = any(c.status == "DEGRADED" for c in components)
    has_not_configured = any(c.status == "NOT_CONFIGURED" for c in components)
    
    # Determine overall status with NOT_CONFIGURED as distinct state
    # If all components are NOT_CONFIGURED (no optional services configured), report NOT_CONFIGURED
    all_not_configured = all(c.status == "NOT_CONFIGURED" for c in components)
    if all_not_configured:
        overall = "NOT_CONFIGURED"
    elif has_required_down or has_down:
        overall = "DOWN"
    elif has_degraded or has_not_configured:
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"
    
    return SystemHealthResponse(
        overall=overall,
        components=components,
        checked_at=checked_at,
    )


@router.get("/queue-status", response_model=QueueStatusResponse)
def get_queue_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get message queue processing status."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    pending = db.execute(select(func.count(Message.id)).where(Message.status == MessageStatus.PENDING.value)).scalar() or 0
    processing = db.execute(select(func.count(Message.id)).where(Message.status == MessageStatus.PROCESSING.value)).scalar() or 0
    awaiting_review = db.execute(select(func.count(Message.id)).where(Message.status == MessageStatus.AWAITING_REVIEW.value)).scalar() or 0
    
    posted_today = db.execute(
        select(func.count(Message.id)).where(
            Message.status == MessageStatus.POSTED.value,
            Message.processed_at >= today_start
        )
    ).scalar() or 0
    
    failed_today = db.execute(
        select(func.count(Message.id)).where(
            Message.status == MessageStatus.FAILED.value,
            Message.processed_at >= today_start
        )
    ).scalar() or 0
    
    recalled_today = db.execute(
        select(func.count(Message.id)).where(
            Message.status == MessageStatus.RECALLED.value,
            Message.processed_at >= today_start
        )
    ).scalar() or 0
    
    oldest_pending = db.execute(
        select(Message.created_at)
        .where(Message.status == MessageStatus.PENDING.value)
        .order_by(Message.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()
    
    oldest_pending_age = None
    if oldest_pending:
        pending_dt = oldest_pending
        if pending_dt.tzinfo is None:
            pending_dt = pending_dt.replace(tzinfo=timezone.utc)
        oldest_pending_age = int((datetime.now(timezone.utc) - pending_dt).total_seconds())
    
    avg_processing = db.execute(
        select(func.avg(func.extract('epoch', Message.processed_at - Message.created_at)))
        .where(
            Message.status == MessageStatus.POSTED.value,
            Message.processed_at >= today_start,
            Message.processed_at.is_not(None)
        )
    ).scalar()
    
    return QueueStatusResponse(
        pending=pending,
        processing=processing,
        awaiting_review=awaiting_review,
        posted_today=posted_today,
        failed_today=failed_today,
        recalled_today=recalled_today,
        oldest_pending_age_seconds=oldest_pending_age,
        avg_processing_time_seconds=float(avg_processing) if avg_processing else None,
    )