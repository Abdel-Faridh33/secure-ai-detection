#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entraînement Baseline avec MobileNetV2
Architecture légère adaptée au dataset de taille moyenne (~2000 images)
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, models
from PIL import Image
import os
import json
from tqdm import tqdm
import matplotlib.pyplot as plt
from typing import Tuple, Dict, List
import numpy as np
from pathlib import Path
import sys

# Fix encoding pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))


class DangerousObjectDataset(Dataset):
    """Dataset pour les images safe/dangerous"""

    def __init__(self, data_dir: str, split: str, transform=None):
        """
        Args:
            data_dir: Chemin vers data/prepared/
            split: 'train', 'val' ou 'test'
            transform: Transformations à appliquer
        """
        self.data_dir = Path(data_dir)
        self.split = split
        self.transform = transform

        self.images = []
        self.labels = []

        # Charger les images depuis safe/ et dangerous/
        split_dir = self.data_dir / split

        # Classe safe (label 0)
        safe_dir = split_dir / 'safe'
        if safe_dir.exists():
            for img_path in safe_dir.glob('*.jpg'):
                self.images.append(str(img_path))
                self.labels.append(0)

        # Classe dangerous (label 1)
        dangerous_dir = split_dir / 'dangerous'
        if dangerous_dir.exists():
            for img_path in dangerous_dir.glob('*.jpg'):
                self.images.append(str(img_path))
                self.labels.append(1)

        print(f"  {split}: {len(self.images)} images "
              f"(safe: {self.labels.count(0)}, dangerous: {self.labels.count(1)})")

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        img_path = self.images[idx]
        label = self.labels[idx]

        # Charger l'image
        image = Image.open(img_path).convert('RGB')

        # Appliquer les transformations
        if self.transform:
            image = self.transform(image)

        return image, label


class MobileNetV2Classifier(nn.Module):
    """
    Classificateur basé sur MobileNetV2

    Avantages de MobileNetV2:
    - 3.5M paramètres (vs 25.6M pour ResNet50)
    - Architecture optimisée pour mobile/embedded
    - Meilleure généralisation sur petits datasets
    - Transfer learning efficace
    """

    def __init__(self, num_classes: int = 2, pretrained: bool = True):
        super().__init__()

        # Charger MobileNetV2 pré-entraîné sur ImageNet
        self.mobilenet = models.mobilenet_v2(pretrained=pretrained)

        # Freeze early layers (transfer learning)
        # On ne fine-tune que les dernières couches
        for param in self.mobilenet.features[:-3].parameters():
            param.requires_grad = False

        # Remplacer le classifier
        # MobileNetV2 a 1280 features en sortie
        in_features = self.mobilenet.classifier[1].in_features

        self.mobilenet.classifier = nn.Sequential(
            nn.Dropout(0.3),  # Dropout pour régularisation
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.mobilenet(x)


class EarlyStopping:
    """
    Early stopping pour éviter l'overfitting

    Arrête l'entraînement si la validation loss ne s'améliore pas
    pendant 'patience' epochs
    """

    def __init__(self, patience: int = 7, min_delta: float = 0.0, verbose: bool = True):
        """
        Args:
            patience: Nombre d'epochs sans amélioration avant arrêt
            min_delta: Amélioration minimale considérée comme significative
            verbose: Afficher les messages
        """
        self.patience = patience
        self.min_delta = min_delta
        self.verbose = verbose
        self.counter = 0
        self.best_loss = None
        self.early_stop = False
        self.best_model_state = None

    def __call__(self, val_loss: float, model: nn.Module) -> bool:
        """
        Args:
            val_loss: Validation loss actuelle
            model: Modèle à sauvegarder

        Returns:
            True si l'entraînement doit s'arrêter
        """
        if self.best_loss is None:
            self.best_loss = val_loss
            self.best_model_state = model.state_dict().copy()
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.verbose:
                print(f"  EarlyStopping counter: {self.counter}/{self.patience}")
            if self.counter >= self.patience:
                self.early_stop = True
                if self.verbose:
                    print("  Early stopping triggered!")
        else:
            if self.verbose:
                print(f"  Validation loss improved: {self.best_loss:.4f} → {val_loss:.4f}")
            self.best_loss = val_loss
            self.best_model_state = model.state_dict().copy()
            self.counter = 0

        return self.early_stop


class BaselineTrainer:
    """Entraîneur pour le modèle baseline MobileNetV2"""

    def __init__(
        self,
        data_dir: str = "data/prepared",
        model_dir: str = "models/baseline",
        batch_size: int = 32,
        num_epochs: int = 50,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-4,
        device: str = None
    ):
        """
        Args:
            data_dir: Dossier contenant train/val/test
            model_dir: Dossier pour sauvegarder le modèle
            batch_size: Taille des batchs
            num_epochs: Nombre d'epochs maximum
            learning_rate: Learning rate initial
            weight_decay: L2 regularization
            device: 'cuda' ou 'cpu' (auto-détection si None)
        """
        self.data_dir = data_dir
        self.model_dir = Path(model_dir)
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay

        # Device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"🖥️  Device: {self.device}")

        # Créer le dossier modèle
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Transformations
        self.train_transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])  # ImageNet stats
        ])

        self.val_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

        # Historique d'entraînement
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }

    def create_dataloaders(self) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """Crée les dataloaders"""
        print("\n📦 Chargement des datasets...")

        train_dataset = DangerousObjectDataset(
            self.data_dir, 'train', self.train_transform
        )
        val_dataset = DangerousObjectDataset(
            self.data_dir, 'val', self.val_transform
        )
        test_dataset = DangerousObjectDataset(
            self.data_dir, 'test', self.val_transform
        )

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )
        test_loader = DataLoader(
            test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )

        return train_loader, val_loader, test_loader

    def train_epoch(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        criterion: nn.Module,
        optimizer: optim.Optimizer
    ) -> Tuple[float, float]:
        """Entraîne le modèle pour une epoch"""
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        pbar = tqdm(train_loader, desc="Training")
        for images, labels in pbar:
            images, labels = images.to(self.device), labels.to(self.device)

            # Forward
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)

            # Backward
            loss.backward()
            optimizer.step()

            # Statistiques
            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

            # Update progress bar
            pbar.set_postfix({
                'loss': loss.item(),
                'acc': 100. * correct / total
            })

        epoch_loss = running_loss / total
        epoch_acc = 100. * correct / total

        return epoch_loss, epoch_acc

    def validate(
        self,
        model: nn.Module,
        val_loader: DataLoader,
        criterion: nn.Module
    ) -> Tuple[float, float]:
        """Évalue le modèle sur le validation set"""
        model.eval()
        running_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for images, labels in tqdm(val_loader, desc="Validation"):
                images, labels = images.to(self.device), labels.to(self.device)

                outputs = model(images)
                loss = criterion(outputs, labels)

                running_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

        epoch_loss = running_loss / total
        epoch_acc = 100. * correct / total

        return epoch_loss, epoch_acc

    def train(self):
        """Lance l'entraînement complet"""
        print("="*60)
        print("🚀 ENTRAÎNEMENT BASELINE MOBILENETV2")
        print("="*60)

        # Créer les dataloaders
        train_loader, val_loader, test_loader = self.create_dataloaders()

        # Créer le modèle
        print("\n🏗️  Création du modèle MobileNetV2...")
        model = MobileNetV2Classifier(num_classes=2, pretrained=True)
        model = model.to(self.device)

        # Compter les paramètres
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"  Total parameters: {total_params:,}")
        print(f"  Trainable parameters: {trainable_params:,}")

        # Loss et optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=self.learning_rate,
            weight_decay=self.weight_decay
        )

        # Learning rate scheduler
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )

        # Early stopping
        early_stopping = EarlyStopping(patience=10, verbose=True)

        # Entraînement
        print(f"\n📚 Entraînement sur {self.num_epochs} epochs max...")
        print("="*60)

        best_val_acc = 0.0

        for epoch in range(1, self.num_epochs + 1):
            print(f"\nEpoch {epoch}/{self.num_epochs}")
            print("-" * 40)

            # Train
            train_loss, train_acc = self.train_epoch(
                model, train_loader, criterion, optimizer
            )

            # Validate
            val_loss, val_acc = self.validate(model, val_loader, criterion)

            # Update learning rate
            scheduler.step(val_loss)

            # Sauvegarder l'historique
            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)

            # Afficher les résultats
            print(f"\n📊 Résultats Epoch {epoch}:")
            print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
            print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc:.2f}%")

            # Sauvegarder le meilleur modèle
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_acc': val_acc,
                    'val_loss': val_loss,
                }, self.model_dir / 'best_model.pth')
                print(f"  ✓ Meilleur modèle sauvegardé (val_acc: {val_acc:.2f}%)")

            # Early stopping
            if early_stopping(val_loss, model):
                print(f"\n⏹️  Early stopping à l'epoch {epoch}")
                # Restaurer le meilleur modèle
                model.load_state_dict(early_stopping.best_model_state)
                break

        # Évaluation finale sur test set
        print("\n" + "="*60)
        print("🧪 ÉVALUATION FINALE SUR TEST SET")
        print("="*60)

        test_loss, test_acc = self.validate(model, test_loader, criterion)
        print(f"\n📊 Résultats Test:")
        print(f"  Test Loss: {test_loss:.4f}")
        print(f"  Test Acc:  {test_acc:.2f}%")

        # Sauvegarder le modèle final
        torch.save({
            'model_state_dict': model.state_dict(),
            'test_acc': test_acc,
            'test_loss': test_loss,
            'history': self.history
        }, self.model_dir / 'final_model.pth')

        # Sauvegarder l'historique
        with open(self.model_dir / 'training_history.json', 'w') as f:
            json.dump(self.history, f, indent=2)

        # Générer les graphiques
        self.plot_history()

        print(f"\n✅ Entraînement terminé!")
        print(f"📂 Modèle sauvegardé dans: {self.model_dir}")
        print(f"🎯 Meilleure validation accuracy: {best_val_acc:.2f}%")
        print(f"🧪 Test accuracy finale: {test_acc:.2f}%")

    def plot_history(self):
        """Génère les graphiques d'entraînement"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        epochs = range(1, len(self.history['train_loss']) + 1)

        # Loss
        ax1.plot(epochs, self.history['train_loss'], 'b-', label='Train Loss')
        ax1.plot(epochs, self.history['val_loss'], 'r-', label='Val Loss')
        ax1.set_title('Training and Validation Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        ax1.grid(True)

        # Accuracy
        ax2.plot(epochs, self.history['train_acc'], 'b-', label='Train Acc')
        ax2.plot(epochs, self.history['val_acc'], 'r-', label='Val Acc')
        ax2.set_title('Training and Validation Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy (%)')
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()
        plt.savefig(self.model_dir / 'training_history.png', dpi=150)
        print(f"  📈 Graphiques sauvegardés: {self.model_dir / 'training_history.png'}")


def main():
    """Point d'entrée principal"""
    trainer = BaselineTrainer(
        data_dir="data/prepared",
        model_dir="models/baseline",
        batch_size=32,
        num_epochs=50,
        learning_rate=0.001,
        weight_decay=1e-4
    )

    trainer.train()


if __name__ == "__main__":
    main()
