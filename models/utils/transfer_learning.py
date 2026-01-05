"""
Module de transfer learning pour adaptation à la détection d'objets dangereux
"""

import torch
import torch.nn as nn
from torch.optim import Adam

class TransferLearning:
    """Gestionnaire du transfer learning pour ResNet50"""
    
    def __init__(self, model: nn.Module, freeze_layers: bool = True):
        self.model = model
        if freeze_layers:
            self.freeze_backbone()
    
    def freeze_backbone(self):
        """Gèle les couches du backbone pour ne fine-tuner que le classifier"""
        for param in self.model.parameters():
            param.requires_grad = False
        
        # Dégeler seulement la dernière couche
        for param in self.model.fc.parameters():
            param.requires_grad = True
