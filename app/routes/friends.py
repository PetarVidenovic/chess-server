from fastapi import APIRouter
from app import schemas, auth, models
from app.auth import get_current_user

router = APIRouter(prefix="/friends", tags=["prijatelji"])

# Ovde će ići rute za prijateljstva
