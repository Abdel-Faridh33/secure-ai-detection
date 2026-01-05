# 4.1 Présentation du PoC et choix du modèle

## 4.1.1 Objectif de la Proof of Concept

Cette Proof of Concept (PoC) vise à démontrer empiriquement l'efficacité des méthodes de sécurisation proposées dans les chapitres précédents, appliquées à un cas d'usage concret dans le domaine du maintien de l'ordre.

L'objectif principal est de comparer deux approches de développement de modèles d'intelligence artificielle :

1. **Approche Baseline (vulnérable)** : Un modèle ResNet50 entraîné de manière standard via transfer learning, représentant les pratiques courantes de développement IA sans considération particulière pour la sécurité adversariale.

2. **Approche Secured (robuste)** : Un modèle ResNet50 identique architecturalement, mais entraîné avec des défenses multicouches intégrant adversarial training selon la méthode TRADES, differential privacy, et des mécanismes de détection d'anomalies.

Cette comparaison permettra de quantifier précisément :
- L'**amélioration de robustesse** apportée par les mécanismes de défense proposés
- Le **trade-off** entre performance sur données propres (clean accuracy) et robustesse adversariale
- La **faisabilité pratique** de déploiement de modèles robustes en production

## 4.1.2 Scénario d'application : Détection d'objets dangereux

Le scénario choisi pour cette PoC est la **détection binaire d'objets dangereux versus objets sûrs**, un cas d'usage critique dans les systèmes de maintien de l'ordre où les erreurs de classification peuvent avoir des conséquences graves.

### Contexte opérationnel

Dans les systèmes de sécurité modernes, les algorithmes de vision par ordinateur sont déployés pour identifier automatiquement des objets dangereux dans des flux vidéo de surveillance, des contrôles d'accès, ou lors de fouilles automatisées. La compromission de ces systèmes par des attaques adversariales pourrait permettre à un adversaire de faire passer un objet dangereux pour un objet sûr, créant un risque de sécurité majeur.

### Classification binaire

Le problème est formulé comme une tâche de **classification binaire** :
- **Classe 0 (safe)** : Objets sûrs ne présentant pas de menace
- **Classe 1 (dangerous)** : Objets dangereux nécessitant une intervention

Cette simplification binaire, bien que réductrice par rapport à un système de production réel multi-classes, permet de :
- Concentrer l'analyse sur la **robustesse adversariale** plutôt que sur la complexité taxonomique
- Faciliter l'**interprétation des résultats** de sécurité (attack success rate, robustness degradation)
- Valider la **méthodologie de sécurisation** dans un cadre contrôlé avant généralisation

### Criticité du scénario

Ce scénario présente plusieurs caractéristiques critiques :
- **Asymétrie du coût d'erreur** : Un faux négatif (objet dangereux classé sûr) est bien plus grave qu'un faux positif
- **Adversaire motivé** : Un attaquant a un intérêt direct à tromper le système
- **Conséquences graves** : Les erreurs peuvent mener à des incidents de sécurité réels
- **Déploiement temps réel** : Le modèle doit être robuste dans des conditions opérationnelles variables

## 4.1.3 Justification du choix de ResNet50

Le choix de l'architecture **ResNet50** (He et al., 2016) [1] pour cette PoC repose sur plusieurs critères scientifiques et pratiques.

### 4.1.3.1 Architecture et capacité

ResNet50 est un réseau de neurones convolutif profond de 50 couches basé sur le mécanisme de **connexions résiduelles** (residual connections) introduit par He et al. (2016) [1]. Cette architecture présente les caractéristiques suivantes :

- **Profondeur** : 50 couches convolutives permettant l'extraction de features hiérarchiques complexes
- **Paramètres** : Approximativement 25 millions de paramètres (25.6M exactement)
- **Connexions résiduelles** : Permettent de résoudre le problème de gradient vanishing dans les réseaux très profonds [1]
- **Blocs résiduels** : Architecture modulaire composée de bottleneck blocks facilitant le transfer learning

L'innovation principale de ResNet réside dans l'utilisation de connexions skip (ou shortcut connections) qui permettent au gradient de se propager directement à travers le réseau, facilitant ainsi l'entraînement de réseaux très profonds [1].

### 4.1.3.2 Performance sur ImageNet

ResNet50 a démontré des performances exceptionnelles sur le benchmark ImageNet (Deng et al., 2009) [2] :
- **Top-1 accuracy** : ~76% sur ImageNet validation set
- **Top-5 accuracy** : ~93% sur ImageNet validation set
- **Features généralisables** : Les représentations apprises sur ImageNet transfèrent efficacement vers d'autres domaines de vision par ordinateur

Ces performances font de ResNet50 un point de départ idéal pour le **transfer learning** vers notre tâche de détection d'objets dangereux.

### 4.1.3.3 Adoption industrielle et standardisation

ResNet50 est largement adopté dans l'industrie et la recherche académique :
- **Standardisation** : Architecture de référence dans de nombreux benchmarks de robustesse adversariale comme RobustBench (Croce et al., 2021) [3]
- **Implémentations disponibles** : PyTorch, TensorFlow, ONNX avec poids pré-entraînés publiquement accessibles
- **Littérature abondante** : Nombreuses études sur sa robustesse adversariale, facilitant la comparaison avec l'état de l'art
- **Déploiement éprouvé** : Utilisé dans des systèmes de production réels avec support GPU/CPU

### 4.1.3.4 Vulnérabilité adversariale documentée

La littérature scientifique a largement documenté la **vulnérabilité de ResNet50 aux attaques adversariales** :

- **Sensibilité aux perturbations L∞** : Les attaques FGSM et PGD sont efficaces avec des epsilons (ε) relativement faibles
- **Gradient-based attacks** : Vulnérable aux attaques utilisant les gradients de la fonction de perte
- **Robustness gap** : Écart significatif entre clean accuracy (~76% sur ImageNet) et adversarial accuracy (<10% sans défenses) documenté dans plusieurs études [3]

Cette vulnérabilité connue en fait un excellent candidat pour démontrer l'efficacité des méthodes de sécurisation proposées dans ce mémoire.

### 4.1.3.5 Adaptabilité au scénario

ResNet50 s'adapte parfaitement à notre scénario de détection binaire :

- **Transfer Learning** : La dernière couche fully-connected peut être remplacée pour passer de 1000 classes ImageNet à 2 classes (safe/dangerous), tout en conservant les features génériques apprises sur ImageNet
- **Fine-tuning flexible** : Les couches convolutives pré-entraînées peuvent être gelées (pour transfer learning rapide) ou fine-tunées (pour adaptation au domaine spécifique)
- **Taille raisonnable** : ~280MB en format PyTorch (.pth), permettant un déploiement sur des systèmes embarqués ou des serveurs sans GPU haute performance
- **Inference temps réel** : Capable de traiter des images 224×224 pixels à plus de 30 FPS sur GPU moderne, et en temps quasi-réel sur CPU

### 4.1.3.6 Comparabilité scientifique

Le choix de ResNet50 facilite la **comparaison avec l'état de l'art** :
- **Benchmarks standardisés** : RobustBench [3] propose des baselines ResNet50 robustes contre lesquelles comparer nos résultats
- **Métriques comparables** : Clean accuracy, robust accuracy, attack success rate largement documentées dans la littérature
- **Reproductibilité** : Poids pré-entraînés (ImageNet weights) publiquement disponibles, garantissant la reproductibilité de nos expériences

En résumé, ResNet50 représente un choix optimal pour cette PoC car il combine **performance élevée**, **vulnérabilité adversariale documentée**, **adoption industrielle**, et **comparabilité scientifique**, tout en étant suffisamment compact pour un déploiement pratique.

## 4.1.4 Architecture expérimentale

L'architecture expérimentale mise en place pour cette PoC suit une approche **DevSecOps** intégrant la sécurité dès la phase de développement.

### Infrastructure de développement

L'ensemble du projet est **100% conteneurisé avec Docker** pour garantir la reproductibilité et l'isolation :

```
Infrastructure Docker :
├── Dockerfile.dev       # Environnement de développement complet
├── Dockerfile.baseline  # Container production modèle baseline
├── Dockerfile.secured   # Container production modèle sécurisé
├── Dockerfile.test      # Container pour tests automatisés
└── docker-compose.*.yml # Orchestration multi-containers
```

**Avantages de l'approche conteneurisée** :
- **Reproductibilité** : Environnement identique dev/test/prod
- **Isolation** : Dépendances encapsulées, pas de conflits
- **Portabilité** : Déploiement sur tout système supportant Docker
- **Versioning** : Traçabilité complète des environnements

### Stack technologique

Le projet utilise un stack moderne basé sur PyTorch :

**Framework ML** :
- **PyTorch 2.0.1** : Framework de deep learning avec autograd et GPU support
- **TorchVision 0.15.2** : Implémentations ResNet50, transformations d'images, datasets
- **Foolbox 3.3.3** : Bibliothèque d'attaques adversariales
- **Opacus 1.4.0** : Differential Privacy pour PyTorch

**Data Processing** :
- **NumPy 1.24.3** : Calcul numérique vectorisé
- **OpenCV 4.8.0** : Traitement d'images, augmentation
- **Pandas 2.0.3** : Manipulation de données tabulaires

**API et Production** :
- **FastAPI 0.100.0** : API REST moderne avec validation Pydantic
- **Uvicorn** : ASGI server pour FastAPI
- **Prometheus Client** : Métriques de monitoring

**Evaluation et Visualisation** :
- **scikit-learn 1.3.0** : Métriques ML (precision, recall, F1, ROC-AUC)
- **Matplotlib 3.7.2** : Visualisations scientifiques
- **Seaborn 0.12.2** : Visualisations statistiques avancées

### Pipeline expérimental

Le pipeline suit une architecture en **5 zones de sécurité** :

**Zone 1 : Préparation des données**
- Collecte et labélisation des images
- Vérification d'intégrité (checksums SHA-256)
- Augmentation de données (rotation, zoom, brightness)
- Détection d'anomalies dans le dataset

**Zone 2 : Entraînement sécurisé**
- **Baseline** : Transfer learning standard de ResNet50 ImageNet
- **Secured** : Adversarial training avec TRADES (β=6.0)
- Differential Privacy avec Opacus (ε, δ)-DP
- Validation croisée avec early stopping
- Sauvegarde de checkpoints versionnés

**Zone 3 : Validation adversariale**
- Tests sur données propres (clean test set)
- Attaques FGSM (ε=0.031)
- Attaques PGD (ε=0.031, 10 itérations)
- Attaques PGD Strong (ε=0.063, 20 itérations)
- AutoAttack gold standard

**Zone 4 : Déploiement production**
- API FastAPI avec endpoints /predict
- Input filtering et preprocessing
- Monitoring temps réel (Prometheus + Grafana)
- Logging de sécurité

**Zone 5 : Gouvernance et audit**
- Versioning Git avec traçabilité complète
- CI/CD GitHub Actions avec security gates
- Documentation technique et scientifique
- Rapports de validation automatisés

### Environnements de test

Trois environnements distincts pour assurer la séparation des phases :

| Environnement | Conteneur | Port | Usage |
|---------------|-----------|------|-------|
| **Development** | `dev` | 8888 (Jupyter) | Expérimentation interactive |
| **Testing** | `test` | - | Tests unitaires/intégration (pytest) |
| **Production** | `baseline`/`secured` | 8000 (API) | Inference temps réel |

---

## Références

[1] He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*. https://arxiv.org/abs/1512.03385

[2] Deng, J., Dong, W., Socher, R., Li, L. J., Li, K., & Fei-Fei, L. (2009). ImageNet: A large-scale hierarchical image database. *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*.

[3] Croce, F., Andriushchenko, M., Sehwag, V., Debenedetti, E., Flammarion, N., Chiang, M., Mittal, P., & Hein, M. (2021). RobustBench: A standardized adversarial robustness benchmark. *NeurIPS Datasets and Benchmarks Track*. https://arxiv.org/abs/2010.09670
