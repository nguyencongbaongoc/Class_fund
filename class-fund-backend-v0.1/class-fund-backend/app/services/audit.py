from typing import Any
from sqlalchemy.orm import Session
from app.models.models import AuditLog


def write_audit(db: Session, *, actor_id: str | None, action: str, entity_type: str, entity_id: str | None,
                before: Any = None, after: Any = None, ip: str | None = None) -> None:
    db.add(AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before,
        after_data=after,
        ip=ip,
    ))
