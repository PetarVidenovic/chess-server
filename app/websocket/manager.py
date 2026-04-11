from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.usernames: Dict[int, str] = {}   # dodaj ovo

    async def connect(self, user_id: int, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.usernames[user_id] = username
        await self.broadcast_online_users()

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            del self.usernames[user_id]       # obriši i username

    async def broadcast_online_users(self):
        users_list = [{"id": uid, "username": self.usernames[uid]} for uid in self.active_connections.keys()]
        message = {"type": "online_users", "users": users_list}
        for ws in self.active_connections.values():
            try:
                await ws.send_json(message)
            except:
                pass

manager = ConnectionManager()
