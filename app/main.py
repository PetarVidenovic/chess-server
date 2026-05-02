from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles      # DODATO
from fastapi.responses import HTMLResponse       # DODATO
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
#app.include_router(matchmaking.router)
app.include_router(tournaments.router)
app.include_router(ws.router)  
app.include_router(leaderboard.router)

from app.database import init_db

@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Tabele su kreirane (ili već postoje)")

# ========== DODATAK ZA VEB KLIJENTA (STATIČKI FAJLOVI) ==========
# Montiraj folder static/ na putanju /static
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()
