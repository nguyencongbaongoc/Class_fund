"""WebSocket API Routes for Real-time Communication"""

from fastapi import APIRouter, WebSocket, Query, Depends
from sqlalchemy.orm import Session

from app.core.websocket import (
    websocket_chat, websocket_transactions, websocket_admin,
    manager
)
from app.db.session import get_db

router = APIRouter(prefix="/ws", tags=["realtime"])


@router.websocket("/chat/{conversation_id}")
async def ws_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for real-time chat in a conversation."""
    from app.core.websocket import websocket_chat as ws_chat_handler
    await ws_chat_handler(websocket, conversation_id, token, db)


@router.websocket("/transactions")
async def ws_transactions(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for real-time transaction updates."""
    from app.core.websocket import websocket_transactions as ws_tx_handler
    await ws_tx_handler(websocket, token, db)


@router.websocket("/admin")
async def ws_admin(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for admin dashboard real-time updates."""
    from app.core.websocket import websocket_admin as ws_admin_handler
    await ws_admin_handler(websocket, token, db)


@router.get("/health")
async def ws_health():
    """WebSocket service health check."""
    return {
        "status": "healthy",
        "service": "websocket",
        "active_connections": sum(
            sum(len(conns) for conns in channel.values())
            for channel in manager.active_connections.values()
        ),
        "channels": list(manager.active_connections.keys())
    }