"""
Food classifier — DukeMacros backend.

Active model: CLIP ViT-B/32 zero-shot (openai/clip-vit-base-patch32)
  Text-image cosine similarity against 101 Food-101 class prompts.
  No fine-tuning required. ~70-75% top-1 on Food-101 zero-shot.

Future model: EfficientNet-B3 fine-tuned on Food-101.
  Run models/train_food101.py to produce the checkpoint, then swap
  the _load_model() implementation below.
  Standalone loader: models/load_models.py --model efficientnet

Why the original EfficientNet head was useless:
  The head was a randomly-initialised Linear(1536→101) that was never
  trained. With 101 classes the output was a near-uniform distribution
  (observed mean=0.0099 = 1/101, std≈0.001) — effectively a coin flip.
  CLIP bypasses this entirely by using pre-trained text-image alignment.
"""
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# Food-101 class labels — alphabetical, matches torchvision dataset indexing
FOOD101_CLASSES = [
    "apple pie", "baby back ribs", "baklava", "beef carpaccio", "beef tartare",
    "beet salad", "beignets", "bibimbap", "bread pudding", "breakfast burrito",
    "bruschetta", "caesar salad", "cannoli", "caprese salad", "carrot cake",
    "ceviche", "cheese plate", "cheesecake", "chicken curry", "chicken quesadilla",
    "chicken wings", "chocolate cake", "chocolate mousse", "churros", "clam chowder",
    "club sandwich", "crab cakes", "creme brulee", "croque madame", "cup cakes",
    "deviled eggs", "donuts", "dumplings", "edamame", "eggs benedict",
    "escargots", "falafel", "filet mignon", "fish and chips", "foie gras",
    "french fries", "french onion soup", "french toast", "fried calamari", "fried rice",
    "frozen yogurt", "garlic bread", "gnocchi", "greek salad", "grilled cheese sandwich",
    "grilled salmon", "guacamole", "gyoza", "hamburger", "hot and sour soup",
    "hot dog", "huevos rancheros", "hummus", "ice cream", "lasagna",
    "lobster bisque", "lobster roll sandwich", "macaroni and cheese", "macarons", "miso soup",
    "mussels", "nachos", "omelette", "onion rings", "oysters",
    "pad thai", "paella", "pancakes", "panna cotta", "peking duck",
    "pho", "pizza", "pork chop", "poutine", "prime rib",
    "pulled pork sandwich", "ramen", "ravioli", "red velvet cake", "risotto",
    "samosa", "sashimi", "scallops", "seaweed salad", "shrimp and grits",
    "spaghetti bolognese", "spaghetti carbonara", "spring rolls", "steak", "strawberry shortcake",
    "sushi", "tacos", "takoyaki", "tiramisu", "tuna tartare", "waffles",
]

# Prompt template — "a photo of X" significantly outperforms bare class names in CLIP
_PROMPT_TEMPLATE = "a photo of {cls}, a type of food"


class FoodClassifier:
    """
    CLIP ViT-B/32 zero-shot food classifier.

    At construction the class prompts are embedded once and cached as
    `self._text_features`. Per-image inference is a single forward pass
    through the vision encoder + a cosine similarity against those cached
    text features — typically <100 ms on CPU.

    # To upgrade to fine-tuned EfficientNet-B3:
    #   1. Run `python models/train_food101.py` from the repo root (~2-4h on T4).
    #   2. In _load_model() below, comment out the CLIP block and uncomment
    #      the EfficientNet block (checkpoint at models/food101_efficientnet_b3.pth).
    #   Expected top-1 improvement: ~70% (CLIP zero-shot) → ~85% (fine-tuned).
    """

    _CLIP_MODEL_ID = "openai/clip-vit-base-patch32"

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_model()
        self._cache_text_features()

    # ------------------------------------------------------------------
    # Model loading — swap this block to switch to EfficientNet-B3
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Load CLIP ViT-B/32. Weights are cached by HuggingFace after first download."""
        self._processor = CLIPProcessor.from_pretrained(self._CLIP_MODEL_ID)
        self._model     = CLIPModel.from_pretrained(self._CLIP_MODEL_ID).to(self.device)
        self._model.eval()
        print(f"[FoodClassifier] CLIP ViT-B/32 loaded on {self.device}.")

        # TODO: uncomment to use a fine-tuned EfficientNet-B3 checkpoint instead:
        # import os
        # from torchvision import models
        # ckpt_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "models",
        #                          "food101_efficientnet_b3.pth")
        # self._effnet = models.efficientnet_b3(weights=None)
        # self._effnet.classifier[1] = torch.nn.Linear(
        #     self._effnet.classifier[1].in_features, 101)
        # self._effnet.load_state_dict(torch.load(ckpt_path, map_location=self.device))
        # self._effnet.to(self.device).eval()
        # self._use_clip = False

    def _get_text_features(self, inputs) -> torch.Tensor:
        """Extract and L2-normalise CLIP text embeddings (transformers-version-safe)."""
        # transformers >= 5.x returns a ModelOutput object; extract pooler then project
        text_out = self._model.text_model(**inputs)
        feats    = self._model.text_projection(text_out.pooler_output)
        return F.normalize(feats, p=2, dim=-1)

    def _get_image_features(self, inputs) -> torch.Tensor:
        """Extract and L2-normalise CLIP image embeddings (transformers-version-safe)."""
        vision_out = self._model.vision_model(**inputs)
        feats      = self._model.visual_projection(vision_out.pooler_output)
        return F.normalize(feats, p=2, dim=-1)

    def _cache_text_features(self) -> None:
        """Pre-compute and L2-normalise CLIP text embeddings for all 101 classes."""
        prompts = [_PROMPT_TEMPLATE.format(cls=c) for c in FOOD101_CLASSES]
        inputs  = self._processor(text=prompts, return_tensors="pt",
                                  padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            self._text_features = self._get_text_features(inputs)  # (101, D)
        print(f"[FoodClassifier] Text embeddings cached for {len(FOOD101_CLASSES)} classes.")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, image: Image.Image, top_k: int = 3) -> list[dict]:
        """
        Classify a PIL Image via CLIP zero-shot and return top-k predictions.

        Args:
            image:  Input image (any PIL mode; converted to RGB internally).
            top_k:  Number of top predictions to return.

        Returns:
            List of {"class": str, "confidence": float} sorted by confidence desc.

        # TODO: replace with fine-tuned EfficientNet-B3 after running train_food101.py.
        """
        inputs = self._processor(
            images=image.convert("RGB"), return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            img_feat = self._get_image_features(inputs)  # (1, D), already normalised

        # Cosine similarity → softmax over 101 classes (×100 for sharper distribution)
        logits = (img_feat @ self._text_features.T)[0] * 100.0
        probs  = torch.softmax(logits, dim=0)

        top_probs, top_idx = torch.topk(probs, k=min(top_k, 101))
        return [
            {
                "class":      FOOD101_CLASSES[idx.item()],
                "confidence": round(top_probs[i].item(), 4),
            }
            for i, idx in enumerate(top_idx)
        ]
