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