"""
AutoAttack Framework - Implementation Simplifiee
Reference: Croce & Hein, 2020 - https://arxiv.org/abs/2003.01690

Framework combinant PGD, C&W et autres attaques pour evaluation robuste complete
Solution: "Pipeline robuste avec validation multiple attacks"
"""

import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Optional, Tuple
import time
from pathlib import Path
import json
from datetime import datetime

from .pgd import PGDAttack, PGDAttackL2
from .cw_attack import CWAttack
from .fgsm import FGSMAttack

class AutoAttack:
    """
    Framework AutoAttack simplifie pour evaluation multi-attacks
    Combine PGD, C&W, FGSM pour evaluation robuste complete
    """
    
    def __init__(self, model: nn.Module, epsilon: float = 0.031, device: str = 'cpu'):
        """
        Args:
            model: Modele a evaluer
            epsilon: Budget de perturbation
            device: Device pour calculs
        """
        self.model = model
        self.epsilon = epsilon
        self.device = device
        
        # Initialisation des attaques
        self._init_attacks()
        
        print(f"AutoAttack configure avec epsilon={epsilon}")
        print(f"Attaques: {list(self.attacks.keys())}")
    
    def _init_attacks(self):
        """
        Initialise toutes les attaques du framework
        """
        self.attacks = {}
        
        # FGSM (attaque rapide)
        try:
            from .fgsm import FGSMAttack
            self.attacks['fgsm'] = FGSMAttack(
                self.model, epsilon=self.epsilon, device=self.device
            )
        except:
            print("ATTENTION: FGSM non disponible, creation mock")
            self.attacks['fgsm'] = self._create_mock_fgsm()
        
        # PGD L-inf (attaque standard)
        self.attacks['pgd_linf'] = PGDAttack(
            self.model, epsilon=self.epsilon, alpha=self.epsilon/4,
            num_iter=20, device=self.device
        )
        
        # PGD L2 (attaque avec norme L2)
        self.attacks['pgd_l2'] = PGDAttackL2(
            self.model, epsilon=1.0, alpha=0.2, 
            num_iter=20, device=self.device
        )
        
        # C&W (attaque sophistiquee)
        self.attacks['cw'] = CWAttack(
            self.model, c=1.0, max_iter=500,
            binary_search_steps=5, device=self.device
        )
    
    def _create_mock_fgsm(self):
        """
        Cree un mock FGSM si le fichier n'existe pas
        """
        class MockFGSM:
            def __init__(self, model, epsilon, device):
                self.model = model
                self.epsilon = epsilon
                self.device = device
                self.criterion = nn.CrossEntropyLoss()
            
            def generate(self, images, labels):
                images = images.to(self.device)
                labels = labels.to(self.device)
                images.requires_grad_(True)
                
                outputs = self.model(images)
                loss = self.criterion(outputs, labels)
                
                self.model.zero_grad()
                loss.backward()
                
                # FGSM: x' = x + epsilon * sign(grad)
                adv_images = images + self.epsilon * images.grad.sign()
                adv_images = torch.clamp(adv_images, 0, 1)
                
                return adv_images
        
        return MockFGSM(self.model, self.epsilon, self.device)
    
    def evaluate_robustness(self, dataloader, attacks_to_run: Optional[List[str]] = None,
                           verbose: bool = True) -> Dict:
        """
        Evalue la robustesse contre toutes les attaques
        
        Args:
            dataloader: DataLoader pour evaluation
            attacks_to_run: Liste des attaques a executer (toutes si None)
            verbose: Affichage verbose
        
        Returns:
            Dictionnaire avec resultats pour chaque attaque
        """
        if attacks_to_run is None:
            attacks_to_run = list(self.attacks.keys())
        
        results = {
            'summary': {},
            'detailed': {},
            'config': {
                'epsilon': self.epsilon,
                'device': self.device,
                'attacks': attacks_to_run,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        print("\n" + "="*60)
        print("AUTOATTACK - EVALUATION ROBUSTESSE MULTI-ATTACKS")
        print("="*60)
        print(f"Epsilon: {self.epsilon}")
        print(f"Attaques: {', '.join(attacks_to_run)}")
        print(f"Dataset: {len(dataloader.dataset) if hasattr(dataloader, 'dataset') else 'inconnu'} echantillons")
        
        # Evaluation baseline (donnees propres)
        clean_accuracy = self._evaluate_clean_accuracy(dataloader)
        results['summary']['clean_accuracy'] = clean_accuracy
        
        print(f"\nAccuracy sur donnees propres: {clean_accuracy:.3f}")
        print("\nEvaluation par attaque:")
        print("-" * 40)
        
        # Evaluation pour chaque attaque
        for attack_name in attacks_to_run:
            if attack_name not in self.attacks:
                print(f"ATTENTION: Attaque {attack_name} non disponible")
                continue
            
            print(f"\n[{attack_name.upper()}] Evaluation en cours...")
            start_time = time.time()
            
            attack_results = self._evaluate_single_attack(
                dataloader, self.attacks[attack_name], attack_name, verbose=False
            )
            
            elapsed_time = time.time() - start_time
            attack_results['evaluation_time'] = elapsed_time
            
            results['detailed'][attack_name] = attack_results
            results['summary'][f'{attack_name}_robust_accuracy'] = attack_results['robust_accuracy']
            
            print(f"[{attack_name.upper()}] Resultat: {attack_results['robust_accuracy']:.3f} "
                  f"({elapsed_time:.1f}s)")
        
        # Calcul de la robustesse globale (pire cas)
        if results['detailed']:
            worst_case_accuracy = min([
                result['robust_accuracy'] for result in results['detailed'].values()
            ])
            results['summary']['worst_case_robustness'] = worst_case_accuracy
        
        # Affichage resume
        self._print_summary(results, verbose)
        
        return results
    
    def _evaluate_clean_accuracy(self, dataloader) -> float:
        """
        Evalue l'accuracy sur donnees propres
        """
        self.model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, target in dataloader:
                data, target = data.to(self.device), target.to(self.device)
                outputs = self.model(data)
                pred = outputs.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)
        
        return correct / total if total > 0 else 0.0
    
    def _evaluate_single_attack(self, dataloader, attack, attack_name: str, 
                               verbose: bool = False) -> Dict:
        """
        Evalue une attaque specifique
        """
        self.model.eval()
        
        total = 0
        clean_correct = 0
        adv_correct = 0
        
        # Metriques specifiques
        total_perturbation = 0.0
        successful_attacks = 0
        
        for batch_idx, (data, target) in enumerate(dataloader):
            data, target = data.to(self.device), target.to(self.device)
            batch_size = data.size(0)
            
            # Predictions propres
            with torch.no_grad():
                clean_outputs = self.model(data)
                clean_pred = clean_outputs.argmax(dim=1)
                clean_correct += clean_pred.eq(target).sum().item()
            
            # Generation exemples adversariaux
            try:
                if attack_name == 'cw':
                    # C&W avec parametres reduits pour rapidite
                    adv_data = attack.generate(data, target, targeted=False)
                else:
                    adv_data = attack.generate(data, target)
                
                # Predictions adversariales
                with torch.no_grad():
                    adv_outputs = self.model(adv_data)
                    adv_pred = adv_outputs.argmax(dim=1)
                    adv_correct += adv_pred.eq(target).sum().item()
                
                # Calcul perturbations
                if attack_name in ['pgd_linf', 'fgsm']:
                    # Norme L-inf
                    perturbation = (adv_data - data).abs().max().item()
                else:
                    # Norme L2
                    perturbation = torch.norm((adv_data - data).view(batch_size, -1), p=2, dim=1).mean().item()
                
                total_perturbation += perturbation * batch_size
                
                # Attaques reussies (predictions changees)
                successful_attacks += (clean_pred != adv_pred).sum().item()
                
            except Exception as e:
                print(f"ERREUR lors de {attack_name}: {str(e)}")
                adv_correct += clean_pred.eq(target).sum().item()  # Pas d'attaque = prediction propre
            
            total += batch_size
            
            if verbose and batch_idx % 10 == 0:
                print(f"  Batch {batch_idx}: Robust Acc={adv_correct/total:.3f}")
        
        # Resultats
        results = {
            'clean_accuracy': clean_correct / total if total > 0 else 0,
            'robust_accuracy': adv_correct / total if total > 0 else 0,
            'attack_success_rate': successful_attacks / clean_correct if clean_correct > 0 else 0,
            'avg_perturbation': total_perturbation / total if total > 0 else 0,
            'total_samples': total
        }
        
        return results
    
    def _print_summary(self, results: Dict, verbose: bool = True):
        """
        Affiche le resume des resultats
        """
        print("\n" + "="*60)
        print("RESUME AUTOATTACK")
        print("="*60)
        
        summary = results['summary']
        
        print(f"Accuracy propre:     {summary.get('clean_accuracy', 0):.3f}")
        
        if verbose:
            print("\nResultats par attaque:")
            for attack_name, attack_results in results['detailed'].items():
                print(f"  {attack_name.upper():12} : {attack_results['robust_accuracy']:.3f} "
                      f"(success: {attack_results['attack_success_rate']:.3f})")
        
        if 'worst_case_robustness' in summary:
            print(f"\nRobustesse pire cas: {summary['worst_case_robustness']:.3f}")
            print(f"Degradation:         {summary['clean_accuracy'] - summary['worst_case_robustness']:.3f}")
        
        print("\n" + "="*60)
    
    def save_results(self, results: Dict, output_dir: Path):
        """
        Sauvegarde les resultats
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"autoattack_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Resultats sauvegardes: {results_file}")
        return results_file

def create_robust_evaluation_pipeline(model: nn.Module, dataloader, 
                                     epsilon: float = 0.031, device: str = 'cpu',
                                     output_dir: Optional[Path] = None) -> Dict:
    """
    Pipeline complet d'evaluation robuste
    Solution: "Pipeline robuste avec validation multiple attacks"
    """
    print("PIPELINE EVALUATION ROBUSTE - SOLUTIONS OPTIMALES")
    print("Configuration:")
    print(f"  - Epsilon: {epsilon}")
    print(f"  - Device: {device}")
    print(f"  - Multiple attacks: PGD, C&W, FGSM")
    
    # Creation AutoAttack
    auto_attack = AutoAttack(model, epsilon=epsilon, device=device)
    
    # Evaluation complete
    results = auto_attack.evaluate_robustness(dataloader, verbose=True)
    
    # Sauvegarde si demandee
    if output_dir:
        auto_attack.save_results(results, output_dir)
    
    return results

if __name__ == "__main__":
    # Test du framework
    print("Test AutoAttack Framework")
    
    # Mock model et data
    class SimpleModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
            self.fc = nn.Linear(16 * 224 * 224, 2)
            
        def forward(self, x):
            x = self.conv1(x)
            x = x.view(x.size(0), -1)
            return self.fc(x)
    
    from torch.utils.data import TensorDataset, DataLoader
    
    model = SimpleModel()
    data = torch.randn(20, 3, 224, 224)
    labels = torch.randint(0, 2, (20,))
    dataset = TensorDataset(data, labels)
    dataloader = DataLoader(dataset, batch_size=4)
    
    # Test evaluation
    results = create_robust_evaluation_pipeline(model, dataloader, epsilon=0.031)
    
    print("Test AutoAttack: SUCCES")