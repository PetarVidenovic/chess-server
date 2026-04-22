import asyncio
import uuid
from typing import List, Tuple

# Red čekanja: svaki element (websocket, user_id, rating, username)
matchmaking_queue: List[Tuple] = []
matchmaking_lock = asyncio.Lock()

async def add_to_queue(websocket, user_id: int, rating: int, username: str) -> bool:
    """Dodaje korisnika u red čekanja. Vraća True ako je uspešno."""
    async with matchmaking_lock:
        for q in matchmaking_queue:
            if q[1] == user_id:
                return False
        matchmaking_queue.append((websocket, user_id, rating, username))
        print(f"📌 {username} (rating {rating}) ušao u red. Red: {len(matchmaking_queue)}")
    return True

async def remove_from_queue(user_id: int):
    """Uklanja korisnika iz reda čekanja."""
    async with matchmaking_lock:
        before = len(matchmaking_queue)
        matchmaking_queue[:] = [q for q in matchmaking_queue if q[1] != user_id]
        if before != len(matchmaking_queue):
            print(f"🚪 Korisnik {user_id} napustio red. ({before} -> {len(matchmaking_queue)})")

async def try_match():
    """Pokušava da upari igrače iz reda (unutar 200 ELO poena)."""
    async with matchmaking_lock:
        if len(matchmaking_queue) < 2:
            return
        matchmaking_queue.sort(key=lambda x: x[2])
        i = 0
        while i < len(matchmaking_queue) - 1:
            p1_ws, p1_id, p1_rating, p1_name = matchmaking_queue[i]
            p2_ws, p2_id, p2_rating, p2_name = matchmaking_queue[i+1]
            if abs(p1_rating - p2_rating) <= 200:
                matchmaking_queue.pop(i)
                matchmaking_queue.pop(i)
                game_id = str(uuid.uuid4())
                await p1_ws.send_json({
                    "type": "match_found",
                    "game_id": game_id,
                    "opponent": p2_name,
                    "opponent_id": p2_id,
                    "color": "white"
                })
                await p2_ws.send_json({
                    "type": "match_found",
                    "game_id": game_id,
                    "opponent": p1_name,
                    "opponent_id": p1_id,
                    "color": "black"
                })
                print(f"🤝 Sparivanje: {p1_name} (white) vs {p2_name} (black)")
            else:
                i += 1
