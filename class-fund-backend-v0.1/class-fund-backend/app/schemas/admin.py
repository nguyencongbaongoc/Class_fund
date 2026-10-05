from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


class AdminStatsResponse(BaseModel):
    current_balance: Decimal
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    transaction_count: int
    pending_review_count: int
    processing_review_count: int
    worker_online_count: int
    worker_total_count: int
    queue_pending_count: int
    queue_processing_count: int
    last_transaction_at: Optional[datetime]
    last_review_at: Optional[datetime]


class AuditLogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_id: Optional[str]
    actor_name: Optional[str]
    actor_role: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[str]
    before_data: Optional[dict]
    after_data: Optional[dict]
    ip: Optional[str]
    created_at: datetime


class PaginatedAuditLogsResponse(BaseModel):
    items: list[AuditLogItemResponse]
    total: int
    limit: int
    offset: int


class WorkerStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    worker_id: str
    status: str
    model_name: Optional[str]
    last_heartbeat: Optional[datetime]
    last_processed_at: Optional[datetime]
    current_job_id: Optional[str]
    metadata: dict
    health: Literal["ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN"]
    seconds_since_heartbeat: Optional[int]


class ComponentHealth(BaseModel):
    name: str
    status: Literal["HEALTHY", "DEGRADED", "DOWN", "NOT_CONFIGURED"]
    last_check: datetime
    details: Optional[str]
    latency_ms: Optional[int]


class SystemHealthResponse(BaseModel):
    overall: Literal["HEALTHY", "DEGRADED", "DOWN", "NOT_CONFIGURED"]
    components: list[ComponentHealth]
    checked_at: datetime


class QueueStatusResponse(BaseModel):
    pending: int
    processing: int
    awaiting_review: int
    posted_today: int
    failed_today: int
    recalled_today: int
    oldest_pending_age_seconds: Optional[int]
    avg_processing_time_seconds: Optional[float]


class AuditLogExportRequest(BaseModel):
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    actor_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = 10000


class AuditLogExportResponse(BaseModel):
    csv_content: str
    total_records: int
    filename: str