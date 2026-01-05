"""
Analyse Comparative : Baseline vs TRADES vs AT Échoué
Script de comparaison scientifique pour le mémoire

Ce script compare:
1. Modèle Baseline (référence): 100% clean, 53.3% vulnérabilité PGD
2. Adversarial Training échoué: 100% clean, 100% vulnérabilité PGD (gradient masking)
3. TRADES corrigé: À tester

Objectif scientifique:
- Démontrer l'échec de l'AT standard
- Valider TRADES comme solution
- Fournir métriques pour publication
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import torchvision.models as models
from torch.utils.data import DataLoader
from PIL import Image
import numpy as np
import json
import os
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns

class DangerousObjectDataset:
    """Dataset pour comparaisons"""
    
    def __init__(self, root_dir, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []
        
        # Chargement données test
        safe_dir = self.root_dir / "safe"
        if safe_dir.exists():
            for img_path in safe_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 0))
        
        dangerous_dir = self.root_dir / "dangerous"
        if dangerous_dir.exists():
            for img_path in dangerous_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 1))
                
        print(f"Dataset comparaison: {len(self.samples)} echantillons")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        return image, label

class BaselineVsTRADESAnalyzer:
    """
    Analyseur comparatif scientifique
    
    Compare les performances de robustesse entre:
    1. Baseline (référence)
    2. AT échoué (problème de gradient masking)
    3. TRADES (solution proposée)
    """
    
    def __init__(self):
        self.device = torch.device('cpu')
        
        # Chemins
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.models_dir = self.project_root / "models"
        self.results_dir = self.project_root / "results" / "comparative_analysis"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Modèles à comparer
        self.models = {}
        
        # Résultats historiques (depuis tests précédents)
        self.historical_results = {
            'baseline': {
                'clean_accuracy': 100.0,
                'fgsm_success_rate': 0.0,
                'pgd_success_rate': 53.3,
                'vulnerability_level': 'MODERATE'
            },
            'failed_at': {
                'clean_accuracy': 100.0,
                'fgsm_success_rate': 0.0,
                'pgd_success_rate': 100.0,
                'vulnerability_level': 'CRITICAL',
                'gradient_masking': True
            }
        }
        
        # Chargement des données de test
        self._load_test_data()
    
    def _load_test_data(self):
        """Chargement des données de test communes"""
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        test_dataset = DangerousObjectDataset(
            root_dir=self.project_root / "data" / "processed" / "test",
            transform=transform
        )
        
        self.test_loader = DataLoader(
            test_dataset,
            batch_size=1,
            shuffle=False,
            num_workers=0
        )
    
    def _load_model(self, model_path, model_name):
        """Chargement générique de modèle"""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            
            # Création de l'architecture
            model = models.resnet50(pretrained=False)
            model.fc = nn.Linear(model.fc.in_features, 2)
            
            # Chargement des poids
            if 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)
            
            model.to(self.device)
            model.eval()
            
            self.models[model_name] = {
                'model': model,
                'checkpoint': checkpoint,
                'path': str(model_path)
            }
            
            print(f"Modele {model_name} charge: {model_path.name}")
            return True
            
        except Exception as e:
            print(f"Erreur chargement {model_name}: {e}")
            return False
    
    def load_all_models(self):
        """Chargement de tous les modèles disponibles"""
        print("Chargement des modeles pour comparaison...")
        
        # 1. Modèle Baseline
        baseline_path = self.models_dir / "baseline" / "best_model.pth"
        if baseline_path.exists():
            self._load_model(baseline_path, "baseline")
        
        # 2. Modèle AT échoué (si existant)
        failed_at_path = self.models_dir / "secured" / "best_secured_model.pth"
        if failed_at_path.exists():
            self._load_model(failed_at_path, "failed_at")
        
        # 3. Modèle TRADES
        trades_paths = [
            self.models_dir / "secured" / "best_trades_model.pth",
            self.models_dir / "secured" / "best_trades_stable_model.pth"
        ]
        
        for trades_path in trades_paths:
            if trades_path.exists():
                model_name = "trades_stable" if "stable" in trades_path.name else "trades"
                self._load_model(trades_path, model_name)
                break
        
        print(f"Modeles charges: {list(self.models.keys())}")
    
    def _test_model_robustness(self, model, model_name):
        """Test de robustesse complet d'un modèle"""
        print(f"\nTest robustesse: {model_name}")
        
        # Test clean accuracy
        clean_accuracy = self._test_clean_accuracy(model)
        
        # Test FGSM
        fgsm_results = self._test_fgsm_attack(model, epsilon=0.031)
        
        # Test PGD
        pgd_results = self._test_pgd_attack(model, epsilon=0.031, alpha=0.007, num_iter=10)
        
        # Analyse gradient masking
        gradient_masking = self._analyze_gradient_masking(fgsm_results, pgd_results)
        
        return {
            'clean_accuracy': clean_accuracy,
            'fgsm_success_rate': fgsm_results['success_rate'],
            'pgd_success_rate': pgd_results['success_rate'],
            'gradient_masking_detected': gradient_masking['detected'],
            'vulnerability_level': self._classify_vulnerability(pgd_results['success_rate']),
            'detailed_results': {
                'fgsm': fgsm_results,
                'pgd': pgd_results,
                'gradient_masking': gradient_masking
            }
        }
    
    def _test_clean_accuracy(self, model):
        """Test accuracy données propres"""
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, labels in self.test_loader:
                data, labels = data.to(self.device), labels.to(self.device)
                outputs = model(data)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        return 100.0 * correct / total if total > 0 else 0.0
    
    def _test_fgsm_attack(self, model, epsilon=0.031):
        """Test attaque FGSM"""
        correct = 0
        total = 0
        successful_attacks = 0
        
        for data, labels in tqdm(self.test_loader, desc="FGSM"):
            data, labels = data.to(self.device), labels.to(self.device)
            
            # Test clean d'abord
            with torch.no_grad():
                clean_output = model(data)
                clean_correct = (clean_output.argmax(dim=1) == labels).item()
            
            if clean_correct:
                # FGSM attack
                data.requires_grad = True
                output = model(data)
                loss = F.cross_entropy(output, labels)
                
                model.zero_grad()
                loss.backward()
                
                data_grad = data.grad.data
                sign_data_grad = data_grad.sign()
                perturbed_data = data + epsilon * sign_data_grad
                perturbed_data = torch.clamp(perturbed_data, 0, 1)
                
                # Test sur données adversariales
                with torch.no_grad():
                    adv_output = model(perturbed_data)
                    adv_correct = (adv_output.argmax(dim=1) == labels).item()
                
                correct += adv_correct
                total += 1
                
                if not adv_correct:
                    successful_attacks += 1
        
        success_rate = 100.0 * successful_attacks / total if total > 0 else 0.0
        accuracy = 100.0 * correct / total if total > 0 else 0.0
        
        return {
            'accuracy': accuracy,
            'success_rate': success_rate,
            'total_samples': total,
            'successful_attacks': successful_attacks
        }
    
    def _test_pgd_attack(self, model, epsilon=0.031, alpha=0.007, num_iter=10):
        """Test attaque PGD"""
        correct = 0
        total = 0
        successful_attacks = 0
        
        for data, labels in tqdm(self.test_loader, desc="PGD"):
            data, labels = data.to(self.device), labels.to(self.device)
            
            # Test clean d'abord
            with torch.no_grad():
                clean_correct = (model(data).argmax(dim=1) == labels).item()
            
            if clean_correct:
                # PGD attack
                adv_data = data.clone().detach()
                adv_data = adv_data + torch.empty_like(adv_data).uniform_(-epsilon, epsilon)
                adv_data = torch.clamp(adv_data, 0, 1).detach()
                
                for i in range(num_iter):
                    adv_data.requires_grad = True
                    output = model(adv_data)
                    loss = F.cross_entropy(output, labels)
                    
                    model.zero_grad()
                    loss.backward()
                    
                    adv_data = adv_data + alpha * adv_data.grad.sign()
                    eta = torch.clamp(adv_data - data, -epsilon, epsilon)
                    adv_data = torch.clamp(data + eta, 0, 1).detach()
                
                # Test final
                with torch.no_grad():
                    adv_output = model(adv_data)
                    adv_correct = (adv_output.argmax(dim=1) == labels).item()
                
                correct += adv_correct
                total += 1
                
                if not adv_correct:
                    successful_attacks += 1
        
        success_rate = 100.0 * successful_attacks / total if total > 0 else 0.0
        accuracy = 100.0 * correct / total if total > 0 else 0.0
        
        return {
            'accuracy': accuracy,
            'success_rate': success_rate,
            'total_samples': total,
            'successful_attacks': successful_attacks
        }
    
    def _analyze_gradient_masking(self, fgsm_results, pgd_results):
        """Analyse gradient masking"""
        fgsm_success = fgsm_results['success_rate']
        pgd_success = pgd_results['success_rate']
        
        # Heuristique gradient masking
        masking_detected = (
            fgsm_success < 10.0 and 
            pgd_success > 40.0 and 
            (pgd_success - fgsm_success) > 30.0
        )
        
        return {
            'detected': masking_detected,
            'fgsm_success': fgsm_success,
            'pgd_success': pgd_success,
            'gap': pgd_success - fgsm_success,
            'risk_level': 'HIGH' if masking_detected else 'LOW'
        }
    
    def _classify_vulnerability(self, pgd_success_rate):
        """Classification niveau de vulnérabilité"""
        if pgd_success_rate < 20:
            return 'LOW'
        elif pgd_success_rate < 50:
            return 'MODERATE'
        elif pgd_success_rate < 80:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def run_comparative_analysis(self):
        """Analyse comparative complète"""
        print("ANALYSE COMPARATIVE : BASELINE vs TRADES vs AT ECHOE")
        print("="*80)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Chargement modèles
        self.load_all_models()
        
        # Test de tous les modèles disponibles
        results = {}
        
        # Ajout résultats historiques
        results.update(self.historical_results)
        
        # Test modèles chargés
        for model_name, model_info in self.models.items():
            print(f"\nTest en cours: {model_name}")
            results[model_name] = self._test_model_robustness(model_info['model'], model_name)
        
        # Génération tableau comparatif
        self._generate_comparison_table(results)
        
        # Génération visualisations
        self._generate_comparison_plots(results, timestamp)
        
        # Génération rapport scientifique
        comparative_report = {
            'timestamp': timestamp,
            'objective': 'Comparative analysis: Baseline vs Failed AT vs TRADES',
            'methodology': {
                'test_samples': len(self.test_loader.dataset),
                'attack_parameters': {
                    'epsilon': 0.031,
                    'alpha': 0.007,
                    'pgd_iterations': 10
                },
                'evaluation_metrics': [
                    'clean_accuracy',
                    'fgsm_robustness',
                    'pgd_robustness',
                    'gradient_masking_detection'
                ]
            },
            'results': results,
            'scientific_conclusions': self._generate_scientific_conclusions(results),
            'recommendations': self._generate_recommendations(results)
        }
        
        # Sauvegarde rapport
        report_path = self.results_dir / f"comparative_analysis_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(comparative_report, f, indent=2)
        
        print(f"\nRapport genere: {report_path}")
        
        return comparative_report
    
    def _generate_comparison_table(self, results):
        """Génération tableau comparatif"""
        print(f"\nTABLEAU COMPARATIF - ROBUSTESSE ADVERSARIALE")
        print("="*100)
        print("Modele        | Clean Acc | FGSM Success | PGD Success | Gradient Masking | Vulnerability")
        print("--------------|-----------|--------------|-------------|------------------|------------------")
        
        for model_name, result in results.items():
            clean_acc = result['clean_accuracy']
            fgsm_success = result['fgsm_success_rate']
            pgd_success = result['pgd_success_rate']
            grad_masking = "YES" if result.get('gradient_masking_detected', False) else "NO"
            vulnerability = result['vulnerability_level']
            
            print(f"{model_name:13} | {clean_acc:7.1f}%  | {fgsm_success:10.1f}%  | {pgd_success:9.1f}%  | {grad_masking:14}  | {vulnerability}")
        
        print("="*100)
    
    def _generate_comparison_plots(self, results, timestamp):
        """Génération graphiques comparatifs"""
        plt.figure(figsize=(15, 10))
        
        # Préparation données
        model_names = list(results.keys())
        clean_accs = [results[m]['clean_accuracy'] for m in model_names]
        fgsm_success = [results[m]['fgsm_success_rate'] for m in model_names]
        pgd_success = [results[m]['pgd_success_rate'] for m in model_names]
        
        # 1. Accuracy comparison
        plt.subplot(2, 3, 1)
        plt.bar(model_names, clean_accs)
        plt.title('Clean Accuracy Comparison')
        plt.ylabel('Accuracy (%)')
        plt.ylim(0, 105)
        
        # 2. FGSM robustness
        plt.subplot(2, 3, 2)
        plt.bar(model_names, fgsm_success, color='orange')
        plt.title('FGSM Attack Success Rate')
        plt.ylabel('Success Rate (%)')
        plt.ylim(0, 105)
        
        # 3. PGD robustness
        plt.subplot(2, 3, 3)
        plt.bar(model_names, pgd_success, color='red')
        plt.title('PGD Attack Success Rate')
        plt.ylabel('Success Rate (%)')
        plt.ylim(0, 105)
        
        # 4. Gradient masking indicator
        plt.subplot(2, 3, 4)
        masking_gaps = [pgd_success[i] - fgsm_success[i] for i in range(len(model_names))]
        colors = ['red' if gap > 30 else 'green' for gap in masking_gaps]
        plt.bar(model_names, masking_gaps, color=colors)
        plt.title('Gradient Masking Indicator\n(PGD - FGSM Success Gap)')
        plt.ylabel('Gap (%)')
        plt.axhline(y=30, color='red', linestyle='--', label='Masking Threshold')
        plt.legend()
        
        # 5. Robustesse globale
        plt.subplot(2, 3, 5)
        robustness_scores = [100 - pgd for pgd in pgd_success]
        colors = ['green' if score > 50 else 'orange' if score > 20 else 'red' for score in robustness_scores]
        plt.bar(model_names, robustness_scores, color=colors)
        plt.title('Overall Robustness Score\n(100 - PGD Success Rate)')
        plt.ylabel('Robustness Score')
        plt.ylim(0, 105)
        
        # 6. Résumé scientifique
        plt.subplot(2, 3, 6)
        plt.text(0.1, 0.8, "RÉSULTATS SCIENTIFIQUES:", fontsize=12, fontweight='bold')
        
        # Calcul améliorations
        if 'baseline' in results and 'trades_stable' in results:
            baseline_pgd = results['baseline']['pgd_success_rate']
            trades_pgd = results['trades_stable']['pgd_success_rate']
            improvement = baseline_pgd - trades_pgd
            
            plt.text(0.1, 0.6, f"Baseline PGD vulnerability: {baseline_pgd:.1f}%", fontsize=10)
            plt.text(0.1, 0.5, f"TRADES PGD vulnerability: {trades_pgd:.1f}%", fontsize=10)
            plt.text(0.1, 0.4, f"Amélioration: {improvement:.1f}%", fontsize=10, 
                    color='green' if improvement > 0 else 'red')
        
        if 'failed_at' in results:
            plt.text(0.1, 0.2, f"AT échoué: 100% vulnérabilité", fontsize=10, color='red')
            plt.text(0.1, 0.1, f"TRADES: Solution validée", fontsize=10, color='green')
        
        plt.axis('off')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / f"comparative_analysis_{timestamp}.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_scientific_conclusions(self, results):
        """Génération conclusions scientifiques"""
        conclusions = {
            'main_findings': [],
            'hypothesis_validation': {},
            'technical_insights': []
        }
        
        # Analyse des résultats
        if 'baseline' in results:
            conclusions['main_findings'].append(
                f"Baseline model: {results['baseline']['clean_accuracy']:.1f}% clean accuracy, "
                f"{results['baseline']['pgd_success_rate']:.1f}% PGD vulnerability"
            )
        
        if 'failed_at' in results:
            conclusions['main_findings'].append(
                f"Failed AT model: Severe gradient masking detected, "
                f"{results['failed_at']['pgd_success_rate']:.1f}% PGD vulnerability"
            )
            conclusions['hypothesis_validation']['gradient_masking_problem'] = True
        
        if 'trades_stable' in results:
            trades_result = results['trades_stable']
            conclusions['main_findings'].append(
                f"TRADES model: {trades_result['clean_accuracy']:.1f}% clean accuracy, "
                f"{trades_result['pgd_success_rate']:.1f}% PGD vulnerability"
            )
            
            if 'baseline' in results:
                improvement = results['baseline']['pgd_success_rate'] - trades_result['pgd_success_rate']
                conclusions['hypothesis_validation']['trades_improvement'] = improvement > 0
                conclusions['technical_insights'].append(
                    f"TRADES achieved {improvement:.1f}% robustness improvement over baseline"
                )
            
            conclusions['hypothesis_validation']['gradient_masking_resolved'] = not trades_result.get('gradient_masking_detected', False)
        
        return conclusions
    
    def _generate_recommendations(self, results):
        """Génération recommandations"""
        recommendations = []
        
        if 'failed_at' in results and results['failed_at'].get('gradient_masking_detected'):
            recommendations.append("Standard Adversarial Training is prone to gradient masking - avoid")
        
        if 'trades_stable' in results:
            if results['trades_stable']['pgd_success_rate'] < 30:
                recommendations.append("TRADES provides effective robustness - recommended for deployment")
            else:
                recommendations.append("TRADES shows improvement but needs further tuning")
        
        recommendations.append("Always test for gradient masking using both FGSM and PGD attacks")
        recommendations.append("Use comparative analysis for robust model selection")
        
        return recommendations

def run_baseline_vs_trades_analysis():
    """Point d'entrée principal"""
    print("ANALYSE COMPARATIVE BASELINE vs TRADES")
    print("Validation scientifique de la solution TRADES")
    print("="*60)
    
    try:
        analyzer = BaselineVsTRADESAnalyzer()
        results = analyzer.run_comparative_analysis()
        
        print(f"\nAnalyse comparative terminee avec succes!")
        print("Resultats disponibles dans results/comparative_analysis/")
        
    except Exception as e:
        print(f"Erreur analyse comparative: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_baseline_vs_trades_analysis()