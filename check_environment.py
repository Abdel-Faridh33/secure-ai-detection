#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification de l'environnement
Vérifie que tout est prêt pour l'entraînement
"""

import os
import sys
from pathlib import Path

# Fix encoding pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_python():
    """Vérifie la version Python"""
    print("\n📌 Python")
    print("-" * 40)
    version = sys.version_info
    print(f"  Version: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 8:
        print("  ✅ Version OK (>=3.8)")
        return True
    else:
        print("  ❌ Version trop ancienne (requiert >=3.8)")
        return False


def check_packages():
    """Vérifie les packages Python"""
    print("\n📌 Packages Python")
    print("-" * 40)

    packages = {
        'torch': 'PyTorch',
        'torchvision': 'TorchVision',
        'numpy': 'NumPy',
        'PIL': 'Pillow',
        'sklearn': 'scikit-learn',
        'scipy': 'SciPy',
        'matplotlib': 'Matplotlib',
        'seaborn': 'Seaborn',
        'tqdm': 'tqdm'
    }

    missing = []
    versions = {}

    for package, name in packages.items():
        try:
            module = __import__(package)
            version = getattr(module, '__version__', 'unknown')
            versions[name] = version
            print(f"  ✅ {name:15s} {version}")
        except ImportError:
            print(f"  ❌ {name:15s} MANQUANT")
            missing.append(name)

    if missing:
        print(f"\n  ❌ Packages manquants: {', '.join(missing)}")
        print("\n  Installation:")
        print("    pip install torch torchvision")
        print("    pip install numpy pillow scikit-learn scipy")
        print("    pip install matplotlib seaborn tqdm")
        return False
    else:
        print("\n  ✅ Tous les packages sont installés")
        return True


def check_cuda():
    """Vérifie la disponibilité CUDA"""
    print("\n📌 GPU / CUDA")
    print("-" * 40)

    try:
        import torch

        if torch.cuda.is_available():
            print(f"  ✅ CUDA disponible")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  Nombre de GPUs: {torch.cuda.device_count()}")

            # Test mémoire GPU
            try:
                total_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
                print(f"  Mémoire GPU: {total_mem:.1f} GB")

                if total_mem < 4:
                    print("  ⚠️  Mémoire GPU limitée (<4GB)")
                    print("      Réduisez batch_size si nécessaire")
            except:
                pass

            return True
        else:
            print("  ⚠️  CUDA non disponible - Utilisation CPU")
            print("      Entraînement sera plus lent (~5-10x)")
            print("      Temps estimé: 7-13h pour tout le pipeline")
            return False
    except:
        print("  ❌ Impossible de vérifier CUDA")
        return False


def check_dataset():
    """Vérifie le dataset"""
    print("\n📌 Dataset")
    print("-" * 40)

    # Vérifier raw data
    raw_dir = Path("raw/Images")
    if not raw_dir.exists():
        print("  ❌ raw/Images/ introuvable")
        return False

    raw_count = len(list(raw_dir.glob("*.jpg"))) + len(list(raw_dir.glob("*.png")))
    print(f"  ✅ Images sources: {raw_count}")

    # Vérifier prepared data
    prepared_dir = Path("data/prepared")
    if not prepared_dir.exists():
        print("\n  ⚠️  Dataset non préparé")
        print("      Lancez: python data/prepare_dataset.py")
        return False

    # Vérifier les splits
    splits = ['train', 'val', 'test']
    classes = ['safe', 'dangerous']

    total = 0
    for split in splits:
        split_total = 0
        for cls in classes:
            cls_dir = prepared_dir / split / cls
            if cls_dir.exists():
                count = len(list(cls_dir.glob("*.jpg")))
                split_total += count
        print(f"  ✅ {split:5s}: {split_total:4d} images")
        total += split_total

    print(f"\n  ✅ Total: {total} images préparées")

    # Vérifier stats
    stats_file = prepared_dir / "dataset_stats.json"
    if stats_file.exists():
        print(f"  ✅ Stats disponibles: {stats_file}")

    return True


def check_disk_space():
    """Vérifie l'espace disque"""
    print("\n📌 Espace Disque")
    print("-" * 40)

    try:
        import shutil
        total, used, free = shutil.disk_usage(".")

        free_gb = free / (1024**3)
        total_gb = total / (1024**3)

        print(f"  Total: {total_gb:.1f} GB")
        print(f"  Libre: {free_gb:.1f} GB")

        if free_gb < 1:
            print("  ⚠️  Espace disque limité (<1GB)")
            print("      Libérez de l'espace avant l'entraînement")
            return False
        else:
            print("  ✅ Espace suffisant")
            return True
    except:
        print("  ⚠️  Impossible de vérifier l'espace disque")
        return True


def check_scripts():
    """Vérifie que les scripts sont présents"""
    print("\n📌 Scripts d'Entraînement")
    print("-" * 40)

    scripts = {
        'data/prepare_dataset.py': 'Préparation dataset',
        'src/experiments/baseline/train_mobilenet.py': 'Entraînement baseline',
        'src/experiments/secured/train_mobilenet_secured.py': 'Entraînement secured',
        'src/experiments/comparative/evaluate_models.py': 'Évaluation comparative',
        'run_full_pipeline.py': 'Pipeline complet'
    }

    all_ok = True
    for script, desc in scripts.items():
        if Path(script).exists():
            print(f"  ✅ {desc:25s} {script}")
        else:
            print(f"  ❌ {desc:25s} {script} MANQUANT")
            all_ok = False

    return all_ok


def estimate_time():
    """Estime le temps d'entraînement"""
    print("\n📌 Temps d'Entraînement Estimé")
    print("-" * 40)

    try:
        import torch
        has_cuda = torch.cuda.is_available()
    except:
        has_cuda = False

    if has_cuda:
        print("  Mode: GPU (CUDA)")
        print("  • Baseline:    30-60 min")
        print("  • Secured:      1-2 heures")
        print("  • Évaluation:  10-20 min")
        print("  • TOTAL:       ~2-3 heures")
    else:
        print("  Mode: CPU (pas de GPU)")
        print("  • Baseline:     2-4 heures")
        print("  • Secured:      4-8 heures")
        print("  • Évaluation:  30-40 min")
        print("  • TOTAL:       ~7-13 heures")
        print("\n  💡 Recommandation: Utiliser un GPU si possible")


def check_models():
    """Vérifie si des modèles sont déjà entraînés"""
    print("\n📌 Modèles Entraînés")
    print("-" * 40)

    baseline_model = Path("models/baseline/best_model.pth")
    secured_model = Path("models/secured/best_model.pth")

    if baseline_model.exists():
        size_mb = baseline_model.stat().st_size / (1024**2)
        print(f"  ✅ Baseline: {baseline_model} ({size_mb:.1f} MB)")
    else:
        print(f"  ⏳ Baseline: Pas encore entraîné")

    if secured_model.exists():
        size_mb = secured_model.stat().st_size / (1024**2)
        print(f"  ✅ Secured:  {secured_model} ({size_mb:.1f} MB)")
    else:
        print(f"  ⏳ Secured:  Pas encore entraîné")

    if not baseline_model.exists() and not secured_model.exists():
        print("\n  💡 Lancez l'entraînement avec:")
        print("      python run_full_pipeline.py --skip-dataset")


def check_results():
    """Vérifie si des résultats existent"""
    print("\n📌 Résultats")
    print("-" * 40)

    results_dir = Path("results/comparative")

    if results_dir.exists():
        report = results_dir / "evaluation_report.txt"
        plots = results_dir / "comparative_plots.png"

        if report.exists():
            print(f"  ✅ Rapport: {report}")

        if plots.exists():
            print(f"  ✅ Graphiques: {plots}")

        if not report.exists() and not plots.exists():
            print("  ⏳ Pas encore de résultats")
    else:
        print("  ⏳ Pas encore de résultats")


def main():
    """Point d'entrée principal"""
    print("="*80)
    print("🔍 VÉRIFICATION DE L'ENVIRONNEMENT")
    print("="*80)

    checks = []

    # Vérifications critiques
    checks.append(("Python", check_python()))
    checks.append(("Packages", check_packages()))
    checks.append(("GPU/CUDA", check_cuda()))
    checks.append(("Dataset", check_dataset()))
    checks.append(("Scripts", check_scripts()))
    checks.append(("Espace disque", check_disk_space()))

    # Informations additionnelles
    estimate_time()
    check_models()
    check_results()

    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ")
    print("="*80)

    critical_ok = all([
        checks[0][1],  # Python
        checks[1][1],  # Packages
        checks[3][1],  # Dataset
        checks[4][1],  # Scripts
        checks[5][1]   # Espace disque
    ])

    for name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    print()

    if critical_ok:
        print("✅ ENVIRONNEMENT PRÊT POUR L'ENTRAÎNEMENT!")
        print("\n🚀 Commandes pour démarrer:")
        print("  • Pipeline complet:  python run_full_pipeline.py --skip-dataset")
        print("  • Baseline seul:     python src/experiments/baseline/train_mobilenet.py")
        print("  • Secured seul:      python src/experiments/secured/train_mobilenet_secured.py")
        print("  • Évaluation:        python src/experiments/comparative/evaluate_models.py")

        if not checks[2][1]:  # Pas de GPU
            print("\n⚠️  Note: Pas de GPU détecté - L'entraînement sera lent")
    else:
        print("❌ PROBLÈMES DÉTECTÉS - Corrigez-les avant de continuer")

    print("="*80)


if __name__ == "__main__":
    main()
