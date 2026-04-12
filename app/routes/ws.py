import json
import uuid
from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect
from app.websocket.manager import manager
from app.auth import get_current_user_from_token

router = APIRouter(tags=["websocket"])

# In-memory skladište za izazove (challenge_id -> podaci)
pending_challenges = {}

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    user = await get_current_user_from_token(token)
    if not user:
        await websocket.close(code=1008)
        return

    # Poveži korisnika
    await manager.connect(user.id, user.username, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                # Ako nije JSON, samo eho (možeš ukloniti ako ne treba)
                await websocket.send_text(f"Eho: {data}")
                continue

            msg_type = msg.get("type")

            # ---------- IZAZOV ----------
            if msg_type == "challenge":
                opponent_id = msg.get("opponent_id")
                if opponent_id and opponent_id in manager.active_connections:
                    # Generiši jedinstven ID izazova
                    challenge_id = str(uuid.uuid4())
                    # Sačuvaj podatke o izazovu
                    pending_challenges[challenge_id] = {
                        "challenger_id": user.id,
                        "challenger_name": user.username,
                        "opponent_id": opponent_id,
                        "status": "pending"
                    }
                    # Pošalji protivniku poruku o izazovu
                    target_ws = manager.active_connections[opponent_id]
                    await target_ws.send_json({
                        "type": "challenge_received",
                        "challenge_id": challenge_id,
                        "from": user.username,
                        "from_username": user.username,   # klijent očekuje ovo polje
                        "from_id": user.id
                    })
                    # Potvrdi pošiljaocu
                    await websocket.send_json({
                        "type": "challenge_sent",
                        "challenge_id": challenge_id,
                        "to": opponent_id
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Opponent not online"
                    })

            # ---------- PRIHVATI IZAZOV ----------
            elif msg_type == "accept_challenge":
                challenge_id = msg.get("challenge_id")
                challenge = pending_challenges.get(challenge_id)
                if challenge and challenge["opponent_id"] == user.id:
                    # Igrač prihvata izazov
                    challenger_id = challenge["challenger_id"]
                    opponent_id = challenge["opponent_id"]

                    # Kreiraj novu igru (ovde generiši game_id, npr. uuid)
                    game_id = str(uuid.uuid4())

                    # Obavesti oba igrača
                    for uid in (challenger_id, opponent_id):
                        ws = manager.active_connections.get(uid)
                        if ws:
                            # Odredi boju za svakog igrača
                            my_color = "beli" if uid == challenger_id else "crni"
                            opponent_name = user.username if uid == challenger_id else challenge["challenger_name"]
                            await ws.send_json({
                                "type": "challenge_accepted",
                                "game_id": game_id,
                                "my_color": my_color,
                                "opponent": opponent_name
                            })

                    # Ukloni izazov iz skladišta
                    del pending_challenges[challenge_id]

            # ---------- ODBIJ IZAZOV ----------
            elif msg_type == "decline_challenge":
                challenge_id = msg.get("challenge_id")
                challenge = pending_challenges.get(challenge_id)
                if challenge and challenge["opponent_id"] == user.id:
                    # Obavesti pošiljaoca
                    challenger_ws = manager.active_connections.get(challenge["challenger_id"])
                    if challenger_ws:
                        await challenger_ws.send_json({
                            "type": "challenge_declined",
                            "challenge_id": challenge_id
                        })
                    del pending_challenges[challenge_id]

            # ---------- CHAT ----------
            elif msg_type == "chat":
                content = msg.get("content")
                if content:
                    # Prosledi svim povezanim korisnicima (ili samo u sobu)
                    for ws in manager.active_connections.values():
                        try:
                            await ws.send_json({
                                "type": "chat",
                                "sender": user.username,
                                "content": content
                            })
                        except:
                            pass
            # ---------- POTEZ (MOVE) ----------
            elif msg_type == "move":
                game_id = msg.get("game_id")
                # Pronalazimo ko je protivnik. 
                # Pošto trenutno nemaš bazu aktivnih igara u ws.py, 
                # najlakše je da privremeno uradiš broadcast svima ili (bolje)
                # da klijent šalje opponent_id. 
                # Ali, pošto tvoj klijent šalje game_id, moramo poslati poruku SVIMA 
                # osim tebi, ili prosto svima, a klijent će filtrirati po game_id.
                
                for uid, ws_conn in manager.active_connections.items():
                    if uid != user.id:  # Šaljemo svima OSIM onome ko je odigrao potez
                        try:
                            await ws_conn.send_json(msg)
                        except:
                            pass

            # ---------- CHAT UNUTAR IGRE ----------
            elif msg_type == "game_chat":
                for uid, ws_conn in manager.active_connections.items():
                    if uid != user.id:
                        try:
                            await ws_conn.send_json(msg)
                        except:
                            pass
                        
            # ---------- OSTALO ----------
            else:
                # Nepoznat tip – samo eho
                await websocket.send_text(f"Eho: {data}")
            
    except WebSocketDisconnect:
        await manager.disconnect(user.id)   # ISPRAVLJENO: dodato await, uklonjeno dodatno broadcast
    except Exception as e:
        print(f"Greška u WebSocket-u: {e}")
        await manager.disconnect(user.id)   # ISPRAVLJENO: dodato await
