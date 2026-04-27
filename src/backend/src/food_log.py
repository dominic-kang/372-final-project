from datetime import date as dateobj
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import FoodLogEntry, Profile, User

router = APIRouter(prefix="/log", tags=["log"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LogEntryCreate(BaseModel):
    food_name: str
    duke_item_name: str
    dining_location: Optional[str] = ""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    serving_multiplier: float = 1.0


class LogEntryResponse(BaseModel):
    id: int
    food_name: str
    duke_item_name: str
    dining_location: Optional[str]
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    serving_multiplier: float
    logged_at: datetime


class DailyLogResponse(BaseModel):
    entries: list[LogEntryResponse]
    totals: dict
    goals: dict
    remaining: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=DailyLogResponse)
def get_log(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if date:
        try:
            target = dateobj.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD.")
    else:
        # Use UTC date so it stays consistent with how logged_at is stored (naive UTC)
        target = datetime.now(timezone.utc).date()

    day_start = datetime(target.year, target.month, target.day, 0, 0, 0)
    day_end   = datetime(target.year, target.month, target.day, 23, 59, 59)

    entries = (
        db.query(FoodLogEntry)
        .filter(
            FoodLogEntry.user_id   == current_user.id,
            FoodLogEntry.logged_at >= day_start,
            FoodLogEntry.logged_at <= day_end,
        )
        .order_by(FoodLogEntry.logged_at.asc())
        .all()
    )

    totals = {
        "calories":  round(sum(e.calories  * e.serving_multiplier for e in entries), 1),
        "protein_g": round(sum(e.protein_g * e.serving_multiplier for e in entries), 1),
        "carbs_g":   round(sum(e.carbs_g   * e.serving_multiplier for e in entries), 1),
        "fat_g":     round(sum(e.fat_g     * e.serving_multiplier for e in entries), 1),
    }

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    goals = {
        "calories":  profile.calorie_goal if profile else 2200,
        "protein_g": profile.protein_goal if profile else 140,
        "carbs_g":   profile.carbs_goal   if profile else 250,
        "fat_g":     profile.fat_goal     if profile else 70,
    }

    remaining = {k: round(max(0.0, goals[k] - totals[k]), 1) for k in goals}

    return DailyLogResponse(
        entries=[
            LogEntryResponse(
                id=e.id,
                food_name=e.food_name,
                duke_item_name=e.duke_item_name,
                dining_location=e.dining_location,
                calories=round(e.calories   * e.serving_multiplier, 1),
                protein_g=round(e.protein_g * e.serving_multiplier, 1),
                carbs_g=round(e.carbs_g     * e.serving_multiplier, 1),
                fat_g=round(e.fat_g         * e.serving_multiplier, 1),
                serving_multiplier=e.serving_multiplier,
                logged_at=e.logged_at,
            )
            for e in entries
        ],
        totals=totals,
        goals=goals,
        remaining=remaining,
    )


@router.post("", status_code=201)
def add_log_entry(
    entry: LogEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = FoodLogEntry(
        user_id=current_user.id,
        food_name=entry.food_name,
        duke_item_name=entry.duke_item_name,
        dining_location=entry.dining_location or "",
        calories=entry.calories,
        protein_g=entry.protein_g,
        carbs_g=entry.carbs_g,
        fat_g=entry.fat_g,
        serving_multiplier=entry.serving_multiplier,
        logged_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "message": "Logged successfully."}


@router.delete("/{entry_id}")
def delete_log_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(FoodLogEntry)
        .filter(FoodLogEntry.id == entry_id, FoodLogEntry.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Log entry not found.")
    db.delete(entry)
    db.commit()
    return {"message": "Deleted."}
