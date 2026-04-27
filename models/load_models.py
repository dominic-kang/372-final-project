"""
Standalone model loader and inference script for DukeMacros.

Demonstrates how to load and run both models outside the FastAPI server:
  - CLIP ViT-B/32 zero-shot classifier (active, no training required)
  - EfficientNet-B3 fine-tuned classifier (requires checkpoint from train_food101.py)

Usage
-----
    # Classify an image with CLIP (zero-shot, always works):
    python models/load_models.py --image docs/examples/pizza.jpeg

    # Classify with fine-tuned EfficientNet (after running train_food101.py):
    python models/load_models.py --image docs/examples/pizza.jpeg --model efficientnet

Run from the repo root with the backend venv active:
    source src/backend/.venv/bin/activate
    python models/load_models.py --image docs/examples/hamburger.jpeg
"""
import argparse
import os
import time

import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# ---------------------------------------------------------------------------
# Food-101 class labels (alphabetical, matches torchvision dataset indexing)
# ---------------------------------------------------------------------------
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

_PROMPT_TEMPLATE = "a photo of {cls}, a type of food"
_CKPT_PATH       = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "food101_efficientnet_b3.pth")

# ---------------------------------------------------------------------------
# CLIP ViT-B/32 zero-shot loader
# ---------------------------------------------------------------------------

def load_clip(device: torch.device) -> tuple:
    """
    Load CLIP ViT-B/32 and pre-cache text embeddings for all 101 Food-101 classes.

    Returns:
        (processor, model, text_features)
        text_features: (101, 512) L2-normalised tensor, one vector per food class.
    """
    print("Loading CLIP ViT-B/32 ...")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    model.eval()

    prompts  = [_PROMPT_TEMPLATE.format(cls=c) for c in FOOD101_CLASSES]
    txt_in   = processor(text=prompts, return_tensors="pt",
                         padding=True, truncation=True).to(device)
    with torch.no_grad():
        txt_out  = model.text_model(**txt_in)
        txt_feat = F.normalize(
            model.text_projection(txt_out.pooler_output), p=2, dim=-1
        )
    print(f"  CLIP loaded on {device}. Text embeddings cached: {txt_feat.shape}")
    return processor, model, txt_feat


def predict_clip(image_path: str, processor, model, text_features,
                 device: torch.device, top_k: int = 3) -> list[dict]:
    """
    Zero-shot classify an image with CLIP.

    Steps:
      1. Encode image through CLIP vision encoder.
      2. L2-normalise → cosine similarity against cached (101, 512) text features.
      3. Temperature-scaled softmax (×100) → top-k.

    Returns:
        List of {'class': str, 'confidence': float} sorted desc.
    """
    img    = Image.open(image_path).convert("RGB")
    img_in = processor(images=img, return_tensors="pt").to(device)

    with torch.no_grad():
        vis_out  = model.vision_model(**img_in)
        img_feat = F.normalize(
            model.visual_projection(vis_out.pooler_output), p=2, dim=-1
        )
        logits = (img_feat @ text_features.T)[0] * 100.0
        probs  = torch.softmax(logits, dim=0)

    top_probs, top_idx = torch.topk(probs, k=min(top_k, 101))
    return [
        {"class": FOOD101_CLASSES[i.item()], "confidence": round(top_probs[j].item(), 4)}
        for j, i in enumerate(top_idx)
    ]


# ---------------------------------------------------------------------------
# EfficientNet-B3 fine-tuned loader
# ---------------------------------------------------------------------------

def load_efficientnet(checkpoint_path: str, device: torch.device):
    """
    Load a fine-tuned EfficientNet-B3 checkpoint produced by train_food101.py.

    Args:
        checkpoint_path: Path to .pth file (default: models/food101_efficientnet_b3.pth).
        device: Torch device.

    Returns:
        model in eval mode, or None if checkpoint not found.
    """
    from torchvision import models as tv_models

    if not os.path.exists(checkpoint_path):
        print(f"  Checkpoint not found: {checkpoint_path}")
        print("  Run models/train_food101.py to produce the checkpoint (~2-4h on T4 GPU).")
        return None

    print(f"Loading EfficientNet-B3 from {checkpoint_path} ...")
    model = tv_models.efficientnet_b3(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 101)
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.to(device).eval()
    print(f"  EfficientNet-B3 loaded on {device}.")
    return model


def predict_efficientnet(image_path: str, model, device: torch.device,
                         top_k: int = 3) -> list[dict]:
    """
    Classify an image with fine-tuned EfficientNet-B3.

    Returns:
        List of {'class': str, 'confidence': float} sorted desc.
    """
    from torchvision import transforms

    tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    img    = Image.open(image_path).convert("RGB")
    tensor = tf(img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs  = torch.softmax(logits, dim=1)[0]

    top_probs, top_idx = torch.topk(probs, k=top_k)
    return [
        {"class": FOOD101_CLASSES[i.item()], "confidence": round(top_probs[j].item(), 4)}
        for j, i in enumerate(top_idx)
    ]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DukeMacros model inference")
    parser.add_argument("--image",  required=True, help="Path to food image")
    parser.add_argument("--model",  default="clip",
                        choices=["clip", "efficientnet"],
                        help="Which model to use (default: clip)")
    parser.add_argument("--top-k",  type=int, default=3,
                        help="Number of top predictions to show")
    parser.add_argument("--ckpt",   default=_CKPT_PATH,
                        help="EfficientNet checkpoint path")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}\n")

    if args.model == "clip":
        processor, clip_model, text_feat = load_clip(device)
        t0    = time.perf_counter()
        preds = predict_clip(args.image, processor, clip_model, text_feat,
                             device, top_k=args.top_k)
        ms = (time.perf_counter() - t0) * 1000
        print(f"\nCLIP ViT-B/32 predictions for '{args.image}'  ({ms:.0f} ms):")

    else:
        effnet = load_efficientnet(args.ckpt, device)
        if effnet is None:
            raise SystemExit(1)
        t0    = time.perf_counter()
        preds = predict_efficientnet(args.image, effnet, device, top_k=args.top_k)
        ms = (time.perf_counter() - t0) * 1000
        print(f"\nEfficientNet-B3 predictions for '{args.image}'  ({ms:.0f} ms):")

    for rank, p in enumerate(preds, 1):
        print(f"  {rank}. {p['class']:<30s}  confidence={p['confidence']:.4f}")
