import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import auth, food_log, identify, nutrition, profile
from .classifier import FoodClassifier
from .identify import set_classifier
from .nutrition import load_nutrition_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    # Load SBERT + EfficientNet concurrently in background threads so
    # the event loop stays responsive and total wall-clock time is the
    # max of the two loads rather than their sum.
    print("[startup] Loading models in parallel (SBERT + EfficientNet-B3)…")
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=2) as pool:
        sbert_task = loop.run_in_executor(pool, load_nutrition_db)
        clf_task   = loop.run_in_executor(pool, FoodClassifier)
        _, clf = await asyncio.gather(sbert_task, clf_task)

    set_classifier(clf)
    print("[startup] Ready.")
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────


app = FastAPI(
    title="DukeMacros API",
    version="0.1.0",
    description="Backend for the Duke dining hall macro tracker.",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_allowed_origins = list({
    "http://localhost:5173",
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def _global_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(food_log.router)
app.include_router(nutrition.router)
app.include_router(identify.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
