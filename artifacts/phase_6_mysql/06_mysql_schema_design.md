# Phase 6 MySQL Schema Design

## Overview
Complete MySQL 8.4 schema design for CLASS_FUND_WEB, including all tables, columns, indexes, constraints, and MySQL-specific optimizations. This design is derived from the PostgreSQL compatibility matrix and target architecture.

---

## 1. MySQL-Specific SQLAlchemy Model Definitions

### 1.1 Base Model with MySQL Variants

```python
# app/db/base.py - Extended for MySQL
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.mysql import DATETIME, VARCHAR, JSON as MYSQL_JSON
from sqlalchemy import DateTime, String, Text, JSON

class Base(DeclarativeBase):
    pass

# Type annotations for MySQL variants
MySQLDateTime = DateTime(timezone=True).with_variant(DATETIME(6), "mysql")
MySQLString = String
MySQLText = Text
MySQLJSON = JSON.with_variant(MYSQL_JSON, "mysql")
MySQLVarchar = VARCHAR
```

### 1.2 Updated Models (models.py - MySQL Version)

```python
# app/models/models.py - MySQL compatible version
import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, 
    Numeric, String, Text, UniqueConstraint, text, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME, VARCHAR, JSON as MYSQL_JSON

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid4_str() -> str:
    return str(uuid.uuid4())


# Enums (native_enum=False creates VARCHAR + CHECK on MySQL 8.0.16+)
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


class MessageStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    POSTED = "posted"
    REJECTED = "rejected"
    FAILED = "failed"
    RECALLED = "recalled"


# ============================================================
# TABLES
# ============================================================

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql")
    )
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.MEMBER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    currency: Mapped[str] = mapped_column(String(8), default="VND")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, native_enum=False), 
        default=UploadStatus.PENDING, 
        index=True
    )


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
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, native_enum=False), 
        default=CampaignStatus.DRAFT
    )


class CampaignMember(Base):
    __tablename__ = "campaign_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("collection_campaigns.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    status: Mapped[CampaignMemberStatus] = mapped_column(
        Enum(CampaignMemberStatus, native_enum=False), 
        default=CampaignMemberStatus.UNPAID
    )
    __table_args__ = (
        UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student"),
    )


class ExtractedTransaction(Base):
    __tablename__ = "extracted_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id"), unique=True)
    transaction_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account_id: Mapped[str | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    transaction_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    raw_ocr: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("collection_campaigns.id"), nullable=True)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, native_enum=False), 
        default=UploadStatus.PROCESSING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    # AI Pipeline fields
    field_confidences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_image_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # Review audit fields
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True, index=True)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    original_entry_id: Mapped[str | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )


class PaymentMatch(Base):
    __tablename__ = "payment_matches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), unique=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("collection_campaigns.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    matched_by: Mapped[str] = mapped_column(String(32), default="AI")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sender_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sender_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sender_role: Mapped[str] = mapped_column(String(40), nullable=False, default="PUBLIC")
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, default="TEXT")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attachment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=MessageStatus.PENDING.value)
    public_code: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True, index=True)
    recall_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    worker_id: Mapped[str | None] = mapped_column(ForeignKey("worker_status.worker_id"), nullable=True)

    __table_args__ = (
        # Partial indexes using mysql_where (MySQL 8.0.13+)
        Index("ix_messages_status_created", "status", "created_at", 
              mysql_where=text("status = 'pending'")),
        Index("ix_messages_conversation_status_created", "conversation_id", "status", "created_at"),
        Index("ix_messages_processing_lease", "status", "lease_expires_at", 
              mysql_where=text("status = 'processing'")),
        Index("ix_messages_worker_id", "worker_id"),
    )


class WorkerStatus(Base):
    __tablename__ = "worker_status"
    worker_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    last_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    current_job_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class RecallToken(Base):
    __tablename__ = "recall_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), unique=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        nullable=True
    )

    __table_args__ = (
        Index("ix_recall_tokens_message_id", "message_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    sender_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sender_role: Mapped[str] = mapped_column(String(40))
    message_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    attachment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ledger_entry_id: Mapped[str | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
        default=utcnow
    )
```

---

## 2. MySQL Alembic Migrations

### 2.1 Alembic Environment (alembic/env.py)

```python
# alembic/env.py - MySQL compatible
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.models import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # MySQL specific
        render_as_batch=True,  # For MySQL ALTER TABLE limitations
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Set MySQL session variables
        connection.execute(text("SET time_zone = '+00:00'"))
        connection.execute(text("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"))
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # MySQL requires batch mode for ALTER TABLE
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 2.2 Migration 0001_initial_mysql.py

```python
"""initial class fund schema - MySQL 8.4"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME, JSON, VARCHAR

revision = "0001_initial_mysql"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # revoked_tokens
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", DATETIME(6), nullable=False),
        sa.Column("revoked_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", VARCHAR(20), nullable=False, server_default="MEMBER"),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.CheckConstraint("role IN ('OWNER_TREASURER','MODERATOR','MEMBER','PUBLIC')", name="ck_users_role"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="VND"),
        sa.Column("opening_balance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # bank_accounts
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bank_name", sa.String(120), nullable=False),
        sa.Column("account_name", sa.String(160), nullable=False),
        sa.Column("account_number", sa.String(64), nullable=False),
        sa.Column("payment_link", sa.String(500), nullable=True),
        sa.Column("qr_image_url", sa.String(500), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # uploads
    op.create_table(
        "uploads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("file_hash", sa.String(64), nullable=False, index=True),
        sa.Column("perceptual_hash", sa.String(128), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploader_name", sa.String(120), nullable=False),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("status", VARCHAR(20), nullable=False, server_default="PENDING"),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','NEEDS_REVIEW','VERIFIED','REJECTED','DUPLICATE')", name="ck_uploads_status"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_uploads_status", "uploads", ["status"])

    # students
    op.create_table(
        "students",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("full_name", sa.String(160), nullable=False, index=True),
        sa.Column("aliases", JSON, nullable=True),
        sa.Column("student_code", sa.String(64), nullable=True, index=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # collection_campaigns
    op.create_table(
        "collection_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("start_at", DATETIME(6), nullable=True),
        sa.Column("end_at", DATETIME(6), nullable=True),
        sa.Column("status", VARCHAR(20), nullable=False, server_default="DRAFT"),
        sa.CheckConstraint("status IN ('DRAFT','OPEN','CLOSED')", name="ck_campaigns_status"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # campaign_members
    op.create_table(
        "campaign_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("collection_campaigns.id"), nullable=False),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("status", VARCHAR(20), nullable=False, server_default="UNPAID"),
        sa.CheckConstraint("status IN ('UNPAID','PAID','EXEMPT')", name="ck_campaign_members_status"),
        sa.UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # extracted_transactions
    op.create_table(
        "extracted_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("upload_id", sa.String(36), sa.ForeignKey("uploads.id"), nullable=False, unique=True),
        sa.Column("transaction_code", sa.String(120), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("sender_name", sa.String(160), nullable=True),
        sa.Column("bank_name", sa.String(120), nullable=True),
        sa.Column("bank_account_id", sa.String(36), sa.ForeignKey("bank_accounts.id"), nullable=True),
        sa.Column("transaction_time", DATETIME(6), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("raw_ocr", sa.Text(), nullable=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("collection_campaigns.id"), nullable=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id"), nullable=True),
        sa.Column("status", VARCHAR(20), nullable=False, server_default="PROCESSING"),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','NEEDS_REVIEW','VERIFIED','REJECTED','DUPLICATE')", name="ck_extracted_status"),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("field_confidences", JSON, nullable=True),
        sa.Column("extraction_method", sa.String(50), nullable=True),
        sa.Column("source_image_id", sa.String(36), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", DATETIME(6), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("accounts.id"), nullable=False, index=True),
        sa.Column("bank_account_id", sa.String(36), sa.ForeignKey("bank_accounts.id"), nullable=True),
        sa.Column("transaction_code", sa.String(120), nullable=True),
        sa.Column("type", VARCHAR(20), nullable=False),
        sa.CheckConstraint("type IN ('CREDIT','DEBIT','REVERT')", name="ck_transactions_type"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="VND"),
        sa.Column("source", VARCHAR(20), nullable=False),
        sa.CheckConstraint("source IN ('IMAGE','MANUAL','REVERT')", name="ck_transactions_source"),
        sa.Column("status", VARCHAR(20), nullable=False, server_default="VERIFIED"),
        sa.CheckConstraint("status IN ('VERIFIED','REVERTED')", name="ck_transactions_status"),
        sa.Column("upload_id", sa.String(36), sa.ForeignKey("uploads.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("effective_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=True, index=True),
        sa.UniqueConstraint("bank_account_id", "transaction_code", name="uq_bank_transaction_code"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # ledger_entries
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False, unique=True),
        sa.Column("type", VARCHAR(20), nullable=False),
        sa.CheckConstraint("type IN ('CREDIT','DEBIT','REVERT')", name="ck_ledger_type"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="VND"),
        sa.Column("transaction_code", sa.String(120), nullable=True, index=True),
        sa.Column("source", VARCHAR(20), nullable=False),
        sa.CheckConstraint("source IN ('IMAGE','MANUAL','REVERT')", name="ck_ledger_source"),
        sa.Column("status", VARCHAR(20), nullable=False),
        sa.CheckConstraint("status IN ('VERIFIED','REVERTED')", name="ck_ledger_status"),
        sa.Column("upload_id", sa.String(36), sa.ForeignKey("uploads.id"), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("effective_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("original_entry_id", sa.String(36), sa.ForeignKey("ledger_entries.id"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # idempotency_keys
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", JSON, nullable=False),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(120), nullable=False),
        sa.Column("entity_id", sa.String(120), nullable=True),
        sa.Column("before_data", JSON, nullable=True),
        sa.Column("after_data", JSON, nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # payment_matches
    op.create_table(
        "payment_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=False, unique=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("collection_campaigns.id"), nullable=False),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("matched_by", sa.String(32), nullable=False, server_default="AI"),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False, index=True),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sender_name", sa.String(120), nullable=False),
        sa.Column("sender_photo", sa.String(500), nullable=True),
        sa.Column("sender_role", sa.String(40), nullable=False, server_default="PUBLIC"),
        sa.Column("message_type", sa.String(50), nullable=False, server_default="TEXT"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_id", sa.String(36), nullable=True),
        sa.Column("attachment_ids", JSON, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("public_code", sa.String(50), nullable=True, unique=True, index=True),
        sa.Column("recall_token_hash", sa.String(64), nullable=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("claimed_at", DATETIME(6), nullable=True),
        sa.Column("lease_expires_at", DATETIME(6), nullable=True),
        sa.Column("processed_at", DATETIME(6), nullable=True),
        sa.Column("worker_id", sa.String(36), sa.ForeignKey("worker_status.worker_id"), nullable=True),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    
    # Partial indexes (MySQL 8.0.13+)
    op.create_index(
        "ix_messages_status_created", "messages", ["status", "created_at"],
        mysql_where=sa.text("status = 'pending'")
    )
    op.create_index(
        "ix_messages_conversation_status_created", "messages", 
        ["conversation_id", "status", "created_at"]
    )
    op.create_index(
        "ix_messages_processing_lease", "messages", 
        ["status", "lease_expires_at"],
        mysql_where=sa.text("status = 'processing'")
    )
    op.create_index("ix_messages_worker_id", "messages", ["worker_id"])

    # worker_status
    op.create_table(
        "worker_status",
        sa.Column("worker_id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline"),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("last_heartbeat", DATETIME(6), nullable=True),
        sa.Column("last_processed_at", DATETIME(6), nullable=True),
        sa.Column("current_job_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("metadata", JSON, nullable=False, server_default="{}"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )

    # recall_tokens
    op.create_table(
        "recall_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        sa.Column("expires_at", DATETIME(6), nullable=True),
        sa.Column("used_at", DATETIME(6), nullable=True),
        sa.Column("revoked_at", DATETIME(6), nullable=True),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_recall_tokens_message_id", "recall_tokens", ["message_id"])

    # chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sender_role", sa.String(40), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_id", sa.String(36), nullable=True),
        sa.Column("ledger_entry_id", sa.String(36), sa.ForeignKey("ledger_entries.id"), nullable=True),
        sa.Column("created_at", DATETIME(6), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_index("ix_recall_tokens_message_id", table_name="recall_tokens")
    op.drop_table("recall_tokens")
    op.drop_table("worker_status")
    op.drop_index("ix_messages_worker_id", table_name="messages")
    op.drop_index("ix_messages_processing_lease", table_name="messages")
    op.drop_index("ix_messages_conversation_status_created", table_name="messages")
    op.drop_index("ix_messages_status_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("payment_matches")
    op.drop_table("audit_logs")
    op.drop_table("idempotency_keys")
    op.drop_table("ledger_entries")
    op.drop_table("transactions")
    op.drop_table("extracted_transactions")
    op.drop_table("campaign_members")
    op.drop_table("collection_campaigns")
    op.drop_table("students")
    op.drop_table("uploads")
    op.drop_table("bank_accounts")
    op.drop_table("accounts")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("revoked_tokens")
```

### 2.3 Remaining Migrations (0002-0005)

Since 0001_initial_mysql creates all tables with MySQL-compatible schema, the subsequent migrations (0002-0005) are **not needed** for fresh MySQL initialization. They can be:

1. **Kept for history** - Mark as already applied in MySQL
2. **Or squashed** - Single initial migration for MySQL

**Recommendation**: Use single initial migration for MySQL. Archive PostgreSQL migrations.

---

## 3. Additional MySQL Optimizations

### 3.1 Covering Indexes for Common Queries

```sql
-- Message polling (most frequent query)
CREATE INDEX ix_messages_polling_covering 
ON messages (status, created_at, conversation_id, id, sender_name, content, attachment_ids)
WHERE status IN ('pending', 'processing', 'awaiting_review');

-- Ledger balance calculation
CREATE INDEX ix_ledger_balance_covering 
ON ledger_entries (effective_at, created_at, type, amount, transaction_id)
WHERE status = 'VERIFIED';

-- Worker heartbeat cleanup
CREATE INDEX ix_worker_heartbeat 
ON worker_status (last_heartbeat) WHERE status != 'offline';
```

### 3.2 Generated Columns for JSON Querying

```sql
-- If frequently querying field_confidences
ALTER TABLE extracted_transactions
ADD COLUMN confidence_overall DECIMAL(5,4) 
GENERATED ALWAYS AS (JSON_EXTRACT(field_confidences, '$.overall')) STORED,
ADD INDEX idx_confidence_overall (confidence_overall);

-- Worker metadata querying
ALTER TABLE worker_status
ADD COLUMN worker_version VARCHAR(50) 
GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.version'))) STORED,
ADD INDEX idx_worker_version (worker_version);
```

---

## 4. Verification Queries

```sql
-- Verify all tables use InnoDB
SELECT TABLE_NAME, ENGINE 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'classfund' AND ENGINE != 'InnoDB';

-- Verify charset/collation
SELECT TABLE_NAME, TABLE_COLLATION 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'classfund' AND TABLE_COLLATION != 'utf8mb4_unicode_ci';

-- Verify DECIMAL precision
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'classfund' 
  AND DATA_TYPE = 'decimal'
  AND (NUMERIC_PRECISION != 18 OR NUMERIC_SCALE != 2)
  AND COLUMN_NAME IN ('opening_balance', 'amount', 'expected_amount');

-- Verify partial indexes
SELECT TABLE_NAME, INDEX_NAME, INDEX_DEFINITION
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = 'classfund' 
  AND INDEX_COMMENT LIKE '%WHERE%';

-- Verify CHECK constraints
SELECT TABLE_NAME, CONSTRAINT_NAME, CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'classfund';
```

---

## 5. Schema Version Control

### 5.1 Alembic Version Table
```sql
-- Alembic creates this automatically
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    PRIMARY KEY (version_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 5.2 Migration History Tracking
- Store migration checksums
- Track execution time
- Record success/failure

---

**Status: MYSQL SCHEMA DESIGN COMPLETE - Ready for ORM Migration Report**