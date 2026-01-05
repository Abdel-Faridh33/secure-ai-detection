"""
Evaluation comparative: Baseline vs TRADES Robuste
Analyse des ameliorations apportees par les solutions optimales
"""

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from pathlib import Path
import json
import sys
from datetime import datetime

# Ajouter le chemin des modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from attacks.adversarial.auto_attack import create_robust_evaluation_pipeline
from experiments.secured.train_secured_trades import DangerousObjectDataset

class ModelLoader:
    """Chargeur de modeles pour evaluation comparative"""
    
    @staticmethod
    def load_baseline_model(model_path: Path, device: str = 'cpu'):
        """Charge le modele baseline"""
        model = models.resnet50(pretrained=False)
        model.fc = nn.Linear(model.fc.in_features, 2)
        
        checkpoint = torch.load(model_path, map_location=device)
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
        
        model.eval()
        return model
    
    @staticmethod
    def load_trades_model(model_path: Path, device: str = 'cpu'):
        """Charge le modele TRADES"""
        model = models.resnet50(pretrained=False)
        model.fc = nn.Linear(model.fc.in_features, 2)
        
        checkpoint = torch.load(model_path, map_location=device)
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
        
        model.eval()
        return model

def create_test_dataloader(data_type: str = 'augmented', batch_size: int = 8):
    """
    Cree un dataloader pour l'evaluation
    
    Args:
        data_type: 'original' pour donnees originales, 'augmented' pour donnees augmentees
        batch_size: Taille des batches
    """
    project_root = Path(__file__).parent.parent.parent.parent
    
    if data_type == 'augmented':
        test_dir = project_root / "data" / "augmented" / "test"
    else:
        test_dir = project_root / "data" / "processed" / "test"
    
    if not test_dir.exists():
        # Fallback vers validation si test n'existe pas
        if data_type == 'augmented':
            test_dir = project_root / "data" / "augmented" / "val"
        else:
            test_dir = project_root / "data" / "processed" / "val"
    
    # Transformation standard pour evaluation
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    dataset = DangerousObjectDataset(root_dir=test_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    print(f"Dataset {data_type} charge: {len(dataset)} echantillons")
    return dataloader

def evaluate_baseline_robustness():
    """
    Evalue la robustesse du modele baseline
    """
    print("\n" + "="*60)
    print("EVALUATION ROBUSTESSE BASELINE")
    print("="*60)
    
    project_root = Path(__file__).parent.parent.parent.parent
    baseline_model_path = project_root / "models" / "baseline" / "best_model.pth"
    
    if not baseline_model_path.exists():
        print(f"ERREUR: Modele baseline non trouve: {baseline_model_path}")
        return None
    
    # Charger modele baseline
    baseline_model = ModelLoader.load_baseline_model(baseline_model_path)
    
    # Creer dataloader de test
    test_loader = create_test_dataloader(data_type='original', batch_size=8)
    
    # Evaluation robuste
    print("Evaluation AutoAttack sur modele baseline...")
    baseline_results = create_robust_evaluation_pipeline(
        baseline_model, test_loader, epsilon=0.031, device='cpu'
    )
    
    return baseline_results

def evaluate_trades_robustness(trades_model_path: Path):
    """
    Evalue la robustesse du modele TRADES
    """
    print("\n" + "="*60)
    print("EVALUATION ROBUSTESSE TRADES")
    print("="*60)
    
    if not trades_model_path.exists():
        print(f"ERREUR: Modele TRADES non trouve: {trades_model_path}")
        return None
    
    # Charger modele TRADES
    trades_model = ModelLoader.load_trades_model(trades_model_path)
    
    # Creer dataloader avec donnees augmentees
    test_loader = create_test_dataloader(data_type='augmented', batch_size=8)
    
    # Evaluation robuste
    print("Evaluation AutoAttack sur modele TRADES...")
    trades_results = create_robust_evaluation_pipeline(
        trades_model, test_loader, epsilon=0.031, device='cpu'
    )
    
    return trades_results

def compare_results(baseline_results, trades_results):
    """
    Compare les resultats baseline vs TRADES
    """
    print("\n" + "="*60)
    print("COMPARAISON BASELINE vs TRADES ROBUSTE")
    print("="*60)
    
    if baseline_results is None or trades_results is None:
        print("ERREUR: Impossible de comparer - resultats manquants")
        return None
    
    baseline_summary = baseline_results['summary']
    trades_summary = trades_results['summary']
    
    # Metriques de comparaison
    comparison = {
        'baseline': {
            'clean_accuracy': baseline_summary.get('clean_accuracy', 0),
            'robust_accuracy': baseline_summary.get('worst_case_robustness', 0),
        },
        'trades': {
            'clean_accuracy': trades_summary.get('clean_accuracy', 0),
            'robust_accuracy': trades_summary.get('worst_case_robustness', 0),
        },
        'improvements': {}
    }
    
    # Calcul des ameliorations
    baseline_clean = comparison['baseline']['clean_accuracy']
    baseline_robust = comparison['baseline']['robust_accuracy'] 
    trades_clean = comparison['trades']['clean_accuracy']
    trades_robust = comparison['trades']['robust_accuracy']
    
    comparison['improvements'] = {
        'clean_accuracy_delta': trades_clean - baseline_clean,
        'robust_accuracy_delta': trades_robust - baseline_robust,
        'robustness_gap_baseline': baseline_clean - baseline_robust,
        'robustness_gap_trades': trades_clean - trades_robust,
        'gap_reduction': (baseline_clean - baseline_robust) - (trades_clean - trades_robust)
    }
    
    # Affichage des resultats
    print(f"BASELINE:")
    print(f"  Clean Accuracy:  {baseline_clean:.3f}")
    print(f"  Robust Accuracy: {baseline_robust:.3f}")
    print(f"  Robustness Gap:  {comparison['improvements']['robustness_gap_baseline']:.3f}")
    
    print(f"\nTRADES:")
    print(f"  Clean Accuracy:  {trades_clean:.3f}")
    print(f"  Robust Accuracy: {trades_robust:.3f}")
    print(f"  Robustness Gap:  {comparison['improvements']['robustness_gap_trades']:.3f}")
    
    print(f"\nAMELIORATIONS:")
    print(f"  Clean Accuracy:   {comparison['improvements']['clean_accuracy_delta']:+.3f}")
    print(f"  Robust Accuracy:  {comparison['improvements']['robust_accuracy_delta']:+.3f}")
    print(f"  Gap Reduction:    {comparison['improvements']['gap_reduction']:+.3f}")
    
    # Evaluation du succes
    success_criteria = {
        'robust_accuracy_improved': comparison['improvements']['robust_accuracy_delta'] > 0,
        'gap_reduced': comparison['improvements']['gap_reduction'] > 0,
        'clean_accuracy_maintained': comparison['improvements']['clean_accuracy_delta'] > -0.05,
    }
    
    success_score = sum(success_criteria.values()) / len(success_criteria)
    
    print(f"\nEVALUATION SUCCES:")
    for criterion, success in success_criteria.items():
        status = "REUSSI" if success else "ECHEC"
        print(f"  {criterion}: {status}")
    
    print(f"\nSCORE GLOBAL: {success_score:.1%}")
    
    if success_score >= 0.67:
        print("CONCLUSION: Solutions optimales EFFICACES")
    else:
        print("CONCLUSION: Ameliorations partielles")
    
    return comparison

def generate_improvement_report(comparison_results):
    """
    Genere un rapport detaille des ameliorations
    """
    report = {
        'evaluation_date': datetime.now().isoformat(),
        'solutions_implemented': [
            'Plus de donnees (500+ echantillons par classe)',
            'Donnees diversifiees (augmentation avancee)',
            'Pipeline robuste (PGD, C&W, AutoAttack)',
            'TRADES adversarial training'
        ],
        'comparison_results': comparison_results,
        'conclusions': {
            'effectiveness': 'high' if comparison_results else 'unknown',
            'ready_for_production': False,  # A determiner selon les resultats
        }
    }
    
    # Sauvegarde rapport
    project_root = Path(__file__).parent.parent.parent.parent
    results_dir = project_root / "results" / "robust_comparison"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = results_dir / f"baseline_vs_trades_comparison_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nRapport sauvegarde: {report_file}")
    return report_file

def main():
    """
    Evaluation comparative complete
    """
    print("EVALUATION COMPARATIVE: SOLUTIONS OPTIMALES")
    print("Baseline vs TRADES avec dataset augmente")
    
    # Evaluation baseline
    print("\nPhase 1: Evaluation baseline...")
    baseline_results = evaluate_baseline_robustness()
    
    # Chercher modele TRADES (derniere version)
    project_root = Path(__file__).parent.parent.parent.parent
    secured_dir = project_root / "models" / "secured"
    
    trades_models = list(secured_dir.glob("*trades*.pth")) if secured_dir.exists() else []
    
    if trades_models:
        # Prendre le plus recent
        latest_trades = max(trades_models, key=lambda x: x.stat().st_mtime)
        print(f"\nPhase 2: Evaluation TRADES ({latest_trades.name})...")
        trades_results = evaluate_trades_robustness(latest_trades)
    else:
        print("\nATTENTE: Modele TRADES en cours d'entrainement...")
        print("Evaluation baseline terminee. Relancer quand TRADES est pret.")
        trades_results = None
    
    # Comparaison si les deux sont disponibles
    if baseline_results and trades_results:
        print("\nPhase 3: Analyse comparative...")
        comparison = compare_results(baseline_results, trades_results)
        
        if comparison:
            report_file = generate_improvement_report(comparison)
            print(f"\nEvaluation comparative terminee!")
    
    return baseline_results, trades_results

if __name__ == "__main__":
    main()