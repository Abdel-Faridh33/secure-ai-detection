# Contexte du Projet : Secure AI Detection System

## 🎯 Vue d'ensemble du projet

Je travaille sur un **projet de mémoire de Master en Sécurité Informatique** sur le thème : "Sécurité des modèles d'intelligence artificielle dans les systèmes de maintien de l'ordre : vulnérabilités, menaces et méthodes de protection".

### Objectif principal
Créer une **preuve de concept (PoC)** démontrant la différence de robustesse entre :
1. **Modèle Baseline** : ResNet50 fine-tuné standard (vulnérable)
2. **Modèle Sécurisé** : ResNet50 avec défenses multicouches (robuste)

### Scénario d'application
**Détection d'objets dangereux vs sûrs** (classification binaire) :
- Classe 0 : `safe` (objets sûrs)
- Classe 1 : `dangerous` (objets dangereux)

## 📁 Structure du projet (déjà créée)

```
secure-ai-detection/
├── docker/                    # Environnement Docker complet
│   ├── Dockerfile.dev        # Dev avec tous les outils
│   ├── Dockerfile.baseline   # Production baseline
│   ├── Dockerfile.secured    # Production sécurisé
│   └── docker-compose.*.yml  # Orchestration
│
├── src/
│   ├── attacks/              # Modules d'attaque
│   │   ├── adversarial/     # FGSM, PGD, Patch attacks
│   │   ├── poisoning/       # Label flipping, Backdoor
│   │   └── extraction/      # Model stealing
│   │
│   ├── defenses/            # Mécanismes de défense
│   │   ├── training/        # Adversarial training, DP
│   │   ├── detection/       # Input filtering, Anomaly detection
│   │   └── mitigation/      # Input transformation, Ensemble
│   │
│   ├── evaluation/          # Métriques et comparaison
│   │   ├── metrics/         # Performance, Robustness, Fairness, Privacy
│   │   └── comparison/      # Baseline vs Secured
│   │
│   ├── experiments/         # Scripts d'expérimentation
│   │   ├── baseline/        # Train/Test/Attack baseline
│   │   ├── secured/         # Train/Test/Attack secured
│   │   └── comparative/     # Comparaison globale
│   │
│   └── api/                 # API FastAPI
│       └── endpoints/       # Baseline, Secured, Comparison
│
├── models/
│   ├── utils/               # model_loader.py, transfer_learning.py
│   ├── pretrained/          # ResNet50.pth téléchargé
│   ├── baseline/            # Modèle baseline entraîné
│   └── secured/             # Modèle sécurisé entraîné
│
├── data/
│   ├── raw/                 # Données brutes
│   ├── processed/           # Train/Val/Test splits
│   ├── poisoned/            # Données empoisonnées
│   └── adversarial/         # Exemples adversariaux
│
├── configs/                 # Configurations YAML
├── notebooks/               # Jupyter notebooks
├── tests/                   # Tests unitaires et intégration
└── results/                 # Résultats expérimentaux
```

## 🚀 État actuel du projet

### ✅ Ce qui est fait :
1. **Structure complète** du projet créée
2. **Environnement Docker** configuré (dev, test, prod)
3. **Squelettes de tous les modules** avec docstrings
4. **API FastAPI** basique fonctionnelle
5. **Configuration** complète (Docker, CI/CD, Makefile)

### ❌ Ce qui reste à implémenter :

#### **PRIORITÉ 1 - Core Modules** (à faire cette semaine) :

1. **`models/utils/model_loader.py`** - COMPLET
   - ✅ Méthode `load_resnet50()` de base existe
   - ❌ TODO: Ajouter `load_checkpoint()`, `save_model()`, gestion GPU/CPU

2. **`src/experiments/baseline/train_baseline.py`** - À IMPLÉMENTER
   ```python
   # Besoins :
   - DataLoader PyTorch pour charger data/processed/
   - Boucle d'entraînement complète avec validation
   - Métriques : accuracy, loss, F1
   - Sauvegarde checkpoints tous les 5 epochs
   - Support GPU optionnel (device agnostic)
   - Logging avec tqdm
   - Early stopping
   ```

3. **`src/attacks/adversarial/fgsm.py`** - À COMPLÉTER
   ```python
   # Structure existe, implémenter :
   - Méthode generate() complète
   - Support batch processing
   - Calcul epsilon adaptatif
   - Visualisation des perturbations
   ```

4. **`src/defenses/training/adversarial_training.py`** - À IMPLÉMENTER
   ```python
   # Besoins :
   - Intégration avec FGSMAttack
   - Mix 50/50 clean + adversarial
   - Loss combinée
   - Métriques de robustesse
   ```

5. **`src/evaluation/comparison/baseline_vs_secured.py`** - À IMPLÉMENTER
   ```python
   # Besoins :
   - Charger les 2 modèles
   - Comparer sur test set clean
   - Comparer sur adversarial examples
   - Calculer ASR (Attack Success Rate)
   - Générer tableau comparatif
   - Créer graphiques (matplotlib)
   ```

#### **PRIORITÉ 2 - Attaques complètes** :
- `pgd.py` : Implémenter PGD (iterative FGSM)
- `patch_attack.py` : Adversarial patches
- `label_flip.py` : Poison 10% des labels
- `backdoor.py` : Trigger pattern insertion

#### **PRIORITÉ 3 - Défenses avancées** :
- `differential_privacy.py` : Avec Opacus
- `input_filter.py` : Détection statistique
- `ensemble_defense.py` : Vote majoritaire

## 🔧 Stack Technique

### Environnement
- **Python 3.9** (dans Docker)
- **Docker** + **Docker Compose** pour tout
- **100% conteneurisé** - Pas d'installation locale

### Libraries principales
```python
torch==2.0.1          # Deep Learning
torchvision==0.15.2   # Vision, ResNet50
numpy==1.24.3         # Calcul numérique
pandas==2.0.3         # Données tabulaires
scikit-learn==1.3.0   # Métriques ML
opencv-python==4.8.0  # Traitement d'images
fastapi==0.100.0      # API REST
opacus==1.4.0         # Differential Privacy
foolbox==3.3.3        # Librairie d'attaques (optionnel)
matplotlib==3.7.2     # Graphiques
seaborn==0.12.2       # Visualisations statistiques
```

### Modèle de base
- **ResNet50** pré-entraîné sur ImageNet
- **Transfer Learning** : On ne fine-tune que la dernière couche FC
- **Input size** : 224x224x3
- **Output** : 2 classes (dangerous, safe)

## 📊 Dataset

### Structure actuelle
```
data/processed/
├── train/
│   ├── dangerous/  (35 images)
│   └── safe/       (35 images)
├── val/
│   ├── dangerous/  (7 images)
│   └── safe/       (7 images)
└── test/
    ├── dangerous/  (8 images)
    └── safe/       (8 images)
```

### Format
- Images synthétiques 224x224 RGB
- `dangerous` : Triangles rouges
- `safe` : Cercles verts
- Annotations dans `data/processed/annotations.json`

## 🎯 Métriques à implémenter

### Performance
- **Accuracy** : Classification correcte
- **Precision/Recall/F1** : Par classe
- **Confusion Matrix** : Visualisation

### Robustesse
- **ASR (Attack Success Rate)** : % d'attaques réussies
- **Robust Accuracy** : Accuracy sur adversarial examples
- **Perturbation moyenne** : Epsilon moyen nécessaire

### Comparaison Baseline vs Secured
```python
# Résultats attendus (approximatifs)
results = {
    "baseline": {
        "clean_accuracy": 0.92,
        "robust_accuracy": 0.15,
        "asr_fgsm": 0.73,
        "asr_pgd": 0.85
    },
    "secured": {
        "clean_accuracy": 0.90,  # Légère baisse
        "robust_accuracy": 0.75,  # Grande amélioration
        "asr_fgsm": 0.12,        # Forte réduction
        "asr_pgd": 0.24          # Forte réduction
    }
}
```

## 📝 Conventions de code

### Style
- **PEP 8** pour Python
- **Type hints** partout où possible
- **Docstrings Google style**
- **Comments** en français OK (projet académique français)

### Structure d'un module type
```python
"""
Module Description
Référence: Paper et al., 2024 - https://arxiv.org/...
"""

import torch
import torch.nn as nn
from typing import Optional, Tuple, Dict

class ModuleName:
    """Description de la classe."""
    
    def __init__(self, param: float = 0.1):
        """
        Args:
            param: Description du paramètre
        """
        self.param = param
    
    def method(self, x: torch.Tensor) -> torch.Tensor:
        """
        Description de la méthode.
        
        Args:
            x: Input tensor [batch_size, channels, height, width]
            
        Returns:
            Output tensor
        """
        # Implémentation
        pass
```

### Tests
- Utiliser **pytest**
- Un test minimum par méthode publique
- Mock pour les dépendances externes

## 🚀 Commandes Docker disponibles

```bash
# Développement
make dev          # Lance environnement complet
make shell        # Ouvre shell dans container
make notebook     # Lance Jupyter Lab

# Entraînement
make train-baseline  # Entraîne modèle baseline
make train-secured   # Entraîne modèle sécurisé

# Tests
make test           # Lance tous les tests
make test-attacks   # Teste les attaques

# Production
make prod           # Lance en production
```

## 📌 Workflow d'implémentation recommandé

1. **Commencer par `train_baseline.py`**
   - C'est la base de tout
   - Permet de valider le pipeline data → model → training
   
2. **Puis `fgsm.py` attack**
   - Attaque la plus simple
   - Permet de tester la vulnérabilité

3. **Ensuite `adversarial_training.py`**
   - Intègre FGSM dans l'entraînement
   - Crée le modèle sécurisé

4. **Finir par `baseline_vs_secured.py`**
   - Compare les deux modèles
   - Génère les métriques finales

## ⚠️ Points d'attention

1. **Pas de GPU obligatoire** : Code doit fonctionner sur CPU
2. **Dataset petit** : 100 images total, donc overfitting attendu (c'est OK pour PoC)
3. **Docker obligatoire** : Tout doit tourner dans les containers
4. **Checkpoints** : Sauvegarder régulièrement dans `models/`
5. **Logs** : Utiliser `print()` ou `logging`, visible dans `docker logs`

## 🎯 Objectif final

Démontrer par l'expérimentation que :
1. **Le modèle baseline est vulnérable** aux attaques adversariales
2. **L'adversarial training améliore significativement la robustesse**
3. **Il y a un trade-off** entre accuracy et robustesse
4. **La méthode est reproductible** et bien documentée

## 📚 Références importantes

- Goodfellow et al., 2014 - FGSM : https://arxiv.org/abs/1412.6572
- Madry et al., 2018 - PGD : https://arxiv.org/abs/1706.06083
- Papernot et al., 2016 - Adversarial Training
- Document "Cahier de charges.docx" pour les exigences académiques

---

**DEMANDE ACTUELLE** : Implémenter les modules prioritaires en commençant par `train_baseline.py`, puis `fgsm.py`, puis `adversarial_training.py`, et enfin la comparaison. Chaque module doit être fonctionnel et testable indépendamment.