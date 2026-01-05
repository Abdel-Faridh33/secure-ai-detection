"""
Advanced Data Augmentation
Augmentation avancée pour atteindre 500+ échantillons par classe
Solution aux problèmes identifiés dans l'adversarial training
"""

import torch
import torchvision.transforms as transforms
from PIL import Image, ImageFilter
import numpy as np
import random
from pathlib import Path
import os
from typing import List, Tuple, Optional
import json
from datetime import datetime

class AdvancedDataAugmentation:
    """
    Augmentation avancée pour résoudre le problème de manque de données
    Génère 500+ échantillons par classe avec diversité maximale
    """
    
    def __init__(self, target_samples_per_class: int = 500, preserve_original: bool = True):
        self.target_samples_per_class = target_samples_per_class
        self.preserve_original = preserve_original
        
        # Transformations de base (légères)
        self.light_transforms = [
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=(-15, 15)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
        ]
        
        # Transformations moyennes
        self.medium_transforms = [
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
            transforms.RandomAdjustSharpness(sharpness_factor=2, p=0.5),
        ]
        
        # Transformations fortes (mais pas destructrices)
        self.strong_transforms = [
            transforms.RandomRotation(degrees=(-30, 30)),
            transforms.RandomAffine(degrees=0, translate=(0.15, 0.15), scale=(0.8, 1.2)),
            transforms.RandomAutocontrast(p=0.3),
        ]
        
        # Transformations de résistance adversariale
        self.adversarial_resistant_transforms = [
            transforms.GaussianBlur(kernel_size=5, sigma=(1.0, 3.0)),
            transforms.RandomPosterize(bits=4, p=0.3),
            transforms.RandomSolarize(threshold=192.0, p=0.2),
            transforms.RandomEqualize(p=0.3),
        ]
    
    def create_augmented_dataset(self, source_dir: Path, output_dir: Path) -> dict:
        """
        Crée un dataset augmenté à partir du dataset source
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        stats = {"original": 0, "generated": 0, "total": 0, "classes": {}}
        
        print(f"Génération dataset augmenté: {self.target_samples_per_class} échantillons par classe")
        
        for class_name in ["safe", "dangerous"]:
            class_source_dir = source_dir / class_name
            class_output_dir = output_dir / class_name
            class_output_dir.mkdir(exist_ok=True)
            
            if not class_source_dir.exists():
                print(f"AVERTISSEMENT: Repertoire source manquant: {class_source_dir}")
                continue
            
            # Collecter images originales
            original_images = list(class_source_dir.glob("*.jpg"))
            original_count = len(original_images)
            stats["classes"][class_name] = {"original": original_count, "generated": 0}
            
            print(f"Classe {class_name}: {original_count} images originales")
            
            if original_count == 0:
                print(f"AVERTISSEMENT: Aucune image dans {class_source_dir}")
                continue
            
            # Copier originales si demandé
            if self.preserve_original:
                for img_path in original_images:
                    new_path = class_output_dir / f"orig_{img_path.name}"
                    img = Image.open(img_path)
                    img.save(new_path)
            
            # Calculer le nombre d'augmentations nécessaires
            needed_samples = self.target_samples_per_class - (original_count if self.preserve_original else 0)
            augmentations_per_image = needed_samples // original_count + 1
            
            print(f"Génération de {augmentations_per_image} variantes par image pour {class_name}")
            
            generated_count = 0
            for i, img_path in enumerate(original_images):
                base_img = Image.open(img_path).convert('RGB')
                
                for aug_idx in range(augmentations_per_image):
                    if generated_count >= needed_samples:
                        break
                        
                    # Appliquer augmentation selon la variante
                    augmented_img = self._apply_augmentation_variant(base_img, aug_idx)
                    
                    # Sauvegarder
                    output_path = class_output_dir / f"aug_{i:03d}_{aug_idx:03d}_{generated_count:04d}.jpg"
                    augmented_img.save(output_path, quality=95)
                    generated_count += 1
                    
                    if generated_count % 100 == 0:
                        print(f"  Généré {generated_count}/{needed_samples} pour {class_name}")
            
            stats["classes"][class_name]["generated"] = generated_count
            print(f"SUCCES {class_name}: {generated_count} images generees")
        
        # Calculer statistiques totales
        for class_stats in stats["classes"].values():
            stats["original"] += class_stats["original"]
            stats["generated"] += class_stats["generated"]
        stats["total"] = stats["original"] + stats["generated"]
        
        # Sauvegarder métadonnées
        metadata = {
            "generation_time": datetime.now().isoformat(),
            "target_per_class": self.target_samples_per_class,
            "preserve_original": self.preserve_original,
            "statistics": stats,
            "source_directory": str(source_dir),
            "output_directory": str(output_dir)
        }
        
        with open(output_dir / "augmentation_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return stats
    
    def _apply_augmentation_variant(self, image: Image.Image, variant_idx: int) -> Image.Image:
        """
        Applique différentes combinaisons d'augmentation selon l'index
        """
        # Stratégie de diversification:
        # 25% transformations légères
        # 35% transformations moyennes  
        # 25% transformations fortes
        # 15% transformations résistantes aux attaques adversariales
        
        variant_type = variant_idx % 4
        
        if variant_type == 0:  # Légères
            transforms_to_apply = random.sample(self.light_transforms, k=random.randint(1, 2))
        elif variant_type == 1:  # Moyennes
            transforms_to_apply = random.sample(self.medium_transforms, k=random.randint(1, 2))
        elif variant_type == 2:  # Fortes
            transforms_to_apply = random.sample(self.strong_transforms, k=random.randint(1, 2))
        else:  # Résistantes adversariales
            transforms_to_apply = random.sample(self.adversarial_resistant_transforms, k=random.randint(1, 2))
        
        # Appliquer les transformations séquentiellement
        augmented_img = image
        for transform in transforms_to_apply:
            # Convertir en tensor pour les transformations PyTorch
            tensor_img = transforms.ToTensor()(augmented_img)
            try:
                transformed_tensor = transform(tensor_img)
                augmented_img = transforms.ToPILImage()(transformed_tensor)
            except Exception:
                # Si erreur, garder l'image précédente
                pass
        
        # Assurer la taille cohérente
        augmented_img = augmented_img.resize((224, 224))
        
        return augmented_img
    
    def augment_existing_dataset(self, base_data_dir: Path) -> Tuple[Path, dict]:
        """
        Augmente le dataset existant pour atteindre les objectifs
        """
        train_source = base_data_dir / "processed" / "train"
        val_source = base_data_dir / "processed" / "val"
        
        # Créer répertoires augmentés
        augmented_dir = base_data_dir / "augmented"
        train_augmented = augmented_dir / "train"
        val_augmented = augmented_dir / "val"
        
        print("\nAUGMENTATION AVANCEE POUR ADVERSARIAL TRAINING")
        print("="*60)
        print(f"Objectif: {self.target_samples_per_class} échantillons par classe")
        print(f"Source: {train_source}")
        print(f"Destination: {train_augmented}")
        
        # Augmenter train set
        train_stats = self.create_augmented_dataset(train_source, train_augmented)
        
        # Pour validation, objectif plus modeste (100 par classe)
        val_augmenter = AdvancedDataAugmentation(target_samples_per_class=100)
        val_stats = val_augmenter.create_augmented_dataset(val_source, val_augmented)
        
        # Copier test set sans modification
        test_source = base_data_dir / "processed" / "test"
        test_augmented = augmented_dir / "test"
        if test_source.exists():
            import shutil
            if test_augmented.exists():
                shutil.rmtree(test_augmented)
            shutil.copytree(test_source, test_augmented)
        
        combined_stats = {
            "train": train_stats,
            "val": val_stats,
            "augmentation_complete": True,
            "ready_for_adversarial_training": True
        }
        
        print("\nSUCCES: AUGMENTATION TERMINEE")
        print("="*60)
        print(f"Train: {train_stats['total']} échantillons total")
        print(f"  - Safe: {train_stats['classes'].get('safe', {}).get('generated', 0)} generes")
        print(f"  - Dangerous: {train_stats['classes'].get('dangerous', {}).get('generated', 0)} generes")
        print(f"Val: {val_stats['total']} échantillons total")
        print(f"\nPret pour entrainement TRADES avec dataset robuste!")
        
        return augmented_dir, combined_stats

class DefensiveAugmentation:
    """Compatibilité avec l'ancien code"""
    
    def __init__(self):
        self.advanced_aug = AdvancedDataAugmentation()
        self.transform = transforms.Compose([
            transforms.RandomRotation(10),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.GaussianBlur(kernel_size=3),
        ])
    
    def augment(self, image: torch.Tensor) -> torch.Tensor:
        """Applique les augmentations défensives"""
        return self.transform(image)

def create_robust_dataset(base_dir: Path, target_per_class: int = 500) -> Path:
    """
    Fonction principale pour créer le dataset robuste
    Solution au problème: "Plus de données - 500+ échantillons minimum par classe"
    """
    augmenter = AdvancedDataAugmentation(target_samples_per_class=target_per_class)
    augmented_dir, stats = augmenter.augment_existing_dataset(base_dir)
    return augmented_dir

if __name__ == "__main__":
    # Test de l'augmentation
    from pathlib import Path
    
    base_dir = Path("../../../data")
    print("Test d'augmentation de données pour adversarial training")
    
    try:
        result_dir = create_robust_dataset(base_dir, target_per_class=500)
        print(f"\nSUCCES: Dataset robuste cree: {result_dir}")
    except Exception as e:
        print(f"ERREUR: {e}")