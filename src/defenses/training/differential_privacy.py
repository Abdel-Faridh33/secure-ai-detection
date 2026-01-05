"""
Differential Privacy Training
Entraînement avec confidentialité différentielle
Référence: Abadi et al., 2016 - https://arxiv.org/abs/1607.00133
"""

import torch
import numpy as np

class DifferentialPrivacy:
    """Module de confidentialité différentielle"""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Args:
            epsilon: Budget de confidentialité
            delta: Probabilité de violation
        """
        self.epsilon = epsilon
        self.delta = delta
    
    def add_noise(self, gradients: torch.Tensor, sensitivity: float) -> torch.Tensor:
        """Ajoute du bruit calibré aux gradients"""
        noise_scale = sensitivity / self.epsilon
        noise = torch.normal(0, noise_scale, size=gradients.shape)
        return gradients + noise
