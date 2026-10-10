"""add worker_id to messages table"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_worker_id_to_messages"
down_revision = "0003_add_recall_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("worker_id", sa.String(36), sa.ForeignKey("worker_status.worker_id"), nullable=True))
    op.create_index("ix_messages_worker_id", "messages", ["worker_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_worker_id", table_name="messages")
    op.drop_column("messages", "worker_id")