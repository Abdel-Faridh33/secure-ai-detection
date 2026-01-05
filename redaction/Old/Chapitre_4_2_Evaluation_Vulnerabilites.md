# 4.2 Évaluation des vulnérabilités de ResNet50

## 4.2.1 Dataset expérimental

L'évaluation de la robustesse adversariale nécessite un dataset expérimental soigneusement conçu. Au cours du développement du projet, le dataset a connu une évolution significative, guidée par les observations empiriques sur les performances du modèle et les exigences de robustesse adversariale.

### 4.2.1.1 Dataset initial (Phase 1)

Dans sa première version, le dataset expérimental comprenait 100 images synthétiques représentant des formes géométriques simples : des cercles verts pour la classe "safe" et des triangles rouges pour la classe "dangerous". Ces images, de format RGB 224×224 pixels, étaient réparties en 70 échantillons pour l'entraînement, 15 pour la validation et 15 pour les tests, avec une distribution équilibrée de 50% par classe.

Cette approche initiale, bien que permettant une mise en œuvre rapide, révéla rapidement plusieurs limitations. La faible diversité visuelle créait un risque important de surapprentissage : le modèle pouvait mémoriser les caractéristiques spécifiques des formes géométriques sans développer une véritable capacité de généralisation. De plus, les images synthétiques ne capturaient ni les variations d'éclairage, ni les différents angles de vue, ni les occlusions partielles que l'on rencontre dans des conditions réelles. La distribution strictement équilibrée entre les deux classes, si elle simplifie l'entraînement, ne reflète pas nécessairement la rareté relative des objets dangereux dans un contexte opérationnel.

### 4.2.1.2 Dataset optimisé (Phase 2)

Ces constats ont conduit au développement d'une seconde version substantiellement enrichie du dataset. Le volume a été porté à plus de 1000 images, réparties en 512 échantillons d'entraînement, 256 de validation et 256 de test, maintenant un équilibre approximatif de 500 images par classe. Cette augmentation n'est pas uniquement quantitative : elle s'accompagne d'une diversification qualitative des données.

L'enrichissement du dataset repose sur des techniques d'augmentation avancées appliquées à des photographies d'objets réels. Les transformations géométriques comprennent des rotations variant de -15° à +15° pour l'invariance angulaire, des variations de zoom entre 0.8× et 1.2× pour l'invariance d'échelle, ainsi que des symétries horizontales et des transformations de perspective légères. Les augmentations photométriques ajustent la luminosité à ±20%, simulant ainsi différentes conditions d'éclairage. Cette stratégie permet de capturer la variété des angles de vue (frontal, latéral, oblique), des arrière-plans (neutres ou complexes), et des conditions d'éclairage (intérieur, extérieur, artificiel) que le modèle pourrait rencontrer en production.

L'impact de cette diversification sur la robustesse adversariale est multiple. En exposant le modèle à une plus grande variété de représentations visuelles, on réduit le risque de surapprentissage sur des caractéristiques superficielles et fragiles. La capacité de généralisation s'en trouve renforcée, et plus important encore pour notre contexte, la variété des exemples adversariaux générés pendant l'entraînement adversarial s'enrichit, permettant au modèle d'apprendre à résister à un spectre plus large de perturbations.

### 4.2.1.3 Validation de la qualité du dataset

Pour garantir la fiabilité des évaluations de robustesse, plusieurs contrôles de qualité ont été appliqués au dataset. L'intégrité des images est vérifiée par des empreintes cryptographiques SHA-256, permettant de détecter toute corruption ou modification involontaire. Une analyse statistique des distributions de pixels identifie les valeurs aberrantes susceptibles de biaiser l'entraînement. L'équilibrage approximatif des classes (50/50) est maintenu pour éviter qu'une classe ne domine l'apprentissage, tandis qu'une inspection manuelle des annotations permet d'écarter tout risque d'empoisonnement des données.

Les annotations sont structurées dans un fichier JSON (`data/processed/annotations.json`) qui associe à chaque image ses métadonnées : classe d'appartenance, split d'affectation (train/val/test), et empreinte cryptographique. Cette traçabilité complète assure la reproductibilité des expériences, condition essentielle pour valider scientifiquement les résultats obtenus.

## 4.2.2 Métriques d'évaluation

L'évaluation comparative entre le modèle baseline et le modèle sécurisé repose sur un ensemble de métriques couvrant trois dimensions complémentaires : performance sur données propres, robustesse adversariale, et sécurité opérationnelle.

### 4.2.2.1 Métriques de performance sur données propres

Les métriques classiques de performance permettent d'établir la capacité du modèle à effectuer la tâche de classification dans des conditions normales. L'accuracy, définie par le rapport (TP + TN) / (TP + TN + FP + FN), mesure la proportion globale de prédictions correctes sur données non perturbées. Elle constitue la métrique de référence pour évaluer la performance baseline.

La precision et le recall apportent une granularité supplémentaire essentielle dans un contexte de sécurité. La precision, calculée comme TP / (TP + FP), quantifie la proportion de prédictions positives correctes. Pour la classe "dangerous", une precision faible implique de nombreuses fausses alertes, générant un coût opérationnel non négligeable. Le recall, défini par TP / (TP + FN), mesure la proportion d'échantillons réellement dangereux correctement détectés. Cette métrique est critique : un recall insuffisant signifie que des objets dangereux échappent au système de détection, créant un risque de sécurité majeur. Le F1-score combine ces deux métriques par leur moyenne harmonique 2 × (Precision × Recall) / (Precision + Recall), offrant ainsi une vision équilibrée de la performance.

L'AUC-ROC (Area Under ROC Curve) évalue la capacité discriminante du modèle entre les classes, indépendamment du seuil de classification choisi. Une valeur de 1.0 indique une séparation parfaite. Enfin, la matrice de confusion visualise la répartition des vrais positifs, vrais négatifs, faux positifs et faux négatifs, révélant les patterns d'erreurs spécifiques au contexte opérationnel.

### 4.2.2.2 Métriques de robustesse adversariale

La robustesse adversariale évalue la capacité du modèle à maintenir ses performances face à des entrées malicieusement perturbées. L'adversarial accuracy mesure la proportion de prédictions correctes sur des exemples générés par une attaque spécifique (FGSM ou PGD). Elle constitue la métrique centrale de l'évaluation de robustesse.

L'Attack Success Rate (ASR), défini comme le rapport entre exemples adversariaux mal classifiés et le total d'exemples testés, quantifie directement l'efficacité de l'attaque : un ASR élevé révèle une forte vulnérabilité du modèle. Cette métrique inverse de la robustesse permet de mesurer l'exposition réelle aux menaces adversariales.

La dégradation de robustesse (Robustness Degradation) capture l'écart de performance entre données propres et données adversariales. Un modèle véritablement robuste devrait présenter une dégradation minimale, idéalement inférieure à 5%. Un écart important signale que le modèle s'appuie sur des caractéristiques fragiles, facilement perturbables. Enfin, le comptage des échantillons robustes (Robust Samples Count) fournit une mesure absolue du nombre d'exemples résistant aux perturbations, permettant un suivi granulaire de la robustesse.

### 4.2.2.3 Métriques de sécurité spécialisées

Au-delà des métriques standards, plusieurs indicateurs spécialisés complètent l'évaluation de sécurité. La perturbation moyenne effective (ε effectif) mesure l'amplitude minimale de perturbation, en norme L∞ ou L2, nécessaire pour tromper le modèle. Un seuil ε élevé témoigne d'une robustesse accrue : l'adversaire doit introduire des perturbations plus visibles pour réussir son attaque.

La robustesse dans le pire cas (Worst-Case Robustness) évalue l'accuracy sous l'attaque la plus sophistiquée testée, typiquement PGD ou AutoAttack. Cette métrique conservatrice fournit une borne inférieure fiable de la robustesse réelle, écartant les évaluations optimistes basées sur des attaques faibles.

Enfin, la détection de masquage de gradients est cruciale pour valider l'authenticité de la robustesse observée. Certaines défenses créent l'illusion de robustesse en masquant les gradients, rendant les attaques basées sur le gradient inefficaces sans véritablement sécuriser le modèle. Plusieurs tests permettent de détecter ce phénomène : le test BPDA (Backward Pass Differentiable Approximation), la vérification de la magnitude des gradients, et la comparaison FGSM vs PGD. Si une attaque simple comme FGSM échoue alors qu'une attaque itérative comme PGD réussit, cela suggère un masquage de gradients plutôt qu'une robustesse authentique.

### 4.2.2.4 Critères de validation production

Pour être considéré **production-ready**, un modèle doit satisfaire les seuils suivants :

| Critère | Seuil Minimum | Justification |
|---------|---------------|---------------|
| **Clean Accuracy** | ≥ 95% | Performance acceptable sur données normales |
| **FGSM Robustness** | ≥ 80% | Résistance aux attaques de base |
| **PGD Robustness** | ≥ 80% | Résistance aux attaques itératives |
| **Gradient Health** | Pas de masking | Robustesse réelle vs artificielle |
| **AutoAttack** | ≥ 75% | Certification gold standard |

**Security Grade** (classification qualitative) :
- **A+** : Tous critères ≥90%, AutoAttack ≥85% (invulnérable)
- **A** : Tous critères ≥80%, AutoAttack ≥75% (robuste)
- **B** : Clean ≥90%, PGD ≥60% (robustesse partielle)
- **C** : Clean ≥90%, PGD <60% (vulnérable)
- **F** : Clean <90% (non déployable)

## 4.2.3 Protocole de test du modèle Baseline

### 4.2.3.1 Entraînement du modèle Baseline

**Objectif** : Établir une baseline représentative des pratiques de développement IA courantes, sans considération de sécurité adversariale.

**Procédure** :
1. **Initialisation** :
   - Charger ResNet50 pré-entraîné sur ImageNet
   - Remplacer la couche FC finale : 1000 classes → 2 classes (safe/dangerous)
   - Geler les couches convolutives (feature extractor)
   - Entraîner uniquement la nouvelle couche FC (transfer learning)

2. **Configuration d'entraînement** :
   - Optimizer : SGD avec momentum
   - Learning rate : 0.01 avec decay
   - Batch size : 16 (limité par ressources CPU)
   - Loss : Cross-Entropy standard
   - Early stopping : Patience de 3 epochs sur validation loss

3. **Validation** :
   - Évaluation sur validation set tous les epochs
   - Sauvegarde du meilleur checkpoint (best validation accuracy)
   - Métriques trackées : Loss, Accuracy, Precision, Recall, F1

**Résultat attendu** : Modèle performant sur données propres (~95-100% accuracy) mais **vulnérable aux attaques adversariales**.

### 4.2.3.2 Batterie de tests adversariaux

**Test Set** :
- 15 échantillons test réels
- Distribution équilibrée : safe/dangerous
- Données complètement isolées de l'entraînement (jamais vues)

**Batterie d'attaques** (par ordre de sophistication) :

**1. Clean Test (baseline de performance)** :
- Évaluation sur test set non perturbé
- Métriques : Accuracy, Precision, Recall, F1, AUC
- Temps d'exécution attendu : ~14 secondes

**2. FGSM Attack** :
- Méthode : Fast Gradient Sign Method (single-step)
- Configuration :
  - Epsilon ε = 0.031 (norme L∞)
  - Direction : Sign du gradient de la loss
  - Formule : x_adv = x + ε × sign(∇_x L(θ, x, y))
- Métriques : Adversarial Accuracy, ASR, Robustness Degradation
- Temps d'exécution attendu : ~39 secondes

**3. PGD Attack** :
- Méthode : Projected Gradient Descent (iterative FGSM)
- Configuration :
  - Epsilon ε = 0.031 (norme L∞)
  - Iterations : 10
  - Step size α = ε/4 = 0.00775
  - Projection : Clip dans l'ε-ball L∞
- Métriques : Adversarial Accuracy, ASR, Robustness Degradation
- Temps d'exécution attendu : ~55 minutes (computation intensive)

**4. PGD Strong Attack** :
- Méthode : PGD renforcé (plus d'itérations, epsilon plus grand)
- Configuration :
  - Epsilon ε = 0.063 (2× epsilon standard)
  - Iterations : 20 (2× iterations standard)
  - Step size α = ε/8
- Métriques : Worst-case robustness
- Temps d'exécution attendu : ~13 minutes

## 4.2.4 Résultats de vulnérabilité du modèle Baseline

*Cette section sera remplie avec les résultats réels obtenus lors des tests*

### 4.2.4.1 Performance sur données propres

**Résultats Clean Test** :
- **Clean Accuracy** : 100.0% (15/15 échantillons)
- **Loss** : 0.0046
- **AUC-ROC** : 1.000
- **Precision Safe** : 100.0%
- **Recall Safe** : 100.0%
- **F1-Score Safe** : 100.0%
- **Precision Dangerous** : 100.0%
- **Recall Dangerous** : 100.0%
- **F1-Score Dangerous** : 100.0%

**Analyse** : Le modèle baseline atteint une performance parfaite sur données propres, démontrant que le transfer learning de ResNet50 fonctionne efficacement pour notre tâche de classification binaire.

### 4.2.4.2 Vulnérabilité aux attaques FGSM

**Résultats FGSM Attack (ε=0.031)** :
- **Adversarial Accuracy** : 100.0% (15/15 échantillons)
- **Attack Success Rate (ASR)** : 0.0%
- **Robustness Degradation** : 0.0%
- **Exemples compromis** : 0/15

**Analyse** : Résistance parfaite aux attaques FGSM avec ε=0.031. Cela suggère que le modèle baseline possède une certaine robustesse naturelle aux attaques single-step de faible magnitude.

### 4.2.4.3 Vulnérabilité critique aux attaques PGD

**Résultats PGD Attack (ε=0.031, 10 itérations)** :
- **Adversarial Accuracy** : 46.7% (7/15 échantillons) ⚠️
- **Attack Success Rate (ASR)** : 53.3% (8/15 échantillons) 🚨
- **Robustness Degradation** : 53.3%
- **Exemples compromis** : 8/15

**Analyse critique** :
Le modèle baseline présente une **vulnérabilité critique** aux attaques PGD :
- Plus de la moitié des échantillons (53.3%) sont compromis par l'attaque
- Dégradation de performance de 53.3 points entre données propres et adversariales
- **Non conforme aux critères de production** (seuil minimum : 80% PGD robustness)
- **Security Grade : C** (vulnérable)

Cette vulnérabilité démontre que :
1. Les attaques itératives (PGD) sont significativement plus efficaces que les attaques single-step (FGSM)
2. Le modèle baseline, malgré sa performance parfaite sur données propres, est **inadapté au déploiement en production** dans un contexte adversarial
3. Des mécanismes de défense avancés sont nécessaires pour atteindre le niveau de robustesse requis

### 4.2.4.4 Comparaison FGSM vs PGD

| Métrique | FGSM (ε=0.031) | PGD (ε=0.031, 10 iter) | Écart |
|----------|----------------|------------------------|-------|
| Adversarial Accuracy | 100.0% | 46.7% | **-53.3%** |
| Attack Success Rate | 0.0% | 53.3% | **+53.3%** |
| Robustness Degradation | 0.0% | 53.3% | **+53.3%** |

**Conclusion** : L'écart massif entre FGSM et PGD (53.3 points) confirme que :
- Les attaques itératives exploitent plus efficacement les vulnérabilités du modèle
- La robustesse apparente contre FGSM est insuffisante pour garantir la sécurité
- **PGD est la métrique critique** pour évaluer la robustesse réelle du modèle

### 4.2.4.5 Certification de sécurité du Baseline

**Évaluation selon critères de production** :

| Critère | Seuil | Résultat Baseline | Status |
|---------|-------|-------------------|--------|
| **Clean Accuracy** | ≥ 95% | 100.0% | ✅ **PASSED** |
| **FGSM Robustness** | ≥ 80% | 100.0% | ✅ **PASSED** |
| **PGD Robustness** | ≥ 80% | 46.7% | ❌ **FAILED** |
| **Production Ready** | 3/3 critères | 2/3 critères | ❌ **NOT READY** |

**Security Grade : C (Vulnérable)**
- **Threat Level** : MEDIUM
- **Confidence Level** : LOW
- **Recommandation** : **Development only - NOT production ready**

**Conclusion de l'évaluation** :
Le modèle baseline, bien que performant sur données propres (100% accuracy), présente une vulnérabilité critique aux attaques adversariales PGD (53.3% ASR). Il ne satisfait pas les critères de sécurité pour un déploiement en production dans un environnement adversarial. **Des mécanismes de défense avancés sont impératifs.**
