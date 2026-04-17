from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, users, friends, chat, challenges, games, matchmaking, tournaments, leaderboard, ws
from app.database import engine, Base
from app import models  # uvozi sve modele

app = FastAPI(title="Chess Server", version="1.0")

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
app.include_router(ws.router)  
app.include_router(leaderboard.router)

from app.database import init_db

@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Tabele su kreirane (ili već postoje)")
