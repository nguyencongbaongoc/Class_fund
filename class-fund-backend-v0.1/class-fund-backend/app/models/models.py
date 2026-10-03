import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid4_str() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    OWNER_TREASURER = "OWNER_TREASURER"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"
    PUBLIC = "PUBLIC"


class LedgerType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    REVERT = "REVERT"


class LedgerSource(str, enum.Enum):
    IMAGE = "IMAGE"
    MANUAL = "MANUAL"
    REVERT = "REVERT"


class LedgerStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    REVERTED = "REVERTED"


class UploadStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CampaignMemberStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    EXEMPT = "EXEMPT"


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    currency: Mapped[str] = mapped_column(String(8), default="VND")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    bank_name: Mapped[str] = mapped_column(String(120))
    account_name: Mapped[str] = mapped_column(String(160))
    account_number: Mapped[str] = mapped_column(String(64))
    payment_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    qr_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    perceptual_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploader_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus, native_enum=False), default=UploadStatus.PENDING, index=True)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    student_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CollectionCampaign(Base):
    __tablename__ = "collection_campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus, native_enum=False), default=CampaignStatus.DRAFT)


class CampaignMember(Base):
    __tablename__ = "campaign_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("collection_campaigns.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    status: Mapped[CampaignMemberStatus] = mapped_column(Enum(CampaignMemberStatus, native_enum=False), default=CampaignMemberStatus.UNPAID)
    __table_args__ = (UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student"),)


class ExtractedTransaction(Base):
    __tablename__ = "extracted_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"), unique=True)
    transaction_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account_id: Mapped[str | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    raw_ocr: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("collection_campaigns.id"), nullable=True)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus, native_enum=False), default=UploadStatus.PROCESSING)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    bank_account_id: Mapped[str | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    transaction_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    type: Mapped[LedgerType] = mapped_column(Enum(LedgerType, native_enum=False))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(8), default="VND")
    source: Mapped[LedgerSource] = mapped_column(Enum(LedgerSource, native_enum=False))
    status: Mapped[LedgerStatus] = mapped_column(Enum(LedgerStatus, native_enum=False), default=LedgerStatus.VERIFIED)
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (
        UniqueConstraint("bank_account_id", "transaction_code", name="uq_bank_transaction_code"),
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), unique=True)
    type: Mapped[LedgerType] = mapped_column(Enum(LedgerType, native_enum=False))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(8), default="VND")
    transaction_code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source: Mapped[LedgerSource] = mapped_column(Enum(LedgerSource, native_enum=False))
    status: Mapped[LedgerStatus] = mapped_column(Enum(LedgerStatus, native_enum=False))
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    original_entry_id: Mapped[str | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    before_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PaymentMatch(Base):
    __tablename__ = "payment_matches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), unique=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("collection_campaigns.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    matched_by: Mapped[str] = mapped_column(String(32), default="AI")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    sender_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sender_role: Mapped[str] = mapped_column(String(40))
    message_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    attachment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ledger_entry_id: Mapped[str | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
