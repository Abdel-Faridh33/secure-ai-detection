"""
Run All Experiments
Lance tous les tests comparatifs
"""

import sys
import os

def run_all_experiments():
    """Execute tous les experiments"""
    print("🚀 Lancement de tous les experiments...")
    
    experiments = [
        "baseline/train_baseline.py",
        "secured/train_secured.py",
        "baseline/test_baseline.py",
        "secured/test_secured.py",
        "baseline/attack_baseline.py",
        "secured/attack_secured.py"
    ]
    
    for exp in experiments:
        print(f"\n▶️ Exécution: {exp}")
        # os.system(f"python src/experiments/{exp}")

if __name__ == "__main__":
    run_all_experiments()
