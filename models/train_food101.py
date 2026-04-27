"""
Fine-tune EfficientNet-B3 on Food-101.

Why this is needed
------------------
The current active classifier uses CLIP zero-shot (~70-75 % top-1).
Fine-tuning EfficientNet-B3 on Food-101 achieves ~85 % top-1 and is
significantly faster at inference (~30 ms vs ~80 ms on CPU).

After this script finishes, swap the classifier in src/backend/src/classifier.py:
  - Uncomment the EfficientNet block in _load_model()
  - Comment out the CLIP block

Usage
-----
Run from the repo root with the backend venv active:
    cd models
    python train_food101.py [--epochs 10] [--batch 32] [--lr 1e-4]

Hardware
--------
- GPU (T4/A100 in Colab): ~2-4 h for 10 epochs
- CPU only:               not recommended (days)

Dataset
-------
torchvision.datasets.Food101 downloads ~5 GB to ~/.torchvision/datasets/food-101/
on first run. Subsequent runs use the local cache.
"""
import argparse
import os
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models, transforms
from torchvision.datasets import Food101

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--epochs",     type=int,   default=10)
parser.add_argument("--batch",      type=int,   default=32)
parser.add_argument("--lr",         type=float, default=1e-4)
parser.add_argument("--data-dir",   type=str,   default=os.path.expanduser("~/.torchvision/datasets"))
parser.add_argument("--output",     type=str,   default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "food101_efficientnet_b3.pth"))
args = parser.parse_args()

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")

os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
os.makedirs(args.data_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
_MEAN = [0.485, 0.456, 0.406]
_STD  = [0.229, 0.224, 0.225]

train_tf = transforms.Compose([
    transforms.Resize(256),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize(_MEAN, _STD),
])

val_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(_MEAN, _STD),
])

print("Downloading / loading Food-101 dataset …")
train_ds = Food101(root=args.data_dir, split="train", transform=train_tf, download=True)
val_ds   = Food101(root=args.data_dir, split="test",  transform=val_tf,   download=True)
print(f"  Train: {len(train_ds):,} images  |  Val: {len(val_ds):,} images")

train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                          num_workers=4, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=args.batch, shuffle=False,
                          num_workers=4, pin_memory=True)

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)
in_features = model.classifier[1].in_features
model.classifier[1] = nn.Linear(in_features, 101)
model = model.to(DEVICE)

# Freeze backbone for the first 2 epochs, then unfreeze
def set_backbone_grad(requires_grad: bool):
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = requires_grad

set_backbone_grad(False)  # warmup: only train head

optimizer = torch.optim.AdamW(
    filter(lambda p: p.requires_grad, model.parameters()),
    lr=args.lr,
)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
best_val_acc = 0.0

for epoch in range(1, args.epochs + 1):
    # Unfreeze backbone after warmup
    if epoch == 3:
        set_backbone_grad(True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr * 0.1)
        print("  [epoch 3] Backbone unfrozen — full fine-tune at lr=", args.lr * 0.1)

    # Train
    model.train()
    train_loss, train_correct, n = 0.0, 0, 0
    t0 = time.time()
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        loss = criterion(model(imgs), labels)
        loss.backward()
        optimizer.step()
        train_loss    += loss.item() * imgs.size(0)
        train_correct += (model(imgs).argmax(1) == labels).sum().item()
        n             += imgs.size(0)

    scheduler.step()

    # Validate
    model.eval()
    val_correct, val_total = 0, 0
    top3_correct = 0
    with torch.no_grad():
        for imgs, labels in val_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            logits = model(imgs)
            val_correct  += (logits.argmax(1) == labels).sum().item()
            top3_preds    = logits.topk(3, dim=1).indices
            top3_correct += (top3_preds == labels.unsqueeze(1)).any(dim=1).sum().item()
            val_total    += imgs.size(0)

    top1 = val_correct  / val_total
    top3 = top3_correct / val_total
    print(f"Epoch {epoch:>2}/{args.epochs}  "
          f"loss={train_loss/n:.3f}  top-1={top1:.3%}  top-3={top3:.3%}  "
          f"({time.time()-t0:.0f}s)")

    if top1 > best_val_acc:
        best_val_acc = top1
        torch.save(model.state_dict(), args.output)
        print(f"  ✓ Saved best model → {args.output}  (top-1={top1:.3%})")

print(f"\nTraining complete. Best val top-1: {best_val_acc:.3%}")
print(f"Checkpoint: {args.output}")
print()
print("Next steps:")
print("  1. Checkpoint is saved to models/food101_efficientnet_b3.pth (repo root).")
print("  2. In src/backend/src/classifier.py, comment out the CLIP block")
print("     in _load_model() and uncomment the EfficientNet block.")
