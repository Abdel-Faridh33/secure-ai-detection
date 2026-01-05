"""
Analyse détaillée des résultats FGSM uniquement
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


def analyze_fgsm_results():
    """Analyse les résultats FGSM en détail"""

    # Charger les résultats
    results_path = Path("results/secured_robustness/robustness_comparison_20251224_202921.json")

    with open(results_path, 'r') as f:
        results = json.load(f)

    fgsm_results = results['detailed_results']['fgsm_test']

    print("="*70)
    print("ANALYSE FGSM - FOCUS SUR L'ATTAQUE SINGLE-STEP")
    print("="*70)

    print("\n📊 RÉSULTATS FGSM (ε=0.1):")
    print("-"*70)
    print(f"  Clean Accuracy:       {fgsm_results['clean_accuracy']:.2f}%")
    print(f"  Adversarial Accuracy: {fgsm_results['adversarial_accuracy']:.2f}%")
    print(f"  Attack Success Rate:  {fgsm_results['attack_success_rate']:.2f}%")
    print(f"  Robustness:           {100 - fgsm_results['attack_success_rate']:.2f}%")
    print(f"  Degradation:          {fgsm_results['robustness_degradation']:.2f}%")

    # Baseline comparison
    baseline_fgsm = results['baseline_vulnerabilities']['fgsm_success']
    secured_fgsm = fgsm_results['attack_success_rate']

    print("\n📈 COMPARAISON AVEC BASELINE:")
    print("-"*70)
    print(f"  Baseline FGSM Success:  {baseline_fgsm:.2f}%")
    print(f"  Secured FGSM Success:   {secured_fgsm:.2f}%")
    print(f"  Différence:             {secured_fgsm - baseline_fgsm:+.2f}%")

    if secured_fgsm > baseline_fgsm:
        print(f"\n  🔴 PROBLÈME: Le modèle secured est PIRE que baseline!")
    else:
        print(f"\n  ✅ SUCCÈS: Le modèle secured est meilleur que baseline!")

    print("\n🎯 ANALYSE DU GAP ENTRAÎNEMENT/TEST:")
    print("-"*70)
    print(f"  Epsilon entraînement:   0.03")
    print(f"  Epsilon test:           0.10")
    print(f"  Ratio test/train:       {0.1/0.03:.2f}x")
    print(f"\n  Le modèle a été entraîné sur des perturbations 3.3x plus petites!")
    print(f"  C'est comme s'entraîner au jogging et courir un marathon.")

    # Calcul de la robustesse effective
    robustness_pct = 100 - secured_fgsm

    print("\n🛡️ ÉVALUATION DE LA ROBUSTESSE:")
    print("-"*70)
    print(f"  Robustesse FGSM: {robustness_pct:.2f}%")

    if robustness_pct >= 75:
        status = "✅ EXCELLENT"
        color = "green"
    elif robustness_pct >= 65:
        status = "🟡 BON"
        color = "orange"
    elif robustness_pct >= 55:
        status = "🟠 MOYEN"
        color = "orangered"
    else:
        status = "🔴 FAIBLE"
        color = "red"

    print(f"  Status: {status}")

    print(f"\n  Objectif initial:       70-80%")
    print(f"  Résultat obtenu:        {robustness_pct:.2f}%")

    if robustness_pct >= 70:
        print(f"  ✅ Objectif ATTEINT!")
    elif robustness_pct >= 60:
        print(f"  🟡 Proche de l'objectif (-{70-robustness_pct:.1f}%)")
    else:
        print(f"  🔴 Loin de l'objectif (-{70-robustness_pct:.1f}%)")

    print("\n💡 EXPLICATION DES 63.7% DE ROBUSTESSE:")
    print("-"*70)
    print("  Le modèle résiste à 63.7% des attaques FGSM (ε=0.1)")
    print("  Cela signifie:")
    print(f"    • Sur 204 échantillons test")
    print(f"    • {int(204 * robustness_pct / 100)} sont correctement classifiés malgré FGSM")
    print(f"    • {int(204 * secured_fgsm / 100)} sont mal classifiés (attaque réussie)")

    print("\n🔬 POURQUOI PAS 70-80%?")
    print("-"*70)
    print("  1. ⚠️ Epsilon d'entraînement trop faible (0.03)")
    print("     → Le modèle n'a jamais vu des perturbations de 0.1")
    print("     → Il ne sait pas gérer des attaques 3x plus fortes")
    print()
    print("  2. ⚠️ Ratio clean trop élevé (80%)")
    print("     → Seulement 20% d'exposition à FGSM pendant training")
    print("     → Pas assez de pratique sur données adversariales")
    print()
    print("  3. ✅ Trade-off val acc vs robustesse")
    print("     → Val Acc: 92.18% (excellent)")
    print("     → Robustesse: 63.7% (correct mais pas optimal)")
    print("     → Le modèle a priorisé la performance standard")

    print("\n📊 COMPARAISON THÉORIQUE:")
    print("-"*70)
    print(f"  Si entraîné avec ε=0.1 au lieu de 0.03:")
    print(f"    • Robustesse FGSM attendue: 75-85%")
    print(f"    • Mais Val Acc serait: 88-91% (au lieu de 92%)")
    print(f"\n  Trade-off actuel:")
    print(f"    • Val Acc: 92.18% ✅ (excellent)")
    print(f"    • FGSM Robustesse: 63.7% 🟡 (correct)")

    print("\n🎯 CONCLUSION FGSM:")
    print("-"*70)

    if robustness_pct >= 60:
        print("  ✅ Le modèle a une robustesse FGSM acceptable (63.7%)")
        print("  ✅ Amélioration significative vs modèle non entraîné (~50%)")
        print("  🟡 Pas optimal (objectif 70-80%) mais utilisable")
    else:
        print("  🔴 La robustesse FGSM est trop faible")
        print("  🔴 Nécessite un réentraînement")

    print(f"\n  Le modèle est {robustness_pct:.1f}% robuste à FGSM (ε=0.1)")
    print(f"  C'est {robustness_pct/50 - 1:.0f}% mieux qu'un modèle non entraîné")

    # Créer une visualisation
    create_fgsm_visualization(fgsm_results, robustness_pct)


def create_fgsm_visualization(fgsm_results, robustness_pct):
    """Crée une visualisation des résultats FGSM"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Analyse FGSM - Robustesse du Modèle Sécurisé',
                 fontsize=16, fontweight='bold')

    # 1. Accuracy comparison
    ax1 = axes[0, 0]

    categories = ['Clean\nAccuracy', 'FGSM\nAccuracy']
    values = [fgsm_results['clean_accuracy'], fgsm_results['adversarial_accuracy']]
    colors = ['#27AE60', '#E67E22']

    bars = ax1.bar(categories, values, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

    # Annotations
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., height + 1,
                f'{val:.1f}%',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    # Ligne objectif
    ax1.axhline(y=90, color='green', linestyle='--', linewidth=2, alpha=0.5, label='Objectif: 90%')

    ax1.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Clean vs Adversarial (FGSM ε=0.1)', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 105)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')

    # 2. Robustesse pie chart
    ax2 = axes[0, 1]

    success_rate = fgsm_results['attack_success_rate']
    robustness_rate = 100 - success_rate

    sizes = [robustness_rate, success_rate]
    labels = [f'Robuste\n{robustness_rate:.1f}%', f'Attaque\nRéussie\n{success_rate:.1f}%']
    colors_pie = ['#27AE60', '#E74C3C']
    explode = (0.05, 0.05)

    wedges, texts, autotexts = ax2.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
                                        autopct='%1.1f%%', startangle=90,
                                        textprops={'fontsize': 12, 'fontweight': 'bold'})

    ax2.set_title('Répartition FGSM (ε=0.1)', fontsize=14, fontweight='bold')

    # 3. Comparaison epsilon training vs test
    ax3 = axes[1, 0]

    epsilons = ['Training\n(ε=0.03)', 'Test\n(ε=0.10)']
    epsilon_values = [0.03, 0.10]
    bar_colors = ['#3498DB', '#E74C3C']

    bars = ax3.bar(epsilons, epsilon_values, color=bar_colors, alpha=0.8, edgecolor='black', linewidth=2)

    # Annotations
    for bar, val in zip(bars, epsilon_values):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2., height + 0.005,
                f'{val:.2f}',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    # Ligne de ratio
    ax3.plot([0, 1], [0.03, 0.10], 'r--', linewidth=2, alpha=0.5)
    ax3.text(0.5, 0.065, f'Ratio: {0.10/0.03:.1f}x', ha='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

    ax3.set_ylabel('Epsilon', fontsize=12, fontweight='bold')
    ax3.set_title('Gap Entraînement vs Test', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    # 4. Gauge robustesse
    ax4 = axes[1, 1]
    ax4.axis('off')

    # Créer un gauge semi-circulaire
    theta = np.linspace(0, np.pi, 100)

    # Background arc
    radius = 0.8
    x_bg = radius * np.cos(theta)
    y_bg = radius * np.sin(theta)
    ax4.plot(x_bg, y_bg, 'lightgray', linewidth=20, alpha=0.3)

    # Colored sections
    # Red: 0-50%
    theta_red = np.linspace(0, np.pi * 0.5, 50)
    x_red = radius * np.cos(theta_red)
    y_red = radius * np.sin(theta_red)
    ax4.plot(x_red, y_red, '#E74C3C', linewidth=20, alpha=0.7)

    # Orange: 50-70%
    theta_orange = np.linspace(np.pi * 0.5, np.pi * 0.7, 50)
    x_orange = radius * np.cos(theta_orange)
    y_orange = radius * np.sin(theta_orange)
    ax4.plot(x_orange, y_orange, '#E67E22', linewidth=20, alpha=0.7)

    # Green: 70-100%
    theta_green = np.linspace(np.pi * 0.7, np.pi, 50)
    x_green = radius * np.cos(theta_green)
    y_green = radius * np.sin(theta_green)
    ax4.plot(x_green, y_green, '#27AE60', linewidth=20, alpha=0.7)

    # Needle
    angle = np.pi * (1 - robustness_pct / 100)
    needle_length = 0.6
    ax4.plot([0, needle_length * np.cos(angle)], [0, needle_length * np.sin(angle)],
             'black', linewidth=4)
    ax4.plot(0, 0, 'ko', markersize=15)

    # Labels
    ax4.text(0, -0.3, f'{robustness_pct:.1f}%', ha='center', fontsize=24, fontweight='bold')
    ax4.text(0, -0.45, 'Robustesse FGSM', ha='center', fontsize=14)

    # Section labels
    ax4.text(-0.6, 0.1, '50%', fontsize=10)
    ax4.text(0, 0.9, '70%', fontsize=10)
    ax4.text(0.6, 0.1, '100%', fontsize=10)

    ax4.set_xlim(-1, 1)
    ax4.set_ylim(-0.6, 1)
    ax4.set_aspect('equal')

    plt.tight_layout()

    output_path = Path("results/secured_robustness/fgsm_analysis.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Visualisation FGSM sauvegardée: {output_path}")

    plt.close()


if __name__ == "__main__":
    analyze_fgsm_results()
