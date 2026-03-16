import json
import asyncio
from ..redis_client import get_redis
from .chess_logic import validate_move, apply_move, is_game_over, get_game_result

class GameManager:
    def __init__(self):
        self.active_games = {}  # game_id -> {fen, white_id, black_id, turn, last_move_time}

    async def load_game(self, game_id: int):
        """Učitaj stanje igre iz Redis-a (ili baze)."""
        redis = await get_redis()
        data = await redis.get(f"game:{game_id}")
        if data:
            self.active_games[game_id] = json.loads(data)
        return self.active_games.get(game_id)

    async def save_game(self, game_id: int, state: dict):
        """Sačuvaj stanje igre u Redis."""
        redis = await get_redis()
        await redis.setex(f"game:{game_id}", 3600, json.dumps(state))  # 1h TTL
        self.active_games[game_id] = state

    async def process_move(self, game_id: int, player_id: int, move_uci: str) -> dict:
        """Obradi potez, ažurira stanje, vrati grešku ili novo stanje."""
        state = await self.load_game(game_id)
        if not state:
            return {"error": "Game not found"}

        # Provera čija je potez
        if state["turn"] == "white" and player_id != state["white_id"]:
            return {"error": "Not your turn"}
        if state["turn"] == "black" and player_id != state["black_id"]:
            return {"error": "Not your turn"}

        if not validate_move(state["fen"], move_uci):
            return {"error": "Illegal move"}

        # Primena poteza
        new_fen = apply_move(state["fen"], move_uci)
        state["fen"] = new_fen
        state["turn"] = "black" if state["turn"] == "white" else "white"

        # Provera kraja igre
        result = get_game_result(new_fen)
        if result:
            state["status"] = "finished"
            state["result"] = result

        await self.save_game(game_id, state)
        return {"state": state}

game_manager = GameManager()
