# app/websocket/manager.py
import json
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, any] = {}  # user_id -> websocket
        self.user_names: Dict[int, str] = {}

    async def connect(self, user_id: int, username: str, websocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_names[user_id] = username
        await self.broadcast_online_users()

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        self.user_names.pop(user_id, None)

    async def broadcast_online_users(self):
        """Šalje listu online korisnika svim povezanim klijentima."""
        users_list = [
            {"id": uid, "username": self.user_names[uid]}
            for uid in self.active_connections.keys()
        ]
        message = json.dumps({"type": "online_users", "users": users_list})
        for ws in self.active_connections.values():
            await ws.send_text(message)

manager = ConnectionManager()
