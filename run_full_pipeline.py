#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline complet d'entraînement et d'évaluation
Exécute toutes les étapes du projet de A à Z
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Fix encoding pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class PipelineRunner:
    """Exécute le pipeline complet"""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.steps = []
        self.current_step = 0

    def run_command(self, cmd: str, description: str, timeout: int = None):
        """
        Exécute une commande

        Args:
            cmd: Commande à exécuter
            description: Description de l'étape
            timeout: Timeout en secondes (None = pas de timeout)
        """
        self.current_step += 1
        print("\n" + "="*80)
        print(f"ÉTAPE {self.current_step}: {description}")
        print("="*80)
        print(f"Commande: {cmd}")
        print()

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                cwd=self.root_dir,
                timeout=timeout
            )

            elapsed = time.time() - start_time
            print(f"\n✓ Étape {self.current_step} terminée en {elapsed:.1f}s")
            return True

        except subprocess.CalledProcessError as e:
            print(f"\n❌ Erreur à l'étape {self.current_step}")
            print(f"Code de retour: {e.returncode}")
            return False

        except subprocess.TimeoutExpired:
            print(f"\n❌ Timeout à l'étape {self.current_step}")
            return False

    def check_requirements(self) -> bool:
        """Vérifie que les prérequis sont présents"""
        print("="*80)
        print("VÉRIFICATION DES PRÉREQUIS")
        print("="*80)

        # Vérifier Python
        print(f"\n✓ Python: {sys.version}")

        # Vérifier les packages nécessaires
        required_packages = [
            'torch',
            'torchvision',
            'numpy',
            'PIL',
            'sklearn',
            'scipy',
            'matplotlib',
            'seaborn',
            'tqdm'
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"✓ {package}")
            except ImportError:
                print(f"❌ {package} manquant")
                missing.append(package)

        if missing:
            print(f"\n❌ Packages manquants: {', '.join(missing)}")
            print("Installez-les avec: pip install torch torchvision numpy pillow scikit-learn scipy matplotlib seaborn tqdm")
            return False

        # Vérifier les données sources
        raw_dir = self.root_dir / "raw" / "Images"
        if not raw_dir.exists():
            print(f"\n❌ Dossier raw/Images/ introuvable")
            return False

        n_images = len(list(raw_dir.glob("*.jpg"))) + len(list(raw_dir.glob("*.png")))
        print(f"\n✓ {n_images} images trouvées dans raw/Images/")

        if n_images < 100:
            print(f"⚠️  Attention: seulement {n_images} images disponibles")

        return True

    def run_full_pipeline(self, skip_dataset: bool = False):
        """
        Lance le pipeline complet

        Args:
            skip_dataset: Si True, ne pas régénérer le dataset
        """
        print("\n" + "="*80)
        print("🚀 DÉMARRAGE DU PIPELINE COMPLET")
        print("="*80)

        start_total = time.time()

        # Vérifier les prérequis
        if not self.check_requirements():
            print("\n❌ Prérequis non satisfaits. Pipeline interrompu.")
            return False

        # Étape 1: Préparation du dataset (optionnel)
        if not skip_dataset:
            if not self.run_command(
                "python data/prepare_dataset.py",
                "Préparation du dataset avec augmentation",
                timeout=3600
            ):
                print("\n❌ Échec de la préparation du dataset")
                return False
        else:
            print("\n⏭️  Étape de préparation du dataset ignorée")

        # Étape 2: Entraînement Baseline
        if not self.run_command(
            "python src/experiments/baseline/train_mobilenet.py",
            "Entraînement du modèle Baseline (MobileNetV2)",
            timeout=7200
        ):
            print("\n❌ Échec de l'entraînement Baseline")
            return False

        # Étape 3: Entraînement Secured
        if not self.run_command(
            "python src/experiments/secured/train_mobilenet_secured.py",
            "Entraînement du modèle Secured (TRADES)",
            timeout=10800
        ):
            print("\n❌ Échec de l'entraînement Secured")
            return False

        # Étape 4: Évaluation comparative
        if not self.run_command(
            "python src/experiments/comparative/evaluate_models.py",
            "Évaluation comparative des modèles",
            timeout=1800
        ):
            print("\n❌ Échec de l'évaluation")
            return False

        # Pipeline terminé
        elapsed_total = time.time() - start_total
        hours = int(elapsed_total // 3600)
        minutes = int((elapsed_total % 3600) // 60)
        seconds = int(elapsed_total % 60)

        print("\n" + "="*80)
        print("✅ PIPELINE COMPLET TERMINÉ")
        print("="*80)
        print(f"\nTemps total: {hours}h {minutes}m {seconds}s")
        print("\n📂 Résultats disponibles dans:")
        print("  - models/baseline/")
        print("  - models/secured/")
        print("  - results/comparative/")
        print("\n🎉 Succès!")

        return True


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pipeline complet d'entraînement et d'évaluation"
    )
    parser.add_argument(
        '--skip-dataset',
        action='store_true',
        help="Ne pas régénérer le dataset (utiliser l'existant)"
    )
    parser.add_argument(
        '--step',
        choices=['dataset', 'baseline', 'secured', 'evaluate', 'all'],
        default='all',
        help="Exécuter une étape spécifique"
    )

    args = parser.parse_args()

    runner = PipelineRunner()

    if args.step == 'all':
        # Pipeline complet
        success = runner.run_full_pipeline(skip_dataset=args.skip_dataset)

    elif args.step == 'dataset':
        # Seulement dataset
        success = runner.run_command(
            "python data/prepare_dataset.py",
            "Préparation du dataset",
            timeout=3600
        )

    elif args.step == 'baseline':
        # Seulement baseline
        success = runner.run_command(
            "python src/experiments/baseline/train_mobilenet.py",
            "Entraînement Baseline",
            timeout=7200
        )

    elif args.step == 'secured':
        # Seulement secured
        success = runner.run_command(
            "python src/experiments/secured/train_mobilenet_secured.py",
            "Entraînement Secured",
            timeout=10800
        )

    elif args.step == 'evaluate':
        # Seulement évaluation
        success = runner.run_command(
            "python src/experiments/comparative/evaluate_models.py",
            "Évaluation comparative",
            timeout=1800
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
