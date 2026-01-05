"""
Ensemble Defense
Défense par ensemble de modèles
"""

import torch
import torch.nn as nn
from typing import List

class EnsembleDefense:
    """Défense utilisant un ensemble de modèles"""
    
    def __init__(self, models: List[nn.Module]):
        self.models = models
    
    def predict(self, image: torch.Tensor) -> torch.Tensor:
        """Prédiction par vote majoritaire"""
        predictions = []
        for model in self.models:
            pred = model(image)
            predictions.append(pred)
        
        # Vote majoritaire
        ensemble_pred = torch.stack(predictions).mean(dim=0)
        return ensemble_pred
