"""NRW Game Router — Game server endpoints + WebSocket"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()

# เก็บ connections ทั้งหมด
active_connections: List[WebSocket] = []

@router.get("/")
async def game_home():
    return {"module": "Game", "players_online": len(active_connections)}

@router.websocket("/ws/{player_id}")
async def game_websocket(websocket: WebSocket, player_id: str):
    """WebSocket สำหรับ real-time game"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast ให้ทุกคน
            for conn in active_connections:
                await conn.send_text(f"[{player_id}]: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
