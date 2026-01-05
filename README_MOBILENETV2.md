# 🛡️ Secure AI Detection - MobileNetV2 Edition

**Détection d'objets dangereux résistante aux attaques adversariales**

Version améliorée avec architecture MobileNetV2 et métriques réalistes.

---

## 📋 Vue d'ensemble

Ce projet compare deux approches pour la classification d'objets dangereux:

1. **Baseline**: MobileNetV2 standard avec transfer learning
2. **Secured**: MobileNetV2 + TRADES (adversarial training)

### 🎯 Objectifs

- Classifier des images en "safe" ou "dangerous"
- Résister aux attaques adversariales (FGSM, PGD)
- Obtenir des métriques réalistes et reproductibles
- Documenter le trade-off accuracy/robustness

---

## 🏗️ Architecture

### Baseline
- **Modèle**: MobileNetV2 pré-entraîné (ImageNet)
- **Paramètres**: 3.5M (vs 25.6M pour ResNet50)
- **Techniques**:
  - Transfer learning (freeze early layers)
  - Dropout (0.3)
  - Early stopping
  - Learning rate scheduling
  - Data augmentation

### Secured
- **Modèle**: MobileNetV2 + TRADES
- **Adversarial Training**: PGD-based
- **Paramètres**: 3.5M + régularisation renforcée
- **Techniques**:
  - Toutes celles du baseline
  - TRADES loss (β=6.0)
  - KL divergence regularization
  - Adversarial examples generation

---

## 📊 Dataset

### Source
- **Classe dangerous**: 333 images (Guns Dataset)
- **Classe safe**: Générées par transformations (temporaire)
  - ⚠️ Pour production: utiliser COCO ou OpenImages

### Augmentation
- Target: 1000 images par classe
- Techniques:
  - Random crop, flip, rotation
  - Color jitter
  - Affine transformations
  - Perspective distortion

### Split
- **Train**: 70% (~1400 images)
- **Validation**: 15% (~300 images)
- **Test**: 15% (~300 images)

---

## 🚀 Installation

### Prérequis
```bash
# Python 3.8+
python --version

# Vérifier CUDA (optionnel, pour GPU)
python -c "import torch; print(torch.cuda.is_available())"
```

### Installation des dépendances
```bash
pip install torch torchvision
pip install numpy pillow
pip install scikit-learn scipy
pip install matplotlib seaborn
pip install tqdm
```

---

## 📁 Structure du Projet

```
AA-secure-ai-detection/
├── data/
│   ├── prepare_dataset.py      # Préparation du dataset
│   └── prepared/                # Dataset final (généré)
│       ├── train/
│       ├── val/
│       └── test/
│
├── raw/
│   └── Images/                  # 333 images guns (source)
│
├── src/
│   └── experiments/
│       ├── baseline/
│       │   └── train_mobilenet.py         # Entraînement baseline
│       ├── secured/
│       │   └── train_mobilenet_secured.py # Entraînement secured
│       └── comparative/
│           └── evaluate_models.py          # Évaluation comparative
│
├── models/                      # Modèles entraînés (généré)
│   ├── baseline_mobilenet/
│   └── secured/
│
├── results/                     # Résultats et graphiques (généré)
│   └── comparative/
│
├── run_full_pipeline.py         # Pipeline automatique
└── README_MOBILENETV2.md        # Ce fichier
```

---

## 🎯 Utilisation

### Option 1: Pipeline Automatique (Recommandé)

Exécuter tout le pipeline de A à Z:

```bash
python run_full_pipeline.py
```

Étapes individuelles:

```bash
# Seulement préparer le dataset
python run_full_pipeline.py --step dataset

# Seulement entraîner baseline
python run_full_pipeline.py --step baseline

# Seulement entraîner secured
python run_full_pipeline.py --step secured

# Seulement évaluer
python run_full_pipeline.py --step evaluate

# Pipeline complet mais réutiliser le dataset existant
python run_full_pipeline.py --skip-dataset
```

### Option 2: Exécution Manuelle

#### 1. Préparer le dataset
```bash
python data/prepare_dataset.py
```

**Sortie**:
- `data/prepared/train/`, `val/`, `test/`
- `data/prepared/dataset_stats.json`

#### 2. Entraîner le modèle baseline
```bash
python src/experiments/baseline/train_mobilenet.py
```

**Sortie**:
- `models/baseline/best_model.pth`
- `models/baseline/training_history.png`

#### 3. Entraîner le modèle secured
```bash
python src/experiments/secured/train_mobilenet_secured.py
```

**Sortie**:
- `models/secured/best_model.pth`
- `models/secured/training_history.png`

#### 4. Évaluer et comparer
```bash
python src/experiments/comparative/evaluate_models.py
```

**Sortie**:
- `results/comparative/evaluation_report.txt`
- `results/comparative/results.json`
- `results/comparative/comparative_plots.png`

---

## 📈 Résultats Attendus

### Métriques Réalistes

| Métrique | Baseline | Secured | Amélioration |
|----------|----------|---------|--------------|
| **Clean Accuracy** | 85-92% | 83-90% | -2 à -5% |
| **ASR FGSM** (ε=8/255) | 60-75% | 10-20% | -50 à -60% |
| **ASR PGD** (ε=8/255) | 70-85% | 20-35% | -50 à -55% |

### Interprétation

- **Clean Accuracy**: Légère baisse pour le modèle secured (trade-off)
- **ASR** (Attack Success Rate): Taux d'images où l'attaque réussit
  - Plus bas = meilleur (plus robuste)
  - Le modèle secured devrait avoir un ASR ~50% plus bas

### Trade-off Accuracy/Robustness

Le modèle secured sacrifie 2-5% d'accuracy sur données propres pour gagner 50-60% de robustness aux attaques.

---

## 🔬 Détails Techniques

### TRADES Loss

```
L_total = L_classification + β × L_robustness

L_classification = CrossEntropy(f(x_natural), y)
L_robustness = KL(f(x_natural) || f(x_adv))
```

**Paramètres**:
- β = 6.0 (trade-off parameter)
- ε = 8/255 (perturbation max)
- PGD: 10 iterations, α = 2/255

### Régularisation

- **Dropout**: 0.3 (baseline), 0.4 (secured)
- **Weight decay**: 1e-4
- **Batch Normalization**: Secured uniquement
- **Early stopping**: patience=10 epochs
- **Learning rate scheduling**: ReduceLROnPlateau

### Attaques Adversariales

**FGSM** (Fast Gradient Sign Method):
```
x_adv = x + ε × sign(∇_x L(x, y))
```

**PGD** (Projected Gradient Descent):
```
x_adv^(t+1) = Π_{||δ||_∞≤ε} (x_adv^(t) + α × sign(∇_x L(x_adv^(t), y)))
```

---

## 📊 Métriques d'Évaluation

### Clean Performance
- Accuracy, Precision, Recall, F1-score
- AUC-ROC
- Confusion Matrix
- Intervalles de confiance (95%)

### Adversarial Robustness
- Attack Success Rate (ASR)
- Robust Accuracy
- Robustness Drop

### Tests Statistiques
- McNemar's test (paired comparison)
- p-value < 0.05 pour significativité

---

## 🐛 Dépannage

### Dataset trop petit
```
⚠️ Seulement X images trouvées
```
**Solution**: Vérifier que `raw/Images/` contient bien les images

### Out of Memory (GPU)
```
CUDA out of memory
```
**Solution**: Réduire `batch_size` dans les scripts d'entraînement

### Encodage Windows
```
UnicodeEncodeError
```
**Solution**: Scripts déjà corrigés avec encodage UTF-8

### Entraînement trop lent
**CPU**: ~2-4h par modèle
**GPU**: ~30-60min par modèle

**Solution**: Utiliser un GPU si disponible

---

## 📚 Références

### Papers
1. **MobileNetV2**: Sandler et al. (2018)
   - "Inverted Residuals and Linear Bottlenecks"

2. **TRADES**: Zhang et al. (2019)
   - "Theoretically Principled Trade-off between Robustness and Accuracy"

3. **PGD Attack**: Madry et al. (2018)
   - "Towards Deep Learning Models Resistant to Adversarial Attacks"

4. **Adversarial Examples**: Goodfellow et al. (2015)
   - "Explaining and Harnessing Adversarial Examples"

### Datasets
- **Guns Dataset**: Dataset public d'images d'armes à feu
- **COCO**: Common Objects in Context (recommandé pour classe "safe")

---

## 🎓 Contexte Académique

Ce projet démontre:
- ✅ Trade-off accuracy/robustness
- ✅ Efficacité de l'adversarial training
- ✅ Importance du choix d'architecture
- ✅ Métriques d'évaluation robustes
- ✅ Reproductibilité scientifique

### Améliorations par rapport à la version précédente
1. **Dataset**: 100 → 2000 images
2. **Architecture**: ResNet50 (25.6M) → MobileNetV2 (3.5M)
3. **Résultats**: 100% → 85-90% (réaliste)
4. **Métriques**: Basiques → Complètes + tests statistiques
5. **Régularisation**: Minimale → Complète (dropout, early stopping, etc.)

---

## 📝 TODO / Améliorations Futures

### Court terme
- [ ] Remplacer classe "safe" par vraies images (COCO)
- [ ] Ajouter AutoAttack pour évaluation robuste
- [ ] Cross-validation K-fold
- [ ] Ensembling de modèles

### Long terme
- [ ] Certified defense (randomized smoothing)
- [ ] Détection d'attaques adversariales
- [ ] Explainability (Grad-CAM)
- [ ] Déploiement API REST

---

## 👥 Auteur

Projet de mémoire - Détection d'objets dangereux sécurisée

---

## 📄 Licence

Projet académique - Usage éducatif uniquement

---

## 🆘 Support

En cas de problème:
1. Vérifier les prérequis
2. Consulter la section Dépannage
3. Vérifier les logs d'erreur
4. Contacter l'auteur

---

**Note**: Ce README correspond à la version MobileNetV2 du projet.
Pour l'ancienne version (ResNet50), consulter l'historique git.
