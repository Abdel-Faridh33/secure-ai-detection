"""
Fast Gradient Sign Method (FGSM) Attack
Référence: Goodfellow et al., 2014 - https://arxiv.org/abs/1412.6572
"""

import torch
import torch.nn as nn

class FGSMAttack:
    """Implémentation de l'attaque FGSM"""
    
    def __init__(self, model: nn.Module, epsilon: float = 0.03):
        """
        Args:
            model: Modèle cible
            epsilon: Intensité de la perturbation
        """
        self.model = model
        self.epsilon = epsilon
    
    def generate(self, images: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Génère des exemples adversariaux
        
        Returns:
            Images perturbées
        """
        images.requires_grad = True
        
        # Forward pass
        outputs = self.model(images)
        loss = nn.CrossEntropyLoss()(outputs, labels)
        
        # Calcul du gradient
        self.model.zero_grad()
        loss.backward()
        
        # Création de la perturbation
        perturbation = self.epsilon * images.grad.sign()
        adversarial_images = images + perturbation
        
        # Clip pour rester dans [0, 1]
        adversarial_images = torch.clamp(adversarial_images, 0, 1)
        
        return adversarial_images
