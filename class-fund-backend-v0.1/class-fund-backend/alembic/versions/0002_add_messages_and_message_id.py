"""add messages table and message_id to transactions"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_add_messages_and_message_id"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False, index=True),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sender_name", sa.String(120), nullable=False),
        sa.Column("sender_photo", sa.String(500), nullable=True),
        sa.Column("sender_role", sa.String(40), nullable=False, default="PUBLIC"),
        sa.Column("message_type", sa.String(50), nullable=False, default="TEXT"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("attachment_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, default="pending"),
        sa.Column("public_code", sa.String(50), nullable=True, unique=True, index=True),
        sa.Column("recall_token_hash", sa.String(64), nullable=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for efficient polling
    op.create_index("ix_messages_status_created", "messages", ["status", "created_at"], 
                      postgresql_where=sa.text("status = 'pending'"))
    op.create_index("ix_messages_conversation_status_created", "messages", 
                      ["conversation_id", "status", "created_at"])
    op.create_index("ix_messages_processing_lease", "messages", 
                      ["status", "lease_expires_at"],
                      postgresql_where=sa.text("status = 'processing'"))
    
    # Add message_id to transactions
    op.add_column("transactions", sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=True, index=True))
    
    # Create worker_status table
    op.create_table(
        "worker_status",
        sa.Column("worker_id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, default="offline"),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("worker_status")
    op.drop_column("transactions", "message_id")
    op.drop_index("ix_messages_processing_lease", table_name="messages")
    op.drop_index("ix_messages_conversation_status_created", table_name="messages")
    op.drop_index("ix_messages_status_created", table_name="messages")
    op.drop_table("messages")