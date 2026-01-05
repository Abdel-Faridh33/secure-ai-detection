# Guide Google Colab - Training Models

Ce guide couvre l'entraînement sur Google Colab pour **deux notebooks**:
1. **Baseline** - Entraînement standard
2. **Secured** - Entraînement sécurisé avec Zone 1 & Zone 2

---

## 📓 Notebook 1: Baseline (Standard)

### 🚀 Quick Start (5 étapes)

#### 1. Préparer le ZIP
```bash
python scripts/prepare_colab_dataset.py
```
Crée `prepared.zip` avec la structure correcte.

#### 2. Ouvrir Colab
- Aller sur [colab.research.google.com](https://colab.research.google.com)
- Upload `notebooks/train_baseline_colab.ipynb`

#### 3. Activer GPU
Runtime > Change runtime type > **GPU** > Save

#### 4. Upload Dataset
- Exécuter cellule d'upload
- Sélectionner `prepared.zip` (~5-10 min)

**Alternative**: Uploader sur Google Drive puis monter Drive dans Colab

#### 5. Lancer Training
Runtime > Run all (~40 min)

### 📥 Récupération Résultats

Le notebook génère `baseline_results.zip` contenant:
- `best_model.pth` - Meilleur modèle
- `final_model.pth` - Modèle final
- `training_history.json` - Métriques
- `training_history.png` - Graphiques

**Import local**:
```bash
unzip baseline_results.zip -d models/baseline/
```

### ⏱️ Temps Estimés
- Upload: 5-10 min
- Training (GPU): 30-45 min
- **Total**: ~50 min

---

## 🔒 Notebook 2: Secured (Zone 1 & Zone 2)

### 🚀 Quick Start (6 étapes)

#### 1. Préparer les fichiers
```bash
python scripts/prepare_colab_dataset.py
```
Crée `prepared.zip` + Vérifier que `notebooks/security_modules_colab.py` existe

#### 2. Ouvrir Colab
- Aller sur [colab.research.google.com](https://colab.research.google.com)
- Upload `notebooks/train_secured_colab.ipynb`

#### 3. Activer GPU
Runtime > Change runtime type > **GPU** > Save

#### 4. Upload Module de Sécurité
**IMPORTANT**: À la cellule d'upload du module, sélectionner:
- `notebooks/security_modules_colab.py`

Ce module contient toutes les classes de sécurité Zone 1 & Zone 2.

#### 5. Upload Dataset
- Exécuter cellule d'upload
- Sélectionner `prepared.zip` (~5-10 min)

**Alternative**: Uploader sur Google Drive puis monter Drive dans Colab

#### 6. Lancer Training Sécurisé
Runtime > Run all (~50 min)

### 🛡️ Mesures de Sécurité Appliquées

Le notebook sécurisé intègre automatiquement:

**Zone 1 - Sécurité des Données**:
- ✅ Vérification statistique (DataVerifier)
- ✅ Détection d'empoisonnement (PoisoningDetector)
- ✅ Quarantaine automatique des échantillons suspects

**Zone 2 - Entraînement Sécurisé**:
- ✅ Adversarial Training (70% clean + 30% FGSM)
- ✅ Differential Privacy (optionnel)
- ✅ Chiffrement AES-256-GCM des modèles
- ✅ Signatures numériques RSA-4096
- ✅ Early Stopping (patience=8)

### 📥 Récupération Résultats

Le notebook génère `secured_results.zip` contenant:

**Modèles**:
- `best_secured_model.pth` - Meilleur modèle
- `best_secured_model_encrypted.enc` - Modèle chiffré (AES-256-GCM)
- `best_secured_model_signature.bin` - Signature RSA-4096
- `best_secured_model_public_key.pem` - Clé publique
- `best_secured_model_private_key.pem` - Clé privée (🔐 PROTÉGÉE)

**Quarantaine (Zone 1)**:
- `quarantine/train_TIMESTAMP/` - Images suspectes isolées
- `quarantine/train_TIMESTAMP/report.json` - Rapport de détection

**Résultats**:
- `training_history.json` - Métriques
- `training_history.png` - Graphiques

**Import local**:
```bash
unzip secured_results.zip -d models/secured/
```

### ⏱️ Temps Estimés
- Upload module: 1 min
- Upload dataset: 5-10 min
- Training sécurisé (GPU): 45-60 min
- **Total**: ~60-70 min

---

## 🆘 Dépannage

| Problème | Solution |
|----------|----------|
| GPU not available | Runtime > Change runtime type > GPU |
| Out of memory | Réduire `BATCH_SIZE` à 16 |
| Upload lent | Utiliser Google Drive |
| Structure incorrecte | Vérifier `prepared/` à la racine du ZIP |
| Module sécurité non trouvé | Uploader `security_modules_colab.py` depuis `notebooks/` |
| Erreur chiffrement | Vérifier installation cryptography (`pip install cryptography`) |

---

## 📊 Comparaison Notebooks

| Caractéristique | Baseline | Secured |
|-----------------|----------|---------|
| **Architecture** | MobileNetV2 | MobileNetV2 |
| **Sécurité données** | ❌ | ✅ Zone 1 complète |
| **Adversarial Training** | ❌ | ✅ FGSM optimisé |
| **Chiffrement** | ❌ | ✅ AES-256-GCM |
| **Signatures** | ❌ | ✅ RSA-4096 |
| **Quarantaine** | ❌ | ✅ Automatique |
| **Clean Accuracy** | ~96% | ~91-93% |
| **Robustesse FGSM** | ~50% | ~75-82% |
| **Temps training** | ~40 min | ~50 min |

---

## 📝 Notebooks Disponibles

- `train_baseline_colab.ipynb` - Entraînement standard
- `train_secured_colab.ipynb` - Entraînement sécurisé (Zone 1 & Zone 2)

**Script de préparation**: `scripts/prepare_colab_dataset.py`
