# 📘 Guide Simple - Projet Secure AI Detection

**Version MobileNetV2 - Tout ce qu'il faut savoir**

---

## 🎯 C'est Quoi ?

Un projet qui compare deux modèles de détection d'objets:
- **Baseline**: Modèle standard (rapide mais vulnérable)
- **Secured**: Modèle robuste (légèrement plus lent mais résistant aux attaques)

**Résultat**: Démonstration du trade-off accuracy vs robustness

---

## 🚀 Comment Démarrer ?

### Étape 1: Images "Safe" (15 min)

1. Allez sur **Pixabay.com**
2. Téléchargez ~333 images de: chaises, tables, laptops, bouteilles, livres
3. Placez-les dans: `data/coco_safe/`

**Pourquoi ?** Le projet classifie "safe" vs "dangerous". On a déjà les armes (dangerous), il manque les objets sûrs (safe).

### Étape 2: Préparer (5 min)

```bash
python data/prepare_dataset.py
```

Génère ~2000 images avec augmentation (rotation, flip, etc.)

### Étape 3: Entraîner (2-3h)

```bash
python run_full_pipeline.py --skip-dataset
```

Entraîne les deux modèles et génère les résultats.

---

## 📊 Résultats Attendus

| Modèle | Accuracy | Robustesse FGSM | Robustesse PGD |
|--------|----------|-----------------|----------------|
| Baseline | ~90% | Faible (60-75% ASR) | Faible (70-85% ASR) |
| Secured | ~87% | **Forte** (10-20% ASR) | **Forte** (20-35% ASR) |

**ASR** = Attack Success Rate (plus bas = meilleur)

**Trade-off**: -3% accuracy pour -50 à -60% de vulnérabilité

---

## 📁 Fichiers Importants

### Pour Démarrer
- **[START_HERE.md](START_HERE.md)** ⭐ Guide détaillé étape par étape

### Documentation
- **[README_MOBILENETV2.md](README_MOBILENETV2.md)** - Architecture complète
- **[GUIDE_SIMPLE.md](GUIDE_SIMPLE.md)** - Ce fichier

### Scripts
```
run_full_pipeline.py    → Lance tout automatiquement
check_environment.py    → Vérifie que tout est OK
reset_project.py        → Nettoie pour recommencer
COMMANDS.bat            → Menu interactif (Windows)
```

---

## 🔧 Commandes Utiles

```bash
# Vérifier environnement
python check_environment.py

# Préparer dataset
python data/prepare_dataset.py

# Entraîner tout
python run_full_pipeline.py --skip-dataset

# Voir résultats
type results\comparative\evaluation_report.txt

# Nettoyer pour recommencer
python reset_project.py
```

---

## ❓ FAQ

### Combien de temps ça prend ?

- **Avec GPU**: 2-3 heures total
- **Sans GPU (CPU)**: 7-13 heures total

### J'ai pas de GPU ?

Pas grave ! Ça marche sur CPU, juste plus lent. Ou utilisez Google Colab (GPU gratuit).

### Pourquoi télécharger des images ?

L'ancien dataset utilisait des armes transformées comme "safe", ce qui n'est pas valide scientifiquement. On a besoin de vraies images d'objets sûrs.

### Combien d'images télécharger ?

**Minimum**: 200 images
**Recommandé**: 333 images
**Optimal**: 500+ images

### Où mettre les images ?

Dans le dossier `data/coco_safe/`, n'importe quel nom de fichier .jpg

### Le script dit "Mode temporaire" ?

Les images safe ne sont pas détectées. Vérifiez que `data/coco_safe/` existe et contient des .jpg

---

## 🎓 Pour le Mémoire

### Points Forts du Projet

1. **Architecture moderne**: MobileNetV2 (efficace, 3.5M params)
2. **Trade-off quantifié**: Accuracy vs Robustness avec chiffres précis
3. **Adversarial training**: TRADES implémenté correctement
4. **Méthodologie rigoureuse**: Tests statistiques, intervalles de confiance
5. **Reproductible**: Code documenté, seeds fixés

### Résultats Scientifiquement Valides

- ✅ Dataset réaliste (vraies images)
- ✅ Régularisation complète (early stopping, dropout)
- ✅ Évaluation robuste (FGSM, PGD)
- ✅ Tests statistiques (McNemar)

---

## 🛠️ Architecture Technique

### Baseline
```
MobileNetV2 (pré-entraîné ImageNet)
  ↓
Transfer learning (freeze early layers)
  ↓
Classifier: 1280 → 256 → 2 classes
  ↓
Entraînement standard
```

### Secured
```
MobileNetV2 (pré-entraîné ImageNet)
  ↓
Transfer learning (freeze early layers)
  ↓
Classifier: 1280 → 512 → 256 → 2 classes
  ↓
TRADES Adversarial Training (β=6.0)
  ├─ Natural Loss (classification)
  └─ Robustness Loss (KL divergence vs PGD)
```

**Différence clé**: TRADES génère des exemples adversariaux pendant l'entraînement

---

## 📦 Structure du Projet

```
AA-secure-ai-detection/
│
├── 📖 Documentation
│   ├── START_HERE.md              ⭐ Commencez ici
│   ├── GUIDE_SIMPLE.md            📘 Ce fichier
│   └── README_MOBILENETV2.md      📚 Doc complète
│
├── 🔧 Scripts Principaux
│   ├── run_full_pipeline.py       🚀 Pipeline auto
│   ├── check_environment.py       ✓ Vérification
│   ├── reset_project.py           🧹 Nettoyage
│   └── COMMANDS.bat               📋 Menu Windows
│
├── 📂 Données
│   ├── raw/Images/                🔫 333 images guns
│   ├── coco_safe/                 ⏳ Vos images safe (à créer)
│   └── prepared/                  📦 Dataset généré
│
├── 🤖 Scripts d'Entraînement
│   ├── data/prepare_dataset.py
│   ├── src/experiments/baseline/train_mobilenet.py
│   ├── src/experiments/secured/train_mobilenet_secured.py
│   └── src/experiments/comparative/evaluate_models.py
│
├── 💾 Résultats (après entraînement)
│   ├── models/baseline/
│   ├── models/secured/
│   └── results/comparative/
│
```

---

## 🆘 Problèmes Courants

### Images safe non détectées

**Symptôme**: Message "⚠️ Mode temporaire"

**Solution**:
```bash
# Vérifier le dossier
powershell -Command "Test-Path data\coco_safe"

# Compter les images
powershell -Command "(Get-ChildItem data\coco_safe -Filter *.jpg).Count"
```

### Out of Memory

**Solution**: Réduire batch_size dans les scripts
```python
# Dans train_mobilenet.py ligne ~120
batch_size = 16  # Au lieu de 32
```

### Entraînement bloqué

**Vérifier**:
- Le script tourne toujours ? (normal que ça prenne du temps)
- GPU utilisé ? (`python -c "import torch; print(torch.cuda.is_available())"`)
- Logs d'erreur ?

---

## ✅ Checklist Avant Entraînement

- [ ] Images safe téléchargées (~333)
- [ ] Placées dans `data/coco_safe/`
- [ ] `python data/prepare_dataset.py` exécuté
- [ ] Message "✅ Vraies images" vu
- [ ] `python check_environment.py` → tout vert
- [ ] Temps disponible (2-3h minimum)

---

## 🎯 Workflow Complet

```
1. Télécharger images     → 15 min
   ↓
2. Préparer dataset       → 5 min
   ↓
3. Vérifier environnement → 1 min
   ↓
4. Entraîner baseline     → 30-60 min (GPU)
   ↓
5. Entraîner secured      → 1-2h (GPU)
   ↓
6. Évaluer                → 10-20 min
   ↓
7. Analyser résultats     → À vous de jouer !
```

**Total**: ~2.5-3.5h avec GPU

---

## 💡 Conseils

1. **Commencez par lire**: [START_HERE.md](START_HERE.md)
2. **Téléchargez depuis Pixabay**: C'est le plus simple
3. **Utilisez le pipeline auto**: Plus simple que manuel
4. **Patience**: L'entraînement prend du temps (normal)
5. **GPU recommandé**: Mais CPU fonctionne aussi

---

## 📞 Besoin d'Aide ?

1. **Lisez**: [START_HERE.md](START_HERE.md)
2. **Vérifiez**: `python check_environment.py`
3. **Documentation complète**: [README_MOBILENETV2.md](README_MOBILENETV2.md)

---

**Prêt ? → [START_HERE.md](START_HERE.md) ⭐**

---

**Version**: MobileNetV2
**Dernière mise à jour**: 2025-12-23
**Status**: ✅ Prêt (après téléchargement images safe)
