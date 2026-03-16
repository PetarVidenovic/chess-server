from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, users, friends, chat, challenges, games, matchmaking, tournaments, websocket

app = FastAPI(title="Chess Platform API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicijalizacija baze (opciono, ako želiš automatsko kreiranje tabela)
@app.on_event("startup")
async def init_db():
    from app.database import engine
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Uključivanje ruta
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(friends.router)
app.include_router(chat.router)
app.include_router(challenges.router)
app.include_router(games.router)
app.include_router(matchmaking.router)
app.include_router(tournaments.router)
app.include_router(websocket.router)

@app.get("/")
async def root():
    return {"message": "Chess Platform API"}
