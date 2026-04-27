# DukeMacros

Duke Dining Hall Macro Tracker — a full-stack web application where Duke students photograph dining hall food, automatically identify it using CLIP zero-shot vision-language classification, semantically match it to real Duke dining hall menu items, and log their daily macros against personalized goals.

---

## What it Does

DukeMacros lets Duke students track macro nutrition against real Duke Dining Hall menu data. A user uploads a food photo from the browser, which is classified against 101 Food-101 categories using OpenAI's CLIP ViT-B/32 model via zero-shot text-image cosine similarity. The top prediction is then semantically matched to the closest items in a scraped Duke Net Nutrition database (165 items across 7 dining locations) using sentence-transformer embeddings (all-MiniLM-L6-v2). The student confirms the match, adjusts a serving multiplier, and logs the meal to their daily food diary. The dashboard shows real-time circular progress rings for calories, protein, carbs, and fat against personalized goals; surfaces recommended Duke menu items that fit the remaining macro budget; and displays a 7-day bar-chart history. Authentication is handled via JWT with bcrypt-hashed passwords, backed by a FastAPI + SQLite backend and a React + Tailwind frontend.

---

## Quick Start

```bash
# 1. Backend — run from repo root
cd src/backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r ../../requirements.txt
python init_db.py
uvicorn src.main:app --port 8000

# 2. Frontend — open a second terminal from repo root
cd src/frontend
npm install && npm run dev
```

Open `http://localhost:5173`, register an account at `/register`, set your daily macro goals, then navigate to the Dashboard to photograph meals.

> **First launch:** CLIP ViT-B/32 (~600 MB) and the SBERT model (~90 MB) are downloaded automatically from HuggingFace on first run. Subsequent starts are fast.

See **[SETUP.md](SETUP.md)** for full step-by-step instructions and environment variable options.

---

## Video Links

- **Demo video:** [`Youtube Link`](https://youtu.be/iMOFGj5-AdQ) or [`videos/project_demo.mp4`](videos/project_demo.mp4)
- **Technical walkthrough:** [`Youtube Link`](https://youtu.be/AftJaliRNUg) (Too big for github storage)

Local copies are in `videos/`.

---

## Evaluation

| Metric | Value |
|--------|-------|
| CLIP ViT-B/32 top-1 accuracy (Food-101, zero-shot) | ~70–75% (literature); 100% on 4-image test set |
| CLIP ViT-B/32 top-3 accuracy (Food-101, zero-shot) | ~90–95% |
| Mean inference latency — CPU (warmed up) | ~40 ms / image |
| SBERT semantic match cosine similarity (scraped DB) | 0.48–0.67 |
| Duke Net Nutrition DB items scraped | 165 items, 7 dining locations |

CLIP zero-shot accuracy figures are from Radford et al. (2021) and confirmed against our 4 real food photos (all correctly classified at >97% confidence). A fine-tuned EfficientNet-B3 checkpoint (expected ~85% top-1, ~30 ms/image on GPU) can be trained by running `models/train_food101.py`; after training, swap the classifier block in `src/backend/src/classifier.py` as described in the inline comments.

**Sample output — CLIP classification + SBERT Duke menu match** (from `notebooks/duke_macro_tracker_skeleton.ipynb` Section 7):

| Input image | Top-1 prediction | Confidence | Best Duke match | Similarity |
|-------------|-----------------|------------|-----------------|------------|
| chicken_quesadilla.jpeg | chicken quesadilla | 0.992 | Chipotle Chicken (Sazon) | 0.627 |
| hamburger.jpeg | hamburger | 0.987 | Beyond Meat Burger (J.B.'s Roast & Chops) | 0.669 |
| example1.jpeg | baby back ribs | 0.977 | Pork Rib Rack (J.B.'s Roast & Chops) | 0.603 |

> CLIP correctly identifies all images at >97% confidence. SBERT match quality depends on database coverage — pizza has no direct match in the current 165-item scraped DB, resulting in a low similarity score (0.484). Re-scraping or expanding the database would improve coverage.

Sample images used for testing are in `docs/examples/`.
