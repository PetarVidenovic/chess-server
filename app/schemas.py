from pydantic import BaseModel, EmailStr, Field, validator
import re
from datetime import datetime
from typing import Optional, List

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8)

    @validator('password')
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Lozinka mora sadržati barem jedno veliko slovo")
        if not re.search(r"[a-z]", v):
            raise ValueError("Lozinka mora sadržati barem jedno malo slovo")
        if not re.search(r"\d", v):
            raise ValueError("Lozinka mora sadržati barem jednu cifru")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    profile_picture: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    receiver_id: int
    content: str = Field(..., max_length=5000)

class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    is_read: bool
    created_at: datetime
    
# ===== Šeme za turnire =====
class TournamentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rounds: int = 1
    type: str  # "knockout", "round_robin", "swiss"
    max_players: int
    settings: dict = {}

class TournamentOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    players_count: int
    created_at: datetime

class TournamentPlayerOut(BaseModel):
    user_id: int
    username: str
    wins: int
    losses: int
    draws: int
    points: float

class TournamentMatchOut(BaseModel):
    id: int
    round: int
    player1: str
    player2: str
    result: Optional[str]
    played: bool

class TournamentDetailOut(BaseModel):
    id: int
    name: str
    status: str
    matches: List[TournamentMatchOut]
    standings: List[TournamentPlayerOut]
