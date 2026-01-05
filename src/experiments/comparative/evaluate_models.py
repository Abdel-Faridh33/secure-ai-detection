#!/usr/bin/env python3
"""
Évaluation comparative Baseline vs Secured
Avec métriques statistiques robustes et tests d'adversarial robustness
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import transforms, models
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List
import json
from tqdm import tqdm
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score
)
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))


class DangerousObjectDataset:
    """Dataset simple pour l'évaluation"""

    def __init__(self, data_dir: str, split: str, transform=None):
        from PIL import Image
        from torch.utils.data import Dataset

        self.data_dir = Path(data_dir)
        self.split = split
        self.transform = transform

        self.images = []
        self.labels = []

        split_dir = self.data_dir / split

        # Classe safe (0)
        safe_dir = split_dir / 'safe'
        if safe_dir.exists():
            for img_path in safe_dir.glob('*.jpg'):
                self.images.append(str(img_path))
                self.labels.append(0)

        # Classe dangerous (1)
        dangerous_dir = split_dir / 'dangerous'
        if dangerous_dir.exists():
            for img_path in dangerous_dir.glob('*.jpg'):
                self.images.append(str(img_path))
                self.labels.append(1)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        from PIL import Image
        img_path = self.images[idx]
        label = self.labels[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image, label


class MobileNetV2Classifier(nn.Module):
    """Classifier MobileNetV2"""

    def __init__(self, num_classes: int = 2, dropout: float = 0.3):
        super().__init__()
        self.mobilenet = models.mobilenet_v2(pretrained=False)
        in_features = self.mobilenet.classifier[1].in_features

        # Baseline version (simple)
        if dropout <= 0.35:
            self.mobilenet.classifier = nn.Sequential(
                nn.Dropout(dropout),
                nn.Linear(in_features, 256),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(256, num_classes)
            )
        # Secured version (plus complexe)
        else:
            self.mobilenet.classifier = nn.Sequential(
                nn.Dropout(dropout),
                nn.Linear(in_features, 512),
                nn.ReLU(),
                nn.BatchNorm1d(512),
                nn.Dropout(dropout),
                nn.Linear(512, 256),
                nn.ReLU(),
                nn.BatchNorm1d(256),
                nn.Dropout(dropout * 0.5),
                nn.Linear(256, num_classes)
            )

    def forward(self, x):
        return self.mobilenet(x)


class AdversarialAttacks:
    """Implémentation des attaques adversariales"""

    @staticmethod
    def fgsm_attack(
        model: nn.Module,
        images: torch.Tensor,
        labels: torch.Tensor,
        epsilon: float = 8/255
    ) -> torch.Tensor:
        """
        Fast Gradient Sign Method (FGSM)

        Args:
            model: Modèle à attaquer
            images: Images naturelles
            labels: Labels
            epsilon: Magnitude de la perturbation

        Returns:
            Images adversariales
        """
        images.requires_grad = True

        # Forward
        outputs = model(images)
        loss = F.cross_entropy(outputs, labels)

        # Backward
        model.zero_grad()
        loss.backward()

        # Générer la perturbation
        perturbation = epsilon * images.grad.sign()

        # Appliquer la perturbation
        adv_images = images + perturbation
        adv_images = torch.clamp(adv_images, 0, 1)

        return adv_images.detach()

    @staticmethod
    def pgd_attack(
        model: nn.Module,
        images: torch.Tensor,
        labels: torch.Tensor,
        epsilon: float = 8/255,
        alpha: float = 2/255,
        num_iter: int = 10
    ) -> torch.Tensor:
        """
        Projected Gradient Descent (PGD)

        Args:
            model: Modèle à attaquer
            images: Images naturelles
            labels: Labels
            epsilon: Perturbation maximale (L∞)
            alpha: Step size
            num_iter: Nombre d'itérations

        Returns:
            Images adversariales
        """
        adv_images = images.clone().detach()

        # Random start
        adv_images = adv_images + torch.zeros_like(adv_images).uniform_(-epsilon, epsilon)
        adv_images = torch.clamp(adv_images, 0, 1)

        for _ in range(num_iter):
            adv_images.requires_grad = True

            # Forward
            outputs = model(adv_images)
            loss = F.cross_entropy(outputs, labels)

            # Backward
            model.zero_grad()
            loss.backward()

            # Update
            adv_images = adv_images.detach() + alpha * adv_images.grad.sign()

            # Project sur L∞ ball
            eta = torch.clamp(adv_images - images, -epsilon, epsilon)
            adv_images = torch.clamp(images + eta, 0, 1).detach()

        return adv_images


class ModelEvaluator:
    """Évaluateur de modèles avec métriques complètes"""

    def __init__(
        self,
        baseline_model_path: str,
        secured_model_path: str,
        data_dir: str = "data/prepared",
        device: str = None
    ):
        """
        Args:
            baseline_model_path: Chemin vers le modèle baseline
            secured_model_path: Chemin vers le modèle secured
            data_dir: Dossier des données
            device: Device (auto-detect si None)
        """
        self.baseline_path = Path(baseline_model_path)
        self.secured_path = Path(secured_model_path)
        self.data_dir = data_dir

        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"🖥️  Device: {self.device}")

        # Charger les modèles
        self.baseline_model = self._load_model(self.baseline_path, dropout=0.3)
        self.secured_model = self._load_model(self.secured_path, dropout=0.4)

        # Attaques
        self.attacks = AdversarialAttacks()

        # Résultats
        self.results = {}

    def _load_model(self, model_path: Path, dropout: float = 0.3) -> nn.Module:
        """Charge un modèle depuis un checkpoint"""
        print(f"\n📂 Chargement modèle: {model_path}")

        model = MobileNetV2Classifier(num_classes=2, dropout=dropout)
        checkpoint = torch.load(model_path, map_location=self.device)

        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)

        model = model.to(self.device)
        model.eval()

        print("  ✓ Modèle chargé")
        return model

    def create_dataloader(self, split: str = 'test') -> DataLoader:
        """Crée le dataloader pour l'évaluation"""
        from torch.utils.data import Dataset

        class CustomDataset(Dataset):
            def __init__(self, base_dataset):
                self.dataset = base_dataset
            def __len__(self):
                return len(self.dataset)
            def __getitem__(self, idx):
                return self.dataset[idx]

        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])

        dataset = DangerousObjectDataset(self.data_dir, split, transform)
        wrapped_dataset = CustomDataset(dataset)

        return DataLoader(
            wrapped_dataset,
            batch_size=32,
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )

    def evaluate_clean_accuracy(
        self,
        model: nn.Module,
        dataloader: DataLoader
    ) -> Dict:
        """Évalue l'accuracy sur données propres"""
        model.eval()

        all_preds = []
        all_labels = []
        all_probs = []

        with torch.no_grad():
            for images, labels in tqdm(dataloader, desc="Clean eval"):
                images = images.to(self.device)
                labels = labels.to(self.device)

                outputs = model(images)
                probs = F.softmax(outputs, dim=1)
                _, preds = outputs.max(1)

                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probs.extend(probs[:, 1].cpu().numpy())

        # Métriques
        acc = accuracy_score(all_labels, all_preds)
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_preds, average='binary'
        )
        cm = confusion_matrix(all_labels, all_preds)
        auc = roc_auc_score(all_labels, all_probs)

        return {
            'accuracy': acc * 100,
            'precision': precision * 100,
            'recall': recall * 100,
            'f1': f1 * 100,
            'auc': auc,
            'confusion_matrix': cm,
            'predictions': all_preds,
            'labels': all_labels,
            'probs': all_probs
        }

    def evaluate_adversarial_robustness(
        self,
        model: nn.Module,
        dataloader: DataLoader,
        attack_type: str = 'fgsm',
        epsilon: float = 8/255
    ) -> Dict:
        """Évalue la robustness aux attaques adversariales"""
        model.eval()

        all_preds_clean = []
        all_preds_adv = []
        all_labels = []

        for images, labels in tqdm(dataloader, desc=f"{attack_type.upper()} attack"):
            images = images.to(self.device)
            labels = labels.to(self.device)

            # Prédictions sur images propres
            with torch.no_grad():
                outputs_clean = model(images)
                _, preds_clean = outputs_clean.max(1)

            # Générer images adversariales
            if attack_type == 'fgsm':
                adv_images = self.attacks.fgsm_attack(model, images, labels, epsilon)
            elif attack_type == 'pgd':
                adv_images = self.attacks.pgd_attack(model, images, labels, epsilon)
            else:
                raise ValueError(f"Unknown attack: {attack_type}")

            # Prédictions sur images adversariales
            with torch.no_grad():
                outputs_adv = model(adv_images)
                _, preds_adv = outputs_adv.max(1)

            all_preds_clean.extend(preds_clean.cpu().numpy())
            all_preds_adv.extend(preds_adv.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

        # Calcul du Attack Success Rate (ASR)
        # ASR = % d'images où la prédiction change après l'attaque
        clean_correct = np.array(all_preds_clean) == np.array(all_labels)
        adv_correct = np.array(all_preds_adv) == np.array(all_labels)

        # ASR parmi les images correctement classifiées initialement
        asr = 100 * (1 - adv_correct[clean_correct].mean())

        # Robust accuracy = accuracy sur images adversariales
        robust_acc = accuracy_score(all_labels, all_preds_adv) * 100

        return {
            'attack_type': attack_type,
            'epsilon': epsilon,
            'clean_accuracy': accuracy_score(all_labels, all_preds_clean) * 100,
            'robust_accuracy': robust_acc,
            'attack_success_rate': asr,
            'robustness_drop': accuracy_score(all_labels, all_preds_clean) * 100 - robust_acc
        }

    def statistical_comparison(
        self,
        baseline_preds: np.ndarray,
        secured_preds: np.ndarray,
        labels: np.ndarray
    ) -> Dict:
        """Compare statistiquement baseline vs secured"""

        # Accuracy par modèle
        baseline_correct = (baseline_preds == labels).astype(int)
        secured_correct = (secured_preds == labels).astype(int)

        # Test de McNemar (paired test)
        # H0: les deux modèles ont la même accuracy
        n01 = np.sum((baseline_correct == 0) & (secured_correct == 1))
        n10 = np.sum((baseline_correct == 1) & (secured_correct == 0))

        if n01 + n10 > 0:
            mcnemar_stat = (abs(n01 - n10) - 1) ** 2 / (n01 + n10)
            mcnemar_p = 1 - stats.chi2.cdf(mcnemar_stat, 1)
        else:
            mcnemar_stat = 0
            mcnemar_p = 1.0

        # Intervalles de confiance (95%)
        def confidence_interval(acc, n):
            z = 1.96  # 95% CI
            margin = z * np.sqrt(acc * (1 - acc) / n)
            return acc - margin, acc + margin

        n = len(labels)
        baseline_acc = baseline_correct.mean()
        secured_acc = secured_correct.mean()

        baseline_ci = confidence_interval(baseline_acc, n)
        secured_ci = confidence_interval(secured_acc, n)

        return {
            'mcnemar_statistic': float(mcnemar_stat),
            'mcnemar_p_value': float(mcnemar_p),
            'significant_difference': mcnemar_p < 0.05,
            'baseline_ci_95': (baseline_ci[0] * 100, baseline_ci[1] * 100),
            'secured_ci_95': (secured_ci[0] * 100, secured_ci[1] * 100),
            'n_samples': n
        }

    def run_full_evaluation(self):
        """Lance l'évaluation complète"""
        print("="*60)
        print("🔬 ÉVALUATION COMPARATIVE BASELINE VS SECURED")
        print("="*60)

        # Créer le dataloader
        test_loader = self.create_dataloader('test')

        # 1. Clean Accuracy
        print("\n📊 Évaluation Clean Accuracy...")
        print("-" * 40)

        baseline_clean = self.evaluate_clean_accuracy(self.baseline_model, test_loader)
        secured_clean = self.evaluate_clean_accuracy(self.secured_model, test_loader)

        print(f"\n✓ Baseline Clean Accuracy: {baseline_clean['accuracy']:.2f}%")
        print(f"✓ Secured Clean Accuracy:  {secured_clean['accuracy']:.2f}%")

        # 2. Adversarial Robustness - FGSM
        print("\n⚔️  Évaluation Robustness - FGSM Attack...")
        print("-" * 40)

        baseline_fgsm = self.evaluate_adversarial_robustness(
            self.baseline_model, test_loader, 'fgsm', epsilon=8/255
        )
        secured_fgsm = self.evaluate_adversarial_robustness(
            self.secured_model, test_loader, 'fgsm', epsilon=8/255
        )

        print(f"\n✓ Baseline ASR (FGSM): {baseline_fgsm['attack_success_rate']:.2f}%")
        print(f"✓ Secured ASR (FGSM):  {secured_fgsm['attack_success_rate']:.2f}%")

        # 3. Adversarial Robustness - PGD
        print("\n⚔️  Évaluation Robustness - PGD Attack...")
        print("-" * 40)

        baseline_pgd = self.evaluate_adversarial_robustness(
            self.baseline_model, test_loader, 'pgd', epsilon=8/255
        )
        secured_pgd = self.evaluate_adversarial_robustness(
            self.secured_model, test_loader, 'pgd', epsilon=8/255
        )

        print(f"\n✓ Baseline ASR (PGD): {baseline_pgd['attack_success_rate']:.2f}%")
        print(f"✓ Secured ASR (PGD):  {secured_pgd['attack_success_rate']:.2f}%")

        # 4. Tests statistiques
        print("\n📈 Tests Statistiques...")
        print("-" * 40)

        stats_results = self.statistical_comparison(
            np.array(baseline_clean['predictions']),
            np.array(secured_clean['predictions']),
            np.array(baseline_clean['labels'])
        )

        print(f"\n✓ McNemar test p-value: {stats_results['mcnemar_p_value']:.4f}")
        print(f"  Différence significative: {stats_results['significant_difference']}")

        # Sauvegarder les résultats
        self.results = {
            'baseline': {
                'clean': baseline_clean,
                'fgsm': baseline_fgsm,
                'pgd': baseline_pgd
            },
            'secured': {
                'clean': secured_clean,
                'fgsm': secured_fgsm,
                'pgd': secured_pgd
            },
            'statistical_tests': stats_results
        }

        # Générer le rapport
        self.generate_report()
        self.generate_plots()

        print("\n✅ Évaluation terminée!")

    def generate_report(self):
        """Génère le rapport comparatif"""
        report_dir = Path("results/comparative")
        report_dir.mkdir(parents=True, exist_ok=True)

        # Rapport texte
        report_path = report_dir / "evaluation_report.txt"

        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("RAPPORT D'ÉVALUATION COMPARATIVE - BASELINE VS SECURED\n")
            f.write("="*80 + "\n\n")

            # Clean Performance
            f.write("1. PERFORMANCE SUR DONNÉES PROPRES\n")
            f.write("-" * 40 + "\n")
            f.write(f"Baseline Accuracy: {self.results['baseline']['clean']['accuracy']:.2f}%\n")
            f.write(f"Secured Accuracy:  {self.results['secured']['clean']['accuracy']:.2f}%\n")
            diff = self.results['secured']['clean']['accuracy'] - self.results['baseline']['clean']['accuracy']
            f.write(f"Différence:        {diff:+.2f}%\n\n")

            # FGSM Robustness
            f.write("2. ROBUSTESSE - FGSM ATTACK (ε=8/255)\n")
            f.write("-" * 40 + "\n")
            f.write(f"Baseline ASR: {self.results['baseline']['fgsm']['attack_success_rate']:.2f}%\n")
            f.write(f"Secured ASR:  {self.results['secured']['fgsm']['attack_success_rate']:.2f}%\n")
            improvement = self.results['baseline']['fgsm']['attack_success_rate'] - \
                         self.results['secured']['fgsm']['attack_success_rate']
            f.write(f"Amélioration: {improvement:+.2f}%\n\n")

            # PGD Robustness
            f.write("3. ROBUSTESSE - PGD ATTACK (ε=8/255, 10 iter)\n")
            f.write("-" * 40 + "\n")
            f.write(f"Baseline ASR: {self.results['baseline']['pgd']['attack_success_rate']:.2f}%\n")
            f.write(f"Secured ASR:  {self.results['secured']['pgd']['attack_success_rate']:.2f}%\n")
            improvement = self.results['baseline']['pgd']['attack_success_rate'] - \
                         self.results['secured']['pgd']['attack_success_rate']
            f.write(f"Amélioration: {improvement:+.2f}%\n\n")

            # Statistical Tests
            f.write("4. TESTS STATISTIQUES\n")
            f.write("-" * 40 + "\n")
            stats = self.results['statistical_tests']
            f.write(f"McNemar p-value: {stats['mcnemar_p_value']:.4f}\n")
            f.write(f"Différence significative (α=0.05): {stats['significant_difference']}\n\n")

            f.write(f"Baseline 95% CI: [{stats['baseline_ci_95'][0]:.2f}%, {stats['baseline_ci_95'][1]:.2f}%]\n")
            f.write(f"Secured 95% CI:  [{stats['secured_ci_95'][0]:.2f}%, {stats['secured_ci_95'][1]:.2f}%]\n\n")

        print(f"  📄 Rapport sauvegardé: {report_path}")

        # Sauvegarder les résultats JSON (sans les arrays numpy)
        results_json = {
            'baseline': {
                'clean_accuracy': float(self.results['baseline']['clean']['accuracy']),
                'fgsm_asr': float(self.results['baseline']['fgsm']['attack_success_rate']),
                'pgd_asr': float(self.results['baseline']['pgd']['attack_success_rate'])
            },
            'secured': {
                'clean_accuracy': float(self.results['secured']['clean']['accuracy']),
                'fgsm_asr': float(self.results['secured']['fgsm']['attack_success_rate']),
                'pgd_asr': float(self.results['secured']['pgd']['attack_success_rate'])
            },
            'statistical_tests': {
                'mcnemar_p_value': float(stats['mcnemar_p_value']),
                'significant': bool(stats['significant_difference'])
            }
        }

        json_path = report_dir / "results.json"
        with open(json_path, 'w') as f:
            json.dump(results_json, f, indent=2)

        print(f"  📊 Résultats JSON: {json_path}")

    def generate_plots(self):
        """Génère les graphiques comparatifs"""
        report_dir = Path("results/comparative")
        report_dir.mkdir(parents=True, exist_ok=True)

        # Figure avec 4 subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Comparison des accuracies
        models = ['Baseline', 'Secured']
        clean_accs = [
            self.results['baseline']['clean']['accuracy'],
            self.results['secured']['clean']['accuracy']
        ]
        fgsm_accs = [
            self.results['baseline']['fgsm']['robust_accuracy'],
            self.results['secured']['fgsm']['robust_accuracy']
        ]
        pgd_accs = [
            self.results['baseline']['pgd']['robust_accuracy'],
            self.results['secured']['pgd']['robust_accuracy']
        ]

        x = np.arange(len(models))
        width = 0.25

        axes[0, 0].bar(x - width, clean_accs, width, label='Clean')
        axes[0, 0].bar(x, fgsm_accs, width, label='FGSM')
        axes[0, 0].bar(x + width, pgd_accs, width, label='PGD')
        axes[0, 0].set_ylabel('Accuracy (%)')
        axes[0, 0].set_title('Accuracy Comparison')
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(models)
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Attack Success Rate
        fgsm_asrs = [
            self.results['baseline']['fgsm']['attack_success_rate'],
            self.results['secured']['fgsm']['attack_success_rate']
        ]
        pgd_asrs = [
            self.results['baseline']['pgd']['attack_success_rate'],
            self.results['secured']['pgd']['attack_success_rate']
        ]

        axes[0, 1].bar(x - width/2, fgsm_asrs, width, label='FGSM')
        axes[0, 1].bar(x + width/2, pgd_asrs, width, label='PGD')
        axes[0, 1].set_ylabel('Attack Success Rate (%)')
        axes[0, 1].set_title('Adversarial Attack Success Rate')
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(models)
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Confusion Matrix - Baseline
        cm_baseline = self.results['baseline']['clean']['confusion_matrix']
        sns.heatmap(cm_baseline, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Safe', 'Dangerous'],
                   yticklabels=['Safe', 'Dangerous'],
                   ax=axes[1, 0])
        axes[1, 0].set_title('Baseline - Confusion Matrix')
        axes[1, 0].set_ylabel('True Label')
        axes[1, 0].set_xlabel('Predicted Label')

        # 4. Confusion Matrix - Secured
        cm_secured = self.results['secured']['clean']['confusion_matrix']
        sns.heatmap(cm_secured, annot=True, fmt='d', cmap='Greens',
                   xticklabels=['Safe', 'Dangerous'],
                   yticklabels=['Safe', 'Dangerous'],
                   ax=axes[1, 1])
        axes[1, 1].set_title('Secured - Confusion Matrix')
        axes[1, 1].set_ylabel('True Label')
        axes[1, 1].set_xlabel('Predicted Label')

        plt.tight_layout()
        plot_path = report_dir / 'comparative_plots.png'
        plt.savefig(plot_path, dpi=150)
        print(f"  📈 Graphiques sauvegardés: {plot_path}")

        plt.close()


def main():
    """Point d'entrée principal"""
    evaluator = ModelEvaluator(
        baseline_model_path="models/baseline/best_model.pth",
        secured_model_path="models/secured/best_secured_model.pth",
        data_dir="data/prepared"
    )

    evaluator.run_full_evaluation()


if __name__ == "__main__":
    main()
