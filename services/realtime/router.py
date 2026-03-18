"""
WebSocket endpoints for real-time notifications and updates.
"""
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from services.config import get_settings
from services.realtime.events import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# Connection manager injected at startup
_manager = None


def set_manager(manager):
    global _manager
    _manager = manager


def _verify_ws_token(token: str) -> dict | None:
    """Verify JWT token from WebSocket query param. Returns payload or None."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            return None
        return {"user_id": str(user_id), "role": payload.get("role", "")}
    except JWTError:
        return None


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = Query(...)):
    """General notification channel for all authenticated users."""
    user = _verify_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await _manager.connect(websocket, Channel.NOTIFICATIONS, user["user_id"])
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(Channel.NOTIFICATIONS, user["user_id"])


@router.websocket("/ws/live-tracking")
async def ws_live_tracking(websocket: WebSocket, token: str = Query(...)):
    """Live GPS tracking channel — broadcasts interpreter location updates."""
    user = _verify_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await _manager.connect(websocket, Channel.LIVE_TRACKING, user["user_id"])
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(Channel.LIVE_TRACKING, user["user_id"])


@router.websocket("/ws/assignment-updates")
async def ws_assignment_updates(websocket: WebSocket, token: str = Query(...)):
    """Assignment lifecycle events channel."""
    user = _verify_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await _manager.connect(websocket, Channel.ASSIGNMENT_UPDATES, user["user_id"])
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(Channel.ASSIGNMENT_UPDATES, user["user_id"])


@router.websocket("/ws/email-updates")
async def ws_email_updates(websocket: WebSocket, token: str = Query(...)):
    """Email inbox events channel — new emails, classifications, replies."""
    user = _verify_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or missing token")
        return

    await _manager.connect(websocket, Channel.EMAIL_UPDATES, user["user_id"])
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(Channel.EMAIL_UPDATES, user["user_id"])


@router.get("/ws/status")
async def ws_status():
    """Get current WebSocket connection counts."""
    if not _manager:
        return {"channels": {}}
    return {"channels": _manager.get_connection_count()}
