#!/bin/bash
# Lance la comparaison complète dans Docker

echo "📊 Évaluation robustesse du modèle sécurisé dans Docker..."

# Lancer tous les experiments
docker-compose -f docker/docker-compose.dev.yml run --rm dev \
    python src/experiments/comparative/run_all_experiments.py

# Collecter les résultats
docker-compose -f docker/docker-compose.dev.yml run --rm dev \
    python src/experiments/comparative/collect_results.py

# Générer le rapport
docker-compose -f docker/docker-compose.dev.yml run --rm dev \
    python src/evaluation/comparison/generate_report.py

echo "✅ Comparaison terminée - Rapport disponible dans results/comparison/reports/"
