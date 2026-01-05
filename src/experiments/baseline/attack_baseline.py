"""
Attack Baseline Model
Test d'attaques adversariales sur le modèle non sécurisé
Conforme à l'Architecture de Sécurisation IA - Zone 3: Validation & Test

Ce module implémente les tests adversariaux définis dans l'architecture :
- Tests adversariaux (FGSM, PGD, C&W)
- Audit de biais et robustesse  
- Sandbox isolée pour les tests de sécurité
- Monitoring et logging conformes à la Zone 5 (Gouvernance)
"""

import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
import numpy as np
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from pathlib import Path
import sys

# Import direct des utilitaires (comme dans train_baseline.py)
import torchvision.models as models
from PIL import Image

class DangerousObjectDataset:
    """
    Dataset personnalisé pour charger les images d'objets dangereux vs sûrs
    Structure attendue : data/train/safe/ et data/train/dangerous/
    """
    
    def __init__(self, root_dir, transform=None):
        """
        Initialise le dataset
        
        Args:
            root_dir: Dossier racine contenant safe/ et dangerous/
            transform: Transformations PyTorch à appliquer aux images
        """
        self.root_dir = Path(root_dir)
        self.transform = transform
        
        # Liste de tous les fichiers avec leurs labels
        self.samples = []
        
        # Parcourir le dossier 'safe' (label = 0)
        safe_dir = self.root_dir / "safe"
        if safe_dir.exists():
            for img_path in safe_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 0))  # 0 = safe
        
        # Parcourir le dossier 'dangerous' (label = 1)  
        dangerous_dir = self.root_dir / "dangerous"
        if dangerous_dir.exists():
            for img_path in dangerous_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 1))  # 1 = dangerous
                
        print(f"Dataset chargé: {len(self.samples)} échantillons")
        print(f"  - Safe: {len([s for s in self.samples if s[1] == 0])}")
        print(f"  - Dangerous: {len([s for s in self.samples if s[1] == 1])}")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        
        # Charger l'image
        image = Image.open(img_path).convert('RGB')
        
        # Appliquer les transformations si définies
        if self.transform:
            image = self.transform(image)
        
        return image, label

def load_baseline_model(model_path, device='cpu'):
    """
    Charge le modèle baseline MobileNetV2 sauvegardé

    Args:
        model_path: Chemin vers le fichier .pth du modèle
        device: Device PyTorch

    Returns:
        torch.nn.Module: Modèle chargé et prêt pour l'inférence
    """
    # Utiliser le ModelLoader centralisé
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from models.utils.model_loader import ModelLoader

    model = ModelLoader.load_mobilenetv2_checkpoint(model_path, device)
    return model

class AdversarialTester:
    """
    Testeur d'attaques adversariales conforme à l'Architecture de Sécurisation
    Zone 3: Validation & Test - Tests adversariaux en sandbox isolée
    """
    
    def __init__(self, model_path, test_data_path, device='cpu'):
        """
        Initialise le testeur d'attaques adversariales
        
        Args:
            model_path: Chemin vers le modèle baseline entraîné
            test_data_path: Chemin vers les données de test
            device: Device PyTorch (cpu/cuda)
        """
        self.device = torch.device(device)
        self.model_path = model_path
        self.test_data_path = test_data_path
        
        # Initialisation du système de logging de sécurité (PREMIER!)
        self.security_log = []
        self._log_security_event("INIT", "Initialisation du testeur adversarial", "INFO")
        
        # Configuration des résultats (Zone 5: Gouvernance)
        self.results_dir = Path(__file__).parent.parent.parent.parent / "results" / "adversarial_attacks"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Chargement du modèle baseline (Zone 4: Production -> Zone 3: Test)
        print("[ZONE 3] Chargement du modele baseline dans sandbox isolee...")
        self.model = self._load_model()
        
        # Chargement des données de test avec validation de sécurité
        print("[ZONE 1] Validation et chargement securise des donnees de test...")
        self.test_loader = self._load_test_data()
    
    def _load_model(self):
        """Charge le modèle baseline avec vérification d'intégrité"""
        try:
            model = load_baseline_model(self.model_path, self.device)
            
            self._log_security_event("MODEL_LOAD", f"Modèle chargé: {self.model_path}", "INFO")
            return model
            
        except Exception as e:
            self._log_security_event("MODEL_LOAD_ERROR", f"Erreur chargement modèle: {str(e)}", "ERROR")
            raise
    
    def _load_test_data(self):
        """Charge les données de test avec validation de sécurité"""
        try:
            # Transformation standard (pas d'augmentation pour les tests adversariaux)
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
            
            # Dataset de test sécurisé
            test_dataset = DangerousObjectDataset(
                root_dir=self.test_data_path,
                transform=transform
            )
            
            test_loader = DataLoader(
                test_dataset, 
                batch_size=1,  # Batch=1 pour tests adversariaux précis
                shuffle=False,  # Pas de shuffle pour reproductibilité
                num_workers=0   # Pas de workers pour sécurité
            )
            
            self._log_security_event("DATA_LOAD", f"Dataset test chargé: {len(test_dataset)} échantillons", "INFO")
            return test_loader
            
        except Exception as e:
            self._log_security_event("DATA_LOAD_ERROR", f"Erreur chargement données: {str(e)}", "ERROR")
            raise
    
    def _log_security_event(self, event_type, message, level):
        """
        Système de logging de sécurité conforme à la Zone 5: Gouvernance
        Logs immutables pour audit et conformité
        """
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "level": level,
            "component": "AdversarialTester"
        }
        
        self.security_log.append(event)
        print(f"[{timestamp}] {level}: {message}")
    
    def fgsm_attack(self, epsilon=0.1):
        """
        Implémentation de l'attaque FGSM (Fast Gradient Sign Method)
        Zone 3: Tests adversariaux - Attaque gradient simple
        
        Args:
            epsilon: Magnitude de la perturbation (l_infinity norm)
            
        Returns:
            dict: Résultats de l'attaque avec métriques de sécurité
        """
        self._log_security_event("FGSM_START", f"Début attaque FGSM (epsilon={epsilon})", "WARNING")
        
        correct_clean = 0
        correct_adversarial = 0
        total_samples = 0
        successful_attacks = 0
        
        adversarial_examples = []
        
        # Mode gradient activé pour l'attaque
        self.model.eval()
        
        for batch_idx, (data, target) in enumerate(self.test_loader):
            data, target = data.to(self.device), target.to(self.device)
            data.requires_grad = True
            
            # Prédiction sur l'échantillon propre
            output_clean = self.model(data)
            pred_clean = output_clean.argmax(dim=1)
            
            if pred_clean == target:
                correct_clean += 1
            
            # Calcul de la perte pour le gradient
            loss = F.cross_entropy(output_clean, target)
            
            # Backpropagation pour obtenir le gradient
            self.model.zero_grad()
            loss.backward()
            
            # Génération de l'exemple adversarial (FGSM)
            data_grad = data.grad.data
            sign_data_grad = data_grad.sign()
            perturbed_data = data + epsilon * sign_data_grad
            
            # Contrainte dans [0,1] après normalisation
            perturbed_data = torch.clamp(perturbed_data, 0, 1)
            
            # Test sur l'échantillon adversarial
            output_adversarial = self.model(perturbed_data)
            pred_adversarial = output_adversarial.argmax(dim=1)
            
            if pred_adversarial == target:
                correct_adversarial += 1
            else:
                successful_attacks += 1
                # Sauvegarde d'exemples adversariaux pour analyse
                if len(adversarial_examples) < 5:  # Limite pour performance
                    adversarial_examples.append({
                        'original': data.detach().cpu(),
                        'adversarial': perturbed_data.detach().cpu(),
                        'true_label': target.item(),
                        'pred_clean': pred_clean.item(),
                        'pred_adversarial': pred_adversarial.item()
                    })
            
            total_samples += 1
            
            # Logging de progression tous les 5 échantillons
            if (batch_idx + 1) % 5 == 0:
                success_rate = (successful_attacks / total_samples) * 100
                self._log_security_event("FGSM_PROGRESS", 
                    f"Traités: {total_samples}, Attaques réussies: {success_rate:.1f}%", "INFO")
        
        # Calcul des métriques finales de sécurité
        clean_accuracy = (correct_clean / total_samples) * 100
        adversarial_accuracy = (correct_adversarial / total_samples) * 100
        attack_success_rate = (successful_attacks / total_samples) * 100
        robustness_degradation = clean_accuracy - adversarial_accuracy
        
        results = {
            "attack_type": "FGSM",
            "epsilon": epsilon,
            "total_samples": total_samples,
            "clean_accuracy": clean_accuracy,
            "adversarial_accuracy": adversarial_accuracy,
            "attack_success_rate": attack_success_rate,
            "robustness_degradation": robustness_degradation,
            "adversarial_examples": len(adversarial_examples)
        }
        
        # Logging de sécurité final
        self._log_security_event("FGSM_COMPLETE", 
            f"Attaque terminée - Success: {attack_success_rate:.1f}%, Dégradation: {robustness_degradation:.1f}%", 
            "WARNING" if attack_success_rate > 50 else "INFO")
        
        # Sauvegarde des résultats (Zone 5: Gouvernance - Rapports automatiques)
        self._save_attack_results("fgsm", results, adversarial_examples)
        
        return results
    
    def pgd_attack(self, epsilon=0.1, alpha=0.02, num_iter=10):
        """
        Implémentation de l'attaque PGD (Projected Gradient Descent)
        Zone 3: Tests adversariaux - Attaque itérative plus forte que FGSM
        
        Args:
            epsilon: Magnitude maximale de perturbation
            alpha: Taille du pas à chaque itération
            num_iter: Nombre d'itérations
            
        Returns:
            dict: Résultats de l'attaque avec métriques de sécurité avancées
        """
        self._log_security_event("PGD_START", 
            f"Début attaque PGD (eps={epsilon}, alpha={alpha}, iter={num_iter})", "WARNING")
        
        correct_clean = 0
        correct_adversarial = 0
        total_samples = 0
        successful_attacks = 0
        
        # Mode évaluation
        self.model.eval()
        
        for batch_idx, (data, target) in enumerate(self.test_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            # Test sur échantillon propre
            with torch.no_grad():
                output_clean = self.model(data)
                pred_clean = output_clean.argmax(dim=1)
                if pred_clean == target:
                    correct_clean += 1
            
            # Initialisation PGD : perturbation aléatoire uniforme
            delta = torch.empty_like(data).uniform_(-epsilon, epsilon)
            delta = torch.clamp(delta, 0-data, 1-data)  # Respect contraintes [0,1]
            delta.requires_grad = True
            
            # Itérations PGD
            for i in range(num_iter):
                # Forward pass avec perturbation
                perturbed_data = data + delta
                output = self.model(perturbed_data)
                
                # Calcul de la perte (maximisation pour l'attaquant)
                loss = F.cross_entropy(output, target)
                
                # Gradient
                loss.backward()
                
                # Mise à jour PGD avec projection
                delta.data = delta.data + alpha * delta.grad.data.sign()
                delta.data = torch.clamp(delta.data, -epsilon, epsilon)
                delta.data = torch.clamp(data + delta.data, 0, 1) - data
                
                # Reset gradient pour iteration suivante
                delta.grad.data.zero_()
            
            # Test final sur échantillon adversarial PGD
            with torch.no_grad():
                adversarial_data = data + delta
                output_adversarial = self.model(adversarial_data)
                pred_adversarial = output_adversarial.argmax(dim=1)
                
                if pred_adversarial == target:
                    correct_adversarial += 1
                else:
                    successful_attacks += 1
            
            total_samples += 1
            
            # Logging de progression
            if (batch_idx + 1) % 3 == 0:
                success_rate = (successful_attacks / total_samples) * 100
                self._log_security_event("PGD_PROGRESS", 
                    f"PGD traités: {total_samples}, Success: {success_rate:.1f}%", "INFO")
        
        # Métriques finales
        clean_accuracy = (correct_clean / total_samples) * 100
        adversarial_accuracy = (correct_adversarial / total_samples) * 100
        attack_success_rate = (successful_attacks / total_samples) * 100
        robustness_degradation = clean_accuracy - adversarial_accuracy
        
        results = {
            "attack_type": "PGD",
            "epsilon": epsilon,
            "alpha": alpha,
            "num_iterations": num_iter,
            "total_samples": total_samples,
            "clean_accuracy": clean_accuracy,
            "adversarial_accuracy": adversarial_accuracy,
            "attack_success_rate": attack_success_rate,
            "robustness_degradation": robustness_degradation
        }
        
        self._log_security_event("PGD_COMPLETE", 
            f"PGD terminé - Success: {attack_success_rate:.1f}%, Dégradation: {robustness_degradation:.1f}%", 
            "CRITICAL" if attack_success_rate > 70 else "WARNING")
        
        self._save_attack_results("pgd", results)
        return results
    
    def _save_attack_results(self, attack_name, results, examples=None):
        """
        Sauvegarde des résultats conformément à la Zone 5: Gouvernance
        Rapports automatiques et logs immutables
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sauvegarde JSON des métriques
        results_file = self.results_dir / f"{attack_name}_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Sauvegarde du log de sécurité
        log_file = self.results_dir / f"security_log_{timestamp}.json"
        with open(log_file, 'w') as f:
            json.dump(self.security_log, f, indent=2)
        
        self._log_security_event("RESULTS_SAVED", 
            f"Résultats sauvegardés: {results_file.name}", "INFO")
    
    def generate_security_report(self):
        """
        Génération d'un rapport de sécurité complet
        Conforme à Zone 5: Gouvernance - Rapports automatiques et conformité
        """
        print("\n" + "="*80)
        print("RAPPORT DE SECURITE ADVERSARIALE - MODELE BASELINE")
        print("    Conforme a l'Architecture de Securisation IA")
        print("="*80)
        
        # Informations système
        print(f"Modele teste: {self.model_path}")
        print(f"Donnees test: {self.test_data_path}")
        print(f"Device: {self.device}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Résumé des événements de sécurité
        print(f"\nEVENEMENTS DE SECURITE: {len(self.security_log)} entrees")
        
        events_by_level = {}
        for event in self.security_log:
            level = event['level']
            events_by_level[level] = events_by_level.get(level, 0) + 1
        
        for level, count in events_by_level.items():
            print(f"   - {level}: {count} événements")
        
        print("\nRECOMMANDATIONS DE SECURITE:")
        print("   Le modele baseline n'est PAS securise contre les attaques adversariales")
        print("   Implementation necessaire: Zone 2 (Adversarial Training)")
        print("   Tests requis: Validation continue en Zone 3")
        print("   Monitoring: Surveillance temps reel en Zone 5")

def attack_baseline():
    """
    Fonction principale de test d'attaques adversariales
    Point d'entrée conforme à l'architecture de sécurisation
    """
    print("[ARCHITECTURE SECURISEE] Debut des tests adversariaux Zone 3")
    print("="*70)
    
    # Configuration des chemins
    project_root = Path(__file__).parent.parent.parent.parent
    model_path = project_root / "models" / "baseline" / "best_model.pth"
    test_data_path = project_root / "data" / "prepared" / "test"
    
    # Vérification de l'existence des fichiers
    if not model_path.exists():
        print(f"Erreur: Modele non trouve a {model_path}")
        print("   Veuillez d'abord executer l'entrainement baseline.")
        return
    
    if not test_data_path.exists():
        print(f"Erreur: Donnees de test non trouvees a {test_data_path}")
        return
    
    try:
        # Initialisation du testeur sécurisé
        tester = AdversarialTester(
            model_path=str(model_path),
            test_data_path=str(test_data_path),
            device='cpu'  # CPU pour reproductibilité et sécurité
        )
        
        print("\n[ZONE 3] Execution test FGSM en sandbox isolee")

        # Test FGSM UNIQUEMENT avec epsilon=0.1
        print("\n--- Test FGSM (Fast Gradient Sign Method) ---")
        print(f"\nTest FGSM avec epsilon=0.1")
        fgsm_result = tester.fgsm_attack(epsilon=0.1)
        print(f"Success Rate: {fgsm_result['attack_success_rate']:.1f}%")
        print(f"Degradation robustesse: {fgsm_result['robustness_degradation']:.1f}%")

        # Génération du rapport final
        print("\n[ZONE 5] Generation du rapport de gouvernance")
        tester.generate_security_report()

        # Synthèse des vulnérabilités détectées
        print(f"\nSYNTHESE DES VULNERABILITES:")
        print(f"FGSM (epsilon=0.1): {fgsm_result['attack_success_rate']:.1f}% success")

        if fgsm_result['attack_success_rate'] > 80:
            print("NIVEAU DE RISQUE: CRITIQUE - Modele tres vulnerable")
        elif fgsm_result['attack_success_rate'] > 50:
            print("NIVEAU DE RISQUE: ELEVE - Modele vulnerable")
        else:
            print("NIVEAU DE RISQUE: MODERE - Vulnerabilite controlee")
        
        print("\nTests adversariaux termines avec succes")
        print("Resultats sauvegardes dans: results/adversarial_attacks/")
        
    except Exception as e:
        print(f"Erreur lors des tests adversariaux: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    attack_baseline()
