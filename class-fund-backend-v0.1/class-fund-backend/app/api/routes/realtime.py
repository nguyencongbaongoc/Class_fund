"""WebSocket endpoints for real-time communication."""
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.services.realtime import manager, publish_message_update
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User, Role, Message, MessageStatus


router = APIRouter(prefix="/ws", tags=["realtime"])


async def get_current_user_ws(token: str, db: Session) -> User:
    """Authenticate user via WebSocket token query parameter."""
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
    except Exception:
        raise HTTPException(status_code=4001, detail="Invalid token")
    
    user = db.get(User, user_id)
    if not user or user.role.value != role:
        raise HTTPException(status_code=4001, detail="User not found")
    return user


@router.websocket("/messages/{conversation_id}")
async def websocket_messages(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for real-time message updates in a conversation."""
    # Authenticate via token
    try:
        user = await get_current_user_ws(token, db)
    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
        return
    
    # Verify user has access to conversation (simplified - implement proper check)
    # For now, allow all authenticated users
    
    channel = f"messages:{conversation_id}"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            # Keep connection alive, handle incoming messages if needed
            data = await websocket.receive_text()
            # Handle ping/pong or client messages
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception:
        await manager.disconnect(websocket, channel)


@router.websocket("/worker")
async def websocket_worker(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for worker status updates and job notifications."""
    # Authenticate as worker (using special token or API key)
    try:
        payload = decode_access_token(token)
        worker_id = payload.get("sub")
        role = payload.get("role")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # For now, allow any authenticated user as worker
    # In production, verify worker-specific credentials
    
    channel = "worker_status"
    await manager.connect(websocket, channel)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "heartbeat":
                    # Worker heartbeat - could update worker_status table
                    pass
                elif msg.get("type") == "job_completed":
                    # Worker completed a job
                    pass
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception:
        await manager.disconnect(websocket, channel)


@router.websocket("/admin")
async def websocket_admin(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket for admin dashboard real-time updates."""
    # Authenticate as admin
    try:
        user = await get_current_user_ws(token, db)
        if user.role not in (Role.OWNER_TREASURER, Role.MODERATOR):
            await websocket.close(code=4003, reason="Insufficient permissions")
            return
    except HTTPException as e:
        await websocket.close(code=e.status_code, reason=e.detail)
        return
    
    # Subscribe to multiple channels for admin
    channels = ["worker_status", "system"]
    for channel in channels:
        await manager.connect(websocket, channel)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle admin messages if needed
    except WebSocketDisconnect:
        for channel in channels:
            await manager.disconnect(websocket, channel)
    except Exception:
        for channel in channels:
            await manager.disconnect(websocket, channel)