#!/bin/bash
# Entraînement du modèle sécurisé dans Docker

echo "🛡️ Lancement de l'entraînement sécurisé dans Docker..."

# Utiliser docker-compose pour lancer l'entraînement
docker-compose -f docker/docker-compose.dev.yml run --rm dev \
    python src/experiments/secured/train_secured.py \
    --epochs ${EPOCHS:-20} \
    --batch-size ${BATCH_SIZE:-32} \
    --adversarial-training \
    --differential-privacy

echo "✅ Entraînement sécurisé terminé"
