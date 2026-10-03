from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import ChatMessage, User
from app.schemas.schemas import ChatMessageIn, ChatMessageOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/messages", response_model=list[ChatMessageOut])
def list_messages(db: Session = Depends(get_db), user: User = Depends(get_current_user), limit: int = 50, offset: int = 0):
    return db.execute(select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(min(limit, 200)).offset(offset)).scalars().all()


@router.post("/messages", response_model=ChatMessageOut, status_code=201)
def create_message(body: ChatMessageIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    msg = ChatMessage(sender_id=user.id, sender_role=user.role.value, message_type="TEXT", content=body.content)
    db.add(msg); db.commit(); db.refresh(msg)
    return msg
