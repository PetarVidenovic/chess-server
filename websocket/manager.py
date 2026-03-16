from fastapi import WebSocket
import json
from ..redis_client import get_redis

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}  # user_id -> websocket
        self.user_channels: dict[int, set] = {}  # user_id -> set of channel names

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_channels[user_id] = set()
        # Slušanje na Redis kanalu za ovog korisnika (privatne poruke, izazovi)
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"user:{user_id}")
        asyncio.create_task(self._listen_redis(user_id, pubsub))

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_channels:
            del self.user_channels[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        """Pošalji poruku direktno ako je korisnik na ovom serveru, inače objavi na Redis."""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
        else:
            redis = await get_redis()
            await redis.publish(f"user:{user_id}", json.dumps(message))

    async def subscribe(self, user_id: int, channel: str):
        """Pretplati korisnika na kanal (npr. game:123, tournament:45)."""
        self.user_channels[user_id].add(channel)
        # Slušanje na Redis kanalu za ovaj kanal (već postoji jedan globalni slušač po kanalu)
        # Za optimizaciju, možemo koristiti jedan globalni PubSub koji prati sve kanale,
        # ali radi jednostavnosti, ovde dodajemo posebnu pretplatu.
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        asyncio.create_task(self._listen_redis(user_id, pubsub, channel))

    async def _listen_redis(self, user_id: int, pubsub, specific_channel: str = None):
        """Osluškuje Redis kanale i prosleđuje poruke korisniku ako je i dalje povezan."""
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                # Ako je korisnik još uvek povezan na ovom serveru, pošalji mu
                if user_id in self.active_connections:
                    await self.active_connections[user_id].send_json(data)
                else:
                    break  # korisnik je napustio, prekini slušanje

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Objavi poruku na Redis kanal – svi serveri će je proslediti svojim korisnicima."""
        redis = await get_redis()
        await redis.publish(channel, json.dumps(message))

manager = ConnectionManager()
