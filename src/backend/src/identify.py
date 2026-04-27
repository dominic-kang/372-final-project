import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

from .auth import get_current_user
from .classifier import FoodClassifier
from .models import User
from .nutrition import match_food_to_duke

router = APIRouter(tags=["identify"])

# Injected at startup by main.py lifespan
_classifier: FoodClassifier = None


def set_classifier(clf: FoodClassifier) -> None:
    global _classifier
    _classifier = clf


@router.post("/identify")
async def identify_food(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a multipart image upload, run Food-101 classification, and return
    ranked Duke menu matches for each top prediction.

    Does NOT write to the food log — logging is triggered only after the user
    confirms their selection in the frontend ConfirmationCard.

    Returns:
        {
          "predictions": [
            {
              "predicted_class": str,
              "confidence": float,
              "duke_matches": [ { food_name, dining_location, serving_size,
                                  calories, protein_g, carbs_g, fat_g,
                                  similarity }, ... ]
            },
            ...
          ],
          "suggested_match": { <top Duke item for highest-confidence prediction> }
        }
    """
    if _classifier is None:
        raise HTTPException(status_code=503, detail="Classifier not initialised yet.")

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode image file.")

    predictions = _classifier.predict(image, top_k=3)

    results = [
        {
            "predicted_class": p["class"],
            "confidence":      p["confidence"],
            "duke_matches":    match_food_to_duke(p["class"], top_k=3),
        }
        for p in predictions
    ]

    suggested = results[0]["duke_matches"][0] if results and results[0]["duke_matches"] else None

    return {"predictions": results, "suggested_match": suggested}
