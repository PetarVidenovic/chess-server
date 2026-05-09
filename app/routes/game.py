from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app import models

router = APIRouter(prefix="/games", tags=["igre"])

async def update_ratings(db: AsyncSession, winner_id: int, loser_id: int, draw: bool = False):
    """Ažurira ELO rejting i statistiku nakon partije."""
    K = 32
    
    # Dohvati oba korisnika
    result = await db.execute(
        select(models.User).where(models.User.id.in_([winner_id, loser_id]))
    )
    users = result.scalars().all()
    user_dict = {u.id: u for u in users}
    winner = user_dict.get(winner_id)
    loser = user_dict.get(loser_id)
    
    if not winner or not loser:
        print("❌ Nisu pronađeni korisnici")
        return
    
    # Ažuriraj statistiku
    if draw:
        winner.draws += 1
        loser.draws += 1
        # Rejting za remi
        expected_winner = 1 / (1 + 10 ** ((loser.rating - winner.rating) / 400))
        winner.rating += K * (0.5 - expected_winner)
        loser.rating += K * (0.5 - expected_loser)
    else:
        winner.wins += 1
        loser.losses += 1
        # Rejting za pobedu/poraz
        expected_winner = 1 / (1 + 10 ** ((loser.rating - winner.rating) / 400))
        expected_loser = 1 - expected_winner
        winner.rating += K * (1 - expected_winner)
        loser.rating += K * (0 - expected_loser)
    
    winner.rating = int(round(winner.rating))
    loser.rating = int(round(loser.rating))
    
    # Sačuvaj promene
    await db.commit()
    
    # Osveži objekte (da bi print pokazao nove vrednosti)
    await db.refresh(winner)
    await db.refresh(loser)
    
    print(f"⭐ Rejting: {winner.username} {winner.rating}, {loser.username} {loser.rating}")
    print(f"📊 Statistika: {winner.username} (W:{winner.wins} L:{winner.losses} D:{winner.draws})")
    print(f"📊 Statistika: {loser.username} (W:{loser.wins} L:{loser.losses} D:{loser.draws})")
