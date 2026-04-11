from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, users, friends, chat, challenges, games, matchmaking, tournaments, leaderboard
from app.database import engine, Base
from app import models  # da se modeli učitaju

# 1. Prvo kreiraj app
app = FastAPI(title="Chess Server", version="1.0")

# 2. Tek onda dodaj CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Dozvoljava svim domenima pristup (za testiranje)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Uključi rute
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

# 4. Startup event (samo jedan)
@app.on_event("startup")
async def startup():
    """Kreiraj tabele pri pokretanju."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tabele su kreirane")
