# 📸 Captures d'écran à générer pour le Chapitre 3.1

Ce document liste toutes les captures d'écran nécessaires pour illustrer le Chapitre 3.1 du mémoire.

---

## 🎯 Captures pour la section 3.1.3 - Dataset

### 1. Grille d'exemples - Classe "dangerous"
**Fichier de sortie :** `figures/dataset_dangerous.png`

**Description :** Grille 4×4 (16 images) montrant des exemples variés d'armes à feu du dataset

**Script à créer/exécuter :**
```python
# Créer le script: scripts/visualize_dataset.py
python scripts/visualize_dataset.py --class dangerous --grid 4x4 --output figures/dataset_dangerous.png
```

**Contenu attendu :**
- 16 images d'armes à feu dans différents contextes
- Titre au-dessus : "Exemples de la classe 'dangerous'"
- Résolution : minimum 1200×1200 pixels

---

### 2. Grille d'exemples - Classe "safe"
**Fichier de sortie :** `figures/dataset_safe.png`

**Description :** Grille 4×4 (16 images) montrant des exemples variés d'images sûres (personnes, objets, scènes)

**Script à créer/exécuter :**
```python
python scripts/visualize_dataset.py --class safe --grid 4x4 --output figures/dataset_safe.png
```

**Contenu attendu :**
- 16 images sûres diverses (personnes, objets quotidiens, scènes urbaines, nature, etc.)
- Titre au-dessus : "Exemples de la classe 'safe'"
- Résolution : minimum 1200×1200 pixels

---

### 3. Distribution des classes
**Fichier de sortie :** `figures/dataset_distribution.png`

**Description :** Graphique en barres montrant la distribution des classes dans chaque ensemble

**Script à créer/exécuter :**
```python
python scripts/visualize_dataset.py --plot distribution --output figures/dataset_distribution.png
```

**Contenu attendu :**
- Graphique avec 3 groupes (Train, Val, Test)
- Chaque groupe avec 2 barres (safe, dangerous)
- Annotations avec les nombres exacts
- Titre : "Distribution des classes dans le dataset"
- Légende claire

**Données à afficher :**
```
Train:      699 safe, 699 dangerous (total: 1,398)
Validation: 147 safe, 147 dangerous (total: 294)
Test:       102 safe, 102 dangerous (total: 204)
```

---

### 4. Exemples d'augmentation de données
**Fichier de sortie :** `figures/data_augmentation_example.png`

**Description :** Visualisation montrant une image originale et ses transformations

**Script à créer/exécuter :**
```python
python scripts/visualize_augmentation.py --sample-image --output figures/data_augmentation_example.png
```

**Contenu attendu :**
- Image originale au centre ou en haut à gauche
- 5-6 versions transformées :
  - Rotation +20°
  - Rotation -20°
  - Flip horizontal
  - Zoom in (1.2×)
  - Zoom out (0.8×)
  - Brightness +20%
  - Brightness -20%
- Annotations sous chaque image
- Layout : grille 2×4 ou 3×3

---

## 🏗️ Captures pour la section 3.1.1 & 3.1.2 - Architecture

### 5. Diagramme d'architecture globale
**Fichier de sortie :** `figures/architecture_globale.png`

**Source :** `redaction/diagramme_architecture_globale.html`

**Instructions :**
1. Ouvrir `diagramme_architecture_globale.html` dans un navigateur
2. Cliquer sur "Télécharger en PNG"
3. Sauvegarder comme `figures/architecture_globale.png`

**Résolution recommandée :** Minimum 1600×1200 pixels

---

### 6. Diagramme de composants
**Fichier de sortie :** `figures/diagramme_composants.png`

**Source :** `redaction/diagramme_composants.html`

**Instructions :**
1. Ouvrir `diagramme_composants.html` dans un navigateur
2. Cliquer sur "Télécharger en PNG"
3. Sauvegarder comme `figures/diagramme_composants.png`

**Résolution recommandée :** Minimum 1800×1400 pixels (diagramme UML large)

---

### 7. Diagrammes de flux de données (5 diagrammes)
**Fichiers de sortie :**
- `figures/phase1_preparation.png`
- `figures/phase2_entrainement.png`
- `figures/phase3_evaluation.png`
- `figures/phase4_deploiement.png`
- `figures/vue_ensemble_complete.png`

**Source :** `redaction/diagramme_flux_donnees.html`

**Instructions :**
1. Ouvrir `diagramme_flux_donnees.html` dans un navigateur
2. Cliquer sur "Télécharger TOUS les diagrammes (PNG)"
3. Ou télécharger individuellement chaque phase

**Résolution recommandée :** Minimum 1400×1000 pixels par diagramme

---

## 🛠️ Scripts Python à créer

### Script 1 : `scripts/visualize_dataset.py`

**Fonctionnalités requises :**
- Charger le dataset depuis `data/prepared/`
- Afficher grille d'images pour une classe donnée
- Générer graphique de distribution
- Sauvegarder en haute résolution

**Exemple de structure :**
```python
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from PIL import Image

def plot_grid(images, title, output_path, grid_size=(4,4)):
    """Affiche une grille d'images"""
    # TODO: Implémenter

def plot_distribution(stats, output_path):
    """Affiche la distribution des classes"""
    # TODO: Implémenter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--class', choices=['safe', 'dangerous'])
    parser.add_argument('--grid', default='4x4')
    parser.add_argument('--plot', choices=['distribution'])
    parser.add_argument('--output', required=True)
    # TODO: Implémenter
```

---

### Script 2 : `scripts/visualize_augmentation.py`

**Fonctionnalités requises :**
- Charger une image d'exemple
- Appliquer toutes les transformations d'augmentation
- Afficher côte à côte dans une grille
- Sauvegarder en haute résolution

**Exemple de structure :**
```python
import argparse
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

def show_augmentations(image_path, output_path):
    """Montre toutes les augmentations appliquées"""
    # TODO: Implémenter avec ImageDataGenerator
    # ou utiliser directement src/defenses/training/data_augmentation.py
```

---

## 📋 Checklist de génération

### Captures d'écran du dataset
- [ ] `dataset_dangerous.png` - Grille 4×4 d'armes
- [ ] `dataset_safe.png` - Grille 4×4 d'images sûres
- [ ] `dataset_distribution.png` - Graphique de distribution
- [ ] `data_augmentation_example.png` - Exemples d'augmentation

### Diagrammes d'architecture
- [ ] `architecture_globale.png` - Architecture 4 couches
- [ ] `diagramme_composants.png` - Composants UML
- [ ] `phase1_preparation.png` - Flux préparation données
- [ ] `phase2_entrainement.png` - Flux entraînement
- [ ] `phase3_evaluation.png` - Flux évaluation
- [ ] `phase4_deploiement.png` - Flux déploiement
- [ ] `vue_ensemble_complete.png` - Vue d'ensemble

### Fichiers LaTeX
- [x] `Chapitre_3.1.tex` - Contenu rédigé avec placeholders pour figures
- [ ] Décommenter les `\includegraphics` une fois les figures générées

---

## 💡 Conseils pour de bonnes captures d'écran

### Qualité
- **Résolution :** Minimum 1200×1000 pixels
- **Format :** PNG (sans perte, meilleur pour diagrammes)
- **DPI :** 300 DPI pour impression (optionnel pour PDF)

### Style
- **Police :** Lisible, minimum 12pt
- **Couleurs :** Contraste élevé, éviter couleurs trop vives
- **Fond :** Blanc ou très clair pour impression
- **Annotations :** Claires et concises

### Consistance
- Même style de police dans tous les diagrammes
- Palette de couleurs cohérente
- Taille similaire pour figures comparables

---

## 🚀 Ordre de génération recommandé

1. **Créer d'abord les scripts Python**
   - `visualize_dataset.py`
   - `visualize_augmentation.py`

2. **Générer les captures du dataset**
   - Plus rapide, données déjà disponibles

3. **Générer les diagrammes HTML**
   - Déjà créés, juste à ouvrir dans navigateur

4. **Vérifier dans LaTeX**
   - Compiler le chapitre pour vérifier le rendu

---

## 📞 Besoin d'aide ?

Si vous avez besoin que je crée les scripts Python de visualisation, dites-le moi et je les générerai avec le code complet !