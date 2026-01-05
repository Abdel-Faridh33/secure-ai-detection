"""
Évaluation Finale de Robustesse
Comparaison complète: Baseline vs Adversarial Training Robuste

Test des améliorations apportées par les solutions optimales:
1. Dataset augmenté (500+ échantillons par classe)
2. Données diversifiées (4 niveaux d'augmentation) 
3. Pipeline robuste (PGD, C&W, AutoAttack)
"""

import torch
import torch.nn as nn
import torchvision.models as models
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
from pathlib import Path
import json
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# Imports des modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from attacks.adversarial.auto_attack import create_robust_evaluation_pipeline
from experiments.secured.train_adversarial_robust import DangerousObjectDataset

class RobustnessComparator:
    """
    Comparateur de robustesse entre baseline et modèle adversarial robuste
    """
    
    def __init__(self, device='cpu'):
        self.device = device
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.results_dir = self.project_root / "results" / "final_comparison"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        print("ÉVALUATION FINALE ROBUSTESSE")
        print("Comparaison Baseline vs Adversarial Training Robuste")
        print("=" * 60)
    
    def load_model(self, model_path: Path, model_type: str = "resnet50"):
        """Charge un modèle sauvegardé"""
        if not model_path.exists():
            raise FileNotFoundError(f"Modèle non trouvé: {model_path}")
        
        # Création modèle
        model = models.resnet50(pretrained=False)
        model.fc = nn.Linear(model.fc.in_features, 2)
        
        # Chargement checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
        
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
            print(f"Modèle chargé: {model_type} ({checkpoint.get('method', 'unknown')})")
        else:
            model.load_state_dict(checkpoint)
            print(f"Modèle chargé: {model_type}")
        
        model.eval()
        return model, checkpoint
    
    def create_test_dataloader(self, data_source="augmented", batch_size=8):
        """Crée le dataloader de test"""
        if data_source == "augmented":
            test_dir = self.project_root / "data" / "augmented" / "val"
        else:
            test_dir = self.project_root / "data" / "processed" / "val"
        
        if not test_dir.exists():
            # Fallback
            if data_source == "augmented":
                test_dir = self.project_root / "data" / "processed" / "val"
            else:
                raise FileNotFoundError(f"Répertoire test non trouvé: {test_dir}")
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        dataset = DangerousObjectDataset(root_dir=test_dir, transform=transform)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
        
        print(f"Dataset test chargé: {len(dataset)} échantillons ({data_source})")
        return dataloader
    
    def evaluate_single_model(self, model, model_name: str, test_loader):
        """Évalue un modèle avec AutoAttack"""
        print(f"\n📊 Évaluation {model_name}")
        print("-" * 40)
        
        # Évaluation robuste avec AutoAttack
        results = create_robust_evaluation_pipeline(
            model, test_loader, epsilon=0.031, device=self.device
        )
        
        # Extraction métriques clés
        summary = results.get('summary', {})
        detailed = results.get('detailed', {})
        
        evaluation_metrics = {
            'model_name': model_name,
            'clean_accuracy': summary.get('clean_accuracy', 0),
            'worst_case_robustness': summary.get('worst_case_robustness', 0),
            'attack_results': {
                attack: details.get('robust_accuracy', 0) 
                for attack, details in detailed.items()
            },
            'robustness_gap': summary.get('clean_accuracy', 0) - summary.get('worst_case_robustness', 0)
        }
        
        print(f"Résultats {model_name}:")
        print(f"  Clean Accuracy: {evaluation_metrics['clean_accuracy']:.3f}")
        print(f"  Robustesse (pire cas): {evaluation_metrics['worst_case_robustness']:.3f}")
        print(f"  Gap robustesse: {evaluation_metrics['robustness_gap']:.3f}")
        
        return evaluation_metrics, results
    
    def compare_models(self, baseline_path: Path, robust_path: Path):
        """
        Comparaison complète baseline vs adversarial robuste
        """
        print("🔍 COMPARAISON BASELINE vs ADVERSARIAL ROBUSTE")
        print("=" * 60)
        
        # Chargement modèles
        try:
            baseline_model, baseline_checkpoint = self.load_model(baseline_path, "Baseline")
        except FileNotFoundError:
            print(f"❌ Modèle baseline non trouvé: {baseline_path}")
            return None
        
        try:
            robust_model, robust_checkpoint = self.load_model(robust_path, "Adversarial Robuste")
        except FileNotFoundError:
            print(f"❌ Modèle robuste non trouvé: {robust_path}")
            return None
        
        # Création dataloader de test
        test_loader = self.create_test_dataloader(data_source="augmented")
        
        # Évaluations
        baseline_metrics, baseline_results = self.evaluate_single_model(
            baseline_model, "Baseline", test_loader
        )
        
        robust_metrics, robust_results = self.evaluate_single_model(
            robust_model, "Adversarial Robuste", test_loader
        )
        
        # Analyse comparative
        comparison = self.analyze_improvements(baseline_metrics, robust_metrics)
        
        # Génération rapport
        report = self.generate_final_report(
            baseline_metrics, robust_metrics, comparison,
            baseline_checkpoint, robust_checkpoint
        )
        
        return report
    
    def analyze_improvements(self, baseline_metrics, robust_metrics):
        """Analyse des améliorations apportées"""
        improvements = {
            'clean_accuracy_delta': robust_metrics['clean_accuracy'] - baseline_metrics['clean_accuracy'],
            'robustness_delta': robust_metrics['worst_case_robustness'] - baseline_metrics['worst_case_robustness'],
            'gap_reduction': baseline_metrics['robustness_gap'] - robust_metrics['robustness_gap'],
            'relative_robustness_improvement': (
                robust_metrics['worst_case_robustness'] / baseline_metrics['worst_case_robustness'] - 1
                if baseline_metrics['worst_case_robustness'] > 0 else float('inf')
            )
        }
        
        # Évaluation du succès
        success_criteria = {\n            'robustness_improved': improvements['robustness_delta'] > 0,\n            'gap_reduced': improvements['gap_reduction'] > 0,\n            'clean_maintained': improvements['clean_accuracy_delta'] > -0.05,  # Tolérance 5%\n        }\n        \n        success_score = sum(success_criteria.values()) / len(success_criteria)\n        \n        print(f\"\\n📈 ANALYSE DES AMÉLIORATIONS\")\n        print(\"-\" * 40)\n        print(f\"Amélioration robustesse: {improvements['robustness_delta']:+.3f}\")\n        print(f\"Réduction gap robustesse: {improvements['gap_reduction']:+.3f}\")\n        print(f\"Maintien clean accuracy: {improvements['clean_accuracy_delta']:+.3f}\")\n        print(f\"Amélioration relative: {improvements['relative_robustness_improvement']:+.1%}\")\n        print(f\"\\nScore de succès: {success_score:.1%}\")\n        \n        if success_score >= 0.67:\n            print(\"✅ SUCCÈS: Solutions optimales efficaces\")\n        elif success_score >= 0.33:\n            print(\"⚠️ PARTIEL: Améliorations mitigées\")\n        else:\n            print(\"❌ ÉCHEC: Pas d'amélioration significative\")\n        \n        return {\n            'improvements': improvements,\n            'success_criteria': success_criteria,\n            'success_score': success_score\n        }\n    \n    def generate_final_report(self, baseline_metrics, robust_metrics, comparison, \n                             baseline_checkpoint, robust_checkpoint):\n        \"\"\"Génère le rapport final complet\"\"\"\n        timestamp = datetime.now().strftime(\"%Y%m%d_%H%M%S\")\n        \n        report = {\n            'evaluation_info': {\n                'timestamp': datetime.now().isoformat(),\n                'comparison_type': 'Baseline vs Adversarial Training Robuste',\n                'solutions_implemented': [\n                    'Dataset augmenté (1000+ échantillons)',\n                    'Données diversifiées (4 niveaux)',\n                    'Pipeline robuste (PGD, C&W, AutoAttack)'\n                ]\n            },\n            'models_info': {\n                'baseline': {\n                    'method': baseline_checkpoint.get('method', 'Standard Training'),\n                    'config': baseline_checkpoint.get('config', {}),\n                    'timestamp': baseline_checkpoint.get('timestamp', 'unknown')\n                },\n                'robust': {\n                    'method': robust_checkpoint.get('method', 'Adversarial Training'),\n                    'solutions': robust_checkpoint.get('solutions_implemented', []),\n                    'config': robust_checkpoint.get('config', {}),\n                    'timestamp': robust_checkpoint.get('timestamp', 'unknown')\n                }\n            },\n            'evaluation_results': {\n                'baseline': baseline_metrics,\n                'adversarial_robust': robust_metrics\n            },\n            'comparative_analysis': comparison,\n            'conclusions': {\n                'solutions_effectiveness': 'high' if comparison['success_score'] >= 0.67 else 'partial',\n                'recommendation': 'production_ready' if comparison['success_score'] >= 0.67 else 'further_optimization',\n                'key_insights': self._generate_insights(comparison)\n            }\n        }\n        \n        # Sauvegarde rapport JSON\n        report_file = self.results_dir / f\"final_robustness_comparison_{timestamp}.json\"\n        with open(report_file, 'w') as f:\n            json.dump(report, f, indent=2)\n        \n        # Graphiques comparatifs\n        self._plot_comparison(baseline_metrics, robust_metrics, timestamp)\n        \n        print(f\"\\n📋 Rapport final sauvegardé: {report_file}\")\n        \n        return report\n    \n    def _generate_insights(self, comparison):\n        \"\"\"Génère les insights clés\"\"\"\n        insights = []\n        \n        if comparison['improvements']['robustness_delta'] > 0.1:\n            insights.append(\"Amélioration robustesse significative (>10%)\")\n        \n        if comparison['improvements']['gap_reduction'] > 0.05:\n            insights.append(\"Réduction substantielle du gap clean/adversarial\")\n        \n        if comparison['success_score'] >= 0.67:\n            insights.append(\"Solutions optimales validées expérimentalement\")\n        \n        return insights\n    \n    def _plot_comparison(self, baseline_metrics, robust_metrics, timestamp):\n        \"\"\"Génère graphiques de comparaison\"\"\"\n        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))\n        \n        # Comparaison accuracies\n        models = ['Baseline', 'Adversarial\\nRobuste']\n        clean_accs = [baseline_metrics['clean_accuracy'], robust_metrics['clean_accuracy']]\n        robust_accs = [baseline_metrics['worst_case_robustness'], robust_metrics['worst_case_robustness']]\n        \n        x = np.arange(len(models))\n        width = 0.35\n        \n        ax1.bar(x - width/2, clean_accs, width, label='Clean Accuracy', alpha=0.8)\n        ax1.bar(x + width/2, robust_accs, width, label='Robust Accuracy', alpha=0.8)\n        ax1.set_ylabel('Accuracy')\n        ax1.set_title('Comparaison Clean vs Robust Accuracy')\n        ax1.set_xticks(x)\n        ax1.set_xticklabels(models)\n        ax1.legend()\n        ax1.grid(True, alpha=0.3)\n        \n        # Gap robustesse\n        gaps = [baseline_metrics['robustness_gap'], robust_metrics['robustness_gap']]\n        ax2.bar(models, gaps, color=['red', 'orange'], alpha=0.7)\n        ax2.set_ylabel('Robustness Gap')\n        ax2.set_title('Gap Clean/Adversarial Accuracy')\n        ax2.grid(True, alpha=0.3)\n        \n        # Détail par attaque (si disponible)\n        if baseline_metrics.get('attack_results') and robust_metrics.get('attack_results'):\n            attacks = list(baseline_metrics['attack_results'].keys())\n            baseline_attack_accs = [baseline_metrics['attack_results'][att] for att in attacks]\n            robust_attack_accs = [robust_metrics['attack_results'][att] for att in attacks]\n            \n            x_att = np.arange(len(attacks))\n            ax3.bar(x_att - width/2, baseline_attack_accs, width, label='Baseline', alpha=0.8)\n            ax3.bar(x_att + width/2, robust_attack_accs, width, label='Robust', alpha=0.8)\n            ax3.set_ylabel('Robust Accuracy')\n            ax3.set_title('Robustesse par Type d\\'Attaque')\n            ax3.set_xticks(x_att)\n            ax3.set_xticklabels(attacks, rotation=45)\n            ax3.legend()\n            ax3.grid(True, alpha=0.3)\n        \n        plt.tight_layout()\n        plt.savefig(self.results_dir / f\"robustness_comparison_{timestamp}.png\", \n                    dpi=300, bbox_inches='tight')\n        plt.close()\n        \n        print(f\"📊 Graphiques sauvegardés: robustness_comparison_{timestamp}.png\")\n\ndef evaluate_final_robustness():\n    \"\"\"\n    Fonction principale d'évaluation finale\n    \"\"\"\n    comparator = RobustnessComparator()\n    \n    # Chemins des modèles\n    project_root = Path(__file__).parent.parent.parent.parent\n    baseline_path = project_root / \"models\" / \"baseline\" / \"best_model.pth\"\n    \n    # Chercher le meilleur modèle adversarial robuste\n    robust_dir = project_root / \"models\" / \"adversarial_robust\"\n    \n    if robust_dir.exists():\n        robust_models = list(robust_dir.glob(\"best_*.pth\"))\n        if not robust_models:\n            robust_models = list(robust_dir.glob(\"*.pth\"))\n        \n        if robust_models:\n            # Prendre le plus récent\n            robust_path = max(robust_models, key=lambda x: x.stat().st_mtime)\n        else:\n            print(\"❌ Aucun modèle adversarial robuste trouvé\")\n            return None\n    else:\n        print(\"❌ Répertoire modèles adversarial robuste non trouvé\")\n        return None\n    \n    # Comparaison\n    report = comparator.compare_models(baseline_path, robust_path)\n    \n    return report\n\nif __name__ == \"__main__\":\n    print(\"🔍 ÉVALUATION FINALE DE ROBUSTESSE\")\n    print(\"Comparaison des améliorations apportées par les solutions optimales\")\n    \n    report = evaluate_final_robustness()\n    \n    if report:\n        print(\"\\n🎯 ÉVALUATION TERMINÉE\")\n        print(\"Consultez les fichiers générés pour l'analyse détaillée\")\n    else:\n        print(\"\\n❌ Évaluation impossible - modèles manquants\")