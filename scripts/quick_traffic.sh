#!/bin/bash
# Script rapide pour générer du trafic API vers l'API sécurisée

API_URL="http://localhost:9800"
COUNT=20

echo "======================================================================"
echo "        Génération de trafic API - Test de Monitoring"
echo "======================================================================"
echo "API: $API_URL"
echo "Nombre de requêtes: $COUNT"
echo "======================================================================"
echo ""

# Trouver des images de test
SAFE_IMAGES=(data/augmented/test/safe/*.jpg)
DANGEROUS_IMAGES=(data/augmented/test/dangerous/*.jpg)

echo "[INFO] Images safe trouvées: ${#SAFE_IMAGES[@]}"
echo "[INFO] Images dangerous trouvées: ${#DANGEROUS_IMAGES[@]}"
echo ""

# Générer du trafic vers l'API sécurisée
for ((i=1; i<=COUNT; i++)); do
    # Alterner entre safe et dangerous
    if [ $((i % 2)) -eq 0 ]; then
        IMAGE="${SAFE_IMAGES[0]}"
        CAT="SAFE"
    else
        IMAGE="${DANGEROUS_IMAGES[0]}"
        CAT="DANGEROUS"
    fi

    echo "[$i/$COUNT] Testing SECURED with $CAT image..."
    curl -s -X POST "$API_URL/predict" -F "file=@$IMAGE" | python -c "import sys, json; d=json.load(sys.stdin); print(f\"  => Prediction: {d.get('prediction')}, Confidence: {d.get('confidence', 0):.3f}\")" 2>/dev/null || echo "  => Error"

    sleep 0.5
done

echo ""
echo "======================================================================"
echo "[OK] Trafic généré avec succès!"
echo ""
echo "Consultez les dashboards:"
echo "  - Grafana:     http://localhost:3000 (admin/admin)"
echo "  - Prometheus:  http://localhost:9890"
echo "======================================================================"
