# Script de test pour la stack de monitoring (Windows PowerShell)
# Vérifie que tous les services sont opérationnels

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "TEST DE LA STACK DE MONITORING" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Fonction de test
function Test-Service {
    param(
        [string]$ServiceName,
        [string]$Url,
        [string]$Expected = "200"
    )

    Write-Host "Testing $ServiceName... " -NoNewline

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $statusCode = $response.StatusCode

        if ($statusCode -eq 200) {
            Write-Host "[OK]" -ForegroundColor Green -NoNewline
            Write-Host " (HTTP $statusCode)"
            return $true
        } else {
            Write-Host "[FAIL]" -ForegroundColor Red -NoNewline
            Write-Host " (HTTP $statusCode, expected $Expected)"
            return $false
        }
    }
    catch {
        Write-Host "[FAIL]" -ForegroundColor Red -NoNewline
        Write-Host " (Connection error: $_)"
        return $false
    }
}

# Test 1: Prometheus
Write-Host ""
Write-Host "=== Test 1: Prometheus ===" -ForegroundColor Yellow
Test-Service "Prometheus" "http://localhost:9090/-/healthy"
Test-Service "Prometheus Targets" "http://localhost:9090/api/v1/targets"

# Test 2: Grafana
Write-Host ""
Write-Host "=== Test 2: Grafana ===" -ForegroundColor Yellow
Test-Service "Grafana" "http://localhost:3000/api/health"

# Test 3: Loki
Write-Host ""
Write-Host "=== Test 3: Loki ===" -ForegroundColor Yellow
Test-Service "Loki Ready" "http://localhost:3100/ready"
Test-Service "Loki Metrics" "http://localhost:3100/metrics"

# Test 4: AlertManager
Write-Host ""
Write-Host "=== Test 4: AlertManager ===" -ForegroundColor Yellow
Test-Service "AlertManager" "http://localhost:9093/-/healthy"

# Test 5: API (si elle tourne)
Write-Host ""
Write-Host "=== Test 5: API (optionnel) ===" -ForegroundColor Yellow
Test-Service "API Health" "http://localhost:8000/health"
Test-Service "API Metrics" "http://localhost:8000/metrics"

# Vérification des containers
Write-Host ""
Write-Host "=== État des Containers ===" -ForegroundColor Yellow
Set-Location -Path "docker"
docker-compose -f docker-compose.monitoring.yml ps
Set-Location -Path ".."

# Résumé
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "RÉSUMÉ DES TESTS" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prometheus:    http://localhost:9090"
Write-Host "Grafana:       http://localhost:3000 " -NoNewline
Write-Host "(admin/admin123)" -ForegroundColor Yellow
Write-Host "AlertManager:  http://localhost:9093"
Write-Host "Loki:          http://localhost:3100"
Write-Host ""
Write-Host "Pour voir les logs:"
Write-Host "  docker-compose -f docker\docker-compose.monitoring.yml logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "Pour arrêter:"
Write-Host "  docker-compose -f docker\docker-compose.monitoring.yml down" -ForegroundColor Gray
Write-Host ""
