# ✅ Chapitre 3.1 - Présentation du cas expérimental et architecture du système

## 📄 Fichiers générés

### Fichier principal de rédaction
- **[Chapitre_3.1.tex](Chapitre_3.1.tex)** - Rédaction complète en LaTeX (style explicatif, non énumératif)

### Diagrammes interactifs (HTML avec Mermaid.js)
- **[diagramme_architecture_globale.html](diagramme_architecture_globale.html)** - Architecture en 4 couches
- **[diagramme_composants.html](diagramme_composants.html)** - Diagramme UML des composants
- **[diagramme_flux_donnees.html](diagramme_flux_donnees.html)** - 5 diagrammes de flux (phases 1-4 + vue d'ensemble)

### Documentation
- **[CAPTURES_ECRAN_A_GENERER.md](CAPTURES_ECRAN_A_GENERER.md)** - Liste complète des figures à générer

---

## 📋 Structure du Chapitre 3.1

### 3.1.1 Objectif et scénario de l'expérimentation
- Comparaison Baseline (vulnérable) vs Secured (robuste)
- Scénario : détection binaire d'armes à feu (safe vs dangerous)
- Justification du cas d'usage critique pour la sécurité

**Figure attendue :** Architecture POC (Baseline vs Secured)

### 3.1.2 Architecture globale et composants du système
- Architecture en 4 couches (données, entraînement, services, présentation)
- Description explicative des interactions entre couches
- Composants clés : DataLoader, AdversarialGenerator, TrainingManager, etc.

**Figures attendues :**
- Architecture globale (4 couches)
- Diagramme de composants UML

### 3.1.3 Présentation du dataset personnalisé
- Dataset équilibré : 1,896 images (948 dangerous + 948 safe)
- Sources : Kaggle (armes) + COCO (images sûres)
- Split 70%/15%/15% (train/val/test)
- Prétraitement : resize 224×224, normalisation, augmentation

**Figures attendues :**
- Grilles 4×4 d'exemples (dangerous + safe)

---

## 🎯 Caractéristiques de la rédaction

### ✅ Ce qui a été fait
- ✅ Rédaction explicative (non énumérative)
- ✅ Style aligné avec Chapitre_3.tex (ResNet50)
- ✅ Présentation du cas expérimental (objectif + scénario)
- ✅ Architecture décrite de manière fluide
- ✅ Dataset présenté dans section dédiée (3.1.3)
- ✅ Statistiques exactes du dataset (extraites de dataset_stats.json)
- ✅ Diagrammes HTML interactifs avec export PNG/SVG

### 📊 Données réelles utilisées
```
Total images: 1,896
- Classe "dangerous": 948 images
- Classe "safe": 948 images

Répartition:
- Train: 1,398 images (699 par classe) - 73.7%
- Val:   294 images (147 par classe) - 15.5%
- Test:  204 images (102 par classe) - 10.8%
```

---

## 🖼️ Captures d'écran à générer

### Priorité 1 : Dataset
- [ ] `figures/dataset_dangerous.png` - Grille 4×4 d'armes
- [ ] `figures/dataset_safe.png` - Grille 4×4 d'images sûres

### Priorité 2 : Architecture
- [ ] `figures/architecture_poc.png` - Baseline vs Secured
- [ ] `figures/architecture_globale.png` - 4 couches du système
- [ ] `figures/diagramme_composants.png` - Composants UML

### Scripts nécessaires
```bash
# À créer
python scripts/visualize_dataset.py --class dangerous --grid 4x4 --output figures/dataset_dangerous.png
python scripts/visualize_dataset.py --class safe --grid 4x4 --output figures/dataset_safe.png
```

**Note :** Les diagrammes HTML peuvent être exportés directement depuis le navigateur (boutons "Télécharger en PNG")

---

## 📝 Comparaison avec Chapitre_3.tex (ResNet50)

| Aspect | Chapitre 3 (ResNet50) | Notre Chapitre 3.1 (MobileNetV2) |
|--------|----------------------|----------------------------------|
| **Modèle** | ResNet50 (25.6M params) | MobileNetV2 (3.5M params) |
| **Dataset** | Non spécifié | Kaggle weapons + COCO safe |
| **Classes** | safe vs dangerous | safe vs dangerous |
| **Style** | Explicatif, académique | Explicatif, académique |
| **Structure** | 3.1.1 Objectif<br>3.1.2 Scénario<br>3.1.3 Justification modèle | 3.1.1 Objectif + Scénario<br>3.1.2 Architecture<br>3.1.3 Dataset |

---

## 🚀 Prochaines étapes

1. **Générer les captures d'écran du dataset**
   - Créer `scripts/visualize_dataset.py`
   - Exécuter pour générer les grilles d'images

2. **Exporter les diagrammes HTML en PNG**
   - Ouvrir les fichiers `.html` dans un navigateur
   - Cliquer sur "Télécharger en PNG"
   - Sauvegarder dans `figures/`

3. **Décommenter les `\includegraphics` dans Chapitre_3.1.tex**
   - Une fois les figures générées et placées dans `figures/`

4. **Compiler le chapitre pour vérifier le rendu**
   - Intégrer dans le document principal du mémoire

5. **Passer à la section 3.2** (Choix du modèle et justification technique)

---

## 💡 Points clés de la rédaction

### Style adopté
- **Paragraphes explicatifs** plutôt que listes à puces
- **Contexte avant détails** (pourquoi → quoi → comment)
- **Transitions fluides** entre sections
- **Références croisées** aux figures et tableaux

### Éviter
- ❌ Énumérations excessives
- ❌ Descriptions trop longues
- ❌ Répétitions inutiles
- ❌ Jargon technique non expliqué

### Privilégier
- ✅ Explication du raisonnement
- ✅ Justification des choix
- ✅ Concision et clarté
- ✅ Cohérence avec le reste du mémoire

---

## 📞 Besoin d'aide ?

- Les diagrammes HTML sont prêts et peuvent être visualisés directement
- Les scripts de visualisation du dataset peuvent être générés sur demande
- La rédaction peut être ajustée selon vos commentaires
