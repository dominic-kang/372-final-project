from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from .database import Base

def _utcnow():
    # Naive UTC — SQLite stores datetimes as strings without tz info
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at    = Column(DateTime, default=_utcnow)


class Profile(Base):
    __tablename__ = "profiles"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    calorie_goal = Column(Integer, default=2200)
    protein_goal = Column(Integer, default=140)
    carbs_goal   = Column(Integer, default=250)
    fat_goal     = Column(Integer, default=70)


class FoodLogEntry(Base):
    __tablename__ = "food_logs"

    id                 = Column(Integer, primary_key=True, index=True)
    user_id            = Column(Integer, ForeignKey("users.id"), nullable=False)
    food_name          = Column(String, nullable=False)   # classifier label
    duke_item_name     = Column(String, nullable=False)   # matched Duke menu item
    dining_location    = Column(String, default="")
    calories           = Column(Float, default=0.0)
    protein_g          = Column(Float, default=0.0)
    carbs_g            = Column(Float, default=0.0)
    fat_g              = Column(Float, default=0.0)
    serving_multiplier = Column(Float, default=1.0)
    logged_at          = Column(DateTime, default=_utcnow)
