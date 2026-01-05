"""
Analyse de l'entraînement sécurisé pour diagnostiquer les problèmes
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys
import io

# Fix encoding pour Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_training_history(path):
    """Charge l'historique d'entraînement"""
    with open(path, 'r') as f:
        return json.load(f)


def analyze_overfitting(history):
    """Analyse l'overfitting"""

    print("="*70)
    print("ANALYSE D'OVERFITTING")
    print("="*70)

    final_train_acc = history['train_acc'][-1]
    final_val_acc = history['val_acc'][-1]
    best_val_acc = max(history['val_acc'])
    best_val_epoch = history['val_acc'].index(best_val_acc) + 1

    overfitting_gap = final_train_acc - final_val_acc

    print(f"\nMétriques finales (Epoch 30):")
    print(f"  Train Accuracy: {final_train_acc:.2f}%")
    print(f"  Val Accuracy:   {final_val_acc:.2f}%")
    print(f"  Overfitting Gap: {overfitting_gap:.2f}%")

    print(f"\nMeilleur validation:")
    print(f"  Best Val Acc: {best_val_acc:.2f}% (Epoch {best_val_epoch})")
    print(f"  Train Acc @ Best: {history['train_acc'][best_val_epoch-1]:.2f}%")

    # Diagnostic
    print(f"\nDIAGNOSTIC:")

    if overfitting_gap > 30:
        print(f"  🔴 OVERFITTING SÉVÈRE ({overfitting_gap:.1f}% gap)")
        print(f"     → Le modèle mémorise les données d'entraînement")
        print(f"     → Ne généralise pas aux données de validation")
    elif overfitting_gap > 15:
        print(f"  🟠 OVERFITTING MODÉRÉ ({overfitting_gap:.1f}% gap)")
    elif overfitting_gap > 5:
        print(f"  🟡 OVERFITTING LÉGER ({overfitting_gap:.1f}% gap)")
    else:
        print(f"  ✅ PAS D'OVERFITTING ({overfitting_gap:.1f}% gap)")

    if best_val_acc < 80:
        print(f"  🔴 VAL ACCURACY TROP BASSE ({best_val_acc:.1f}%)")
        print(f"     → Attendu: 90-95%")
        print(f"     → Obtenu: {best_val_acc:.1f}%")

    # Stabilité
    val_acc_std = np.std(history['val_acc'][-10:])
    if val_acc_std > 5:
        print(f"  🔴 VALIDATION INSTABLE (std={val_acc_std:.1f}% sur 10 derniers epochs)")
        print(f"     → Oscillations importantes")

    return {
        'overfitting_gap': overfitting_gap,
        'best_val_acc': best_val_acc,
        'best_val_epoch': best_val_epoch,
        'val_stability': val_acc_std
    }


def compare_with_baseline(secured_history):
    """Compare avec le baseline"""

    baseline_path = Path("models/baseline/training_history.json")

    if not baseline_path.exists():
        print("\n⚠️ Baseline history not found, skipping comparison")
        return

    with open(baseline_path, 'r') as f:
        baseline_history = json.load(f)

    print("\n" + "="*70)
    print("COMPARAISON BASELINE VS SECURED")
    print("="*70)

    baseline_best_val = max(baseline_history['val_acc'])
    secured_best_val = max(secured_history['val_acc'])

    baseline_final_train = baseline_history['train_acc'][-1]
    secured_final_train = secured_history['train_acc'][-1]

    baseline_overfitting = baseline_final_train - max(baseline_history['val_acc'])
    secured_overfitting = secured_final_train - max(secured_history['val_acc'])

    print(f"\n{'Métrique':<30} {'Baseline':<15} {'Secured':<15} {'Diff':<15}")
    print("-" * 75)
    print(f"{'Best Val Acc':<30} {baseline_best_val:<15.2f} {secured_best_val:<15.2f} {secured_best_val - baseline_best_val:<+15.2f}")
    print(f"{'Final Train Acc':<30} {baseline_final_train:<15.2f} {secured_final_train:<15.2f} {secured_final_train - baseline_final_train:<+15.2f}")
    print(f"{'Overfitting Gap':<30} {baseline_overfitting:<15.2f} {secured_overfitting:<15.2f} {secured_overfitting - baseline_overfitting:<+15.2f}")

    print(f"\nATTENDU pour adversarial training:")
    print(f"  Val Acc:  90-95% (obtenu: {secured_best_val:.1f}%)")
    print(f"  Overfitting: 5-10% (obtenu: {secured_overfitting:.1f}%)")

    if secured_best_val < baseline_best_val - 15:
        print(f"\n🔴 PROBLÈME: Secured est {baseline_best_val - secured_best_val:.1f}% PIRE que baseline!")
        print(f"   Adversarial training devrait donner -3 à -5%, pas -{baseline_best_val - secured_best_val:.1f}%")


def identify_problems(history, diagnostics):
    """Identifie les problèmes potentiels"""

    print("\n" + "="*70)
    print("PROBLÈMES IDENTIFIÉS ET SOLUTIONS")
    print("="*70)

    problems = []

    # Problème 1: Overfitting sévère
    if diagnostics['overfitting_gap'] > 30:
        problems.append({
            'issue': 'Overfitting sévère',
            'severity': 'CRITIQUE',
            'causes': [
                'Learning rate trop élevé (0.001)',
                'Dropout insuffisant (0.3)',
                'Augmentation de données insuffisante'
            ],
            'solutions': [
                'Réduire learning rate à 0.0001-0.0005',
                'Augmenter dropout à 0.4-0.5',
                'Ajouter plus d\'augmentation de données',
                'Utiliser early stopping',
                'Réduire le nombre d\'epochs'
            ]
        })

    # Problème 2: Val accuracy trop basse
    if diagnostics['best_val_acc'] < 85:
        problems.append({
            'issue': f'Validation accuracy trop basse ({diagnostics["best_val_acc"]:.1f}%)',
            'severity': 'CRITIQUE',
            'causes': [
                'Adversarial training trop agressif',
                'Epsilon trop élevé (0.1)',
                'Balance clean/adversarial incorrecte',
                'PGD trop fort (3 iterations)'
            ],
            'solutions': [
                'Réduire epsilon à 0.03-0.05',
                'Augmenter proportion clean: 70% clean + 15% FGSM + 15% PGD',
                'Réduire PGD à 2 iterations',
                'Utiliser FGSM uniquement au début',
                'Warm-up progressif de l\'adversarial training'
            ]
        })

    # Problème 3: Instabilité
    if diagnostics['val_stability'] > 5:
        problems.append({
            'issue': 'Validation instable',
            'severity': 'MODÉRÉ',
            'causes': [
                'Learning rate trop élevé',
                'Batch size trop petit',
                'Adversarial training instable'
            ],
            'solutions': [
                'Réduire learning rate',
                'Utiliser ReduceLROnPlateau plus agressif',
                'Augmenter batch size à 64 si possible'
            ]
        })

    # Affichage
    for i, problem in enumerate(problems, 1):
        print(f"\n{i}. 🔴 {problem['issue'].upper()} - Sévérité: {problem['severity']}")

        print(f"\n   Causes probables:")
        for cause in problem['causes']:
            print(f"     • {cause}")

        print(f"\n   Solutions recommandées:")
        for solution in problem['solutions']:
            print(f"     ✓ {solution}")


def create_diagnostic_plots(history):
    """Crée des graphiques de diagnostic"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Diagnostic Entraînement Sécurisé', fontsize=16, fontweight='bold')

    epochs = range(1, len(history['train_loss']) + 1)

    # 1. Loss
    ax1 = axes[0, 0]
    ax1.plot(epochs, history['train_loss'], 'b-', label='Train Loss', linewidth=2)
    ax1.plot(epochs, history['val_loss'], 'r-', label='Val Loss', linewidth=2)
    ax1.set_title('Loss Evolution', fontweight='bold')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Accuracy
    ax2 = axes[0, 1]
    ax2.plot(epochs, history['train_acc'], 'b-', label='Train Acc', linewidth=2)
    ax2.plot(epochs, history['val_acc'], 'r-', label='Val Acc', linewidth=2)
    ax2.set_title('Accuracy Evolution', fontweight='bold')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=90, color='g', linestyle='--', alpha=0.5, label='Target (90%)')

    # 3. Overfitting Gap
    ax3 = axes[1, 0]
    overfitting_gap = [train - val for train, val in zip(history['train_acc'], history['val_acc'])]
    ax3.plot(epochs, overfitting_gap, 'orange', linewidth=2)
    ax3.fill_between(epochs, overfitting_gap, alpha=0.3, color='orange')
    ax3.set_title('Overfitting Gap (Train - Val)', fontweight='bold')
    ax3.set_xlabel('Epoch')
    ax3.set_ylabel('Gap (%)')
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=10, color='r', linestyle='--', alpha=0.5, label='Threshold (10%)')
    ax3.axhline(y=30, color='darkred', linestyle='--', alpha=0.5, label='Critical (30%)')
    ax3.legend()

    # 4. Val Accuracy Stability
    ax4 = axes[1, 1]
    # Rolling std
    window = 5
    rolling_std = []
    for i in range(len(history['val_acc'])):
        if i < window:
            rolling_std.append(np.nan)
        else:
            rolling_std.append(np.std(history['val_acc'][i-window:i]))

    ax4.plot(epochs, history['val_acc'], 'b-', alpha=0.5, label='Val Acc')
    ax4_twin = ax4.twinx()
    ax4_twin.plot(epochs, rolling_std, 'r-', linewidth=2, label=f'Rolling Std ({window} epochs)')
    ax4.set_title('Validation Stability', fontweight='bold')
    ax4.set_xlabel('Epoch')
    ax4.set_ylabel('Val Accuracy (%)', color='b')
    ax4_twin.set_ylabel('Rolling Std', color='r')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    output_path = Path("results/secured_training/diagnostic_plots.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Graphiques de diagnostic sauvegardés: {output_path}")

    plt.close()


def main():
    """Fonction principale"""

    print("="*70)
    print("ANALYSE DE L'ENTRAÎNEMENT SÉCURISÉ")
    print("="*70)

    # Charger l'historique
    history_path = Path("models/secured/training_history.json")

    if not history_path.exists():
        print(f"❌ Fichier non trouvé: {history_path}")
        return

    history = load_training_history(history_path)
    print(f"\n✅ Historique chargé: {len(history['train_loss'])} epochs")

    # Analyser l'overfitting
    diagnostics = analyze_overfitting(history)

    # Comparer avec baseline
    compare_with_baseline(history)

    # Identifier les problèmes
    identify_problems(history, diagnostics)

    # Créer les graphiques
    create_diagnostic_plots(history)

    print("\n" + "="*70)
    print("ANALYSE TERMINÉE")
    print("="*70)


if __name__ == "__main__":
    main()
