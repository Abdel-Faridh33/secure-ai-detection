"""
Attack Secured Model - Test de Robustesse Zone 3
Conforme à l'Architecture de Sécurisation IA

Ce module teste la robustesse du modèle sécurisé contre les attaques FGSM et PGD.
Valeurs de référence thèse (modèle non-sécurisé) : FGSM ~73%, PGD ~53% de succès.

Zone 3: Validation & Test - Certification de robustesse
"""

import torch
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
import matplotlib.pyplot as plt

class DangerousObjectDataset:
    """Dataset pour tests de robustesse"""
    
    def __init__(self, root_dir, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []
        
        # Chargement safe et dangerous
        safe_dir = self.root_dir / "safe"
        if safe_dir.exists():
            for img_path in safe_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 0))
        
        dangerous_dir = self.root_dir / "dangerous"
        if dangerous_dir.exists():
            for img_path in dangerous_dir.glob("*.jpg"):
                self.samples.append((str(img_path), 1))
                
        print(f"Dataset robustesse: {len(self.samples)} echantillons")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        return image, label

def load_secured_model(model_path, device='cpu'):
    """Charge le modèle sécurisé MobileNetV2 depuis checkpoint"""
    print(f"Chargement modele securise: {model_path}")

    # Utiliser ModelLoader pour MobileNetV2
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from models.utils.model_loader import ModelLoader

    model = ModelLoader.load_mobilenetv2_checkpoint(model_path, device)

    # Chargement checkpoint sécurisé pour info additionnelle
    checkpoint = torch.load(model_path, map_location=device)

    if 'model_state_dict' in checkpoint:
        print(f"Modele securise charge (securite version: {checkpoint.get('security_version', 'unknown')})")

        # Informations de sécurité
        if 'adversarial_training' in checkpoint.get('config', {}):
            print(f"Adversarial Training: {checkpoint['config']['adversarial_training']}")
        if 'val_acc' in checkpoint:
            print(f"Validation accuracy: {checkpoint['val_acc']:.2f}%")

    return model

class SecuredModelTester:
    """
    Testeur de robustesse pour modèles sécurisés
    Conforme Zone 3: Validation & Test
    """
    
    def __init__(self, secured_model_path, test_data_path, device='cpu'):
        self.device = torch.device(device)
        self.secured_model_path = secured_model_path
        self.test_data_path = test_data_path
        
        # Logging sécurisé
        self.security_log = []
        self._log_security_event("INIT", "Test robustesse modele securise", "INFO")
        
        # Configuration résultats
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.results_dir = self.project_root / "results" / "secured_robustness"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Chargement modèle sécurisé
        self.model = load_secured_model(secured_model_path, device)
        
        # Chargement données de test
        self._load_test_data()
        
        self._log_security_event("SETUP_COMPLETE", "Configuration tests robustesse terminee", "INFO")
    
    def _log_security_event(self, event_type, message, level):
        """Logging conforme Zone 5: Gouvernance"""
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "level": level,
            "component": "SecuredModelTester"
        }
        self.security_log.append(event)
        print(f"[{timestamp}] {level}: {message}")
    
    def _load_test_data(self):
        """Chargement sécurisé données de test"""
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        test_dataset = DangerousObjectDataset(
            root_dir=self.test_data_path,
            transform=transform
        )
        
        self.test_loader = DataLoader(
            test_dataset,
            batch_size=1,
            shuffle=False,
            num_workers=0
        )
        
        self._log_security_event("TEST_DATA_LOADED", f"{len(test_dataset)} echantillons test", "INFO")
    
    def fgsm_robustness_test(self, epsilon=0.1):
        """Test robustesse FGSM sur modèle sécurisé"""
        self._log_security_event("FGSM_TEST_START", f"Test robustesse FGSM epsilon={epsilon}", "WARNING")
        
        correct_clean = 0
        correct_adversarial = 0
        total_samples = 0
        successful_attacks = 0
        
        self.model.eval()
        
        for batch_idx, (data, target) in enumerate(self.test_loader):
            data, target = data.to(self.device), target.to(self.device)
            data.requires_grad = True
            
            # Prédiction propre
            output_clean = self.model(data)
            pred_clean = output_clean.argmax(dim=1)
            
            if pred_clean == target:
                correct_clean += 1
            
            # Génération FGSM
            loss = F.cross_entropy(output_clean, target)
            self.model.zero_grad()
            loss.backward()
            
            data_grad = data.grad.data
            sign_data_grad = data_grad.sign()
            perturbed_data = data + epsilon * sign_data_grad
            perturbed_data = torch.clamp(perturbed_data, 0, 1)
            
            # Test adversarial
            output_adversarial = self.model(perturbed_data)
            pred_adversarial = output_adversarial.argmax(dim=1)
            
            if pred_adversarial == target:
                correct_adversarial += 1
            else:
                successful_attacks += 1
            
            total_samples += 1
        
        # Métriques finales
        clean_accuracy = (correct_clean / total_samples) * 100
        adversarial_accuracy = (correct_adversarial / total_samples) * 100
        attack_success_rate = (successful_attacks / total_samples) * 100
        robustness_improvement = clean_accuracy - adversarial_accuracy
        
        results = {
            "attack_type": "FGSM_Robustness_Test",
            "model_type": "secured",
            "epsilon": epsilon,
            "total_samples": total_samples,
            "clean_accuracy": clean_accuracy,
            "adversarial_accuracy": adversarial_accuracy,
            "attack_success_rate": attack_success_rate,
            "robustness_degradation": robustness_improvement
        }
        
        self._log_security_event("FGSM_TEST_COMPLETE", 
            f"FGSM Robustesse - Success: {attack_success_rate:.1f}%, Degradation: {robustness_improvement:.1f}%", 
            "INFO" if attack_success_rate < 20 else "WARNING")
        
        return results
    
    def pgd_robustness_test(self, epsilon=0.1, alpha=0.02, num_iter=10):
        """Test robustesse PGD sur modèle sécurisé (attaque critique détectée)"""
        self._log_security_event("PGD_TEST_START", 
            f"Test robustesse PGD (reference non-securise: 53.3%)", "WARNING")
        
        correct_clean = 0
        correct_adversarial = 0
        total_samples = 0
        successful_attacks = 0
        
        self.model.eval()
        
        for batch_idx, (data, target) in enumerate(self.test_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            # Test propre
            with torch.no_grad():
                output_clean = self.model(data)
                pred_clean = output_clean.argmax(dim=1)
                if pred_clean == target:
                    correct_clean += 1
            
            # PGD Attack
            delta = torch.empty_like(data).uniform_(-epsilon, epsilon)
            delta = torch.clamp(delta, 0-data, 1-data)
            delta.requires_grad = True
            
            # Itérations PGD
            for i in range(num_iter):
                perturbed_data = data + delta
                output = self.model(perturbed_data)
                loss = F.cross_entropy(output, target)
                
                loss.backward()
                delta.data = delta.data + alpha * delta.grad.data.sign()
                delta.data = torch.clamp(delta.data, -epsilon, epsilon)
                delta.data = torch.clamp(data + delta.data, 0, 1) - data
                delta.grad.data.zero_()
            
            # Test final
            with torch.no_grad():
                adversarial_data = data + delta
                output_adversarial = self.model(adversarial_data)
                pred_adversarial = output_adversarial.argmax(dim=1)
                
                if pred_adversarial == target:
                    correct_adversarial += 1
                else:
                    successful_attacks += 1
            
            total_samples += 1
        
        # Métriques finales
        clean_accuracy = (correct_clean / total_samples) * 100
        adversarial_accuracy = (correct_adversarial / total_samples) * 100
        attack_success_rate = (successful_attacks / total_samples) * 100
        robustness_degradation = clean_accuracy - adversarial_accuracy
        
        results = {
            "attack_type": "PGD_Robustness_Test",
            "model_type": "secured",
            "epsilon": epsilon,
            "alpha": alpha,
            "num_iterations": num_iter,
            "total_samples": total_samples,
            "clean_accuracy": clean_accuracy,
            "adversarial_accuracy": adversarial_accuracy,
            "attack_success_rate": attack_success_rate,
            "robustness_degradation": robustness_degradation,
            "reference_improvement": {
                "reference_pgd_success_unsecured": 53.3,
                "improvement_vs_unsecured": 53.3 - attack_success_rate
            }
        }
        
        # Classification du niveau de sécurité
        if attack_success_rate < 20:
            security_level = "HIGH_SECURITY"
            log_level = "INFO"
        elif attack_success_rate < 40:
            security_level = "MODERATE_SECURITY"
            log_level = "WARNING"
        else:
            security_level = "LOW_SECURITY"
            log_level = "CRITICAL"
        
        self._log_security_event("PGD_TEST_COMPLETE", 
            f"PGD Robustesse - Success: {attack_success_rate:.1f}%, Amelioration vs reference: {53.3 - attack_success_rate:.1f}%",
            log_level)
        
        results["security_level"] = security_level
        return results
    
    def generate_fgsm_comparison(self, fgsm_results):
        """Génération rapport robustesse FGSM du modèle sécurisé"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Rapport de comparaison
        comparison_report = {
            "test_type": "secured_model_fgsm_robustness",
            "architecture_compliance": "Zone3_Validation_Test",
            "timestamp": timestamp,
            "secured_performance": fgsm_results,
            "security_assessment": {
                "fgsm_success_rate": fgsm_results['attack_success_rate'],
                "robustness_degradation": fgsm_results['robustness_degradation'],
                "adversarial_training_applied": True
            }
        }

        # Sauvegarde rapport
        report_path = self.results_dir / f"fgsm_robustness_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(comparison_report, f, indent=2)

        # Graphique
        self._create_fgsm_chart(fgsm_results, timestamp)

        self._log_security_event("FGSM_REPORT_GENERATED",
            f"Rapport FGSM genere: {report_path.name}", "INFO")

        return comparison_report
    
    def _create_fgsm_chart(self, fgsm_results, timestamp):
        """Création graphique FGSM"""
        fig, ax = plt.subplots(figsize=(10, 6))

        metrics = ['Clean\nAccuracy', 'Adversarial\nAccuracy', 'Attack\nSuccess Rate']
        values = [
            fgsm_results['clean_accuracy'],
            fgsm_results['adversarial_accuracy'],
            fgsm_results['attack_success_rate']
        ]
        colors = ['green', 'orange', 'red']

        bars = ax.bar(metrics, values, color=colors, alpha=0.7)

        # Valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=12, fontweight='bold')

        ax.set_ylabel('Percentage (%)', fontsize=12)
        ax.set_title(f'Secured Model - FGSM Robustness (ε={fgsm_results["epsilon"]})',
                    fontsize=14, fontweight='bold')
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(self.results_dir / f"fgsm_robustness_{timestamp}.png", dpi=300)
        plt.close()

    def _create_robustness_chart(self, fgsm_results, pgd_results, timestamp):
        """Graphique de robustesse du modèle sécurisé vs valeurs de référence (thèse)"""
        # Valeurs de référence (modèle non sécurisé, issues du mémoire)
        reference_fgsm = 73.2
        reference_pgd  = 53.3

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        attacks = ['FGSM', 'PGD']
        ref_rates = [reference_fgsm, reference_pgd]
        sec_rates = [fgsm_results['attack_success_rate'], pgd_results['attack_success_rate']]

        x = np.arange(len(attacks))
        width = 0.35

        ax1.bar(x - width/2, ref_rates, width, label='Non sécurisé (référence)', color='red',   alpha=0.7)
        ax1.bar(x + width/2, sec_rates, width, label='Secured (Adversarial Training)', color='green', alpha=0.7)
        ax1.set_xlabel('Type d\'attaque')
        ax1.set_ylabel('Taux de succès attaque (%)')
        ax1.set_title('Robustesse : non sécurisé vs sécurisé')
        ax1.set_xticks(x)
        ax1.set_xticklabels(attacks)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        improvements = [ref_rates[i] - sec_rates[i] for i in range(len(attacks))]
        colors = ['green' if imp >= 0 else 'red' for imp in improvements]
        ax2.bar(attacks, improvements, color=colors, alpha=0.7)
        ax2.set_xlabel('Type d\'attaque')
        ax2.set_ylabel('Amélioration (%)')
        ax2.set_title('Gain de robustesse (adversarial training)')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.results_dir / f"robustness_chart_{timestamp}.png", dpi=300)
        plt.close()

def attack_secured():
    """
    Fonction principale de test de robustesse
    Point d'entrée conforme Zone 3: Validation & Test
    """
    print("ZONE 3: TEST DE ROBUSTESSE MODELE SECURISE")
    print("Conforme a l'Architecture de Securisation IA")
    print("="*60)
    
    # Configuration chemins
    project_root = Path(__file__).parent.parent.parent.parent
    secured_model_path = project_root / "models" / "secured" / "best_secured_model.pth"
    test_data_path = project_root / "data" / "prepared" / "test"
    
    # Vérifications préalables
    if not secured_model_path.exists():
        print(f"Erreur: Modele securise non trouve a {secured_model_path}")
        print("Veuillez d'abord executer l'entrainement securise.")
        return
    
    if not test_data_path.exists():
        print(f"Erreur: Donnees de test non trouvees a {test_data_path}")
        return
    
    try:
        # Initialisation testeur robustesse
        tester = SecuredModelTester(
            secured_model_path=str(secured_model_path),
            test_data_path=str(test_data_path),
            device='cpu'
        )
        
        print("\nDEBUT TEST DE ROBUSTESSE FGSM:")

        # Test FGSM UNIQUEMENT
        print("\n--- Test Robustesse FGSM ---")
        fgsm_results = tester.fgsm_robustness_test(epsilon=0.1)
        print(f"FGSM Success Rate: {fgsm_results['attack_success_rate']:.1f}%")

        # Génération rapport
        print("\nGeneration rapport...")
        comparison = tester.generate_fgsm_comparison(fgsm_results)

        # Résumé final
        print(f"\n" + "="*60)
        print("RESUME EVALUATION ROBUSTESSE FGSM:")
        print(f"  Clean Accuracy:       {fgsm_results['clean_accuracy']:.2f}%")
        print(f"  Adversarial Accuracy: {fgsm_results['adversarial_accuracy']:.2f}%")
        print(f"  Attack Success:       {fgsm_results['attack_success_rate']:.2f}%")
        print(f"  Robustness Degradation: {fgsm_results['robustness_degradation']:.2f}%")
        print("Resultats sauvegardes dans: results/secured_robustness/")
        
    except Exception as e:
        print(f"Erreur lors des tests de robustesse: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    attack_secured()
