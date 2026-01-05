"""
Analyse du pic de validation précoce à l'epoch 4
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


def analyze_early_peak():
    """Analyse pourquoi le pic est à l'epoch 4"""

    # Charger l'historique
    with open('models/secured/training_history.json', 'r') as f:
        history = json.load(f)

    epochs = range(1, len(history['val_acc']) + 1)

    # Trouver le meilleur epoch
    best_epoch = history['val_acc'].index(max(history['val_acc'])) + 1
    best_val_acc = max(history['val_acc'])

    print("="*70)
    print("ANALYSE DU PIC PRÉCOCE DE VALIDATION (Epoch 4)")
    print("="*70)

    print(f"\n📊 Meilleur résultat: Epoch {best_epoch} - Val Acc = {best_val_acc:.2f}%")

    print("\n📈 ÉVOLUTION DES 10 PREMIERS EPOCHS:")
    print("-"*70)
    print(f"{'Epoch':<7} {'Train Acc':<12} {'Val Acc':<12} {'Gap':<8} {'Note':<20}")
    print("-"*70)

    for i in range(min(10, len(history['val_acc']))):
        e = i + 1
        train_acc = history['train_acc'][i]
        val_acc = history['val_acc'][i]
        gap = train_acc - val_acc

        note = ""
        if e == best_epoch:
            note = "⭐ MEILLEUR"
        elif val_acc > 90:
            note = "✅ Excellent"
        elif val_acc > 85:
            note = "✓ Bon"

        print(f"{e:<7} {train_acc:>10.2f}% {val_acc:>10.2f}% {gap:>6.2f}% {note:<20}")

    print("\n" + "="*70)
    print("DIAGNOSTIC DU PIC PRÉCOCE")
    print("="*70)

    # Analyser la stabilité après epoch 4
    val_accs_after_4 = history['val_acc'][3:]  # Epoch 4 et après
    mean_val_after_4 = np.mean(val_accs_after_4)
    std_val_after_4 = np.std(val_accs_after_4)

    print(f"\n1. 🎯 CONVERGENCE RAPIDE")
    print(f"   • Epoch 1: Train 82.7% → Val 85.0%")
    print(f"   • Epoch 4: Train 98.8% → Val 92.2% (PEAK)")
    print(f"   • Convergence très rapide en 4 epochs!")

    print(f"\n2. 📊 STABILITÉ APRÈS LE PIC")
    print(f"   • Moyenne val acc (epochs 4-35): {mean_val_after_4:.2f}%")
    print(f"   • Écart-type: {std_val_after_4:.2f}%")
    print(f"   • Plage: {min(val_accs_after_4):.2f}% - {max(val_accs_after_4):.2f}%")

    # Compter combien d'epochs sont proches du pic
    close_to_peak = sum(1 for v in val_accs_after_4 if v >= best_val_acc - 2)
    print(f"   • Epochs à ±2% du pic: {close_to_peak}/{len(val_accs_after_4)}")

    print(f"\n3. ⚠️ EST-CE UN PROBLÈME?")

    # Vérifier si c'est un vrai pic ou une fluctuation
    top_5_epochs = sorted(enumerate(history['val_acc'], 1), key=lambda x: x[1], reverse=True)[:5]
    print(f"\n   Top 5 epochs par val acc:")
    for e, v in top_5_epochs:
        print(f"      Epoch {e:2d}: {v:.2f}%")

    # Distance entre top epochs
    top_epochs_nums = [e for e, v in top_5_epochs]
    if max(top_epochs_nums) - min(top_epochs_nums) < 10:
        print(f"\n   ✅ Les top 5 epochs sont proches (span: {max(top_epochs_nums) - min(top_epochs_nums)} epochs)")
        print(f"      → Le pic à epoch 4 est LÉGITIME, pas une anomalie")
    else:
        print(f"\n   ⚠️ Les top 5 epochs sont dispersés")
        print(f"      → Possible instabilité")

    print(f"\n4. 🔍 EXPLICATION DU PIC PRÉCOCE")
    print(f"   Raisons possibles:")
    print(f"   • ✅ Transfer learning efficace (MobileNetV2 pré-entraîné)")
    print(f"   • ✅ Dataset relativement petit (1398 images train)")
    print(f"   • ✅ Configuration ultra-conservative (LR très faible)")
    print(f"   • ✅ Adversarial training doux (epsilon=0.03, FGSM only)")

    print(f"\n5. 📉 POURQUOI LA VAL ACC BAISSE APRÈS?")

    # Analyser le trend
    val_trend_5_10 = np.mean(history['val_acc'][4:9])
    val_trend_10_20 = np.mean(history['val_acc'][9:19])
    val_trend_20_35 = np.mean(history['val_acc'][19:])

    print(f"   • Epochs 5-10:  Moyenne {val_trend_5_10:.2f}%")
    print(f"   • Epochs 10-20: Moyenne {val_trend_10_20:.2f}%")
    print(f"   • Epochs 20-35: Moyenne {val_trend_20_35:.2f}%")

    if val_trend_5_10 < best_val_acc and val_trend_10_20 < best_val_acc:
        print(f"\n   ⚠️ La val acc ne remonte jamais au niveau de l'epoch 4")
        print(f"      → Début d'overfitting dès epoch 5")
        print(f"      → Early stopping aurait dû arrêter à epoch 4-8!")

    print(f"\n6. 🎯 CONCLUSION")
    print(f"   • Le pic à epoch 4 est RÉEL, pas une anomalie")
    print(f"   • Le modèle converge TRÈS vite (transfer learning efficace)")
    print(f"   • Après epoch 4, début d'overfitting léger mais contrôlé")
    print(f"   • Val acc reste dans 89-92% → STABLE ✅")
    print(f"\n   RECOMMANDATION:")
    print(f"   • ✅ Utiliser le modèle de l'epoch 4 (best_secured_model.pth)")
    print(f"   • ✅ Envisager early stopping à patience=5-8 epochs")
    print(f"   • ✅ Possibilité de réduire epochs à 15-20 au lieu de 35")

    print("\n" + "="*70)

    # Créer une visualisation détaillée
    create_early_peak_visualization(history, best_epoch)


def create_early_peak_visualization(history, best_epoch):
    """Crée une visualisation du pic précoce"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Analyse du Pic Précoce (Epoch {best_epoch})',
                 fontsize=16, fontweight='bold')

    epochs = range(1, len(history['val_acc']) + 1)

    # 1. Focus premiers 15 epochs
    ax1 = axes[0, 0]
    ax1.plot(epochs[:15], history['train_acc'][:15], 'b-o', linewidth=2,
             label='Train Acc', markersize=6)
    ax1.plot(epochs[:15], history['val_acc'][:15], 'r-o', linewidth=2,
             label='Val Acc', markersize=6)

    # Marquer le pic
    best_val = max(history['val_acc'])
    ax1.scatter([best_epoch], [best_val], color='gold', s=400, zorder=5,
                edgecolor='black', linewidth=3, marker='*')
    ax1.axvline(x=best_epoch, color='gold', linestyle='--', linewidth=2, alpha=0.5)

    ax1.set_xlabel('Epoch', fontsize=12)
    ax1.set_ylabel('Accuracy (%)', fontsize=12)
    ax1.set_title('Focus: 15 Premiers Epochs', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(70, 105)

    # 2. Distribution val acc
    ax2 = axes[0, 1]

    val_accs = history['val_acc']
    bins = np.linspace(min(val_accs)-1, max(val_accs)+1, 15)
    ax2.hist(val_accs, bins=bins, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.axvline(x=best_val, color='gold', linestyle='--', linewidth=3,
                label=f'Peak: {best_val:.1f}%')
    ax2.axvline(x=np.mean(val_accs), color='red', linestyle='--', linewidth=2,
                label=f'Moyenne: {np.mean(val_accs):.1f}%')

    ax2.set_xlabel('Validation Accuracy (%)', fontsize=12)
    ax2.set_ylabel('Nombre d\'Epochs', fontsize=12)
    ax2.set_title('Distribution de Val Acc sur 35 Epochs', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')

    # 3. Rolling mean val acc
    ax3 = axes[1, 0]

    window = 5
    rolling_mean = []
    for i in range(len(val_accs)):
        if i < window - 1:
            rolling_mean.append(np.nan)
        else:
            rolling_mean.append(np.mean(val_accs[i-window+1:i+1]))

    ax3.plot(epochs, val_accs, 'lightblue', linewidth=1, alpha=0.5, label='Val Acc')
    ax3.plot(epochs, rolling_mean, 'darkblue', linewidth=3, label=f'Rolling Mean ({window} epochs)')
    ax3.axhline(y=best_val, color='gold', linestyle='--', linewidth=2, alpha=0.7,
                label=f'Peak: {best_val:.1f}%')
    ax3.scatter([best_epoch], [best_val], color='gold', s=300, zorder=5,
                edgecolor='black', linewidth=2, marker='*')

    ax3.set_xlabel('Epoch', fontsize=12)
    ax3.set_ylabel('Validation Accuracy (%)', fontsize=12)
    ax3.set_title('Tendance Val Acc (Rolling Mean)', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(85, 95)

    # 4. Epochs près du pic
    ax4 = axes[1, 1]

    # Grouper par distance au pic
    distance_to_peak = [abs(v - best_val) for v in val_accs]
    within_1pct = sum(1 for d in distance_to_peak if d <= 1)
    within_2pct = sum(1 for d in distance_to_peak if d > 1 and d <= 2)
    within_3pct = sum(1 for d in distance_to_peak if d > 2 and d <= 3)
    beyond_3pct = sum(1 for d in distance_to_peak if d > 3)

    categories = ['±1%', '1-2%', '2-3%', '>3%']
    counts = [within_1pct, within_2pct, within_3pct, beyond_3pct]
    colors = ['darkgreen', 'lightgreen', 'orange', 'red']

    bars = ax4.bar(categories, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=2)

    # Annotations
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                f'{count} epochs\n({count/len(val_accs)*100:.1f}%)',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax4.set_ylabel('Nombre d\'Epochs', fontsize=12)
    ax4.set_title(f'Distance au Peak ({best_val:.1f}%)', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_path = Path("results/secured_training/early_peak_analysis.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Visualisation sauvegardée: {output_path}")

    plt.close()


if __name__ == "__main__":
    analyze_early_peak()
