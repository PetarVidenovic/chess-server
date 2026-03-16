from fastapi import APIRouter, WebSocket
from ..websocket.manager import manager

router = APIRouter(tags=["websocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Eho: {data}")
    except Exception:
        manager.disconnect(websocket)
