from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models

async def update_ratings(db: AsyncSession, winner_id: int, loser_id: int, draw: bool = False):
    K = 32
    result = await db.execute(select(models.User).where(models.User.id.in_([winner_id, loser_id])))
    users = result.scalars().all()
    user_dict = {u.id: u for u in users}
    winner = user_dict.get(winner_id)
    loser = user_dict.get(loser_id)
    if not winner or not loser:
        return
    expected_winner = 1 / (1 + 10 ** ((loser.rating - winner.rating) / 400))
    expected_loser = 1 - expected_winner
    if draw:
        winner.rating += K * (0.5 - expected_winner)
        loser.rating += K * (0.5 - expected_loser)
    else:
        winner.rating += K * (1 - expected_winner)
        loser.rating += K * (0 - expected_loser)
    winner.rating = int(round(winner.rating))
    loser.rating = int(round(loser.rating))
    await db.commit()
    print(f"⭐ Rejting: {winner.username} {winner.rating}, {loser.username} {loser.rating}")
