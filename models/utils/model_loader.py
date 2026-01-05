"""
Module de chargement des modèles - GUIDE 

Ce module contient toutes les fonctions pour :
1. Charger des modèles pré-entraînés (comme ResNet50)
2. Sauvegarder nos modèles après entraînement
3. Recharger des modèles sauvegardés

Qu'est-ce qu'un modèle pré-entraîné ?
- C'est un modèle déjà entraîné sur des millions d'images (ImageNet)
- On peut l'adapter à notre tâche (transfer learning)
- C'est plus rapide que d'entraîner depuis zéro
"""

import torch
import torch.nn as nn
import torchvision.models as models
from typing import Optional, Dict, Any
import os
import yaml
import sys
import io

# Fix encoding pour Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class ModelLoader:
    """
    Gestionnaire de chargement des modèles - CLASSE UTILITAIRE
    
    Cette classe contient uniquement des méthodes statiques (@staticmethod)
    Cela signifie qu'on peut les utiliser sans créer d'instance :
    
    Exemple d'utilisation :
        model = ModelLoader.load_resnet50()  # Pas besoin de ModelLoader()
    """
    
    @staticmethod
    def load_resnet50_fast_local(num_classes: int = 2) -> torch.nn.Module:
        """
        Charge ResNet50 depuis le fichier local - RAPIDE
        
        Args:
            num_classes: Nombre de classes de sortie (2 = dangerous/safe)
        
        Returns:
            Le modèle ResNet50 avec poids pré-entraînés locaux
        """
        # Charger ResNet50 sans poids pré-entraînés
        model = models.resnet50(pretrained=False)
        
        # Chemin vers le modèle local
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        local_model_path = os.path.join(project_root, "models", "pretrained", "resnet50.pth")
        
        # Charger les poids locaux s'ils existent
        if os.path.exists(local_model_path):
            print(f"Chargement ResNet50 local: {local_model_path}")
            checkpoint = torch.load(local_model_path, map_location='cpu')
            # Si c'est un dict avec model_state_dict, l'utiliser, sinon utiliser directement
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            else:
                state_dict = checkpoint
            
            # Filtrer la couche fc si elle ne correspond pas à nos classes
            if 'fc.weight' in state_dict:
                fc_classes = state_dict['fc.weight'].shape[0]
                if fc_classes != num_classes:
                    print(f"Suppression couche fc ({fc_classes} -> {num_classes} classes)")
                    del state_dict['fc.weight']
                    del state_dict['fc.bias']
            
            # Charger les poids filtrés (strict=False pour ignorer fc si supprimée)
            model.load_state_dict(state_dict, strict=False)
        else:
            print("Modèle local non trouvé, chargement depuis internet...")
            model = models.resnet50(pretrained=True)
        
        # Adapter la dernière couche pour notre tâche
        model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
        
        return model

    @staticmethod
    def load_resnet50(pretrained: bool = True, num_classes: int = 2) -> torch.nn.Module:
        """
        Charge le modèle ResNet50 - EXPLICATION         
        ResNet50 = Architecture de réseau de neurones avec 50 couches
        - Très populaire pour la classification d'images
        - Pré-entraîné sur ImageNet (1M+ images, 1000 classes)
        
        Args:
            pretrained: Si True, charge les poids pré-entraînés ImageNet
                       Si False, poids aléatoires (plus difficile à entraîner)
            num_classes: Nombre de classes de sortie
                        2 = dangerous (1) vs safe (0)
        
        Returns:
            Le modèle PyTorch prêt à utiliser
        
        Étapes :
        1. Charger ResNet50 de torchvision
        2. Remplacer la dernière couche pour nos 2 classes
        3. Retourner le modèle modifié
        """
        # Étape 1: Charger ResNet50 pré-entraîné
        # models.resnet50() vient de torchvision (bibliothèque PyTorch)
        model = models.resnet50(pretrained=pretrained)
        
        # Étape 2: Adapter la dernière couche pour notre tâche
        # ResNet50 original : 1000 classes ImageNet
        # Notre tâche : 2 classes (dangerous/safe)
        # 
        # model.fc = dernière couche (Fully Connected)
        # model.fc.in_features = nombre d'entrées (2048 pour ResNet50)
        # torch.nn.Linear = couche linéaire : y = Wx + b
        model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
        
        # Maintenant le modèle sort 2 probabilités au lieu de 1000
        
        return model
    
    @staticmethod
    def load_checkpoint(checkpoint_path: str, device: str = 'cpu') -> torch.nn.Module:
        """
        Charge un modèle depuis un checkpoint - EXPLICATION      
        Qu'est-ce qu'un checkpoint ?
        - Fichier .pth qui contient :
          * Les poids du modèle (paramètres appris)
          * La configuration (nombre de classes, etc.)
          * Optionnel : état de l'optimiseur, epoch, loss
        
        Pourquoi sauvegarder des checkpoints ?
        - Reprendre l'entraînement si interrompu
        - Garder le meilleur modèle
        - Utiliser le modèle pour faire des prédictions
        
        Args:
            checkpoint_path: Chemin vers le fichier .pth
            device: 'cpu' ou 'cuda' (GPU)
            
        Returns:
            Le modèle rechargé avec ses poids
        """
        # Vérifier que le fichier existe
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint non trouvé: {checkpoint_path}")
            
        # Charger le checkpoint en mémoire
        # map_location=device : force le chargement sur CPU/GPU spécifié
        checkpoint = torch.load(checkpoint_path, map_location=device)
        
        # Récupérer les métadonnées sauvegardées
        model_config = checkpoint.get('config', {})  # Configuration du modèle
        num_classes = model_config.get('num_classes', 2)  # Par défaut 2 classes
        
        # Recréer la même architecture
        # pretrained=False car on va charger nos propres poids
        model = ModelLoader.load_resnet50(pretrained=False, num_classes=num_classes)
        
        # Charger les poids sauvegardés dans le modèle
        # state_dict = dictionnaire des paramètres du modèle
        model.load_state_dict(checkpoint['model_state_dict'])
        
        # Déplacer le modèle sur le bon device (CPU/GPU)
        model.to(device)
        
        return model
    
    @staticmethod
    def save_model(model: torch.nn.Module, save_path: str, config: Dict[str, Any] = None,
                   optimizer: torch.optim.Optimizer = None, epoch: int = None,
                   loss: float = None) -> None:
        """
        Sauvegarde un modèle avec métadonnées - EXPLICATION 
        
        Qu'est-ce qu'on sauvegarde ?
        1. Les poids du modèle (obligatoire)
        2. La configuration (nombre de classes, etc.)
        3. L'état de l'optimiseur (pour reprendre l'entraînement)
        4. L'epoch et la loss (pour le suivi)
        
        Pourquoi sauvegarder l'optimiseur ?
        - L'optimiseur (Adam, SGD) a sa propre mémoire
        - Pour reprendre l'entraînement exactement où on s'était arrêté
        
        Args:
            model: Le modèle PyTorch à sauvegarder
            save_path: Où sauvegarder (ex: 'models/best_model.pth')
            config: Dictionnaire avec les paramètres d'entraînement
            optimizer: L'optimiseur utilisé (Adam, SGD, etc.)
            epoch: Numéro de l'epoch actuelle
            loss: Valeur de la loss actuelle
        """
        # Créer le dossier de destination s'il n'existe pas
        # exist_ok=True : pas d'erreur si le dossier existe déjà
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Créer le dictionnaire checkpoint avec toutes les informations
        checkpoint = {
            'model_state_dict': model.state_dict(),  # Poids du modèle
            'config': config or {},  # Configuration (ou {} si None)
        }
        
        # Ajouter les éléments optionnels s'ils sont fournis
        if optimizer is not None:
            # Sauvegarder l'état de l'optimiseur (momentum, etc.)
            checkpoint['optimizer_state_dict'] = optimizer.state_dict()
        if epoch is not None:
            checkpoint['epoch'] = epoch
        if loss is not None:
            checkpoint['loss'] = loss
            
        # Sauvegarder le tout dans un fichier .pth
        torch.save(checkpoint, save_path)
        print(f"Modèle sauvegardé: {save_path}")
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        Charge un fichier de configuration YAML
        
        Args:
            config_path: Chemin vers le fichier YAML
            
        Returns:
            Configuration chargée
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def load_mobilenetv2(pretrained: bool = True, num_classes: int = 2) -> torch.nn.Module:
        """
        Charge MobileNetV2 avec architecture personnalisée

        MobileNetV2 = Architecture légère optimisée pour mobile/embedded
        - 3.5M paramètres (vs 25.6M pour ResNet50)
        - Plus rapide en inférence
        - Meilleure généralisation sur petits datasets

        Args:
            pretrained: Si True, charge les poids ImageNet
            num_classes: Nombre de classes (2 = dangerous/safe)

        Returns:
            Modèle MobileNetV2 avec classifier personnalisé
        """
        # Classe wrapper pour MobileNetV2
        class MobileNetV2Classifier(nn.Module):
            def __init__(self, num_classes=2, pretrained=True):
                super().__init__()
                self.mobilenet = models.mobilenet_v2(pretrained=pretrained)

                # Freeze early layers (transfer learning)
                for param in self.mobilenet.features[:-3].parameters():
                    param.requires_grad = False

                # Classifier personnalisé
                in_features = self.mobilenet.classifier[1].in_features
                self.mobilenet.classifier = nn.Sequential(
                    nn.Dropout(0.3),
                    nn.Linear(in_features, 256),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(256, num_classes)
                )

            def forward(self, x):
                return self.mobilenet(x)

        return MobileNetV2Classifier(num_classes=num_classes, pretrained=pretrained)

    @staticmethod
    def load_mobilenetv2_checkpoint(checkpoint_path: str, device: str = 'cpu') -> torch.nn.Module:
        """
        Charge un checkpoint MobileNetV2

        Args:
            checkpoint_path: Chemin vers le .pth
            device: 'cpu' ou 'cuda'

        Returns:
            Modèle MobileNetV2 chargé
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint non trouvé: {checkpoint_path}")

        # Charger le checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=device)

        # Créer le modèle
        model = ModelLoader.load_mobilenetv2(pretrained=False, num_classes=2)

        # Charger les poids
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
            print(f"✅ MobileNetV2 chargé (epoch {checkpoint.get('epoch', 'N/A')})")
            if 'val_acc' in checkpoint:
                print(f"   Val Accuracy: {checkpoint['val_acc']:.2f}%")
        else:
            model.load_state_dict(checkpoint)
            print("✅ MobileNetV2 chargé")

        model.to(device)
        model.eval()

        return model

    @staticmethod
    def get_device() -> str:
        """
        Détecte le meilleur device disponible - EXPLICATION

        Device = où les calculs vont s'exécuter :
        - CPU : Processeur classique (lent mais toujours disponible)
        - CUDA/GPU : Carte graphique (très rapide pour l'IA)

        Cette fonction choisit automatiquement :
        - GPU si disponible (10x+ plus rapide)
        - CPU sinon (plus lent mais ça marche)

        Returns:
            'cuda' si GPU disponible, 'cpu' sinon
        """
        # torch.cuda.is_available() vérifie si CUDA (GPU NVIDIA) est dispo
        return 'cuda' if torch.cuda.is_available() else 'cpu'
