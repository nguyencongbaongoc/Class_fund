"""add attachment_ids to messages and AI pipeline fields"""
from alembic import op
import sqlalchemy as sa

revision = "0005_add_attachment_ids_and_ai_fields"
down_revision = "0004_add_worker_id_to_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add attachment_ids column to messages
    op.add_column("messages", sa.Column("attachment_ids", sa.JSON, nullable=True))
    
    # Add AI pipeline fields to uploads
    op.add_column("uploads", sa.Column("perceptual_hash", sa.String(128), nullable=True))
    
    # Add AI pipeline fields to extracted_transactions
    op.add_column("extracted_transactions", sa.Column("field_confidences", sa.JSON, nullable=True))
    op.add_column("extracted_transactions", sa.Column("extraction_method", sa.String(50), nullable=True))
    op.add_column("extracted_transactions", sa.Column("source_image_id", sa.String(36), nullable=True))
    op.add_column("extracted_transactions", sa.Column("currency", sa.String(8), nullable=True))
    
    # Add review audit fields
    op.add_column("extracted_transactions", sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("extracted_transactions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("extracted_transactions", sa.Column("review_notes", sa.Text, nullable=True))
    
    # Add indexes for duplicate detection
    op.create_index("ix_uploads_perceptual_hash", "uploads", ["perceptual_hash"])
    op.create_index("ix_extracted_transactions_field_confidences", "extracted_transactions", ["field_confidences"])


def downgrade() -> None:
    op.drop_index("ix_extracted_transactions_field_confidences", table_name="extracted_transactions")
    op.drop_index("ix_uploads_perceptual_hash", table_name="uploads")
    
    op.drop_column("extracted_transactions", "review_notes")
    op.drop_column("extracted_transactions", "reviewed_at")
    op.drop_column("extracted_transactions", "reviewed_by")
    op.drop_column("extracted_transactions", "currency")
    op.drop_column("extracted_transactions", "source_image_id")
    op.drop_column("extracted_transactions", "extraction_method")
    op.drop_column("extracted_transactions", "field_confidences")
    
    op.drop_column("uploads", "perceptual_hash")
    op.drop_column("messages", "attachment_ids")