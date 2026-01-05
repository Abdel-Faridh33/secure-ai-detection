# Makefile pour développement conteneurisé

.PHONY: help build dev train test api-baseline api-secured monitoring clean stop logs shell web open-web start-api up demo wait-for-containers prod prod-fast test-prod health-prod status-prod logs-prod

# Variables
DOCKER_COMPOSE = docker-compose -f docker/docker-compose.dev.yml
DOCKER_COMPOSE_PROD = docker-compose -f docker/docker-compose.prod.yml 
PROJECT_NAME = secure-ai-detection

help:
	@echo "╔══════════════════════════════════════════════════════════╗"
	@echo "║         Secure AI Detection - Docker Commands            ║"
	@echo "╠══════════════════════════════════════════════════════════╣"
	@echo "║ Quick Start:                                             ║"
	@echo "║   make up           - 🚀 Démarre TOUT (API + Web + DB)   ║"
	@echo "║   make demo         - 🎬 Démarre la démo web complète    ║"
	@echo "║   make stop         - ⏹️  Arrête tous les containers      ║"
	@echo "║                                                          ║"
	@echo "║ Development:                                             ║"
	@echo "║   make dev          - Lance l'environnement complet dev  ║"
	@echo "║   make web          - Lance l'interface web              ║"
	@echo "║   make start-api    - Démarre l'API dans le container    ║"
	@echo "║   make shell        - Ouvre un shell dans le container   ║"
	@echo "║                                                          ║"
	@echo "║ Training:                                                ║"
	@echo "║   make train-baseline - Entraîne le modèle baseline     ║"
	@echo "║   make train-secured  - Entraîne le modèle sécurisé     ║"
	@echo "║                                                          ║"
	@echo "║ Testing:                                                 ║"
	@echo "║   make test         - Lance tous les tests              ║"
	@echo "║   make test-attacks - Teste les attaques                ║"
	@echo "║                                                          ║"
	@echo "║ Production:                                              ║"
	@echo "║   make prod         - 🏭 Lance production (avec build)   ║"
	@echo "║   make prod-fast    - ⚡ Lance production (sans build)   ║"
	@echo "║   make test-prod    - 🧪 Teste les endpoints production  ║"
	@echo "║   make health-prod  - 🏥 Health check production         ║"
	@echo "║   make monitoring   - 📊 Lance Prometheus + Grafana      ║"
	@echo "║                                                          ║"
	@echo "║ Utils:                                                   ║"
	@echo "║   make logs         - Affiche les logs dev              ║"
	@echo "║   make logs-prod    - Affiche les logs production       ║"
	@echo "║   make status       - Statut des containers dev         ║"
	@echo "║   make status-prod  - Statut des containers production  ║"
	@echo "║   make clean        - Nettoie tout                      ║"
	@echo "╚══════════════════════════════════════════════════════════╝"

# Construction des images
build:
	@echo "🔨 Construction des images Docker..."
	$(DOCKER_COMPOSE) build

# Attendre que les containers soient prêts
wait-for-containers:
	@echo "⏳ Attente du démarrage des containers (5 secondes)..."
	@sleep 5

# 🚀 COMMANDE PRINCIPALE - Démarre tout en une fois
up: build
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║       🚀 DÉMARRAGE COMPLET DE L'ENVIRONNEMENT          ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Étape 1/2: Démarrage des conteneurs Docker (API incluse)..."
	$(DOCKER_COMPOSE) up -d
	@$(MAKE) --no-print-directory wait-for-containers
	@echo "✅ Conteneurs démarrés (l'API démarre automatiquement)"
	@echo ""
	@echo "✨ Étape 2/2: Vérification des services..."
	@$(MAKE) --no-print-directory status
	@echo ""
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║              ✅ SYSTÈME PRÊT À L'EMPLOI                ║"
	@echo "╠════════════════════════════════════════════════════════╣"
	@echo "║  🌐 Interface Web:    http://localhost:8080           ║"
	@echo "║  🔌 API:              http://localhost:9800           ║"
	@echo "║  📊 Prometheus:       http://localhost:9890           ║"
	@echo "║  📈 Grafana:          http://localhost:3500           ║"
	@echo "║                       (admin/admin)                    ║"
	@echo "╠════════════════════════════════════════════════════════╣"
	@echo "║  💡 Commandes utiles:                                 ║"
	@echo "║     make logs        - Voir les logs                  ║"
	@echo "║     make shell       - Ouvrir un shell                ║"
	@echo "║     make stop        - Arrêter tout                   ║"
	@echo "╚════════════════════════════════════════════════════════╝"

# 🎬 DÉMO WEB - Démarre tout et ouvre le navigateur
demo: up
	@echo ""
	@echo "🌍 Ouverture de l'interface web dans le navigateur..."
	@sleep 2
	@python launch_web.py || (command -v xdg-open > /dev/null && xdg-open http://localhost:8080) || (command -v open > /dev/null && open http://localhost:8080) || echo "⚠️  Ouvrez manuellement: http://localhost:8080"

# Environnement de développement (commande legacy)
dev: build
	@echo "🚀 Lancement de l'environnement de développement..."
	$(DOCKER_COMPOSE) up -d dev
	@echo "✅ Environnement prêt! Shell disponible avec: make shell"
	@echo "💡 Utilisez 'make up' pour démarrer avec l'API automatiquement"

# Environnement de développement sans rebuild
dev-fast:
	@echo "⚡ Lancement rapide de l'environnement de développement (sans rebuild)..."
	$(DOCKER_COMPOSE) up -d
	@$(MAKE) --no-print-directory wait-for-containers
	@echo "✅ Environnement prêt! Shell disponible avec: make shell"
	@echo "💡 Utilisez 'make up' pour démarrer avec l'API



# Shell interactif
shell:
	@echo "🐚 Ouverture du shell dans le container de dev..."
	$(DOCKER_COMPOSE) exec dev /bin/bash

# Interface Web
web:
	@echo "🌐 Lancement de l'interface web..."
	$(DOCKER_COMPOSE) up -d web
	@echo "✅ Interface web disponible sur http://localhost:8080"

# Ouvrir l'interface dans le navigateur
open-web:
	@echo "🌍 Ouverture de l'interface web..."
	python launch_web.py

# Démarrer l'API dans le container dev
start-api:
	@echo "🚀 Démarrage de l'API..."
	@docker exec -d secure-ai-dev1 bash -c "cd /workspace && nohup python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload > /tmp/api.log 2>&1 &"
	@sleep 3
	@echo "✅ API disponible sur http://localhost:9800"
	@echo "📋 Logs: docker exec secure-ai-dev1 tail -f /tmp/api.log"

# Entraînement baseline
train-baseline:
	@echo "🎯 Entraînement du modèle baseline..."
	$(DOCKER_COMPOSE) run --rm dev python src/experiments/baseline/train_baseline.py

# Entraînement sécurisé
train-secured:
	@echo "🛡️ Entraînement du modèle sécurisé..."
	$(DOCKER_COMPOSE) run --rm dev python src/experiments/secured/train_secured.py

# Tests
test:
	@echo "🧪 Lancement des tests..."
	$(DOCKER_COMPOSE) run --rm test

test-attacks:
	@echo "⚔️ Test des attaques..."
	$(DOCKER_COMPOSE) run --rm dev python src/experiments/baseline/attack_baseline.py

# Production
prod:
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║       🏭 DÉMARRAGE DE L'ENVIRONNEMENT PRODUCTION       ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Étape 1/3: Build des images de production..."
	$(DOCKER_COMPOSE_PROD) build --no-cache
	@echo ""
	@echo "🚀 Étape 2/3: Démarrage des services..."
	$(DOCKER_COMPOSE_PROD) up -d
	@echo ""
	@echo "⏳ Étape 3/3: Attente du démarrage complet (15 secondes)..."
	@sleep 15
	@echo ""
	@$(MAKE) --no-print-directory status-prod
	@echo ""
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║         ✅ ENVIRONNEMENT PRODUCTION DÉMARRÉ            ║"
	@echo "╠════════════════════════════════════════════════════════╣"
	@echo "║  🔌 Baseline API:     http://localhost:8001           ║"
	@echo "║  🛡️  Secured API:      http://localhost:8002           ║"
	@echo "║  🌐 Interface Web:    http://localhost:8080           ║"
	@echo "║  🔀 Nginx (HTTPS):    https://localhost               ║"
	@echo "║  📊 Prometheus:       http://localhost:9090           ║"
	@echo "║  📈 Grafana:          http://localhost:3500           ║"
	@echo "║  💾 PostgreSQL:       localhost:5432                  ║"
	@echo "║  🔴 Redis:            localhost:6379                  ║"
	@echo "╠════════════════════════════════════════════════════════╣"
	@echo "║  💡 Commandes utiles:                                 ║"
	@echo "║     make logs-prod   - Voir les logs production      ║"
	@echo "║     make test-prod   - Tester les endpoints          ║"
	@echo "║     make stop        - Arrêter tout                   ║"
	@echo "╚════════════════════════════════════════════════════════╝"

prod-fast:
	@echo "🏭 Lancement rapide de la production (sans rebuild)..."
	$(DOCKER_COMPOSE_PROD) up -d
	@$(MAKE) --no-print-directory status-prod

# Monitoring
monitoring:
	@echo "📊 Lancement du monitoring..."
	$(DOCKER_COMPOSE) up -d prometheus grafana
	@echo "✅ Prometheus: http://localhost:9090"
	@echo "✅ Grafana: http://localhost:3000 (admin/admin)"

# Logs
logs:
	$(DOCKER_COMPOSE) logs -f

logs-prod:
	$(DOCKER_COMPOSE_PROD) logs -f

# Nettoyage
clean:
	@echo "🧹 Nettoyage des containers et volumes..."
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE_PROD) down -v
	docker system prune -f

stop:
	@echo "⏹️ Arrêt de tous les containers..."
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE_PROD) down

# Status
status:
	@echo "📊 Status des containers:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

status-prod:
	@echo "📊 Status des containers de production:"
	@docker ps --filter "name=prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Tests production
test-prod:
	@echo "🧪 Test des endpoints de production..."
	@echo ""
	@echo "🔌 Test Baseline API..."
	@curl -s http://localhost:8001/health || echo "❌ Baseline API non accessible"
	@echo ""
	@echo "🛡️  Test Secured API..."
	@curl -s http://localhost:8002/health || echo "❌ Secured API non accessible"
	@echo ""
	@echo "🌐 Test Interface Web..."
	@curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8080 || echo "❌ Web non accessible"
	@echo ""
	@echo "📊 Test Prometheus..."
	@curl -s http://localhost:9090/-/healthy || echo "❌ Prometheus non accessible"
	@echo ""
	@echo "📈 Test Grafana..."
	@curl -s http://localhost:3000/api/health | head -3 || echo "❌ Grafana non accessible"
	@echo ""
	@echo "✅ Tests terminés!"

# Health check production
health-prod:
	@echo "🏥 Health check de l'environnement de production..."
	@echo ""
	@echo "Vérification PostgreSQL..."
	@docker exec secure-ai-db-prod1 pg_isready -U secure_ai && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL KO"
	@echo ""
	@echo "Vérification Redis..."
	@docker exec secure-ai-redis-prod1 redis-cli ping && echo "✅ Redis OK" || echo "❌ Redis KO"
	@echo ""
	@echo "Vérification des conteneurs..."
	@$(MAKE) --no-print-directory status-prod
