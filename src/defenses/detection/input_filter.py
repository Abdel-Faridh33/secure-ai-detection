"""
Input Filtering
Filtrage et validation des entrées suspectes
"""

import torch
import numpy as np

class InputFilter:
    """Filtre de détection d'entrées malveillantes"""
    
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
    
    def is_suspicious(self, image: torch.Tensor) -> bool:
        """Détecte si une image est suspecte"""
        # Analyse statistique de l'image
        mean = image.mean().item()
        std = image.std().item()
        
        # Critères de suspicion
        if std < 0.01:  # Image trop uniforme
            return True
        if mean > 0.99 or mean < 0.01:  # Valeurs extrêmes
            return True
            
        return False
