#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de préparation du dataset pour Google Colab

Ce script crée une archive ZIP du dataset préparé pour l'upload sur Google Colab.
Il vérifie également la structure et affiche des statistiques.

Usage:
    python scripts/prepare_colab_dataset.py
    python scripts/prepare_colab_dataset.py --output custom_name.zip
    python scripts/prepare_colab_dataset.py --verify-only
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path
from typing import Dict, Tuple


def count_images(directory: Path, extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png')) -> int:
    """Compte le nombre d'images dans un dossier"""
    if not directory.exists():
        return 0
    return sum(1 for f in directory.rglob('*') if f.suffix.lower() in extensions)


def verify_dataset_structure(base_path: Path) -> Tuple[bool, Dict]:
    """
    Vérifie la structure du dataset et retourne les statistiques

    Args:
        base_path: Chemin vers data/prepared/

    Returns:
        Tuple (is_valid, stats_dict)
    """
    print("🔍 Vérification de la structure du dataset...\n")

    if not base_path.exists():
        print(f"❌ Dossier {base_path} non trouvé!")
        return False, {}

    stats = {
        'train': {'safe': 0, 'dangerous': 0},
        'val': {'safe': 0, 'dangerous': 0},
        'test': {'safe': 0, 'dangerous': 0}
    }

    is_valid = True

    for split in ['train', 'val', 'test']:
        split_path = base_path / split

        if not split_path.exists():
            print(f"❌ {split}/ manquant!")
            is_valid = False
            continue

        for class_name in ['safe', 'dangerous']:
            class_path = split_path / class_name

            if not class_path.exists():
                print(f"❌ {split}/{class_name}/ manquant!")
                is_valid = False
                continue

            count = count_images(class_path)
            stats[split][class_name] = count

            if count == 0:
                print(f"⚠️  {split}/{class_name}/ est vide!")
                is_valid = False

    return is_valid, stats


def display_statistics(stats: Dict):
    """Affiche les statistiques du dataset"""
    print("\n📊 Statistiques du dataset:\n")
    print("─" * 60)
    print(f"{'Split':<10} {'Safe':<15} {'Dangerous':<15} {'Total':<10}")
    print("─" * 60)

    total_all = 0

    for split in ['train', 'val', 'test']:
        safe = stats[split]['safe']
        dangerous = stats[split]['dangerous']
        total = safe + dangerous
        total_all += total

        print(f"{split:<10} {safe:<15} {dangerous:<15} {total:<10}")

    print("─" * 60)
    print(f"{'TOTAL':<10} {sum(s['safe'] for s in stats.values()):<15} "
          f"{sum(s['dangerous'] for s in stats.values()):<15} {total_all:<10}")
    print("─" * 60)

    # Ratios
    train_total = stats['train']['safe'] + stats['train']['dangerous']
    val_total = stats['val']['safe'] + stats['val']['dangerous']
    test_total = stats['test']['safe'] + stats['test']['dangerous']

    if total_all > 0:
        print(f"\n📈 Ratios de split:")
        print(f"  Train: {train_total / total_all * 100:.1f}%")
        print(f"  Val:   {val_total / total_all * 100:.1f}%")
        print(f"  Test:  {test_total / total_all * 100:.1f}%")

    # Balance des classes
    print(f"\n⚖️  Balance des classes:")
    for split in ['train', 'val', 'test']:
        safe = stats[split]['safe']
        dangerous = stats[split]['dangerous']
        total = safe + dangerous
        if total > 0:
            print(f"  {split.capitalize()}: {safe/total*100:.1f}% safe, {dangerous/total*100:.1f}% dangerous")


def create_zip_archive(source_dir: Path, output_file: Path) -> bool:
    """
    Crée une archive ZIP du dataset

    Args:
        source_dir: Dossier source (data/prepared)
        output_file: Fichier de sortie (.zip)

    Returns:
        True si succès, False sinon
    """
    print(f"\n📦 Création de l'archive ZIP: {output_file.name}")
    print("─" * 60)

    try:
        total_files = sum(1 for _ in source_dir.rglob('*') if _.is_file())
        current_file = 0

        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    # Calculer le chemin relatif depuis le parent de prepared/
                    # Cela garantit que le ZIP contient prepared/ à la racine
                    arc_name = file_path.relative_to(source_dir.parent)
                    zipf.write(file_path, arc_name)

                    current_file += 1
                    if current_file % 100 == 0:
                        progress = (current_file / total_files) * 100
                        print(f"  Progression: {progress:.1f}% ({current_file}/{total_files} fichiers)", end='\r')

        print(f"\n  ✅ {total_files} fichiers compressés")

        # Afficher la taille du fichier
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"  📊 Taille du fichier: {file_size_mb:.2f} MB")

        # Estimer le temps d'upload
        upload_time_10mbps = (file_size_mb * 8) / 10  # en minutes
        upload_time_50mbps = (file_size_mb * 8) / 50
        print(f"\n⏱️  Temps d'upload estimé:")
        print(f"  - 10 Mbps: ~{upload_time_10mbps:.1f} minutes")
        print(f"  - 50 Mbps: ~{upload_time_50mbps:.1f} minutes")

        return True

    except Exception as e:
        print(f"\n❌ Erreur lors de la création du ZIP: {e}")
        return False


def verify_zip_structure(zip_path: Path) -> bool:
    """Vérifie la structure interne du ZIP"""
    print(f"\n🔍 Vérification de la structure du ZIP...")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()

            # Vérifier que tous les fichiers commencent par 'prepared/'
            root_folders = set(f.split('/')[0] for f in files if '/' in f)

            if 'prepared' not in root_folders:
                print("❌ Le ZIP ne contient pas 'prepared/' à la racine!")
                print(f"Dossiers racine trouvés: {root_folders}")
                return False

            # Vérifier la présence des sous-dossiers requis
            required_paths = [
                'prepared/train/safe',
                'prepared/train/dangerous',
                'prepared/val/safe',
                'prepared/val/dangerous',
                'prepared/test/safe',
                'prepared/test/dangerous'
            ]

            for req_path in required_paths:
                found = any(f.startswith(req_path + '/') for f in files)
                if found:
                    print(f"  ✅ {req_path}")
                else:
                    print(f"  ❌ {req_path} manquant!")
                    return False

            print("\n✅ Structure du ZIP valide!")
            return True

    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Prépare le dataset pour Google Colab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python scripts/prepare_colab_dataset.py
  python scripts/prepare_colab_dataset.py --output mon_dataset.zip
  python scripts/prepare_colab_dataset.py --verify-only
        """
    )

    parser.add_argument(
        '--data-dir',
        type=str,
        default='data/prepared',
        help='Chemin vers le dossier du dataset (défaut: data/prepared)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='prepared.zip',
        help='Nom du fichier ZIP de sortie (défaut: prepared.zip)'
    )

    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Vérifier la structure sans créer le ZIP'
    )

    parser.add_argument(
        '--verify-zip',
        type=str,
        help='Vérifier la structure d\'un ZIP existant'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📦 PRÉPARATION DU DATASET POUR GOOGLE COLAB")
    print("=" * 60)

    # Vérification d'un ZIP existant
    if args.verify_zip:
        zip_path = Path(args.verify_zip)
        if not zip_path.exists():
            print(f"❌ Fichier {zip_path} non trouvé!")
            sys.exit(1)

        is_valid = verify_zip_structure(zip_path)
        sys.exit(0 if is_valid else 1)

    # Vérifier la structure du dataset source
    data_dir = Path(args.data_dir)
    is_valid, stats = verify_dataset_structure(data_dir)

    if not is_valid:
        print("\n❌ La structure du dataset est invalide!")
        print("Assurez-vous que le dataset a été correctement préparé.")
        sys.exit(1)

    # Afficher les statistiques
    display_statistics(stats)

    # Mode verify-only
    if args.verify_only:
        print("\n✅ Vérification terminée (--verify-only activé)")
        sys.exit(0)

    # Créer le ZIP
    output_path = Path(args.output)

    # Demander confirmation si le fichier existe déjà
    if output_path.exists():
        response = input(f"\n⚠️  {output_path} existe déjà. Écraser? [o/N] ")
        if response.lower() not in ['o', 'oui', 'y', 'yes']:
            print("Opération annulée.")
            sys.exit(0)
        output_path.unlink()

    # Créer l'archive
    success = create_zip_archive(data_dir, output_path)

    if not success:
        sys.exit(1)

    # Vérifier le ZIP créé
    if not verify_zip_structure(output_path):
        print("\n❌ La structure du ZIP créé est invalide!")
        sys.exit(1)

    # Instructions finales
    print("\n" + "=" * 60)
    print("✅ PRÉPARATION TERMINÉE")
    print("=" * 60)
    print(f"\n📁 Fichier créé: {output_path.absolute()}")
    print(f"\n📋 Prochaines étapes:")
    print(f"  1. Ouvrir notebooks/train_secured_colab.ipynb dans Google Colab")
    print(f"  2. Activer le GPU (Runtime > Change runtime type > GPU)")
    print(f"  3. Uploader {output_path.name} dans la section appropriée")
    print(f"  4. Exécuter toutes les cellules")
    print(f"  5. Télécharger secured_results.zip à la fin")
    print(f"\n📖 Documentation complète: notebooks/README_COLAB.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
