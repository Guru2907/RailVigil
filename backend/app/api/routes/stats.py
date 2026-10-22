from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas.encroachment import StatsOut
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=StatsOut)
def summary(db: Session = Depends(get_db)):
    return stats_service.summary(db)
