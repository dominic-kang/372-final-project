"""
Initialise the SQLite database.

Run once from the backend/ directory before starting the server:
    python init_db.py
"""
import os
import sys

# Ensure backend/ is on the path so 'src.*' imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import Base, engine
from src.models import FoodLogEntry, Profile, User  # noqa: F401 — registers models with Base

os.makedirs(os.path.join(os.path.dirname(__file__), "..", "..", "data"), exist_ok=True)

Base.metadata.create_all(bind=engine)
print("✓ Database tables created (users, profiles, food_logs).")
print(f"  DB location: {engine.url}")
