"""add recall tokens table"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_add_recall_tokens"
down_revision = "0002_add_messages_and_message_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recall_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id"), unique=True, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index("ix_recall_tokens_message_id", "recall_tokens", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_recall_tokens_message_id", table_name="recall_tokens")
    op.drop_table("recall_tokens")