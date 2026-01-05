#!/bin/bash
# Script d'entrée pour le conteneur de développement

echo "🚀 Démarrage du conteneur de développement..."

# Démarrer l'API en arrière-plan
echo "🔌 Démarrage de l'API..."
cd /workspace
nohup python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload > /tmp/api.log 2>&1 &

# Attendre un peu pour que l'API démarre
sleep 3
echo "✅ API démarrée sur le port 8000"
echo "📋 Logs: tail -f /tmp/api.log"

# Garder le conteneur actif
echo "💻 Shell interactif disponible..."
/bin/bash
