#!/bin/bash
# Script de test pour la stack de monitoring
# Vérifie que tous les services sont opérationnels

echo "=================================================="
echo "TEST DE LA STACK DE MONITORING"
echo "=================================================="
echo ""

# Couleurs pour l'affichage
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de test
test_service() {
    SERVICE_NAME=$1
    URL=$2
    EXPECTED=$3

    echo -n "Testing $SERVICE_NAME... "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL 2>/dev/null)

    if [ "$RESPONSE" = "$EXPECTED" ] || [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}[OK]${NC} (HTTP $RESPONSE)"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} (HTTP $RESPONSE, expected $EXPECTED)"
        return 1
    fi
}

# Test 1: Prometheus
echo "=== Test 1: Prometheus ==="
test_service "Prometheus" "http://localhost:9090/-/healthy" "200"
test_service "Prometheus Targets" "http://localhost:9090/api/v1/targets" "200"
echo ""

# Test 2: Grafana
echo "=== Test 2: Grafana ==="
test_service "Grafana" "http://localhost:3000/api/health" "200"
echo ""

# Test 3: Loki
echo "=== Test 3: Loki ==="
test_service "Loki Ready" "http://localhost:3100/ready" "200"
test_service "Loki Metrics" "http://localhost:3100/metrics" "200"
echo ""

# Test 4: AlertManager
echo "=== Test 4: AlertManager ==="
test_service "AlertManager" "http://localhost:9093/-/healthy" "200"
echo ""

# Test 5: API (si elle tourne)
echo "=== Test 5: API (optionnel) ==="
test_service "API Health" "http://localhost:8000/health" "200"
test_service "API Metrics" "http://localhost:8000/metrics" "200"
echo ""

# Vérification des containers
echo "=== État des Containers ==="
docker-compose -f docker-compose.monitoring.yml ps
echo ""

# Résumé
echo "=================================================="
echo "RÉSUMÉ DES TESTS"
echo "=================================================="
echo ""
echo -e "Prometheus:    http://localhost:9090"
echo -e "Grafana:       http://localhost:3000 ${YELLOW}(admin/admin123)${NC}"
echo -e "AlertManager:  http://localhost:9093"
echo -e "Loki:          http://localhost:3100"
echo ""
echo "Pour voir les logs:"
echo "  docker-compose -f docker-compose.monitoring.yml logs -f"
echo ""
echo "Pour arrêter:"
echo "  docker-compose -f docker-compose.monitoring.yml down"
echo ""
