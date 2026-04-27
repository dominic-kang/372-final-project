import os
from datetime import date as dateobj
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends
from sentence_transformers import SentenceTransformer
from sentence_transformers import util as sbert_util
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import FoodLogEntry, Profile, User

_HERE      = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "data", "duke_nutrition_db.csv"))

router = APIRouter(tags=["recommendations"])

# Module-level singletons — populated by load_nutrition_db() at startup
_duke_df:           pd.DataFrame = pd.DataFrame()
_sbert:             SentenceTransformer = None
_corpus_embeddings  = None   # pre-computed embeddings for all Duke food names

_FALLBACK_ROWS = [
    ("Grilled Chicken Breast",  180, 34,  0, 4,  "4 oz",      "Marketplace"),
    ("Caesar Salad",            230,  8, 14, 17, "1 plate",   "West Union"),
    ("Spaghetti Bolognese",     490, 24, 62, 14, "1 bowl",    "Brodhead"),
    ("Cheese Pizza (2 slices)", 480, 20, 56, 18, "2 slices",  "Marketplace"),
    ("Vegetable Stir Fry",      210,  7, 38,  5, "1 cup",     "West Union"),
    ("Chocolate Cake",          350,  4, 52, 15, "1 slice",   "Marketplace"),
    ("Scrambled Eggs",          180, 12,  2, 13, "3 eggs",    "Brodhead"),
    ("Beef Burger",             620, 38, 42, 28, "1 burger",  "West Union"),
    ("Steamed Broccoli",         55,  4, 10,  1, "1 cup",     "Marketplace"),
    ("Mac and Cheese",          410, 14, 58, 14, "1 cup",     "Brodhead"),
    ("Greek Yogurt w/ Granola", 280, 15, 38,  7, "1 bowl",    "West Union"),
    ("Salmon Fillet",           290, 40,  0, 14, "5 oz",      "Marketplace"),
]

_COLS = ["food_name", "calories", "protein_g", "carbs_g", "fat_g", "serving_size", "dining_location"]


def load_nutrition_db() -> None:
    """
    Load Duke nutrition CSV and pre-compute SBERT corpus embeddings.
    Called once during FastAPI lifespan startup.
    Re-entrant safe: returns immediately if already loaded.
    """
    global _duke_df, _sbert, _corpus_embeddings

    if _sbert is not None:
        return  # already loaded — skip re-download and re-embed

    if os.path.exists(_DATA_PATH):
        _duke_df = pd.read_csv(_DATA_PATH)
        print(f"[nutrition] Loaded {len(_duke_df)} items from {_DATA_PATH}.")
    else:
        print(f"[nutrition] CSV not found — using built-in fallback data.")
        _duke_df = pd.DataFrame(_FALLBACK_ROWS, columns=_COLS)

    _sbert             = SentenceTransformer("all-MiniLM-L6-v2")
    _corpus_embeddings = _sbert.encode(_duke_df["food_name"].tolist(), convert_to_tensor=True)
    print(f"[nutrition] SBERT embeddings ready ({len(_duke_df)} items).")


def match_food_to_duke(predicted_name: str, top_k: int = 3) -> list[dict]:
    """
    Return the top-k Duke menu items semantically closest to predicted_name.

    Uses cosine similarity on all-MiniLM-L6-v2 embeddings.
    """
    if _duke_df.empty:
        return []

    query_emb = _sbert.encode(predicted_name, convert_to_tensor=True)
    scores    = sbert_util.cos_sim(query_emb, _corpus_embeddings)[0]
    k         = min(top_k, len(_duke_df))
    top_idx   = scores.topk(k).indices.cpu().numpy()

    return [
        {
            "food_name":       _duke_df.iloc[i]["food_name"],
            "dining_location": str(_duke_df.iloc[i].get("dining_location", "")),
            "serving_size":    str(_duke_df.iloc[i].get("serving_size", "")),
            "calories":        float(_duke_df.iloc[i]["calories"]),
            "protein_g":       float(_duke_df.iloc[i]["protein_g"]),
            "carbs_g":         float(_duke_df.iloc[i]["carbs_g"]),
            "fat_g":           float(_duke_df.iloc[i]["fat_g"]),
            "similarity":      round(float(scores[i].item()), 4),
        }
        for i in top_idx
    ]


def get_recommendations(remaining: dict, n: int = 5) -> list[dict]:
    """
    Return up to n Duke menu items that fit within the remaining macro budget.

    Scoring: average normalized closeness across all four macros.
    Items that exceed any budget by >20 % are excluded.
    """
    if _duke_df.empty:
        return []

    cal  = remaining.get("calories",  0)
    prot = remaining.get("protein_g", 0)
    carb = remaining.get("carbs_g",   0)
    fat  = remaining.get("fat_g",     0)

    scored = []
    for _, row in _duke_df.iterrows():
        if (
            (cal  > 0 and row["calories"]  > cal  * 1.20) or
            (prot > 0 and row["protein_g"] > prot * 1.20) or
            (carb > 0 and row["carbs_g"]   > carb * 1.20) or
            (fat  > 0 and row["fat_g"]     > fat  * 1.20)
        ):
            continue

        def _norm(v, budget):
            return 1.0 - abs(v - budget) / max(budget, 1)

        fit = (
            _norm(row["calories"],  cal)  +
            _norm(row["protein_g"], prot) +
            _norm(row["carbs_g"],   carb) +
            _norm(row["fat_g"],     fat)
        ) / 4.0

        scored.append({
            "food_name":       row["food_name"],
            "dining_location": str(row.get("dining_location", "")),
            "serving_size":    str(row.get("serving_size", "")),
            "calories":        float(row["calories"]),
            "protein_g":       float(row["protein_g"]),
            "carbs_g":         float(row["carbs_g"]),
            "fat_g":           float(row["fat_g"]),
            "fit_score":       round(fit, 4),
        })

    scored.sort(key=lambda x: x["fit_score"], reverse=True)
    return scored[:n]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/recommendations")
def recommendations_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return Duke items that best fill the user's remaining macro budget for today."""
    today     = datetime.now(timezone.utc).date()
    day_start = datetime(today.year, today.month, today.day, 0, 0, 0)
    day_end   = datetime(today.year, today.month, today.day, 23, 59, 59)

    entries = (
        db.query(FoodLogEntry)
        .filter(
            FoodLogEntry.user_id   == current_user.id,
            FoodLogEntry.logged_at >= day_start,
            FoodLogEntry.logged_at <= day_end,
        )
        .all()
    )

    consumed = {
        "calories":  sum(e.calories  * e.serving_multiplier for e in entries),
        "protein_g": sum(e.protein_g * e.serving_multiplier for e in entries),
        "carbs_g":   sum(e.carbs_g   * e.serving_multiplier for e in entries),
        "fat_g":     sum(e.fat_g     * e.serving_multiplier for e in entries),
    }

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    goals = {
        "calories":  profile.calorie_goal if profile else 2200,
        "protein_g": profile.protein_goal if profile else 140,
        "carbs_g":   profile.carbs_goal   if profile else 250,
        "fat_g":     profile.fat_goal     if profile else 70,
    }

    remaining = {k: round(max(0.0, goals[k] - consumed[k]), 1) for k in goals}
    return {"recommendations": get_recommendations(remaining), "remaining": remaining}
