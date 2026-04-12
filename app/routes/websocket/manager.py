# app/websocket/manager.py
import json
from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_names: Dict[int, str] = {}

    async def connect(self, user_id: int, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_names[user_id] = username
        await self.broadcast_online_users()

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            self.user_names.pop(user_id, None)
            await self.broadcast_online_users()   # OVO JE KLJUČNO

    async def broadcast_online_users(self):
        """Šalje listu online korisnika svim povezanim klijentima."""
        users_list = [
            {"id": uid, "username": self.user_names.get(uid, f"User{uid}")}
            for uid in self.active_connections.keys()
        ]
        message = json.dumps({"type": "online_users", "users": users_list})
        for ws in self.active_connections.values():
            try:
                await ws.send_text(message)
            except:
                pass

manager = ConnectionManager()
