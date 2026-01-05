#!/bin/bash
# Entraînement du modèle baseline dans Docker

echo "🎯 Lancement de l'entraînement baseline dans Docker..."

# Utiliser docker-compose pour lancer l'entraînement
docker-compose -f docker/docker-compose.dev.yml run --rm dev \
    python src/experiments/baseline/train_baseline.py \
    --epochs ${EPOCHS:-10} \
    --batch-size ${BATCH_SIZE:-32} \
    --learning-rate ${LEARNING_RATE:-0.001}

echo "✅ Entraînement terminé"
