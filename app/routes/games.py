from fastapi import APIRouter
from app import schemas, auth, models
from app.auth import get_current_user

router = APIRouter(prefix="/games", tags=["igre"])

# Ovde će ići rute za igre – za sada prazno
