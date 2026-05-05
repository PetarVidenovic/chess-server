from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth import get_current_user
from app import models, schemas
from typing import List
import datetime

router = APIRouter(prefix="/tournaments", tags=["turniri"])

# Helper za generisanje mečeva (svako sa svakim, jedan krug)
async def generate_matches(tournament_id: int, db: AsyncSession):
    # Dobavi sve prijavljene igrače
    players = (await db.execute(
        select(models.TournamentPlayer).where(models.TournamentPlayer.tournament_id == tournament_id)
    )).scalars().all()
    user_ids = [p.user_id for p in players]
    # Generiši parove (svako sa svakim)
    matches = []
    for i in range(len(user_ids)):
        for j in range(i+1, len(user_ids)):
            matches.append(models.TournamentMatch(
                tournament_id=tournament_id,
                round=1,
                player1_id=user_ids[i],
                player2_id=user_ids[j]
            ))
    db.add_all(matches)
    await db.commit()

# 1. Kreiranje turnira (samo admin ili bilo koji korisnik – prilagodi)
@router.post("/", response_model=schemas.TournamentOut)
async def create_tournament(
    t: schemas.TournamentCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Možeš dozvoliti samo adminu: if current_user.id != 1: raise...
    tournament = models.Tournament(
        name=t.name,
        description=t.description,
        created_by=current_user.id,
        rounds=t.rounds,
        status="open"
    )
    db.add(tournament)
    await db.commit()
    await db.refresh(tournament)
    return {"id": tournament.id, "name": tournament.name, "description": tournament.description, "status": tournament.status, "players_count": 0, "created_at": tournament.created_at}

# 2. Lista turnira
@router.get("/", response_model=List[schemas.TournamentOut])
async def list_tournaments(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tournaments = (await db.execute(select(models.Tournament))).scalars().all()
    result = []
    for t in tournaments:
        count = (await db.execute(select(func.count()).where(models.TournamentPlayer.tournament_id == t.id))).scalar()
        result.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "status": t.status,
            "players_count": count,
            "created_at": t.created_at
        })
    return result

# 3. Prijava na turnir
@router.post("/{tournament_id}/join")
async def join_tournament(
    tournament_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tournament = await db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Turnir ne postoji")
    if tournament.status != "open":
        raise HTTPException(status_code=400, detail="Turnir nije otvoren za prijave")
    # Provjeri da li je već prijavljen
    existing = (await db.execute(
        select(models.TournamentPlayer).where(
            models.TournamentPlayer.tournament_id == tournament_id,
            models.TournamentPlayer.user_id == current_user.id
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Već ste prijavljeni")
    tp = models.TournamentPlayer(tournament_id=tournament_id, user_id=current_user.id)
    db.add(tp)
    await db.commit()
    return {"message": "Prijavljeni ste na turnir"}

# 4. Detalji turnira (mečevi i tabela)
@router.get("/{tournament_id}/details")
async def tournament_details(
    tournament_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tournament = await db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Turnir ne postoji")
    # Mečevi
    matches = (await db.execute(
        select(models.TournamentMatch).where(models.TournamentMatch.tournament_id == tournament_id)
    )).scalars().all()
    matches_out = []
    for m in matches:
        p1 = await db.get(models.User, m.player1_id)
        p2 = await db.get(models.User, m.player2_id)
        matches_out.append({
            "id": m.id,
            "round": m.round,
            "player1": p1.username if p1 else "?",
            "player2": p2.username if p2 else "?",
            "result": m.result,
            "played": m.played
        })
    # Tabela (standings)
    players = (await db.execute(
        select(models.TournamentPlayer).where(models.TournamentPlayer.tournament_id == tournament_id)
    )).scalars().all()
    standings = []
    for p in players:
        user = await db.get(models.User, p.user_id)
        standings.append({
            "user_id": p.user_id,
            "username": user.username if user else "?",
            "wins": p.wins,
            "losses": p.losses,
            "draws": p.draws,
            "points": p.points
        })
    standings.sort(key=lambda x: x["points"], reverse=True)
    return {
        "id": tournament.id,
        "name": tournament.name,
        "status": tournament.status,
        "matches": matches_out,
        "standings": standings
    }

# 5. Pokretanje turnira (admin) – generiše mečeve
@router.post("/{tournament_id}/start")
async def start_tournament(
    tournament_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tournament = await db.get(models.Tournament, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Turnir ne postoji")
    if tournament.status != "open":
        raise HTTPException(status_code=400, detail="Turnir nije otvoren")
    # Generiši mečeve
    await generate_matches(tournament_id, db)
    tournament.status = "started"
    await db.commit()
    return {"message": "Turnir je počeo"}

# 6. Unošenje rezultata meča
@router.post("/{tournament_id}/matches/{match_id}/result")
async def set_match_result(
    tournament_id: int,
    match_id: int,
    result: str,  # "player1", "player2", "draw"
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    match = await db.get(models.TournamentMatch, match_id)
    if not match or match.tournament_id != tournament_id:
        raise HTTPException(status_code=404, detail="Meč ne postoji")
    if match.played:
        raise HTTPException(status_code=400, detail="Meč je već odigran")
    # Ažuriraj meč
    match.result = result
    match.played = True
    # Ažuriraj statistiku igrača
    p1 = (await db.execute(
        select(models.TournamentPlayer).where(
            models.TournamentPlayer.tournament_id == tournament_id,
            models.TournamentPlayer.user_id == match.player1_id
        )
    )).scalar_one()
    p2 = (await db.execute(
        select(models.TournamentPlayer).where(
            models.TournamentPlayer.tournament_id == tournament_id,
            models.TournamentPlayer.user_id == match.player2_id
        )
    )).scalar_one()
    if result == "player1":
        p1.wins += 1
        p1.points += 1
        p2.losses += 1
    elif result == "player2":
        p2.wins += 1
        p2.points += 1
        p1.losses += 1
    elif result == "draw":
        p1.draws += 1
        p1.points += 0.5
        p2.draws += 1
        p2.points += 0.5
    await db.commit()
    return {"message": "Rezultat unesen"}
