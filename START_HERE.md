# 🚀 START HERE - Guide Complet

**Tout ce dont vous avez besoin pour démarrer le projet**

---

## ⚡ Démarrage Ultra-Rapide (3 étapes)

### 1. Télécharger Images "Safe" (15 min)

Allez sur https://pixabay.com/ et téléchargez ~333 images de:
- Chaises, tables, laptops, téléphones, bouteilles, livres, etc.

Placez-les dans: `data/coco_safe/`

**Détail**: Ces images seront utilisées comme classe "safe" (non-dangereuse).

### 2. Préparer le Dataset (5 min)

```bash
python data/prepare_dataset.py
```

Vérifiez le message: `✅ Utilisation de VRAIES images safe depuis COCO`

### 3. Entraîner (2-3h GPU / 7-13h CPU)

```bash
python run_full_pipeline.py --skip-dataset
```

**C'est tout !** Les résultats seront dans `results/comparative/`

---

## 📊 État du Projet

### ✅ Prêt
- Scripts d'entraînement (baseline + secured MobileNetV2)
- Pipeline automatisé
- Documentation

### ⏳ En Attente
- **Images "safe" à télécharger** (étape 1 ci-dessus)
- Dataset à préparer (étape 2)
- Entraînement à lancer (étape 3)

### 🧹 Nettoyé
- Ancien dataset (images transformées) supprimé
- Anciens modèles supprimés
- Prêt pour nouveau départ

---

## ❓ Pourquoi Télécharger des Images ?

**Problème**: L'ancien dataset utilisait des **armes transformées** comme classe "safe"
- Images floues, déformées
- Pas valide scientifiquement

**Solution**: Télécharger de **vraies** images d'objets sûrs
- Chaises, laptops, bouteilles, etc.
- Résultats scientifiquement valides

---

## 📁 Où Télécharger les Images ?

### Option 1: Pixabay (Recommandé) ⭐

1. https://pixabay.com/
2. Recherchez: "chair", "laptop", "bottle", "book", etc.
3. Téléchargez ~333 images au total
4. Placez dans `data/coco_safe/`

### Option 2: Kaggle Dataset (Automatique) ⭐

**Le plus rapide si vous avez un compte Kaggle !**

```bash
# Installer API Kaggle
pip install kaggle

# Configurer (une seule fois):
# 1. Allez sur https://www.kaggle.com/settings
# 2. Cliquez "Create New Token" (section API)
# 3. Placez kaggle.json dans C:\Users\<vous>\.kaggle\

# Télécharger automatiquement
python data/download_kaggle_safe.py
```

Le script télécharge automatiquement un dataset d'objets courants (bouteilles, chaises, laptops, etc.)

### Option 3: Script COCO (Avancé)

```bash
pip install pycocotools
python data/download_coco_safe.py
```

---

## 🔍 Vérifications

### Images bien placées ?

```bash
# Dossier existe ?
powershell -Command "Test-Path data\coco_safe"
# Doit retourner: True

# Combien d'images ?
powershell -Command "(Get-ChildItem data\coco_safe -Filter *.jpg).Count"
# Doit retourner: ~333
```

### Dataset utilise vraies images ?

Lors de `python data/prepare_dataset.py`, vous DEVEZ voir:
```
✅ Utilisation de VRAIES images safe depuis COCO
```

Si vous voyez `⚠️ Mode temporaire`, les images ne sont pas détectées.

### Environnement OK ?

```bash
python check_environment.py
```

Tous les items doivent être ✅

---

## 📚 Documentation Complète

### Essentiel
- **README_MOBILENETV2.md** - Architecture et méthodologie complète

### Scripts Utiles
```bash
python check_environment.py      # Vérifier environnement
python reset_project.py          # Nettoyer (si besoin)
python run_full_pipeline.py      # Pipeline complet
COMMANDS.bat                     # Menu interactif Windows
```

---

## 🎯 Résultats Attendus

| Métrique | Baseline | Secured | Amélioration |
|----------|----------|---------|--------------|
| Clean Accuracy | 85-92% | 83-90% | -2 à -5% |
| FGSM ASR | 60-75% | 10-20% | ✅ -50 à -60% |
| PGD ASR | 70-85% | 20-35% | ✅ -50 à -55% |

**Trade-off**: Légère baisse d'accuracy pour forte amélioration de robustness.

---

## 🆘 Problèmes Courants

### "Mode temporaire" au lieu de "Vraies images"

**Cause**: Images safe non trouvées

**Solution**:
1. Vérifiez que `data/coco_safe/` existe
2. Vérifiez qu'il contient des .jpg
3. Relancez `python data/prepare_dataset.py`

### Entraînement trop lent

**CPU**: Normal, ~7-13h total
**GPU**: Devrait être ~2-3h

**Solutions**:
- Utilisez Google Colab (GPU gratuit)
- Ou attendez (le CPU fonctionne, juste plus lent)

### Out of Memory

Réduire `batch_size` dans les scripts:
```python
batch_size = 16  # Au lieu de 32
```

---

## ⏱️ Temps Total

- **Télécharger images**: 15-20 min
- **Préparer dataset**: 5 min
- **Entraîner**: 2-3h (GPU) ou 7-13h (CPU)

**Total**: ~2.5-3.5h (GPU) ou ~7.5-13.5h (CPU)

---

## 🎓 Pour Votre Mémoire

### Ce Projet Démontre

1. **Architecture adaptée**: MobileNetV2 (3.5M params) vs ResNet50 (25.6M)
2. **Trade-off accuracy/robustness**: Quantifié avec métriques précises
3. **Adversarial training**: TRADES implémenté correctement
4. **Méthodologie rigoureuse**: Tests statistiques, intervalles de confiance

### Résultats Scientifiquement Valides

- ✅ Dataset réaliste (vraies images safe vs dangerous)
- ✅ Régularisation complète (early stopping, dropout, weight decay)
- ✅ Évaluation robuste (FGSM, PGD, tests statistiques)
- ✅ Reproductible (seeds fixés, code documenté)

---

## 📋 Checklist Complète

- [ ] Lu ce guide
- [ ] Téléchargé ~333 images "safe" depuis Pixabay/Kaggle
- [ ] Placé dans `data/coco_safe/`
- [ ] Vérifié: dossier contient les images
- [ ] Exécuté: `python data/prepare_dataset.py`
- [ ] Vu: "✅ Utilisation de VRAIES images"
- [ ] Vérifié: `python check_environment.py`
- [ ] Lancé: `python run_full_pipeline.py --skip-dataset`
- [ ] Attendu 2-3h (GPU) ou 7-13h (CPU)
- [ ] Consulté: `results/comparative/evaluation_report.txt`
- [ ] Vérifié résultats réalistes (85-92% accuracy, pas 100%)

---

## 🔄 Si Besoin de Recommencer

```bash
python reset_project.py
```

Puis recommencez à l'étape 1.

---

## 💡 Conseils

1. **GPU recommandé** mais pas obligatoire
2. **Pixabay** est le plus simple pour les images
3. **Ne modifiez pas les scripts** sauf si vous savez ce que vous faites
4. **Patience** pendant l'entraînement (c'est normal que ça prenne du temps)

---

## 📞 Structure du Projet

```
AA-secure-ai-detection/
├── START_HERE.md              ⭐ Ce fichier
├── README_MOBILENETV2.md      📖 Documentation technique
├── data/
│   ├── coco_safe/             ⏳ À créer (vos images safe)
│   ├── prepared/              🔄 Sera généré
│   └── prepare_dataset.py     🔧 Script de préparation
├── src/experiments/
│   ├── baseline/train_mobilenet.py
│   ├── secured/train_mobilenet_secured.py
│   └── comparative/evaluate_models.py
├── run_full_pipeline.py       🚀 Pipeline automatique
├── check_environment.py       ✓ Vérification
└── COMMANDS.bat               📋 Menu Windows
```

---

## 🚀 Commandes Essentielles

```bash
# Préparer dataset
python data/prepare_dataset.py

# Vérifier environnement
python check_environment.py

# Entraîner tout
python run_full_pipeline.py --skip-dataset

# Voir résultats
type results\comparative\evaluation_report.txt

# Menu interactif
COMMANDS.bat

# Nettoyer et recommencer
python reset_project.py
```

---

**Prêt ? Commencez par télécharger les images "safe" ! 🎯**

---

**Dernière mise à jour**: 2025-12-23
**Version**: MobileNetV2 avec vraies images COCO
**Status**: ✅ Prêt (après téléchargement images)
