#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'analyse des résultats d'entraînement baseline

Génère des statistiques détaillées et des visualisations avancées
à partir de l'historique d'entraînement.

Usage:
    python scripts/analyze_baseline_results.py
    python scripts/analyze_baseline_results.py --model-dir models/baseline
"""

import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Tuple
import sys
import io

# Fix encoding pour Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_training_history(model_dir: Path) -> Dict:
    """Charge l'historique d'entraînement"""
    history_path = model_dir / 'training_history.json'

    if not history_path.exists():
        raise FileNotFoundError(f"Fichier {history_path} non trouvé!")

    with open(history_path, 'r') as f:
        return json.load(f)


def compute_statistics(history: Dict) -> Dict:
    """Calcule des statistiques avancées"""
    stats = {}

    # Epochs
    n_epochs = len(history['train_loss'])
    stats['n_epochs'] = n_epochs

    # Best epoch (val accuracy)
    best_epoch_idx = np.argmax(history['val_acc'])
    stats['best_epoch'] = best_epoch_idx + 1
    stats['best_val_acc'] = history['val_acc'][best_epoch_idx]
    stats['best_val_loss'] = history['val_loss'][best_epoch_idx]
    stats['best_train_acc'] = history['train_acc'][best_epoch_idx]
    stats['best_train_loss'] = history['train_loss'][best_epoch_idx]

    # Final metrics
    stats['final_train_acc'] = history['train_acc'][-1]
    stats['final_val_acc'] = history['val_acc'][-1]
    stats['final_train_loss'] = history['train_loss'][-1]
    stats['final_val_loss'] = history['val_loss'][-1]

    # Gaps (overfitting indicators)
    stats['final_acc_gap'] = stats['final_train_acc'] - stats['final_val_acc']
    stats['best_acc_gap'] = stats['best_train_acc'] - stats['best_val_acc']

    # Improvements
    stats['initial_val_acc'] = history['val_acc'][0]
    stats['acc_improvement'] = stats['best_val_acc'] - stats['initial_val_acc']
    stats['acc_improvement_pct'] = (stats['acc_improvement'] / stats['initial_val_acc']) * 100

    # Stability (standard deviation of last 10 epochs)
    last_10_val_acc = history['val_acc'][-10:]
    stats['val_acc_std_last10'] = np.std(last_10_val_acc)

    # Loss analysis
    stats['min_train_loss'] = min(history['train_loss'])
    stats['min_val_loss'] = min(history['val_loss'])
    stats['max_train_loss'] = max(history['train_loss'])
    stats['max_val_loss'] = max(history['val_loss'])

    return stats


def print_summary(stats: Dict):
    """Affiche un résumé des statistiques"""
    print("=" * 70)
    print("📊 ANALYSE DES RÉSULTATS D'ENTRAÎNEMENT BASELINE")
    print("=" * 70)

    print("\n🏆 MEILLEURE PERFORMANCE")
    print("-" * 70)
    print(f"  Epoch:           {stats['best_epoch']}/{stats['n_epochs']}")
    print(f"  Val Accuracy:    {stats['best_val_acc']:.2f}%")
    print(f"  Val Loss:        {stats['best_val_loss']:.4f}")
    print(f"  Train Accuracy:  {stats['best_train_acc']:.2f}%")
    print(f"  Train Loss:      {stats['best_train_loss']:.4f}")
    print(f"  Acc Gap:         {stats['best_acc_gap']:.2f}%")

    print("\n📈 PROGRESSION")
    print("-" * 70)
    print(f"  Val Acc initiale:   {stats['initial_val_acc']:.2f}%")
    print(f"  Val Acc finale:     {stats['final_val_acc']:.2f}%")
    print(f"  Amélioration:       +{stats['acc_improvement']:.2f}% ({stats['acc_improvement_pct']:.1f}%)")
    print(f"  Train Acc finale:   {stats['final_train_acc']:.2f}%")

    print("\n⚖️  OVERFITTING ANALYSIS")
    print("-" * 70)
    print(f"  Gap final (train-val):   {stats['final_acc_gap']:.2f}%")
    print(f"  Gap meilleur epoch:      {stats['best_acc_gap']:.2f}%")

    overfitting_level = "Léger" if stats['final_acc_gap'] < 5 else "Modéré" if stats['final_acc_gap'] < 10 else "Sévère"
    print(f"  Niveau d'overfitting:    {overfitting_level}")

    print("\n🎯 STABILITÉ")
    print("-" * 70)
    print(f"  Std val acc (10 derniers epochs): {stats['val_acc_std_last10']:.2f}%")

    stability = "Stable" if stats['val_acc_std_last10'] < 1.0 else "Modérée" if stats['val_acc_std_last10'] < 2.0 else "Instable"
    print(f"  Stabilité:                        {stability}")

    print("\n📉 LOSS ANALYSIS")
    print("-" * 70)
    print(f"  Train Loss range:  {stats['min_train_loss']:.4f} - {stats['max_train_loss']:.4f}")
    print(f"  Val Loss range:    {stats['min_val_loss']:.4f} - {stats['max_val_loss']:.4f}")
    print(f"  Final Train Loss:  {stats['final_train_loss']:.4f}")
    print(f"  Final Val Loss:    {stats['final_val_loss']:.4f}")


def create_advanced_visualizations(history: Dict, stats: Dict, output_dir: Path):
    """Crée des visualisations avancées"""

    epochs = list(range(1, len(history['train_loss']) + 1))

    # Figure avec 6 subplots
    fig = plt.figure(figsize=(18, 12))

    # 1. Loss curves (détaillé)
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(epochs, history['train_loss'], 'b-', label='Train Loss', linewidth=2)
    ax1.plot(epochs, history['val_loss'], 'r-', label='Val Loss', linewidth=2)
    ax1.axvline(x=stats['best_epoch'], color='g', linestyle='--', alpha=0.7, label=f"Best (epoch {stats['best_epoch']})")
    ax1.set_title('Loss Evolution', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Accuracy curves (détaillé)
    ax2 = plt.subplot(3, 2, 2)
    ax2.plot(epochs, history['train_acc'], 'b-', label='Train Acc', linewidth=2)
    ax2.plot(epochs, history['val_acc'], 'r-', label='Val Acc', linewidth=2)
    ax2.axvline(x=stats['best_epoch'], color='g', linestyle='--', alpha=0.7, label=f"Best (epoch {stats['best_epoch']})")
    ax2.axhline(y=stats['best_val_acc'], color='orange', linestyle=':', alpha=0.5, label=f"Best Val Acc: {stats['best_val_acc']:.2f}%")
    ax2.set_title('Accuracy Evolution', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Train/Val Gap (overfitting indicator)
    ax3 = plt.subplot(3, 2, 3)
    acc_gap = [t - v for t, v in zip(history['train_acc'], history['val_acc'])]
    ax3.plot(epochs, acc_gap, 'purple', linewidth=2)
    ax3.axhline(y=5, color='orange', linestyle='--', alpha=0.5, label='Gap = 5% (threshold)')
    ax3.axhline(y=0, color='green', linestyle='-', alpha=0.3)
    ax3.fill_between(epochs, 0, acc_gap, alpha=0.3, color='purple')
    ax3.set_title('Train/Val Accuracy Gap (Overfitting Indicator)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Epoch')
    ax3.set_ylabel('Gap (%)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Loss Gap
    ax4 = plt.subplot(3, 2, 4)
    loss_gap = [v - t for t, v in zip(history['train_loss'], history['val_loss'])]
    ax4.plot(epochs, loss_gap, 'brown', linewidth=2)
    ax4.axhline(y=0, color='green', linestyle='-', alpha=0.3)
    ax4.fill_between(epochs, 0, loss_gap, alpha=0.3, color='brown')
    ax4.set_title('Val/Train Loss Gap', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Epoch')
    ax4.set_ylabel('Gap')
    ax4.legend(['Val - Train Loss'])
    ax4.grid(True, alpha=0.3)

    # 5. Val Accuracy avec tendance
    ax5 = plt.subplot(3, 2, 5)
    ax5.plot(epochs, history['val_acc'], 'r-', label='Val Acc', linewidth=2, marker='o', markersize=4)

    # Ligne de tendance (moving average)
    window = 5
    if len(history['val_acc']) >= window:
        val_acc_ma = np.convolve(history['val_acc'], np.ones(window)/window, mode='valid')
        ax5.plot(range(window, len(history['val_acc']) + 1), val_acc_ma, 'b--',
                label=f'Moving Avg (window={window})', linewidth=2, alpha=0.7)

    ax5.axhline(y=stats['best_val_acc'], color='g', linestyle=':', alpha=0.7,
               label=f"Peak: {stats['best_val_acc']:.2f}%")
    ax5.set_title('Validation Accuracy with Trend', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Epoch')
    ax5.set_ylabel('Accuracy (%)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. Histogram des val accuracies
    ax6 = plt.subplot(3, 2, 6)
    ax6.hist(history['val_acc'], bins=20, color='steelblue', alpha=0.7, edgecolor='black')
    ax6.axvline(x=stats['best_val_acc'], color='red', linestyle='--', linewidth=2,
               label=f"Best: {stats['best_val_acc']:.2f}%")
    ax6.axvline(x=np.mean(history['val_acc']), color='green', linestyle='--', linewidth=2,
               label=f"Mean: {np.mean(history['val_acc']):.2f}%")
    ax6.set_title('Distribution of Validation Accuracies', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Accuracy (%)')
    ax6.set_ylabel('Frequency')
    ax6.legend()
    ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Sauvegarder
    output_path = output_dir / 'advanced_analysis.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n📊 Visualisations avancées sauvegardées: {output_path}")

    plt.close()


def generate_markdown_report(stats: Dict, output_dir: Path):
    """Génère un rapport markdown simplifié"""

    report = f"""# Résumé Rapide - Baseline Training

**Date**: {Path.cwd()}
**Epochs**: {stats['n_epochs']}

## Résultats Clés

- **Meilleure Val Accuracy**: {stats['best_val_acc']:.2f}% (epoch {stats['best_epoch']})
- **Val Accuracy finale**: {stats['final_val_acc']:.2f}%
- **Train Accuracy finale**: {stats['final_train_acc']:.2f}%
- **Gap Train/Val**: {stats['final_acc_gap']:.2f}%

## Performance

| Métrique | Valeur |
|----------|--------|
| Best Val Loss | {stats['best_val_loss']:.4f} |
| Final Val Loss | {stats['final_val_loss']:.4f} |
| Min Train Loss | {stats['min_train_loss']:.4f} |
| Amélioration totale | +{stats['acc_improvement']:.2f}% |

## Stabilité

- **Stabilité (10 derniers epochs)**: {stats['val_acc_std_last10']:.2f}%
- **Niveau overfitting**: {"Léger" if stats['final_acc_gap'] < 5 else "Modéré" if stats['final_acc_gap'] < 10 else "Sévère"}

---

*Généré automatiquement par analyze_baseline_results.py*
"""

    output_path = output_dir / 'quick_summary.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"📝 Rapport markdown généré: {output_path}")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Analyse les résultats d'entraînement baseline")
    parser.add_argument(
        '--model-dir',
        type=str,
        default='models/baseline',
        help='Dossier contenant les résultats (défaut: models/baseline)'
    )
    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Ne pas générer les visualisations'
    )

    args = parser.parse_args()

    model_dir = Path(args.model_dir)

    if not model_dir.exists():
        print(f"❌ Dossier {model_dir} non trouvé!")
        return 1

    # Charger l'historique
    try:
        history = load_training_history(model_dir)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1

    # Calculer les statistiques
    stats = compute_statistics(history)

    # Afficher le résumé
    print_summary(stats)

    # Créer les visualisations
    if not args.no_plots:
        try:
            create_advanced_visualizations(history, stats, model_dir)
        except Exception as e:
            print(f"\n⚠️  Erreur lors de la création des visualisations: {e}")

    # Générer le rapport markdown
    try:
        generate_markdown_report(stats, model_dir)
    except Exception as e:
        print(f"\n⚠️  Erreur lors de la génération du rapport: {e}")

    print("\n" + "=" * 70)
    print("✅ ANALYSE TERMINÉE")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
