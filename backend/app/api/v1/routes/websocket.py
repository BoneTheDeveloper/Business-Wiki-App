"""WebSocket routes for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.utils.websocket import ws_manager
from app.auth.supabase import verify_supabase_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/documents")
async def websocket_documents(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for document status updates.

    Client connects with Supabase JWT token, receives real-time updates
    about document processing status.
    """
    # Validate Supabase JWT
    try:
        payload = await verify_supabase_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # Connect
    await ws_manager.connect(websocket, user_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully"
        })

        # Keep connection alive, handle incoming messages
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_json({"type": "pong"})

            # Could add more message types here

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket, user_id)
