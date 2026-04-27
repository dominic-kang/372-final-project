# DukeMacros — Setup Guide

## Prerequisites

| Tool | Version |
|------|---------|
| Python | >= 3.10 |
| Node.js | >= 18 |
| npm | >= 9 |

---

## Step 1 — Navigate to the Repo Root

All paths below are relative to the repository root (`final372_project/`).

---

## Step 2 — Backend: Virtual Environment & Dependencies

```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../../requirements.txt
```

> First install downloads PyTorch (~800 MB). CLIP ViT-B/32 (~600 MB) and the SBERT model (~90 MB) are downloaded automatically on first server start.
> GPU inference requires a CUDA-capable GPU and the matching `torch+cu*` build.

---

## Step 3 — Initialize the Database

```bash
# Still inside src/backend/ with .venv active
python init_db.py
```

Expected output:
```
✓ Database tables created (users, profiles, food_logs).
  DB location: sqlite:///…/data/dukeamacros.db
```

The Duke nutrition CSV (`data/duke_nutrition_db.csv`) is already included in the repo. If you skip init_db.py the backend falls back to a built-in 12-item sample table automatically.

---

## Step 4 — Environment Variables (optional)

Create `src/backend/.env` and set any of the following:

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `dev-secret-change-in-production` | Secret for signing JWTs — **change this in production** |
| `FRONTEND_URL` | `http://localhost:5173` | Extra origin added to CORS allow-list |
| `DATABASE_URL` | SQLite path inside `data/` | Override to use a different database |

Or export in your shell:

```bash
export JWT_SECRET_KEY="your-strong-secret-here"
```

---

## Step 5 — Start the FastAPI Server

```bash
# Inside src/backend/ with .venv active
uvicorn src.main:app --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`.

> **Startup time:** the first launch downloads CLIP ViT-B/32 (~600 MB) and the SBERT model (~90 MB) from HuggingFace. Subsequent starts are fast.

---

## Step 6 — Frontend: Install & Run

```bash
# From repo root, in a separate terminal
cd src/frontend
npm install
npm run dev
```

The React app will be available at `http://localhost:5173`.

> If your backend runs on a different port or host:
> ```bash
> VITE_API_URL=http://localhost:8000 npm run dev
> ```
> Or create `src/frontend/.env.local` with:
> ```
> VITE_API_URL=http://localhost:8000
> ```

---

## Step 7 — Create Your Account

1. Open `http://localhost:5173/register`.
2. Register with any email + password (>= 6 chars).
3. You will be redirected to the Goals page — set your daily macro targets.
4. Navigate to Dashboard and start photographing meals.

---

## Running Both Servers (convenience)

In two separate terminal tabs from the repo root:

```bash
# Tab 1 — backend
cd src/backend && source .venv/bin/activate && uvicorn src.main:app --port 8000

# Tab 2 — frontend
cd src/frontend && npm run dev
```

---

## Optional: Train the EfficientNet-B3 Classifier

The active classifier uses CLIP ViT-B/32 zero-shot (~70–75% top-1). To fine-tune EfficientNet-B3 for ~85% top-1:

```bash
# From repo root with src/backend venv active
source src/backend/.venv/bin/activate
python models/train_food101.py [--epochs 10] [--batch 32] [--lr 1e-4]
```

The checkpoint is saved to `models/food101_efficientnet_b3.pth`. After training, uncomment the EfficientNet block in `src/backend/src/classifier.py` and comment out the CLIP block.

To test either model standalone (without running the full server):

```bash
python models/load_models.py --image docs/examples/pizza.jpeg
python models/load_models.py --image docs/examples/pizza.jpeg --model efficientnet
```

> Requires a GPU. On a T4/A100 (Google Colab): ~2–4 hours for 10 epochs. CPU-only is not recommended.

---

## Notebook

The companion Jupyter notebook walks through data scraping, model evaluation, and the semantic-matching logic:

```bash
jupyter notebook notebooks/duke_macro_tracker_skeleton.ipynb
```
