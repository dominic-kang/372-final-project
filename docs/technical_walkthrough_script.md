# DukeMacros — Technical Walkthrough Video Script

**Audience:** Fellow ML engineer / course grader  
**Target length:** 7–9 minutes  
**Format:** Screen share of VS Code + browser, narrated  

---

## 0:00–0:45 — Opening: What this project does and why it's technically interesting

- DukeMacros is a full-stack macro nutrition tracker built specifically for Duke dining halls
- The core ML problem: given a photo of food, identify it and look up its real macro nutrition data from Duke's dining system
- Three ML components chained together:
  - **Food image classification** — CLIP ViT-B/32 zero-shot (no training required)
  - **Semantic menu matching** — SBERT all-MiniLM-L6-v2 cosine similarity
  - **Structured data retrieval** — Selenium-scraped Duke Net Nutrition database
- Interesting because we had to pivot from the "obvious" solution (fine-tuned CNN) to zero-shot vision-language models after discovering a fundamental problem with the original approach

---

## 0:45–2:00 — Data: Scraping Duke Net Nutrition

**Show:** `src/backend/src/nutrition.py` lines 15–16, then `notebooks/duke_macro_tracker_skeleton.ipynb` Section 3

- Duke's dining nutrition data lives at `netnutrition.cbord.com/nn-prod/Duke` — built on CBORD's platform
- **Key challenge:** the entire site is JavaScript-rendered — `requests.get()` returns just a bare HTML shell with no menu items or macros
  - Demonstrate: show what `requests.get()` would return vs. what the rendered page looks like
- **Solution:** Selenium with headless Chrome to actually execute the JavaScript
- **Navigation flow** (specific to CBORD's architecture):
  1. Load the URL, wait 10 seconds for the SPA to fully render
  2. Discover dining unit IDs from `a[onclick*='unitsSelectUnit']` elements
  3. For each unit: click unit → expand all `.cbo_nn_itemGroupRow` categories
  4. For each `a.cbo_nn_itemHover` item: click → wait for `#cbo_nn_nutritionDialog` modal → parse calories/protein/carbs/fat with regex → close dialog
- **Result:** 165 items across 7 dining locations (Gothic Grill, J.B.'s Roast & Chops, Sazon, Gyotaku, Ginger + Soy, Bella Union, The Devils Krafthouse)
- **Engineering note:** a fallback 12-item DataFrame is used when Selenium can't connect (Colab network blocks, offline testing)

---

## 2:00–3:30 — The EfficientNet Problem: Why We Had to Change Plans

**Show:** `notebooks/duke_macro_tracker_skeleton.ipynb` Section 2, the comparison plot

- **Original plan:** fine-tune EfficientNet-B3 on Food-101 (101 classes, 101,000 images)
- **What we loaded:** `models.efficientnet_b3(weights=EfficientNet_B3_Weights.IMAGENET1K_V1)` — ImageNet pretrained, then replaced the final head with `nn.Linear(1536, 101)`
- **The bug/discovery:** the new head is **randomly initialized** — EfficientNet's ImageNet weights give you a feature extractor but the Food-101 classification head has never seen food
  - Run inference on a pizza image → every class gets confidence ≈ 0.0099 = 1/101
  - That is literally a coin flip: mean ≈ 1/101, std ≈ 0.001
- **What this tells an ML engineer:** pretraining on ImageNet gives you general visual features, but the output layer is a randomly-initialized Linear — it maps those features to noise until you actually train it on Food-101
- **The solution:** rather than wait for a GPU training run, switch to a model that can classify food zero-shot
- **Show the comparison chart:** EfficientNet confidence (near-uniform) vs CLIP confidence (>99% for pizza)

---

## 3:30–5:30 — CLIP ViT-B/32: Zero-Shot Food Classification

**Show:** `src/backend/src/classifier.py`, then the notebook Section 2 CLIP cells

- **What CLIP is:** Contrastive Language-Image Pretraining — trained on 400M image-text pairs from the internet using a contrastive loss that pulls matching image-text pairs together in embedding space
- **Zero-shot classification mechanism:**
  1. For each of 101 Food-101 classes, format a text prompt: `"a photo of pizza, a type of food"`
     - **Point out:** the prompt template matters — "a photo of X" outperforms bare class names; "a type of food" focuses the text encoder
  2. Encode all 101 prompts through the CLIP text encoder → get a `(101, 512)` matrix of text embeddings
  3. L2-normalize each row
  4. **Cache this matrix** — it never changes, so we compute it once at server startup
  5. Per image: encode through CLIP vision encoder → `(1, 512)` image embedding → L2-normalize
  6. Cosine similarity = `(image_feat @ text_feat.T)` → `(101,)` score vector
  7. Multiply by temperature 100 → sharper softmax distribution → top-k
- **Show the code path:** `_cache_text_features()` called once in `__init__`, then `predict()` is just vision encoder + matrix multiply
- **Critical bug we hit — transformers ≥5.x API break:**
  - `clip_model.get_text_features()` used to return a tensor; in transformers ≥5.x it returns a `BaseModelOutputWithPooling` object
  - Fix: call `model.text_model(**inputs)` directly, then `model.text_projection(text_out.pooler_output)`
  - Same fix required in both `src/backend/src/classifier.py` and the notebook
- **Results:** >97% confidence on all 4 real food test images, ~40ms per image warmed-up on CPU

---

## 5:30–7:00 — SBERT Semantic Matching: Bridging Food-101 to Duke's Menu

**Show:** `src/backend/src/nutrition.py` `load_nutrition_db()` and `match_food_to_duke()`, then notebook Section 4

- **The gap:** CLIP predicts "pizza" but Duke's 165-item database has no pizza entry
  - Exact string match fails — dining halls use custom names ("Chipotle Chicken" not "chicken quesadilla")
- **Why semantic embeddings:** SBERT maps both strings into a shared vector space where similar meanings are close even without word overlap
- **Model:** `all-MiniLM-L6-v2` — 22M params, 384-dim embeddings, pre-trained on NLI + sentence similarity datasets
  - Fast enough to embed 165 items in milliseconds; no fine-tuning needed
- **Implementation:**
  1. At server startup: encode all 165 Duke food names → cache `(165, 384)` corpus embeddings
  2. Per query: encode the CLIP-predicted label → `(1, 384)` query embedding
  3. `cos_sim(query, corpus)` → rank by similarity → return top-k with scores
- **Show the score range:** hamburger → "Beyond Meat Burger" (0.669), chicken quesadilla → "Chipotle Chicken" (0.627), baby back ribs → "Pork Rib Rack" (0.603)
- **Limitation:** pizza → "Shrimp" (0.484) — when the food isn't served at Duke, the similarity is low with anything in the DB
  - This is honest: the system correctly signals low confidence via the similarity score

---

## 7:00–8:00 — Backend Architecture: How It Ties Together

**Show:** `src/backend/src/main.py` lifespan section, then `src/backend/src/identify.py`

- **FastAPI** with a lifespan event handler: both CLIP and SBERT load **once** when the server starts — not on every request
  - This is critical for latency: model loading takes 10–30s; inference is 40ms
- **Request flow for POST /identify:**
  1. Client sends image (multipart)
  2. `identify.py` decodes → PIL Image → `FoodClassifier.predict()` → top-3 CLIP predictions
  3. For each prediction: `match_food_to_duke()` → top-3 SBERT matches → return candidates
  4. Client shows confirmation card → user picks + sets serving multiplier → POST /log
- **Auth:** JWT with python-jose; passwords hashed with direct bcrypt
  - **Notable:** `passlib` is incompatible with `bcrypt >= 4` (passlib calls a renamed internal function) — had to use bcrypt directly
- **Database:** SQLite via SQLAlchemy ORM — three tables: `users`, `profiles`, `food_logs`
- **Key files:** `src/backend/src/main.py`, `identify.py`, `nutrition.py`, `auth.py`

---

## 8:00–9:00 — Model Files and Training Path

**Show:** `models/` directory — `train_food101.py`, `load_models.py`

- `models/train_food101.py` — EfficientNet-B3 fine-tuning script (for future upgrade):
  - Two-stage training: freeze backbone for 2 epochs (head-only warmup), then unfreeze at 10× lower LR
  - Label smoothing α=0.1 + data augmentation + cosine LR decay
  - Saves best checkpoint to `models/food101_efficientnet_b3.pth`
  - Expected: ~85% top-1, ~30ms/image on GPU (vs CLIP's ~40ms on CPU)
- `models/load_models.py` — standalone CLI for testing either model without starting the server:
  ```
  python models/load_models.py --image docs/examples/pizza.jpeg
  python models/load_models.py --image docs/examples/pizza.jpeg --model efficientnet
  ```
- To swap to EfficientNet: uncomment the EfficientNet block in `src/backend/src/classifier.py`

---

## 9:00–9:45 — Key Challenges and Technical Contributions Summary

- **Challenge 1 — CBORD JS scraping:** No public API; Selenium required to maintain session state and trigger per-item nutrition dialogs. Full click-and-parse loop with fallback data for environments where outbound requests are blocked.
- **Challenge 2 — The EfficientNet head discovery:** The pretrained ImageNet backbone is useful, but the Food-101 head was never initialized — output was literally random. This forced the pivot to CLIP and led to a deeper understanding of what pretraining does and does not give you.
- **Challenge 3 — transformers ≥5.x API break:** CLIP's `get_text_features()` API changed between transformers versions — required calling `text_model` and `text_projection` directly. This same fix was needed in both the production backend and the notebook.
- **Challenge 4 — bcrypt/passlib incompatibility:** passlib's bcrypt backend calls an internal function renamed in bcrypt ≥4. Fixed by calling bcrypt directly.
- **Contribution 1:** Clean zero-shot CLIP inference pipeline with startup-time text embedding caching — no training, no labeled data, works for any of 101 food categories immediately.
- **Contribution 2:** SBERT semantic bridge between Food-101 vocabulary and Duke's custom dining hall menu names — generalises without needing a hand-built mapping table.

---

## 9:45–10:00 — Closing

- Everything is in the repo: `src/` (backend + frontend), `models/` (training + loading scripts), `data/` (scraped DB), `notebooks/` (pipeline walkthrough), `docs/` (this script)
- The notebook (`notebooks/duke_macro_tracker_skeleton.ipynb`) walks through every ML concept in order — Section 2 shows the EfficientNet vs CLIP comparison, Section 3 the scraper, Section 4 SBERT matching, Section 7 the evaluation
- SETUP.md has complete setup instructions; README has quick start

---

*Total estimated runtime: ~9 minutes at a comfortable speaking pace (150 wpm)*
