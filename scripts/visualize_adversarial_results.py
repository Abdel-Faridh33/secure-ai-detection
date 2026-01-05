#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualisation des Résultats d'Attaques Adversariales

Génère un rapport visuel complet avec:
- Graphiques de performance
- Comparaison avant/après attaque
- Exemples d'images adversariales
- Statistiques détaillées

Usage:
    python scripts/visualize_adversarial_results.py
    python scripts/visualize_adversarial_results.py --results-dir results/adversarial_attacks
"""

import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime
import sys
import io

# Fix encoding pour Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_latest_results(results_dir: Path) -> dict:
    """Charge les résultats les plus récents"""
    json_files = list(results_dir.glob('fgsm_results_*.json'))

    if not json_files:
        raise FileNotFoundError(f"Aucun résultat trouvé dans {results_dir}")

    # Trier par date (le plus récent en premier)
    latest_file = sorted(json_files, reverse=True)[0]

    print(f"📂 Chargement: {latest_file.name}")

    with open(latest_file, 'r') as f:
        return json.load(f)


def create_performance_comparison(results: dict, output_path: Path):
    """Graphique comparaison Clean vs Adversarial"""

    fig, ax = plt.subplots(figsize=(10, 6))

    categories = ['Clean Images', 'Adversarial Images']
    accuracies = [results['clean_accuracy'], results['adversarial_accuracy']]
    colors = ['#2ecc71', '#e74c3c']

    bars = ax.bar(categories, accuracies, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

    # Ajouter valeurs sur les barres
    for bar, acc in zip(bars, accuracies):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{acc:.1f}%',
                ha='center', va='bottom', fontsize=14, fontweight='bold')

    # Ligne de référence à 50% (aléatoire)
    ax.axhline(y=50, color='gray', linestyle='--', linewidth=2, alpha=0.5, label='Random (50%)')

    # Styling
    ax.set_ylabel('Accuracy (%)', fontsize=13, fontweight='bold')
    ax.set_title(f'Performance du Modèle Baseline\nAttaque FGSM (ε={results["epsilon"]})',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.legend(fontsize=11)

    # Ajouter annotation de dégradation
    degradation = results['robustness_degradation']
    ax.annotate(f'Dégradation:\n-{degradation:.1f}%',
                xy=(0.5, accuracies[0]),
                xytext=(0.5, (accuracies[0] + accuracies[1])/2),
                ha='center',
                fontsize=12,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=2))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Graphique sauvegardé: {output_path}")
    plt.close()


def create_attack_success_visualization(results: dict, output_path: Path):
    """Graphique succès d'attaque"""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Pie chart - Succès d'attaque
    success_rate = results['attack_success_rate']
    failure_rate = 100 - success_rate

    sizes = [success_rate, failure_rate]
    labels = [f'Attaque Réussie\n{success_rate:.1f}%', f'Attaque Échouée\n{failure_rate:.1f}%']
    colors = ['#e74c3c', '#2ecc71']
    explode = (0.1, 0)

    ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='', startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'},
            wedgeprops={'edgecolor': 'black', 'linewidth': 2})
    ax1.set_title('Taux de Succès de l\'Attaque FGSM', fontsize=14, fontweight='bold', pad=15)

    # Bar chart - Nombre d'échantillons
    total = results['total_samples']
    successful_attacks = int(total * success_rate / 100)
    failed_attacks = total - successful_attacks

    categories = ['Attaques\nRéussies', 'Attaques\nÉchouées']
    counts = [successful_attacks, failed_attacks]

    bars = ax2.bar(categories, counts, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'{count}\nimages',
                ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax2.set_ylabel('Nombre d\'Images', fontsize=12, fontweight='bold')
    ax2.set_title(f'Distribution sur {total} Images du Test Set', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylim(0, total + 20)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Graphique sauvegardé: {output_path}")
    plt.close()


def create_robustness_gauge(results: dict, output_path: Path):
    """Jauge de robustesse"""

    fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': 'polar'})

    # Calculer le score de robustesse (inverse du taux d'attaque)
    robustness_score = 100 - results['attack_success_rate']

    # Paramètres de la jauge
    theta = np.linspace(0, np.pi, 100)

    # Zones colorées
    zones = [
        (0, 33, '#e74c3c', 'Très Vulnérable'),
        (33, 66, '#f39c12', 'Vulnérable'),
        (66, 100, '#2ecc71', 'Robuste')
    ]

    for start, end, color, label in zones:
        mask = (theta >= start * np.pi / 100) & (theta <= end * np.pi / 100)
        ax.fill_between(theta[mask], 0, 1, color=color, alpha=0.3, label=label)

    # Aiguille du score
    score_angle = robustness_score * np.pi / 100
    ax.plot([score_angle, score_angle], [0, 0.9], 'k-', linewidth=4)
    ax.plot(score_angle, 0.9, 'ko', markersize=15)

    # Styling
    ax.set_ylim(0, 1)
    ax.set_theta_zero_location('W')
    ax.set_theta_direction(1)
    ax.set_xticks(np.linspace(0, np.pi, 5))
    ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'], fontsize=11)
    ax.set_yticks([])
    ax.spines['polar'].set_visible(False)

    # Titre et score
    ax.text(np.pi/2, 1.3, f'Score de Robustesse: {robustness_score:.1f}%',
            ha='center', fontsize=16, fontweight='bold')
    ax.text(np.pi/2, 1.15, f'(Attaque FGSM ε={results["epsilon"]})',
            ha='center', fontsize=12, style='italic')

    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Jauge sauvegardée: {output_path}")
    plt.close()


def create_summary_table(results: dict, output_path: Path):
    """Table récapitulative"""

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('tight')
    ax.axis('off')

    # Données du tableau
    data = [
        ['Type d\'Attaque', 'FGSM (Fast Gradient Sign Method)'],
        ['Epsilon (ε)', f'{results["epsilon"]}'],
        ['', ''],
        ['Test Set', f'{results["total_samples"]} images'],
        ['', ''],
        ['Clean Accuracy', f'{results["clean_accuracy"]:.2f}%'],
        ['Adversarial Accuracy', f'{results["adversarial_accuracy"]:.2f}%'],
        ['', ''],
        ['Attack Success Rate', f'{results["attack_success_rate"]:.2f}%'],
        ['Robustness Score', f'{100 - results["attack_success_rate"]:.2f}%'],
        ['Performance Degradation', f'{results["robustness_degradation"]:.2f}%'],
        ['', ''],
        ['Images Attaquées avec Succès', f'{int(results["total_samples"] * results["attack_success_rate"] / 100)} / {results["total_samples"]}'],
        ['', ''],
        ['Verdict', 'MODÈLE TRÈS VULNÉRABLE ⚠️' if results["attack_success_rate"] > 40
                    else 'MODÈLE VULNÉRABLE ⚠️' if results["attack_success_rate"] > 20
                    else 'MODÈLE ROBUSTE ✅']
    ]

    # Couleurs des lignes
    colors = []
    for row in data:
        if row[0] == '':
            colors.append(['white', 'white'])
        elif 'Verdict' in row[0]:
            colors.append(['#ffcccc', '#ffcccc'])
        elif any(word in row[0] for word in ['Clean', 'Adversarial', 'Attack', 'Robustness', 'Performance']):
            colors.append(['#e8f4f8', '#e8f4f8'])
        else:
            colors.append(['white', 'white'])

    table = ax.table(cellText=data, cellLoc='left', loc='center',
                    cellColours=colors, colWidths=[0.4, 0.6])

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)

    # Styling des cellules
    for i, row in enumerate(data):
        for j in range(2):
            cell = table[(i, j)]
            if j == 0:
                cell.set_text_props(weight='bold')
            if 'VULNÉRABLE' in str(row[1]):
                cell.set_text_props(weight='bold', color='red')
            if 'ROBUSTE' in str(row[1]):
                cell.set_text_props(weight='bold', color='green')

    ax.set_title('Résumé des Tests Adversariaux - Modèle Baseline MobileNetV2',
                fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Table sauvegardée: {output_path}")
    plt.close()


def create_comprehensive_report(results: dict, output_dir: Path):
    """Crée un rapport PDF/image complet"""

    fig = plt.figure(figsize=(16, 20))

    # Grid layout
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # 1. Titre principal
    fig.suptitle('RAPPORT D\'ANALYSE ADVERSARIALE\nModèle Baseline MobileNetV2',
                fontsize=18, fontweight='bold', y=0.98)

    # 2. Métriques clés (top)
    ax_metrics = fig.add_subplot(gs[0, :])
    ax_metrics.axis('off')

    metrics_text = f"""
    Dataset: {results['total_samples']} images (Test Set)
    Attaque: FGSM (ε={results['epsilon']})

    Clean Accuracy: {results['clean_accuracy']:.2f}%  |  Adversarial Accuracy: {results['adversarial_accuracy']:.2f}%
    Performance Degradation: {results['robustness_degradation']:.2f}%  |  Attack Success Rate: {results['attack_success_rate']:.2f}%
    """

    ax_metrics.text(0.5, 0.5, metrics_text, ha='center', va='center',
                   fontsize=12, bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.8))

    # 3. Graphique performance
    ax_perf = fig.add_subplot(gs[1, 0])
    categories = ['Clean', 'Adversarial']
    accuracies = [results['clean_accuracy'], results['adversarial_accuracy']]
    colors = ['#2ecc71', '#e74c3c']
    bars = ax_perf.bar(categories, accuracies, color=colors, alpha=0.8, edgecolor='black')
    ax_perf.set_ylabel('Accuracy (%)', fontweight='bold')
    ax_perf.set_title('Performance Comparison', fontweight='bold')
    ax_perf.set_ylim(0, 105)
    ax_perf.grid(axis='y', alpha=0.3)
    for bar, acc in zip(bars, accuracies):
        ax_perf.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2,
                    f'{acc:.1f}%', ha='center', fontweight='bold')

    # 4. Pie chart succès
    ax_pie = fig.add_subplot(gs[1, 1])
    success_rate = results['attack_success_rate']
    sizes = [success_rate, 100 - success_rate]
    colors_pie = ['#e74c3c', '#2ecc71']
    ax_pie.pie(sizes, labels=[f'Success\n{success_rate:.1f}%', f'Failure\n{100-success_rate:.1f}%'],
              colors=colors_pie, autopct='', startangle=90, wedgeprops={'edgecolor': 'black'})
    ax_pie.set_title('Attack Success Rate', fontweight='bold')

    # 5. Évolution théorique avec epsilon
    ax_epsilon = fig.add_subplot(gs[2, :])
    epsilons = [0.01, 0.03, 0.05, 0.1, 0.2, 0.3]
    # Simulation basée sur résultat actuel
    current_eps = results['epsilon']
    current_success = results['attack_success_rate']
    simulated_success = [current_success * (eps/current_eps)**0.7 for eps in epsilons]
    simulated_success = [min(95, s) for s in simulated_success]  # Cap à 95%

    ax_epsilon.plot(epsilons, simulated_success, 'o-', linewidth=2, markersize=8, color='#e74c3c')
    ax_epsilon.axvline(x=current_eps, color='blue', linestyle='--', label=f'Testé (ε={current_eps})')
    ax_epsilon.set_xlabel('Epsilon (ε)', fontweight='bold')
    ax_epsilon.set_ylabel('Attack Success Rate (%)', fontweight='bold')
    ax_epsilon.set_title('Prédiction: Impact de Epsilon sur le Succès d\'Attaque', fontweight='bold')
    ax_epsilon.grid(True, alpha=0.3)
    ax_epsilon.legend()
    ax_epsilon.set_ylim(0, 100)

    # 6. Recommandations
    ax_reco = fig.add_subplot(gs[3, :])
    ax_reco.axis('off')

    reco_text = """
    RECOMMANDATIONS:

    ⚠️  VULNÉRABILITÉ CRITIQUE DÉTECTÉE

    Le modèle baseline est extrêmement vulnérable aux attaques adversariales.

    Actions Recommandées:
    1. ✅ Entraîner un modèle sécurisé avec Adversarial Training ou TRADES
    2. ✅ Implémenter des défenses de détection (input sanitization)
    3. ✅ Ajouter un système de monitoring pour détecter les attaques en production
    4. ✅ Tester avec des attaques plus fortes (PGD, C&W, AutoAttack)

    Objectif: Robustesse > 70% contre FGSM
    """

    ax_reco.text(0.05, 0.5, reco_text, va='center', fontsize=11,
                bbox=dict(boxstyle='round,pad=1', facecolor='#ffe6e6', alpha=0.9))

    # Sauvegarder
    report_path = output_dir / 'comprehensive_adversarial_report.png'
    plt.savefig(report_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Rapport complet sauvegardé: {report_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Visualise résultats adversariaux")
    parser.add_argument('--results-dir', type=str, default='results/adversarial_attacks',
                       help='Dossier des résultats')
    parser.add_argument('--output-dir', type=str, default='results/adversarial_visualizations',
                       help='Dossier de sortie')

    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("📊 GÉNÉRATION DU RAPPORT VISUEL D'ANALYSE ADVERSARIALE")
    print("=" * 70)

    # Charger résultats
    results = load_latest_results(results_dir)

    print(f"\n📋 Résultats chargés:")
    print(f"   - Attaque: {results['attack_type']}")
    print(f"   - Epsilon: {results['epsilon']}")
    print(f"   - Test samples: {results['total_samples']}")
    print(f"   - Attack success: {results['attack_success_rate']:.2f}%")

    # Générer visualisations
    print(f"\n🎨 Génération des visualisations...")

    create_performance_comparison(results, output_dir / 'performance_comparison.png')
    create_attack_success_visualization(results, output_dir / 'attack_success.png')
    create_robustness_gauge(results, output_dir / 'robustness_gauge.png')
    create_summary_table(results, output_dir / 'summary_table.png')
    create_comprehensive_report(results, output_dir)

    print("\n" + "=" * 70)
    print("✅ RAPPORT VISUEL GÉNÉRÉ AVEC SUCCÈS")
    print("=" * 70)
    print(f"\n📂 Fichiers créés dans: {output_dir}")
    print("   - performance_comparison.png")
    print("   - attack_success.png")
    print("   - robustness_gauge.png")
    print("   - summary_table.png")
    print("   - comprehensive_adversarial_report.png")
    print("\n💡 Ouvrez comprehensive_adversarial_report.png pour une vue complète")


if __name__ == "__main__":
    main()
