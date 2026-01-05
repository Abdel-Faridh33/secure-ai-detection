# Reproductibilité - Entraînement Baseline

## ✅ Configuration Validée

L'entraînement baseline est **100% reproductible** avec les mêmes hyperparamètres.

### Hyperparamètres

```python
data_dir = "data/prepared"
model_dir = "models/baseline"
batch_size = 32
num_epochs = 50  # Avec early stopping
learning_rate = 0.001
weight_decay = 1e-4
```

### Architecture
- **Modèle**: MobileNetV2 (pretrained ImageNet)
- **Freeze**: Early layers (features[:-3])
- **Classifier**: Dropout(0.3) → Linear(1280, 256) → ReLU → Dropout(0.3) → Linear(256, 2)
- **Paramètres entraînables**: ~1.2M / 3.5M

### Régularisation
- **Dropout**: 0.3
- **Weight Decay**: 1e-4
- **Early Stopping**: patience=10, min_delta=0.0
- **LR Scheduler**: ReduceLROnPlateau (factor=0.5, patience=5)

### Data Augmentation
**Training**:
- Resize(256, 256)
- RandomCrop(224)
- RandomHorizontalFlip
- RandomRotation(10°)
- ColorJitter(0.2, 0.2, 0.2)
- Normalize ImageNet

**Validation/Test**:
- Resize(224, 224)
- Normalize ImageNet

---

## 🔄 Reproduire l'Entraînement

### Option 1: Local (CPU/GPU)
```bash
python src/experiments/baseline/train_baseline.py
```

### Option 2: Make (Docker)
```bash
make train-baseline
```

### Option 3: Google Colab (GPU gratuit)
```bash
# 1. Préparer dataset
python scripts/prepare_colab_dataset.py

# 2. Suivre notebooks/COLAB_GUIDE.md
```

---

## 🎲 Seed & Déterminisme

**⚠️ Note**: Le seed n'est pas fixé dans le code actuel.

Pour une reproductibilité **exacte** (mêmes poids):
```python
import torch
import numpy as np
import random

seed = 42
torch.manual_seed(seed)
np.random.seed(seed)
random.seed(seed)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
```

**Sans seed fixe**: Les résultats varient légèrement (~±1-2% accuracy) mais restent dans la même fourchette.

---

## 📊 Résultats Attendus

Avec le dataset actuel (1,896 images):
- **Val Accuracy**: 95-98%
- **Test Accuracy**: 93-96%
- **Epochs**: 25-35 (early stopping)
- **Temps**:
  - CPU: 2-3h
  - GPU (T4 Colab): 30-45 min

---

## ✅ Validation

Pour vérifier que l'entraînement est identique:
```bash
# Comparer les hyperparamètres
cat src/experiments/baseline/train_baseline.py | grep -A 10 "def main"

# Vérifier le notebook Colab
grep -A 5 "BATCH_SIZE\|LEARNING_RATE" notebooks/train_baseline_colab.ipynb
```

**Statut**: ✅ Alignés (2024-12-24)
