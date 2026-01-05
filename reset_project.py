#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de nettoyage complet du projet
Supprime les datasets, modèles et résultats générés
"""

import os
import sys
import shutil
from pathlib import Path

# Fix encoding pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def confirm_reset():
    """Demande confirmation à l'utilisateur"""
    print("="*80)
    print("⚠️  RÉINITIALISATION COMPLÈTE DU PROJET")
    print("="*80)
    print("\nCe script va SUPPRIMER:")
    print("  • data/prepared/      (dataset généré)")
    print("  • models/             (modèles entraînés)")
    print("  • results/            (résultats d'évaluation)")
    print("\nCe script va CONSERVER:")
    print("  ✓ raw/Images/         (images sources guns)")
    print("  ✓ data/coco_safe/     (images safe si téléchargées)")
    print("  ✓ Scripts Python      (tous les .py)")
    print("  ✓ Documentation       (tous les .md)")

    print("\n" + "="*80)
    response = input("\n⚠️  Êtes-vous SÛR de vouloir continuer? (tapez 'OUI' en majuscules): ")

    return response == "OUI"


def get_size(path: Path) -> float:
    """Calcule la taille totale d'un dossier en MB"""
    if not path.exists():
        return 0.0

    total = 0
    try:
        if path.is_file():
            total = path.stat().st_size
        else:
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
    except:
        pass

    return total / (1024 * 1024)  # Convert to MB


def remove_directory(path: Path, name: str) -> bool:
    """Supprime un dossier avec affichage"""
    if not path.exists():
        print(f"  ⏭️  {name}: N'existe pas (ignoré)")
        return False

    size_mb = get_size(path)

    try:
        shutil.rmtree(path)
        print(f"  ✅ {name}: Supprimé ({size_mb:.1f} MB libérés)")
        return True
    except Exception as e:
        print(f"  ❌ {name}: Erreur - {e}")
        return False


def reset_project():
    """Réinitialise le projet"""
    print("\n" + "="*80)
    print("🧹 NETTOYAGE EN COURS...")
    print("="*80 + "\n")

    removed_count = 0
    total_size = 0

    # Liste des dossiers à supprimer
    to_remove = [
        (Path("data/prepared"), "Dataset préparé"),
        (Path("models"), "Modèles entraînés"),
        (Path("results"), "Résultats d'évaluation"),
        (Path("data/temp_safe"), "Dossier temporaire safe"),
    ]

    for path, name in to_remove:
        if path.exists():
            size = get_size(path)
            total_size += size

        if remove_directory(path, name):
            removed_count += 1

    # Créer les dossiers vides pour les modèles
    print("\n📁 Recréation des dossiers vides...")
    Path("models").mkdir(exist_ok=True)
    print("  ✓ models/ créé")

    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DU NETTOYAGE")
    print("="*80)
    print(f"\n  Dossiers supprimés: {removed_count}/{len(to_remove)}")
    print(f"  Espace libéré: {total_size:.1f} MB")

    print("\n✅ PROJET RÉINITIALISÉ!")
    print("\n📋 PROCHAINES ÉTAPES:")
    print("\n1. Télécharger vraies images 'safe':")
    print("   • Option auto: python data/download_coco_safe.py")
    print("   • Option manuelle: Voir SOLUTION_SIMPLE_SAFE_IMAGES.md")
    print("   • Les placer dans: data/coco_safe/")

    print("\n2. Préparer le dataset:")
    print("   python data/prepare_dataset.py")

    print("\n3. Entraîner les modèles:")
    print("   python run_full_pipeline.py --skip-dataset")

    print("\n4. Ou utiliser le menu interactif:")
    print("   COMMANDS.bat")

    print("\n" + "="*80)


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Réinitialise le projet (supprime datasets, modèles, résultats)"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="Ne pas demander de confirmation"
    )
    parser.add_argument(
        '--keep-dataset',
        action='store_true',
        help="Conserver le dataset préparé (supprimer uniquement modèles/résultats)"
    )

    args = parser.parse_args()

    # Confirmation
    if not args.force:
        if not confirm_reset():
            print("\n❌ Réinitialisation annulée.")
            sys.exit(0)

    # Exécuter le nettoyage
    reset_project()


if __name__ == "__main__":
    main()