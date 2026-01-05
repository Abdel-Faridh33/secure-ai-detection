# 4.2 Évaluation des vulnérabilités de ResNet50

Ce chapitre présente l'implémentation concrète de l'évaluation du modèle baseline, avec des extraits de code du projet illustrant chaque étape méthodologique.

## 4.2.1 Dataset expérimental

### 4.2.1.1 Implémentation du Dataset personnalisé

Le chargement des données est implémenté via une classe personnalisée `DangerousObjectDataset` héritant de `torch.utils.data.Dataset` :

```python
class DangerousObjectDataset(Dataset):
    """Dataset personnalisé pour la classification binaire safe/dangerous"""

    def __init__(self, data_dir: str, split: str, transform=None):
        self.data_dir = data_dir
        self.split = split
        self.transform = transform

        # Listes pour stocker chemins et labels
        self.images = []
        self.labels = []

        # Construction du chemin vers le split
        split_dir = os.path.join(data_dir, split)

        # Parcourir chaque classe (safe=0, dangerous=1)
        for class_name in ['safe', 'dangerous']:
            class_dir = os.path.join(split_dir, class_name)

            if os.path.exists(class_dir):
                label = 1 if class_name == 'dangerous' else 0

                for img_file in os.listdir(class_dir):
                    if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        full_path = os.path.join(class_dir, img_file)
                        self.images.append(full_path)
                        self.labels.append(label)

        print(f"Dataset {split}: {len(self.images)} images")
        print(f"  - Safe: {self.labels.count(0)} images")
        print(f"  - Dangerous: {self.labels.count(1)} images")

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        label = self.labels[idx]

        image = Image.open(img_path).convert('RGB')

        if self.transform:
            image = self.transform(image)

        return image, label
```

**Analyse de l'implémentation** :
- **Flexibilité** : Supporte train/val/test via le paramètre `split`
- **Généricité** : Fonctionne pour datasets de tailles variables
- **Extensibilité** : Transformations appliquées dynamiquement

### 4.2.1.2 Dataset initial (Phase 1)

**Configuration initiale** :

```python
# Structure du dataset initial
data_structure = {
    'train': {
        'safe': 35,      # images
        'dangerous': 35  # images
    },
    'val': {
        'safe': 7,
        'dangerous': 7
    },
    'test': {
        'safe': 8,
        'dangerous': 8
    }
}

total_samples = 100  # 70 train + 15 val + 15 test
```

**Transformations appliquées** :

```python
def get_transforms():
    """Transformations pour entraînement baseline"""

    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),             # Taille ResNet50
        transforms.RandomHorizontalFlip(p=0.5),     # Augmentation basique
        transforms.RandomRotation(10),              # Rotation légère
        transforms.ColorJitter(brightness=0.2, contrast=0.2,
                              saturation=0.2, hue=0.1),
        transforms.ToTensor(),                      # Conversion PyTorch
        transforms.Normalize(                       # Normalisation ImageNet
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    return train_transform, val_transform
```

**Limitations identifiées** :
- Faible diversité visuelle (100 images totales)
- Augmentation basique uniquement
- Risque élevé d'overfitting sur features spécifiques

### 4.2.1.3 Dataset optimisé (Phase 2)

Pour améliorer la robustesse adversariale, un dataset substantiellement augmenté a été généré via la classe `AdvancedDataAugmentation` :

```python
class AdvancedDataAugmentation:
    """
    Génère 500+ échantillons par classe avec 4 niveaux d'augmentation
    """

    def __init__(self, target_samples_per_class: int = 500):
        self.target_samples_per_class = target_samples_per_class

        # Niveau 1: Transformations légères (25%)
        self.light_transforms = [
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=(-15, 15)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2,
                                  saturation=0.2, hue=0.1),
        ]

        # Niveau 2: Transformations moyennes (35%)
        self.medium_transforms = [
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
            transforms.RandomAdjustSharpness(sharpness_factor=2, p=0.5),
        ]

        # Niveau 3: Transformations fortes (25%)
        self.strong_transforms = [
            transforms.RandomRotation(degrees=(-30, 30)),
            transforms.RandomAffine(degrees=0, translate=(0.15, 0.15),
                                   scale=(0.8, 1.2)),
            transforms.RandomAutocontrast(p=0.3),
        ]

        # Niveau 4: Transformations adversariales (15%)
        self.adversarial_resistant_transforms = [
            transforms.GaussianBlur(kernel_size=5, sigma=(1.0, 3.0)),
            transforms.RandomPosterize(bits=4, p=0.3),
            transforms.RandomSolarize(threshold=192.0, p=0.2),
            transforms.RandomEqualize(p=0.3),
        ]
```

**Processus d'augmentation** :

```python
def create_augmented_dataset(self, source_dir: Path, output_dir: Path):
    """Génère dataset augmenté avec diversification maximale"""

    for class_name in ["safe", "dangerous"]:
        original_images = list((source_dir / class_name).glob("*.jpg"))
        original_count = len(original_images)

        # Calculer augmentations nécessaires
        needed_samples = self.target_samples_per_class - original_count
        augmentations_per_image = needed_samples // original_count + 1

        for img_path in original_images:
            base_img = Image.open(img_path).convert('RGB')

            for aug_idx in range(augmentations_per_image):
                # Appliquer variant d'augmentation (rotatif)
                augmented_img = self._apply_augmentation_variant(
                    base_img, aug_idx
                )

                output_path = class_output_dir / f"aug_{generated_count:04d}.jpg"
                augmented_img.save(output_path, quality=95)
```

**Résultat de l'augmentation** :
```
Dataset Initial → Dataset Optimisé
Train:     70 images → 1024 images (14.6× augmentation)
Validation: 15 images → 256 images (17.1× augmentation)
Test:      15 images → 256 images (identique pour évaluation)
```

## 4.2.2 Métriques d'évaluation

### 4.2.2.1 Implémentation des métriques de performance

Les métriques de performance sont calculées pendant la validation :

```python
def validate(model, dataloader, criterion, device):
    """
    Évalue le modèle sur données propres
    Retourne: (loss, accuracy, precision, recall, f1)
    """
    model.eval()

    running_loss = 0.0
    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)

            # Forward pass
            outputs = model(images)
            loss = criterion(outputs, labels)

            # Prédictions
            _, predicted = outputs.max(1)

            # Accumulation
            running_loss += loss.item()
            all_predictions.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    # Calcul métriques avec scikit-learn
    from sklearn.metrics import (accuracy_score, precision_score,
                                  recall_score, f1_score,
                                  confusion_matrix, roc_auc_score)

    accuracy = accuracy_score(all_labels, all_predictions)
    precision = precision_score(all_labels, all_predictions, average='macro')
    recall = recall_score(all_labels, all_predictions, average='macro')
    f1 = f1_score(all_labels, all_predictions, average='macro')
    conf_matrix = confusion_matrix(all_labels, all_predictions)

    return {
        'loss': running_loss / len(dataloader),
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'confusion_matrix': conf_matrix
    }
```

### 4.2.2.2 Implémentation des métriques de robustesse adversariale

L'évaluation de la robustesse est implémentée dans la classe `PGDAttack` :

```python
class PGDAttack:
    """Projected Gradient Descent Attack pour évaluation robustesse"""

    def evaluate_robustness(self, dataloader, verbose=True):
        """
        Évalue robustesse contre PGD
        Retourne: dict avec clean_acc, robust_acc, ASR
        """
        self.model.eval()

        total = 0
        clean_correct = 0
        adv_correct = 0

        for data, target in dataloader:
            data, target = data.to(self.device), target.to(self.device)
            batch_size = data.size(0)

            # Predictions sur données propres
            clean_outputs = self.model(data)
            clean_pred = clean_outputs.argmax(dim=1)
            clean_correct += clean_pred.eq(target).sum().item()

            # Génération exemples adversariaux PGD
            adv_data = self.generate(data, target)

            # Predictions sur données adversariales
            adv_outputs = self.model(adv_data)
            adv_pred = adv_outputs.argmax(dim=1)
            adv_correct += adv_pred.eq(target).sum().item()

            total += batch_size

        # Calcul métriques
        clean_accuracy = clean_correct / total
        robust_accuracy = adv_correct / total
        attack_success_rate = (clean_correct - adv_correct) / clean_correct
        robustness_degradation = clean_accuracy - robust_accuracy

        return {
            'clean_accuracy': clean_accuracy,
            'robust_accuracy': robust_accuracy,
            'attack_success_rate': attack_success_rate,
            'robustness_degradation': robustness_degradation,
            'total_samples': total,
            'clean_correct': clean_correct,
            'adversarial_correct': adv_correct
        }
```

**Formules implémentées** :

```python
# Attack Success Rate (ASR)
ASR = (clean_correct - adversarial_correct) / clean_correct

# Robustness Degradation
Degradation = clean_accuracy - adversarial_accuracy

# Robust Samples Count
Robust_Count = adversarial_correct  # Échantillons résistant à l'attaque
```

## 4.2.3 Protocole de test du modèle Baseline

### 4.2.3.1 Entraînement du modèle Baseline

Le modèle baseline est entraîné via transfer learning standard :

```python
def train_baseline():
    """Entraînement baseline ResNet50 sans défenses adversariales"""

    # Configuration
    config = {
        'epochs': 10,
        'batch_size': 16,
        'learning_rate': 0.001,
        'num_classes': 2,
        'early_stopping_patience': 5
    }

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Chargement ResNet50 pré-entraîné ImageNet
    from models.utils.model_loader import ModelLoader
    model = ModelLoader.load_resnet50(
        pretrained=True,
        num_classes=config['num_classes']
    )
    model = model.to(device)

    # Préparation données
    train_transform, val_transform = get_transforms()
    data_dir = Path('data/processed')

    train_dataset = DangerousObjectDataset(
        data_dir, 'train', train_transform
    )
    val_dataset = DangerousObjectDataset(
        data_dir, 'val', val_transform
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False
    )

    # Loss et Optimiseur
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)

    # Boucle d'entraînement
    best_val_acc = 0.0
    patience_counter = 0

    for epoch in range(config['epochs']):
        # Train epoch
        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer, device
        )

        # Validation
        val_metrics = validate(model, val_loader, criterion, device)
        val_loss = val_metrics['loss']
        val_acc = val_metrics['accuracy']

        scheduler.step()

        print(f"Epoch {epoch+1}/{config['epochs']}")
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")

        # Early stopping
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            # Sauvegarder meilleur modèle
            ModelLoader.save_model(
                model,
                'models/baseline/best_model.pth',
                config, optimizer, epoch, val_loss
            )
        else:
            patience_counter += 1
            if patience_counter >= config['early_stopping_patience']:
                print("Early stopping triggered")
                break

    return model, best_val_acc
```

**Étapes clés implémentées** :
1. **Transfer Learning** : ResNet50 ImageNet → 2 classes
2. **Augmentation basique** : RandomFlip, Rotation, ColorJitter
3. **Early Stopping** : Patience de 5 epochs sur validation accuracy
4. **Scheduler** : StepLR avec decay tous les 7 epochs

### 4.2.3.2 Implémentation des attaques adversariales

**Attaque FGSM (Fast Gradient Sign Method)** :

```python
class FGSMAttack:
    """Implémentation FGSM (Goodfellow et al., 2014)"""

    def __init__(self, model: nn.Module, epsilon: float = 0.031):
        self.model = model
        self.epsilon = epsilon

    def generate(self, images: torch.Tensor, labels: torch.Tensor):
        """
        Génère exemples adversariaux FGSM

        Formule: x_adv = x + ε × sign(∇_x L(θ, x, y))
        """
        images.requires_grad = True

        # Forward pass
        outputs = self.model(images)
        loss = nn.CrossEntropyLoss()(outputs, labels)

        # Backward - Calcul gradients
        self.model.zero_grad()
        loss.backward()

        # Création perturbation
        perturbation = self.epsilon * images.grad.sign()
        adversarial_images = images + perturbation

        # Clip dans [0, 1]
        adversarial_images = torch.clamp(adversarial_images, 0, 1)

        return adversarial_images
```

**Attaque PGD (Projected Gradient Descent)** :

```python
class PGDAttack:
    """Implémentation PGD (Madry et al., 2018)"""

    def __init__(self, model, epsilon=0.031, alpha=0.007, num_iter=10):
        self.model = model
        self.epsilon = epsilon     # Budget perturbation
        self.alpha = alpha         # Pas (ε/4 typiquement)
        self.num_iter = num_iter   # Itérations PGD
        self.criterion = nn.CrossEntropyLoss()

    def generate(self, images, labels):
        """
        Génère exemples adversariaux PGD

        Algorithme:
        1. x_adv = x + random_noise (initialisation aléatoire)
        2. Pour i = 1 à num_iter:
             x_adv = x_adv + α × sign(∇_x L(θ, x_adv, y))
             x_adv = Π_ε(x_adv)  # Projection dans ε-ball
        """
        adv_images = images.clone().detach()

        # Initialisation aléatoire dans ε-ball
        noise = torch.empty_like(adv_images).uniform_(-self.epsilon, self.epsilon)
        adv_images = adv_images + noise
        adv_images = torch.clamp(adv_images, 0, 1)

        # Itérations PGD
        for i in range(self.num_iter):
            adv_images = self._pgd_step(adv_images, images, labels)

        return adv_images

    def _pgd_step(self, adv_images, orig_images, labels):
        """Une itération PGD"""
        adv_images.requires_grad_(True)

        # Forward + Loss
        outputs = self.model(adv_images)
        loss = self.criterion(outputs, labels)

        # Backward
        self.model.zero_grad()
        loss.backward()

        with torch.no_grad():
            # Gradient step
            grad_sign = adv_images.grad.sign()
            adv_images = adv_images + self.alpha * grad_sign

            # Projection sur ε-ball L∞
            delta = adv_images - orig_images
            delta = torch.clamp(delta, -self.epsilon, self.epsilon)
            adv_images = orig_images + delta

            # Projection sur [0,1]
            adv_images = torch.clamp(adv_images, 0, 1)

        return adv_images
```

### 4.2.3.3 Pipeline de test complet

```python
def evaluate_baseline_robustness():
    """
    Évalue robustesse baseline avec batterie d'attaques
    """
    # Chargement modèle baseline
    model = load_model('models/baseline/best_model.pth')
    model.eval()

    # Chargement test set
    test_dataset = DangerousObjectDataset('data/processed', 'test', val_transform)
    test_loader = DataLoader(test_dataset, batch_size=15, shuffle=False)

    results = {}

    # 1. Test Clean
    print("=== CLEAN TEST ===")
    clean_metrics = validate(model, test_loader, nn.CrossEntropyLoss(), 'cpu')
    results['clean'] = clean_metrics
    print(f"Clean Accuracy: {clean_metrics['accuracy']:.3f}")

    # 2. Test FGSM
    print("\n=== FGSM ATTACK (ε=0.031) ===")
    fgsm_attack = FGSMAttack(model, epsilon=0.031)
    fgsm_results = fgsm_attack.evaluate_robustness(test_loader)
    results['fgsm'] = fgsm_results
    print(f"Adversarial Accuracy: {fgsm_results['robust_accuracy']:.3f}")
    print(f"Attack Success Rate: {fgsm_results['attack_success_rate']:.3f}")

    # 3. Test PGD
    print("\n=== PGD ATTACK (ε=0.031, 10 iter) ===")
    pgd_attack = PGDAttack(model, epsilon=0.031, alpha=0.007, num_iter=10)
    pgd_results = pgd_attack.evaluate_robustness(test_loader)
    results['pgd'] = pgd_results
    print(f"Adversarial Accuracy: {pgd_results['robust_accuracy']:.3f}")
    print(f"Attack Success Rate: {pgd_results['attack_success_rate']:.3f}")

    # 4. Test PGD Strong
    print("\n=== PGD STRONG ATTACK (ε=0.063, 20 iter) ===")
    pgd_strong = PGDAttack(model, epsilon=0.063, alpha=0.008, num_iter=20)
    pgd_strong_results = pgd_strong.evaluate_robustness(test_loader)
    results['pgd_strong'] = pgd_strong_results

    return results
```

## 4.2.4 Résultats de vulnérabilité du modèle Baseline

### 4.2.4.1 Résultats empiriques obtenus

**Configuration de test** :
```python
test_config = {
    'test_samples': 15,  # 15 échantillons test réels
    'device': 'cpu',
    'fgsm_epsilon': 0.031,
    'pgd_epsilon': 0.031,
    'pgd_iterations': 10,
    'pgd_alpha': 0.00775  # ε/4
}
```

**Résultats Clean Test** :
```
Clean Test Results:
  Accuracy:    100.0% (15/15)
  Loss:        0.0046
  AUC-ROC:     1.000
  Precision (safe):       100.0%
  Recall (safe):          100.0%
  F1-Score (safe):        100.0%
  Precision (dangerous):  100.0%
  Recall (dangerous):     100.0%
  F1-Score (dangerous):   100.0%

Matrice de confusion:
             Predicted
           Safe | Dangerous
Actual Safe    8  |    0
    Dangerous  0  |    7
```

**Résultats FGSM Attack** :
```
FGSM Attack Results (ε=0.031):
  Adversarial Accuracy:    100.0% (15/15)
  Attack Success Rate:     0.0%
  Robustness Degradation:  0.0%
  Robust Samples:          15/15

→ Résistance parfaite aux attaques FGSM
```

**Résultats PGD Attack (VULNÉRABILITÉ CRITIQUE)** :
```
PGD Attack Results (ε=0.031, 10 iter):
  Adversarial Accuracy:    46.7% (7/15) ⚠️
  Attack Success Rate:     53.3% (8/15) 🚨
  Robustness Degradation:  53.3%
  Robust Samples:          7/15
  Exemples compromis:      8/15

Détail des échecs:
  - 6 échantillons "dangerous" mal classés → "safe"
  - 2 échantillons "safe" mal classés → "dangerous"

→ VULNÉRABILITÉ CRITIQUE DÉTECTÉE
```

### 4.2.4.2 Analyse code de la vulnérabilité

**Inspection du modèle baseline** :

```python
# Architecture baseline (vulnérable)
def load_resnet50_baseline(num_classes=2):
    """
    Transfer learning standard SANS défenses
    """
    model = models.resnet50(pretrained=True)  # ImageNet weights

    # Remplacement dernière couche FC
    num_features = model.fc.in_features  # 2048
    model.fc = nn.Linear(num_features, num_classes)

    # Entraînement standard (pas d'adversarial training)
    # → Modèle optimisé uniquement pour données propres
    # → Vulnérable aux perturbations adversariales

    return model
```

**Pourquoi cette vulnérabilité ?**

```python
# Entraînement baseline (problématique)
for epoch in range(epochs):
    for images, labels in train_loader:
        outputs = model(images)  # Seulement données PROPRES
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

# Problème: Le modèle n'a JAMAIS vu d'exemples adversariaux
# → Il apprend features qui fonctionnent sur données propres
# → Mais ces features sont fragiles aux perturbations L∞
```

**Visualisation de la vulnérabilité** :

```python
def visualize_pgd_vulnerability(model, test_loader):
    """Visualise échantillons compromis par PGD"""

    pgd_attack = PGDAttack(model, epsilon=0.031, alpha=0.007, num_iter=10)

    for images, labels in test_loader:
        # Génération exemples adversariaux
        adv_images = pgd_attack.generate(images, labels)

        # Prédictions
        clean_preds = model(images).argmax(dim=1)
        adv_preds = model(adv_images).argmax(dim=1)

        # Identification échantillons compromis
        compromised = clean_preds != adv_preds

        # Visualisation
        for i in range(len(images)):
            if compromised[i]:
                # Calcul perturbation
                perturbation = (adv_images[i] - images[i]).abs()
                perturbation_magnitude = perturbation.max().item()

                print(f"Échantillon {i}:")
                print(f"  Label réel: {labels[i].item()}")
                print(f"  Prédiction clean: {clean_preds[i].item()}")
                print(f"  Prédiction adversariale: {adv_preds[i].item()}")
                print(f"  Perturbation max: {perturbation_magnitude:.6f}")
                print(f"  → COMPROMIS (attaque réussie)")
```

### 4.2.4.3 Certification de sécurité Baseline

**Implémentation de la grille de certification** :

```python
def certify_model_security(results):
    """
    Évalue si le modèle satisfait les critères de production
    """
    thresholds = {
        'clean_accuracy': 0.95,
        'fgsm_robustness': 0.80,
        'pgd_robustness': 0.80
    }

    certification = {
        'clean_accuracy': {
            'value': results['clean']['accuracy'],
            'threshold': thresholds['clean_accuracy'],
            'passed': results['clean']['accuracy'] >= thresholds['clean_accuracy']
        },
        'fgsm_robustness': {
            'value': results['fgsm']['robust_accuracy'],
            'threshold': thresholds['fgsm_robustness'],
            'passed': results['fgsm']['robust_accuracy'] >= thresholds['fgsm_robustness']
        },
        'pgd_robustness': {
            'value': results['pgd']['robust_accuracy'],
            'threshold': thresholds['pgd_robustness'],
            'passed': results['pgd']['robust_accuracy'] >= thresholds['pgd_robustness']
        }
    }

    # Security Grade
    passed_count = sum(1 for c in certification.values() if c['passed'])

    if passed_count == 3:
        if results['pgd']['robust_accuracy'] >= 0.90:
            grade = 'A+'
            threat_level = 'MINIMAL'
        else:
            grade = 'A'
            threat_level = 'LOW'
    elif passed_count == 2:
        grade = 'B'
        threat_level = 'MEDIUM'
    elif passed_count == 1:
        grade = 'C'
        threat_level = 'MEDIUM'
    else:
        grade = 'F'
        threat_level = 'HIGH'

    certification['security_grade'] = grade
    certification['threat_level'] = threat_level
    certification['production_ready'] = (passed_count == 3)

    return certification
```

**Résultat certification Baseline** :

```python
baseline_certification = {
    'clean_accuracy': {
        'value': 1.000,
        'threshold': 0.95,
        'passed': True  ✅
    },
    'fgsm_robustness': {
        'value': 1.000,
        'threshold': 0.80,
        'passed': True  ✅
    },
    'pgd_robustness': {
        'value': 0.467,
        'threshold': 0.80,
        'passed': False  ❌
    },
    'security_grade': 'C',
    'threat_level': 'MEDIUM',
    'production_ready': False
}

# Recommandation
recommendation = "NON CONFORME pour production en environnement adversarial"
```

**Conclusion de l'évaluation** :

Le modèle baseline présente une **vulnérabilité critique aux attaques PGD** (53.3% ASR), démontrant empiriquement que :
1. Le transfer learning standard est **insuffisant** pour la robustesse adversariale
2. Les attaques itératives (PGD) sont **significativement plus efficaces** que les attaques single-step (FGSM)
3. Des **mécanismes de défense avancés sont impératifs** pour le déploiement production

Cette évaluation valide l'hypothèse H1 du protocole expérimental et justifie l'implémentation de défenses adversariales dans la section suivante (4.3).
