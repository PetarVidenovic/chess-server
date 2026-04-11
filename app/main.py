from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, users, friends, chat, challenges, games, matchmaking, tournaments, leaderboard
from app.database import engine, Base
from app import models

app = FastAPI(title="Chess Server", version="1.0")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket klijent povezan")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Primljeno: {data}")
            await websocket.send_text(f"Eho: {data}")
    except WebSocketDisconnect:
        print("WebSocket klijent prekinuo vezu")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(friends.router)
app.include_router(chat.router)
app.include_router(challenges.router)
app.include_router(games.router)
app.include_router(matchmaking.router)
app.include_router(tournaments.router)
# app.include_router(ws.router)  # ostaje zakomentarisano
app.include_router(leaderboard.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tabele su kreirane")
