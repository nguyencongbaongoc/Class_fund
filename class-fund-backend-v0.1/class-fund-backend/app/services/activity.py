from sqlalchemy.orm import Session
from app.models.models import ChatMessage


def emit_activity(db: Session, *, sender_id: str | None, sender_role: str, message_type: str,
                   content: str, attachment_id: str | None = None, ledger_entry_id: str | None = None) -> None:
    db.add(ChatMessage(sender_id=sender_id, sender_role=sender_role, message_type=message_type,
                       content=content, attachment_id=attachment_id, ledger_entry_id=ledger_entry_id))
