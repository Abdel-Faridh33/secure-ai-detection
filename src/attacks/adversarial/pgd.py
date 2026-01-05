"""
Projected Gradient Descent (PGD) Attack - Implementation Complete
Reference: Madry et al., 2018 - https://arxiv.org/abs/1706.06083

Implementation complete pour pipeline robuste avec 500+ echantillons
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple

class PGDAttack:
    """Implementation complete de l'attaque PGD pour evaluation robuste"""
    
    def __init__(self, model: nn.Module, epsilon: float = 0.031, 
                 alpha: float = 0.007, num_iter: int = 10, 
                 random_start: bool = True, device: str = 'cpu'):
        """
        Args:
            model: Modele cible
            epsilon: Rayon de perturbation maximum (aligne avec TRADES)
            alpha: Taille du pas (epsilon/4 standard)
            num_iter: Nombre d'iterations (aligne avec tests)
            random_start: Initialisation aleatoire
            device: Device pour calculs
        """
        self.model = model
        self.epsilon = epsilon
        self.alpha = alpha
        self.num_iter = num_iter
        self.random_start = random_start
        self.device = device
        self.criterion = nn.CrossEntropyLoss()
        
        print(f"PGD Attack configure: eps={epsilon}, alpha={alpha}, iter={num_iter}")
    
    def generate(self, images: torch.Tensor, labels: torch.Tensor, 
                 targeted: bool = False, target_labels: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Genere des exemples adversariaux avec PGD
        
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
        
        # Clone pour eviter modification des originales
        adv_images = images.clone().detach()
        
        # Initialisation aleatoire dans l'epsilon-ball
        if self.random_start:
            # Uniform random noise in [-epsilon, epsilon]
            noise = torch.empty_like(adv_images).uniform_(-self.epsilon, self.epsilon)
            adv_images = adv_images + noise
            adv_images = torch.clamp(adv_images, 0, 1)
        
        for i in range(self.num_iter):
            adv_images = self._pgd_step(adv_images, images, labels, 
                                      targeted, target_labels)
        
        return adv_images
    
    def _pgd_step(self, adv_images: torch.Tensor, orig_images: torch.Tensor,
                  labels: torch.Tensor, targeted: bool = False,
                  target_labels: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Une iteration PGD
        """
        adv_images.requires_grad_(True)
        
        # Forward pass
        outputs = self.model(adv_images)
        
        # Calcul de la loss
        if targeted and target_labels is not None:
            # Attaque ciblee: minimiser loss pour target
            loss = -self.criterion(outputs, target_labels)
        else:
            # Attaque non-ciblee: maximiser loss pour vrai label
            loss = self.criterion(outputs, labels)
        
        # Backward pass
        self.model.zero_grad()
        loss.backward()
        
        # Gradient step
        with torch.no_grad():
            # Signe du gradient
            grad_sign = adv_images.grad.sign()
            
            # Mise a jour
            if targeted:
                adv_images = adv_images - self.alpha * grad_sign
            else:
                adv_images = adv_images + self.alpha * grad_sign
            
            # Projection sur l'epsilon-ball
            delta = adv_images - orig_images
            delta = torch.clamp(delta, -self.epsilon, self.epsilon)
            adv_images = orig_images + delta
            
            # Projection sur [0,1]
            adv_images = torch.clamp(adv_images, 0, 1)
        
        adv_images.requires_grad_(False)
        return adv_images
    
    def evaluate_robustness(self, dataloader, verbose: bool = True) -> dict:
        """
        Evalue la robustesse du modele contre PGD
        
        Returns:
            Dict avec metriques de robustesse
        """
        self.model.eval()
        
        total = 0
        clean_correct = 0
        adv_correct = 0
        
        results = {
            'clean_accuracy': 0.0,
            'robust_accuracy': 0.0,
            'attack_success_rate': 0.0,
            'total_samples': 0
        }
        
        with torch.no_grad():
            for batch_idx, (data, target) in enumerate(dataloader):
                data, target = data.to(self.device), target.to(self.device)
                batch_size = data.size(0)
                
                # Predictions sur donnees propres
                clean_outputs = self.model(data)
                clean_pred = clean_outputs.argmax(dim=1)
                clean_correct += clean_pred.eq(target).sum().item()
                
                # Generation exemples adversariaux
                # Temporairement enable gradients pour PGD
                self.model.eval()
                data.requires_grad_(True)
                
                adv_data = self.generate(data, target)
                
                # Predictions sur donnees adversariales
                adv_outputs = self.model(adv_data)
                adv_pred = adv_outputs.argmax(dim=1)
                adv_correct += adv_pred.eq(target).sum().item()
                
                total += batch_size
                
                if verbose and batch_idx % 10 == 0:
                    print(f"Batch {batch_idx}: Clean Acc={clean_correct/total:.3f}, "
                          f"Robust Acc={adv_correct/total:.3f}")
        
        results['clean_accuracy'] = clean_correct / total
        results['robust_accuracy'] = adv_correct / total  
        results['attack_success_rate'] = (clean_correct - adv_correct) / clean_correct if clean_correct > 0 else 0
        results['total_samples'] = total
        
        if verbose:
            print("\n=== PGD ROBUSTNESS EVALUATION ===")
            print(f"Clean Accuracy: {results['clean_accuracy']:.3f}")
            print(f"Robust Accuracy: {results['robust_accuracy']:.3f}")
            print(f"Attack Success Rate: {results['attack_success_rate']:.3f}")
            print(f"Total Samples: {results['total_samples']}")
        
        return results

class PGDAttackL2:
    """
    PGD Attack avec norme L2 (pour evaluation complete)
    """
    
    def __init__(self, model: nn.Module, epsilon: float = 1.0,
                 alpha: float = 0.2, num_iter: int = 10, device: str = 'cpu'):
        self.model = model
        self.epsilon = epsilon
        self.alpha = alpha
        self.num_iter = num_iter
        self.device = device
        self.criterion = nn.CrossEntropyLoss()
    
    def generate(self, images: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        PGD-L2 implementation
        """
        images = images.to(self.device)
        labels = labels.to(self.device)
        
        adv_images = images.clone().detach()
        
        # Random start in L2 ball
        noise = torch.randn_like(adv_images)
        noise = noise / noise.view(noise.size(0), -1).norm(dim=1, keepdim=True).view(-1, 1, 1, 1)
        noise = noise * torch.rand(noise.size(0), 1, 1, 1).to(self.device) * self.epsilon
        adv_images = adv_images + noise
        adv_images = torch.clamp(adv_images, 0, 1)
        
        for _ in range(self.num_iter):
            adv_images.requires_grad_(True)
            
            outputs = self.model(adv_images)
            loss = self.criterion(outputs, labels)
            
            self.model.zero_grad()
            loss.backward()
            
            with torch.no_grad():
                # Normalize gradient to unit norm
                grad = adv_images.grad
                grad_norm = grad.view(grad.size(0), -1).norm(dim=1, keepdim=True)
                grad = grad / (grad_norm.view(-1, 1, 1, 1) + 1e-8)
                
                # Update
                adv_images = adv_images + self.alpha * grad
                
                # Project to L2 ball
                delta = adv_images - images
                delta_norm = delta.view(delta.size(0), -1).norm(dim=1, keepdim=True)
                delta = delta / torch.max(delta_norm / self.epsilon, torch.ones_like(delta_norm))
                delta = delta.view(images.size())
                adv_images = images + delta
                
                # Clip to valid range
                adv_images = torch.clamp(adv_images, 0, 1)
        
        return adv_images

def test_pgd_attack():
    """
    Test de l'implementation PGD
    """
    print("Test PGD Attack Implementation")
    
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
    
    # Test data
    batch_size = 4
    images = torch.randn(batch_size, 3, 224, 224)
    labels = torch.randint(0, 2, (batch_size,))
    
    # Test PGD
    pgd = PGDAttack(model, epsilon=0.031, alpha=0.007, num_iter=10)
    adv_images = pgd.generate(images, labels)
    
    # Verification
    perturbation = (adv_images - images).abs().max()
    print(f"Max perturbation: {perturbation:.6f}")
    print(f"Expected max perturbation: {pgd.epsilon:.6f}")
    
    assert perturbation <= pgd.epsilon + 1e-6, "Perturbation exceeds epsilon"
    print("Test PGD: SUCCES")
    
    return True

if __name__ == "__main__":
    test_pgd_attack()