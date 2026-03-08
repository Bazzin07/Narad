"""
WebSocket Live Chat — ephemeral, no persistence.
Users can communicate in real-time on the India Command Center.
Messages are broadcast to all connected users and disappear on disconnect.
"""
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


class ChatManager:
    """Manages WebSocket connections for live chat."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        user_id = str(uuid.uuid4())[:8]
        self.active_connections[user_id] = websocket
        logger.info(f"Chat user {user_id} connected ({len(self.active_connections)} total)")
        return user_id

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        logger.info(f"Chat user {user_id} disconnected ({len(self.active_connections)} total)")

    async def broadcast(self, message: dict):
        dead = []
        for uid, ws in self.active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.active_connections.pop(uid, None)


chat_manager = ChatManager()


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    user_id = await chat_manager.connect(websocket)

    # Notify others of join
    await chat_manager.broadcast({
        "type": "system",
        "user": user_id,
        "message": f"User {user_id} joined",
        "timestamp": datetime.utcnow().isoformat(),
        "online": len(chat_manager.active_connections),
    })

    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast message to all connected users
            await chat_manager.broadcast({
                "type": "message",
                "user": user_id,
                "message": data[:500],  # Limit message length
                "timestamp": datetime.utcnow().isoformat(),
                "online": len(chat_manager.active_connections),
            })
    except WebSocketDisconnect:
        chat_manager.disconnect(user_id)
        await chat_manager.broadcast({
            "type": "system",
            "user": user_id,
            "message": f"User {user_id} left",
            "timestamp": datetime.utcnow().isoformat(),
            "online": len(chat_manager.active_connections),
        })
