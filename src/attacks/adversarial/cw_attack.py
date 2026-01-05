"""
Carlini & Wagner (C&W) Attack - Implementation Complete
Reference: Carlini & Wagner, 2017 - https://arxiv.org/abs/1608.04644

Implementation pour evaluation robuste multi-attacks selon solutions optimales
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from typing import Optional, Tuple

class CWAttack:
    """
    Implementation complete de l'attaque C&W pour evaluation robuste
    Plus sophistiquee que PGD, utilise optimisation continue
    """
    
    def __init__(self, model: nn.Module, c: float = 1.0, kappa: float = 0.0, 
                 learning_rate: float = 0.01, max_iter: int = 1000, 
                 binary_search_steps: int = 9, device: str = 'cpu'):
        """
        Args:
            model: Modele cible
            c: Parametre de regularisation
            kappa: Confidence parameter (0 = untargeted)
            learning_rate: Learning rate pour optimisation
            max_iter: Nombre max d'iterations
            binary_search_steps: Etapes de recherche binaire pour c
            device: Device pour calculs
        """
        self.model = model
        self.c = c
        self.kappa = kappa
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.binary_search_steps = binary_search_steps
        self.device = device
        
        print(f"C&W Attack configure: c={c}, kappa={kappa}, lr={learning_rate}, iter={max_iter}")
    
    def generate(self, images: torch.Tensor, labels: torch.Tensor, 
                 targeted: bool = False, target_labels: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Genere des exemples adversariaux avec C&W
        
        Args:
            images: Batch d'images originales [B, C, H, W]  
            labels: Labels vraies [B]
            targeted: Attaque ciblee si True
            target_labels: Labels cibles pour attaque ciblee
        
        Returns:
            Exemples adversariaux [B, C, H, W]
        """
        images = images.to(self.device)
        labels = labels.to(self.device)
        
        if targeted and target_labels is not None:
            target_labels = target_labels.to(self.device)
        else:
            # Pour attaque non-ciblee, target = least likely class
            target_labels = self._get_least_likely_class(images, labels)
        
        batch_size = images.size(0)
        
        # Variables pour stocker les meilleurs resultats
        best_adv_images = images.clone()
        best_l2_distances = torch.full((batch_size,), float('inf'), device=self.device)
        
        # Recherche binaire sur le parametre c
        c_lower = torch.zeros(batch_size, device=self.device)
        c_upper = torch.full((batch_size,), 1e10, device=self.device)
        
        for binary_step in range(self.binary_search_steps):
            # Valeurs actuelles de c pour chaque image
            if binary_step == 0:
                current_c = torch.full((batch_size,), self.c, device=self.device)
            else:
                current_c = (c_lower + c_upper) / 2
            
            # Optimisation pour c courant
            adv_images, success = self._optimize_cw(images, labels, target_labels, 
                                                   current_c, targeted)
            
            # Calcul distances L2
            l2_distances = torch.norm((adv_images - images).view(batch_size, -1), p=2, dim=1)
            
            # Mise a jour des meilleurs resultats
            for i in range(batch_size):
                if success[i] and l2_distances[i] < best_l2_distances[i]:
                    best_adv_images[i] = adv_images[i]
                    best_l2_distances[i] = l2_distances[i]
                    c_upper[i] = current_c[i]
                else:
                    c_lower[i] = current_c[i]
        
        return best_adv_images
    
    def _get_least_likely_class(self, images: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Calcule la classe la moins probable pour attaque non-ciblee
        """
        with torch.no_grad():
            outputs = self.model(images)
            # Classe avec score le plus faible (excluant vraie classe)
            outputs.scatter_(1, labels.unsqueeze(1), float('-inf'))
            return outputs.argmin(dim=1)
    
    def _optimize_cw(self, images: torch.Tensor, labels: torch.Tensor, 
                     target_labels: torch.Tensor, c_values: torch.Tensor, 
                     targeted: bool) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Optimisation C&W pour un parametre c donne
        """
        batch_size = images.size(0)
        
        # Variable d'optimisation w (transformation arctanh)
        # x = (tanh(w) + 1) / 2 pour assurer x in [0,1]
        w = torch.zeros_like(images, requires_grad=True, device=self.device)
        
        # Initialisation: w = arctanh(2*x - 1)
        # Attention: eviter valeurs extremes pour arctanh
        x_init = torch.clamp(images * 2 - 1, -0.9999, 0.9999)
        with torch.no_grad():
            w.data = torch.atanh(x_init)
        
        optimizer = optim.Adam([w], lr=self.learning_rate)
        
        best_adv = images.clone()
        success = torch.zeros(batch_size, dtype=torch.bool, device=self.device)
        
        for iteration in range(self.max_iter):
            optimizer.zero_grad()
            
            # Transformation w -> x
            x = (torch.tanh(w) + 1) / 2
            
            # Loss function C&W
            loss = self._cw_loss(x, images, labels, target_labels, c_values, targeted)
            
            loss.backward()
            optimizer.step()
            
            # Verification du succes de l'attaque
            with torch.no_grad():
                current_success = self._check_attack_success(x, labels, target_labels, targeted)
                
                # Mise a jour des meilleurs exemples
                for i in range(batch_size):
                    if current_success[i] and not success[i]:
                        best_adv[i] = x[i]
                        success[i] = True
            
            # Early stopping si tous ont reussi
            if success.all():
                break
        
        return best_adv, success
    
    def _cw_loss(self, x: torch.Tensor, orig_x: torch.Tensor, 
                 labels: torch.Tensor, target_labels: torch.Tensor,
                 c_values: torch.Tensor, targeted: bool) -> torch.Tensor:
        """
        Loss function C&W: c * f(x) + ||x - x_orig||_2^2
        """
        batch_size = x.size(0)
        
        # Distance L2
        l2_distance = torch.norm((x - orig_x).view(batch_size, -1), p=2, dim=1)
        
        # Logits du modele
        logits = self.model(x)
        
        # f(x) function pour C&W
        if targeted:
            # Attaque ciblee: max(max(Z_i for i!=t) - Z_t, -kappa)
            target_logits = logits.gather(1, target_labels.unsqueeze(1)).squeeze(1)
            other_logits = logits.clone()
            other_logits.scatter_(1, target_labels.unsqueeze(1), float('-inf'))
            max_other_logits = other_logits.max(dim=1)[0]
            f_x = torch.clamp(max_other_logits - target_logits, min=-self.kappa)
        else:
            # Attaque non-ciblee: max(Z_t - max(Z_i for i!=t), -kappa)
            true_logits = logits.gather(1, labels.unsqueeze(1)).squeeze(1)
            other_logits = logits.clone()
            other_logits.scatter_(1, labels.unsqueeze(1), float('-inf'))
            max_other_logits = other_logits.max(dim=1)[0]
            f_x = torch.clamp(true_logits - max_other_logits, min=-self.kappa)
        
        # Loss totale
        total_loss = (c_values * f_x + l2_distance).sum()
        
        return total_loss
    
    def _check_attack_success(self, x: torch.Tensor, labels: torch.Tensor,
                             target_labels: torch.Tensor, targeted: bool) -> torch.Tensor:
        """
        Verifie si l'attaque a reussi
        """
        with torch.no_grad():
            outputs = self.model(x)
            predicted = outputs.argmax(dim=1)
            
            if targeted:
                # Succes si prediction = target
                success = predicted.eq(target_labels)
            else:
                # Succes si prediction != vrai label
                success = ~predicted.eq(labels)
        
        return success
    
    def evaluate_robustness(self, dataloader, verbose: bool = True) -> dict:
        """
        Evalue la robustesse du modele contre C&W
        """
        self.model.eval()
        
        total = 0
        clean_correct = 0
        adv_correct = 0
        total_l2_distance = 0.0
        
        results = {
            'clean_accuracy': 0.0,
            'robust_accuracy': 0.0,
            'attack_success_rate': 0.0,
            'avg_l2_distance': 0.0,
            'total_samples': 0
        }
        
        for batch_idx, (data, target) in enumerate(dataloader):
            data, target = data.to(self.device), target.to(self.device)
            batch_size = data.size(0)
            
            # Predictions sur donnees propres
            with torch.no_grad():
                clean_outputs = self.model(data)
                clean_pred = clean_outputs.argmax(dim=1)
                clean_correct += clean_pred.eq(target).sum().item()
            
            # Generation exemples adversariaux C&W
            adv_data = self.generate(data, target, targeted=False)
            
            # Predictions sur donnees adversariales
            with torch.no_grad():
                adv_outputs = self.model(adv_data)
                adv_pred = adv_outputs.argmax(dim=1)
                adv_correct += adv_pred.eq(target).sum().item()
            
            # Distance L2 moyenne
            l2_dist = torch.norm((adv_data - data).view(batch_size, -1), p=2, dim=1).mean().item()
            total_l2_distance += l2_dist * batch_size
            
            total += batch_size
            
            if verbose and batch_idx % 5 == 0:
                print(f"C&W Batch {batch_idx}: Clean Acc={clean_correct/total:.3f}, "
                      f"Robust Acc={adv_correct/total:.3f}, Avg L2={l2_dist:.3f}")
        
        results['clean_accuracy'] = clean_correct / total
        results['robust_accuracy'] = adv_correct / total
        results['attack_success_rate'] = (clean_correct - adv_correct) / clean_correct if clean_correct > 0 else 0
        results['avg_l2_distance'] = total_l2_distance / total
        results['total_samples'] = total
        
        if verbose:
            print("\n=== C&W ROBUSTNESS EVALUATION ===")
            print(f"Clean Accuracy: {results['clean_accuracy']:.3f}")
            print(f"Robust Accuracy: {results['robust_accuracy']:.3f}")
            print(f"Attack Success Rate: {results['attack_success_rate']:.3f}")
            print(f"Average L2 Distance: {results['avg_l2_distance']:.3f}")
            print(f"Total Samples: {results['total_samples']}")
        
        return results

def test_cw_attack():
    """
    Test de l'implementation C&W
    """
    print("Test C&W Attack Implementation")
    
    # Mock model simple
    class SimpleModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
            self.conv2 = nn.Conv2d(16, 32, 3, padding=1) 
            self.fc = nn.Linear(32 * 56 * 56, 2)
            
        def forward(self, x):
            x = F.relu(self.conv1(x))
            x = F.max_pool2d(x, 2)
            x = F.relu(self.conv2(x))
            x = F.max_pool2d(x, 2)
            x = x.view(x.size(0), -1)
            return self.fc(x)
    
    model = SimpleModel()
    model.eval()
    
    # Test data (plus petit pour C&W)
    batch_size = 2
    images = torch.randn(batch_size, 3, 224, 224)
    labels = torch.randint(0, 2, (batch_size,))
    
    # Test C&W (parametres reduits pour test rapide)
    cw = CWAttack(model, c=1.0, max_iter=100, binary_search_steps=3)
    adv_images = cw.generate(images, labels)
    
    # Verification
    l2_distance = torch.norm((adv_images - images).view(batch_size, -1), p=2, dim=1).mean()
    print(f"Average L2 distance: {l2_distance:.4f}")
    
    # Verification que les images sont dans [0,1]
    assert adv_images.min() >= 0 and adv_images.max() <= 1, "Images hors de [0,1]"
    print("Test C&W: SUCCES")
    
    return True

if __name__ == "__main__":
    test_cw_attack()