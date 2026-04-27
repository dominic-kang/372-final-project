from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import Profile, User

router = APIRouter(prefix="/profile", tags=["profile"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class GoalsPayload(BaseModel):
    calorie_goal: int
    protein_goal: int
    carbs_goal: int
    fat_goal: int


class ProfileResponse(BaseModel):
    email: str
    calorie_goal: int
    protein_goal: int
    carbs_goal: int
    fat_goal: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_profile(user_id: int, db: Session) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_or_create_profile(current_user.id, db)
    return ProfileResponse(
        email=current_user.email,
        calorie_goal=p.calorie_goal,
        protein_goal=p.protein_goal,
        carbs_goal=p.carbs_goal,
        fat_goal=p.fat_goal,
    )


@router.put("/goals", response_model=ProfileResponse)
def update_goals(
    goals: GoalsPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = _get_or_create_profile(current_user.id, db)
    p.calorie_goal = goals.calorie_goal
    p.protein_goal = goals.protein_goal
    p.carbs_goal   = goals.carbs_goal
    p.fat_goal     = goals.fat_goal
    db.commit()
    db.refresh(p)
    return ProfileResponse(
        email=current_user.email,
        calorie_goal=p.calorie_goal,
        protein_goal=p.protein_goal,
        carbs_goal=p.carbs_goal,
        fat_goal=p.fat_goal,
    )
