"""
Comparaison visuelle des attaques FGSM vs PGD sur le modèle sécurisé
Génère des graphiques pour comprendre l'impact des attaques adversariales
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


def load_latest_results():
    """Charge les derniers résultats FGSM et PGD"""
    results_dir = Path("results/adversarial_attacks")

    # Trouver les derniers fichiers
    fgsm_files = sorted(results_dir.glob("fgsm_results_*.json"), reverse=True)
    pgd_files = sorted(results_dir.glob("pgd_results_*.json"), reverse=True)

    if not fgsm_files or not pgd_files:
        print("❌ Fichiers de résultats non trouvés!")
        return None, None

    # Charger les résultats
    with open(fgsm_files[0], 'r') as f:
        fgsm_results = json.load(f)

    with open(pgd_files[0], 'r') as f:
        pgd_results = json.load(f)

    print(f"✅ FGSM results loaded: {fgsm_files[0].name}")
    print(f"✅ PGD results loaded: {pgd_files[0].name}")

    return fgsm_results, pgd_results


def create_comparison_chart(fgsm_results, pgd_results):
    """Crée un graphique de comparaison FGSM vs PGD"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Comparaison des Attaques Adversariales: FGSM vs PGD',
                 fontsize=16, fontweight='bold', y=0.995)

    # 1. Comparaison des accuracy
    ax1 = axes[0, 0]
    attacks = ['FGSM\n(epsilon=0.1)', 'PGD\n(10 iter, eps=0.1)']
    clean_accs = [fgsm_results['clean_accuracy'], pgd_results['clean_accuracy']]
    adv_accs = [fgsm_results['adversarial_accuracy'], pgd_results['adversarial_accuracy']]

    x = np.arange(len(attacks))
    width = 0.35

    bars1 = ax1.bar(x - width/2, clean_accs, width, label='Clean Accuracy',
                    color='#2ecc71', alpha=0.8)
    bars2 = ax1.bar(x + width/2, adv_accs, width, label='Adversarial Accuracy',
                    color='#e74c3c', alpha=0.8)

    ax1.set_ylabel('Accuracy (%)', fontweight='bold')
    ax1.set_title('Accuracy: Clean vs Adversarial', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(attacks)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    ax1.set_ylim([0, 105])

    # Ajouter les valeurs sur les barres
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom', fontsize=9)

    # 2. Taux de succès des attaques
    ax2 = axes[0, 1]
    success_rates = [
        fgsm_results['attack_success_rate'],
        pgd_results['attack_success_rate']
    ]

    colors = ['#f39c12', '#c0392b']
    bars = ax2.bar(attacks, success_rates, color=colors, alpha=0.8)
    ax2.set_ylabel('Attack Success Rate (%)', fontweight='bold')
    ax2.set_title('Taux de Réussite des Attaques', fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_ylim([0, 105])

    # Ajouter les valeurs
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 3. Dégradation de robustesse
    ax3 = axes[1, 0]
    degradations = [
        fgsm_results['robustness_degradation'],
        pgd_results['robustness_degradation']
    ]

    bars = ax3.bar(attacks, degradations, color=['#e67e22', '#8e44ad'], alpha=0.8)
    ax3.set_ylabel('Robustness Degradation (%)', fontweight='bold')
    ax3.set_title('Dégradation de la Robustesse', fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    ax3.set_ylim([0, 105])
    ax3.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='Seuil critique (50%)')
    ax3.legend()

    # Ajouter les valeurs
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 4. Récapitulatif en tableau
    ax4 = axes[1, 1]
    ax4.axis('off')

    # Données du tableau
    table_data = [
        ['Métrique', 'FGSM', 'PGD', 'Δ'],
        ['Clean Accuracy',
         f"{fgsm_results['clean_accuracy']:.1f}%",
         f"{pgd_results['clean_accuracy']:.1f}%",
         '0.0%'],
        ['Adversarial Accuracy',
         f"{fgsm_results['adversarial_accuracy']:.1f}%",
         f"{pgd_results['adversarial_accuracy']:.1f}%",
         f"{fgsm_results['adversarial_accuracy'] - pgd_results['adversarial_accuracy']:.1f}%"],
        ['Attack Success Rate',
         f"{fgsm_results['attack_success_rate']:.1f}%",
         f"{pgd_results['attack_success_rate']:.1f}%",
         f"{pgd_results['attack_success_rate'] - fgsm_results['attack_success_rate']:+.1f}%"],
        ['Robustness Degradation',
         f"{fgsm_results['robustness_degradation']:.1f}%",
         f"{pgd_results['robustness_degradation']:.1f}%",
         f"{pgd_results['robustness_degradation'] - fgsm_results['robustness_degradation']:+.1f}%"],
    ]

    table = ax4.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.35, 0.2, 0.2, 0.15])

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Style du tableau
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            cell = table[(i, j)]
            if i == 0:  # Header
                cell.set_facecolor('#34495e')
                cell.set_text_props(weight='bold', color='white')
            else:
                if j == 0:  # Première colonne
                    cell.set_facecolor('#ecf0f1')
                    cell.set_text_props(weight='bold')
                elif j == 3:  # Colonne delta
                    cell.set_facecolor('#ffe5e5')

    ax4.set_title('Récapitulatif Comparatif', fontweight='bold', pad=20)

    plt.tight_layout()

    # Sauvegarder
    output_path = Path("results/adversarial_attacks/attack_comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Graphique sauvegardé: {output_path}")

    return output_path


def create_severity_gauge(fgsm_results, pgd_results):
    """Crée une jauge de sévérité des attaques"""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Niveau de Sévérité des Attaques Adversariales',
                 fontsize=16, fontweight='bold')

    # Jauge pour FGSM
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')

    # Cercles de sévérité
    severity_fgsm = fgsm_results['attack_success_rate']
    color_fgsm = '#f39c12' if severity_fgsm < 70 else '#e74c3c'

    circle = plt.Circle((5, 5), 3, color=color_fgsm, alpha=0.3)
    ax1.add_patch(circle)

    ax1.text(5, 5, f"{severity_fgsm:.1f}%",
            ha='center', va='center', fontsize=36, fontweight='bold')
    ax1.text(5, 2, 'FGSM Attack', ha='center', va='center',
            fontsize=14, fontweight='bold')
    ax1.text(5, 1, f'epsilon=0.1', ha='center', va='center',
            fontsize=10, style='italic')

    # Niveau de risque
    risk_level = "ÉLEVÉ" if severity_fgsm < 70 else "CRITIQUE"
    ax1.text(5, 8.5, f'Niveau: {risk_level}', ha='center', va='center',
            fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=color_fgsm, alpha=0.5))

    # Jauge pour PGD
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')

    severity_pgd = pgd_results['attack_success_rate']
    color_pgd = '#e74c3c'  # Toujours critique pour PGD

    circle = plt.Circle((5, 5), 3, color=color_pgd, alpha=0.3)
    ax2.add_patch(circle)

    ax2.text(5, 5, f"{severity_pgd:.1f}%",
            ha='center', va='center', fontsize=36, fontweight='bold')
    ax2.text(5, 2, 'PGD Attack', ha='center', va='center',
            fontsize=14, fontweight='bold')
    ax2.text(5, 1, f'10 iter, eps=0.1', ha='center', va='center',
            fontsize=10, style='italic')

    # Niveau de risque
    risk_level = "CRITIQUE"
    ax2.text(5, 8.5, f'Niveau: {risk_level}', ha='center', va='center',
            fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=color_pgd, alpha=0.5))

    plt.tight_layout()

    # Sauvegarder
    output_path = Path("results/adversarial_attacks/attack_severity.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Jauge de sévérité sauvegardée: {output_path}")

    return output_path


def print_analysis(fgsm_results, pgd_results):
    """Affiche une analyse textuelle des résultats"""

    print("\n" + "="*70)
    print("📊 ANALYSE COMPARATIVE DES ATTAQUES ADVERSARIALES")
    print("="*70)

    print(f"\n🎯 FGSM (Fast Gradient Sign Method) - epsilon=0.1:")
    print(f"   Clean Accuracy:        {fgsm_results['clean_accuracy']:.2f}%")
    print(f"   Adversarial Accuracy:  {fgsm_results['adversarial_accuracy']:.2f}%")
    print(f"   Attack Success Rate:   {fgsm_results['attack_success_rate']:.2f}%")
    print(f"   Robustness Degradation: {fgsm_results['robustness_degradation']:.2f}%")

    print(f"\n⚔️ PGD (Projected Gradient Descent) - 10 iter, eps=0.1:")
    print(f"   Clean Accuracy:        {pgd_results['clean_accuracy']:.2f}%")
    print(f"   Adversarial Accuracy:  {pgd_results['adversarial_accuracy']:.2f}%")
    print(f"   Attack Success Rate:   {pgd_results['attack_success_rate']:.2f}%")
    print(f"   Robustness Degradation: {pgd_results['robustness_degradation']:.2f}%")

    # Différence
    diff_success = pgd_results['attack_success_rate'] - fgsm_results['attack_success_rate']
    diff_deg = pgd_results['robustness_degradation'] - fgsm_results['robustness_degradation']

    print(f"\n📈 DIFFÉRENCE (PGD vs FGSM):")
    print(f"   Attack Success Rate:    {diff_success:+.2f}%")
    print(f"   Robustness Degradation: {diff_deg:+.2f}%")

    print(f"\n🔍 ANALYSE:")
    print(f"   ➤ PGD est {diff_success/fgsm_results['attack_success_rate']*100:.1f}% plus efficace que FGSM")
    print(f"   ➤ Le modèle sécurisé perd {pgd_results['robustness_degradation']:.1f}% de robustesse sous PGD")
    print(f"   ➤ L'adversarial accuracy chute à {pgd_results['adversarial_accuracy']:.1f}% avec PGD")

    print(f"\n⚠️ NIVEAU DE RISQUE:")
    if pgd_results['attack_success_rate'] > 90:
        print(f"   🔴 CRITIQUE - Le modèle est extrêmement vulnérable aux attaques PGD")
    elif pgd_results['attack_success_rate'] > 70:
        print(f"   🟠 ÉLEVÉ - Le modèle est très vulnérable aux attaques PGD")
    else:
        print(f"   🟡 MODÉRÉ - Le modèle a une certaine robustesse")

    print(f"\n💡 RECOMMANDATIONS:")
    print(f"   1. Entraînement sécurisé avec Adversarial Training obligatoire")
    print(f"   2. Utiliser PGD pendant l'entraînement (plus robuste que FGSM)")
    print(f"   3. Tester avec epsilon=0.1 et 10 itérations minimum")
    print(f"   4. Objectif: Réduire la dégradation à moins de 20%")

    print("="*70)


def main():
    """Fonction principale"""

    print("="*70)
    print("📊 COMPARAISON DES ATTAQUES ADVERSARIALES: FGSM vs PGD")
    print("="*70)

    # Charger les résultats
    fgsm_results, pgd_results = load_latest_results()

    if not fgsm_results or not pgd_results:
        return

    # Créer les visualisations
    print("\n🎨 Génération des visualisations...")
    create_comparison_chart(fgsm_results, pgd_results)
    create_severity_gauge(fgsm_results, pgd_results)

    # Afficher l'analyse
    print_analysis(fgsm_results, pgd_results)

    print("\n✅ Analyse comparative terminée!")
    print(f"\n📂 Fichiers générés dans: results/adversarial_attacks/")
    print(f"   - attack_comparison.png")
    print(f"   - attack_severity.png")


if __name__ == "__main__":
    main()
