from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}  # user_id -> websocket

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        # Pošalji svima ažuriranu listu
        await self.broadcast_online_users()

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # Asinhrono slanje bi trebalo pokrenuti odvojeno, ali ovde nema await
        # Najbolje pozvati broadcast izvan disconnect-a ili koristiti asyncio.create_task

    async def broadcast_online_users(self):
        # Kreiraj listu korisnika (treba nam pristup bazi da dobijemo username)
        # Ovde pretpostavljamo da imamo funkciju get_user_by_id
        # Za sada šaljemo samo ID-eve, ali klijent očekuje i username
        users_list = []
        for user_id in self.active_connections.keys():
            # U stvarnosti treba da dohvatiš username iz baze
            # Možeš čuvati tuple (user_id, username) prilikom connect
            users_list.append({"id": user_id, "username": f"User{user_id}"})  # privremeno
        message = {"type": "online_users", "users": users_list}
        for websocket in self.active_connections.values():
            await websocket.send_json(message)

manager = ConnectionManager()
