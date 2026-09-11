"""NRW Game Router — Game server endpoints + WebSocket"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict
import re
import html
from datetime import datetime

router = APIRouter()

# เก็บ connections ทั้งหมด (player_id -> WebSocket)
active_connections: Dict[str, WebSocket] = {}

# Constants
MAX_MESSAGE_LENGTH = 500
MAX_PLAYER_ID_LENGTH = 20
PLAYER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_player_id(player_id: str) -> bool:
    """ตรวจสอบ player_id"""
    if not player_id or len(player_id) > MAX_PLAYER_ID_LENGTH:
        return False
    return bool(PLAYER_ID_PATTERN.match(player_id))


def sanitize_message(message: str) -> str:
    """ทำความสะอาด message ป้องกัน XSS"""
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH]
    return html.escape(message.strip())


@router.get("/")
async def game_home():
    return {
        "module": "Game",
        "players_online": len(active_connections),
        "players": list(active_connections.keys())
    }


@router.websocket("/ws/{player_id}")
async def game_websocket(
    websocket: WebSocket,
    player_id: str,
    token: str = Query(None)  # Optional token for future auth
):
    """WebSocket สำหรับ real-time game"""
    
    # 1. Validate player_id
    if not validate_player_id(player_id):
        await websocket.close(code=4001, reason="Invalid player_id")
        return
    
    # 2. Check duplicate connection
    if player_id in active_connections:
        await websocket.close(code=4002, reason="Player already connected")
        return
    
    # 3. Accept connection
    await websocket.accept()
    active_connections[player_id] = websocket
    
    # 4. Broadcast join message
    join_msg = f"[SYSTEM]: {player_id} joined ({len(active_connections)} online)"
    for conn in active_connections.values():
        try:
            await conn.send_text(join_msg)
        except:
            pass
    
    try:
        while True:
            # 5. Receive and validate message
            data = await websocket.receive_text()
            sanitized = sanitize_message(data)
            
            if not sanitized:
                continue
            
            # 6. Broadcast to all
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            broadcast_msg = f"[{timestamp}] {player_id}: {sanitized}"
            
            for pid, conn in list(active_connections.items()):
                try:
                    await conn.send_text(broadcast_msg)
                except:
                    # Remove dead connection
                    active_connections.pop(pid, None)
                    
    except WebSocketDisconnect:
        # 7. Clean up on disconnect
        active_connections.pop(player_id, None)
        
        # Broadcast leave message
        leave_msg = f"[SYSTEM]: {player_id} left ({len(active_connections)} online)"
        for conn in active_connections.values():
            try:
                await conn.send_text(leave_msg)
            except:
                pass
