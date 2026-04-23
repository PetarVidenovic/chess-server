import json
import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user_from_token
from app.matchmaking import add_to_queue, remove_from_queue, try_match
from app.games import update_ratings

router = APIRouter()

# Aktivne WebSocket veze: {user_id: {"ws": websocket, "username": username}}
active_connections = {}

async def broadcast_online_users():
    """Šalje listu online korisnika svim povezanim klijentima."""
    users_list = [{"id": uid, "username": info["username"]} for uid, info in active_connections.items()]
    message = json.dumps({"type": "online_users", "users": users_list})
    for info in active_connections.values():
        try:
            await info["ws"].send_text(message)
        except:
            pass

# Privremeno skladište igara (u produkciji koristi bazu)
games_store = {}

def create_game(player1_id: int, player2_id: int) -> str:
    game_id = str(uuid.uuid4())
    games_store[game_id] = {
        "white_id": player1_id,
        "black_id": player2_id,
        "status": "active",
        "fen": "start",
        "moves": []
    }
    print(f"🎮 Nova igra: {game_id} ({player1_id} vs {player2_id})")
    return game_id

def get_opponent_id(game_id: str, current_user_id: int):
    game = games_store.get(game_id)
    if not game:
        return None
    if game["white_id"] == current_user_id:
        return game["black_id"]
    elif game["black_id"] == current_user_id:
        return game["white_id"]
    return None

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    # Autentifikacija
    user = await get_current_user_from_token(token)
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()
    # Sačuvaj vezu sa korisničkim imenom
    active_connections[user.id] = {"ws": websocket, "username": user.username}
    print(f"🔌 {user.username} ({user.id}) povezan")

    # Obavesti sve o novom korisniku
    await broadcast_online_users()

    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
            except:
                continue

            msg_type = data.get("type")

            # ========== MATCHMAKING ==========
            if msg_type == "join_queue":
                await add_to_queue(websocket, user.id, user.rating, user.username)
                await try_match()
            elif msg_type == "leave_queue":
                await remove_from_queue(user.id)

            # ========== IZAZOVI ==========
            elif msg_type == "challenge":
                opponent_id = data.get("opponent_id")
                opponent_info = active_connections.get(opponent_id)
                if opponent_info:
                    await opponent_info["ws"].send_json({
                        "type": "challenge_received",
                        "challenge_id": data.get("challenge_id"),
                        "from_username": user.username,
                        "from_id": user.id
                    })
            elif msg_type == "accept_challenge":
                challenger_id = data.get("from_id")  # ID onog ko je poslao izazov
                game_id = create_game(challenger_id, user.id)
    
                # Poruka za izazivača (beli)
                challenger_info = active_connections.get(challenger_id)
                if challenger_info:
                    await challenger_info["ws"].send_json({
                        "type": "challenge_accepted",
                        "game_id": game_id,
                        "my_color": "white",
                        "opponent": user.username,
                        "opponent_id": user.id
                    })
    
                # Poruka za onog ko prihvata (crni)
                await websocket.send_json({
                    "type": "challenge_accepted",
                    "game_id": game_id,
                    "my_color": "black",
                    "opponent": challenger_info["username"] if challenger_info else "Nepoznat",
                    "opponent_id": challenger_id
                })
                
            elif msg_type == "decline_challenge":
                challenger_id = data.get("from_id")
                challenger_info = active_connections.get(challenger_id)
                if challenger_info:
                    await challenger_info["ws"].send_json({
                        "type": "challenge_declined",
                        "message": f"{user.username} je odbio izazov"
                    })

            # ========== POTEZI ==========
            elif msg_type == "move":
                game_id = data.get("game_id")
                fen = data.get("fen")
                move_uci = data.get("move")
                turn = data.get("turn")
                if game_id in games_store:
                    games_store[game_id]["fen"] = fen
                    games_store[game_id]["moves"].append(move_uci)
                opponent_id = get_opponent_id(game_id, user.id)
                if opponent_id:
                    opponent_info = active_connections.get(opponent_id)
                    if opponent_info:
                        await opponent_info["ws"].send_json({
                            "type": "move",
                            "game_id": game_id,
                            "fen": fen,
                            "move": move_uci,
                            "turn": turn
                        })

            # ========== REZULTAT PARTIJE (za ELO) ==========
            elif msg_type == "game_result":
                game_id = data.get("game_id")
                winner_id = data.get("winner_id")
                loser_id = data.get("loser_id")
                draw = data.get("draw", False)
                async for db in get_db():
                    if draw:
                        await update_ratings(db, winner_id, loser_id, draw=True)
                    else:
                        await update_ratings(db, winner_id, loser_id, draw=False)
                    break
                if game_id in games_store:
                    games_store[game_id]["status"] = "finished"

            # ========== REMI I PREDAJA ==========
            elif msg_type == "draw_offer":
                game_id = data.get("game_id")
                opponent_id = get_opponent_id(game_id, user.id)
                if opponent_id:
                    opponent_info = active_connections.get(opponent_id)
                    if opponent_info:
                        await opponent_info["ws"].send_json({"type": "draw_offer", "game_id": game_id})
            elif msg_type == "draw_accept":
                game_id = data.get("game_id")
                opponent_id = get_opponent_id(game_id, user.id)
                if opponent_id:
                    opponent_info = active_connections.get(opponent_id)
                    if opponent_info:
                        await opponent_info["ws"].send_json({"type": "draw_accept", "game_id": game_id})
            elif msg_type == "draw_decline":
                game_id = data.get("game_id")
                opponent_id = get_opponent_id(game_id, user.id)
                if opponent_id:
                    opponent_info = active_connections.get(opponent_id)
                    if opponent_info:
                        await opponent_info["ws"].send_json({"type": "draw_decline", "game_id": game_id})
            elif msg_type == "resign":
                game_id = data.get("game_id")
                opponent_id = get_opponent_id(game_id, user.id)
                if opponent_id:
                    opponent_info = active_connections.get(opponent_id)
                    if opponent_info:
                        await opponent_info["ws"].send_json({
                            "type": "game_over",
                            "result": "resign",
                            "winner": "opponent"
                        })
                    # Ažuriraj rejting
                    async for db in get_db():
                        await update_ratings(db, opponent_id, user.id, draw=False)
                        break
                    if game_id in games_store:
                        games_store[game_id]["status"] = "finished"

            # ========== CHAT ==========
            elif msg_type == "chat":
                target_id = data.get("target_id")
                content = data.get("content")
                target_info = active_connections.get(target_id)
                if target_info:
                    await target_info["ws"].send_json({
                        "type": "chat",
                        "from_username": user.username,
                        "content": content
                    })
            elif msg_type == "game_chat":
                game_id = data.get("game_id")
                content = data.get("content")
                opponent_id = get_opponent_id(game_id, user.id)
                if opponent_id:
                    opponent_info = active_connections.get(opponent_id)
                    if opponent_info:
                        await opponent_info["ws"].send_json({
                            "type": "game_chat",
                            "from_username": user.username,
                            "content": content,
                            "game_id": game_id
                        })

    except WebSocketDisconnect:
        print(f"❌ {user.username} diskonektovan")
        # Ukloni iz aktivnih veza
        active_connections.pop(user.id, None)
        # Obavesti ostale o promeni
        await broadcast_online_users()
        # Ukloni iz reda čekanja
        await remove_from_queue(user.id)
