# Workflow GitHub Actions Complet pour la Production

## Vue d'ensemble

Le workflow deploy-production.yml implémente un pipeline CI/CD complet en 6 jobs:

### Job 1: security-tests
- Tests unitaires avec pytest
- Scan de sécurité avec Bandit
- Audit des dépendances (Safety + pip-audit)
- Upload des rapports en artifacts

### Job 2: build-production
- Build des images Docker (baseline + secured)
- Test des imports critiques
- Sauvegarde et upload des images
- Cache Docker pour performance

### Job 3: deploy
- Téléchargement des images buildées
- Création du fichier .env depuis GitHub Secrets
- Déploiement via docker-compose.prod.yml
- Health checks sur les 8 services:
  - PostgreSQL
  - Redis
  - Baseline API
  - Secured API
  - Nginx
  - Web Interface
  - Prometheus
  - Grafana

### Job 4: smoke-tests
- Tests fonctionnels des API
- Vérification des endpoints
- Tests d'authentification
- Validation Prometheus/Grafana
- Analyse des logs

### Job 5: rollback
- Déclenché automatiquement en cas d'échec
- Arrêt des conteneurs défaillants
- Nettoyage du système
- Génération d'un rapport de rollback

### Job 6: notify
- Notifications de succès/échec
- Résumé du déploiement
- URLs des services déployés

## Configuration requise

### GitHub Secrets
Configurez ces secrets dans Settings > Secrets and variables > Actions:

- POSTGRES_USER
- POSTGRES_PASSWORD
- REDIS_PASSWORD
- JWT_SECRET
- GRAFANA_PASSWORD

### Fichiers nécessaires

- docker/docker-compose.prod.yml (8 services complets)
- docker/Dockerfile.baseline
- docker/Dockerfile.secured
- configs/nginx/ssl/nginx-selfsigned.crt
- configs/nginx/ssl/nginx-selfsigned.key
- configs/nginx/nginx.conf (avec HTTPS)
- configs/monitoring/prometheus.yml
- requirements.txt
- requirements-dev.txt

## Déclenchement

### Automatique
Push sur la branche main (sauf fichiers .md et docs/)

### Manuel
Via GitHub Actions UI:
1. Aller dans Actions
2. Sélectionner "Deploy to Production"
3. Cliquer "Run workflow"
4. Choisir l'environnement (local/vm)

## Adaptation pour VM

Pour déployer sur VM, décommentez et configurez le job deploy-to-vm dans le workflow:

1. Ajoutez le secret VM_SSH_KEY
2. Configurez user@vm-host
3. Assurez-vous que Docker est installé sur la VM
4. Le code doit être dans /opt/secure-ai-detection sur la VM

## Tests locaux

Avant de push, testez localement:

```bash
# Tests de sécurité
docker-compose -f docker/docker-compose.dev.yml run --rm test
bandit -r src/ -ll
safety check
pip-audit

# Build des images
docker build -f docker/Dockerfile.baseline -t secure-ai-baseline:test .
docker build -f docker/Dockerfile.secured -t secure-ai-secured:test .

# Déploiement
docker-compose -f docker/docker-compose.prod.yml up -d

# Health checks
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8080
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

## Dépannage

### Échec au job security-tests
- Vérifiez les tests unitaires: `docker-compose -f docker/docker-compose.dev.yml run --rm test`
- Corrigez les vulnérabilités identifiées par Bandit/Safety

### Échec au job build-production
- Vérifiez que tous les fichiers source sont présents
- Contrôlez les Dockerfiles (dépendances manquantes)

### Échec au job deploy
- Vérifiez que les GitHub Secrets sont configurés
- Contrôlez docker-compose.prod.yml (syntaxe, services)
- Vérifiez les ports disponibles (8001, 8002, 80, 8080, 3000, 9090)

### Échec au job smoke-tests
- Consultez les logs: `docker-compose -f docker/docker-compose.prod.yml logs`
- Vérifiez les health endpoints
- Contrôlez la configuration réseau Docker

### Job rollback déclenché
- Consultez les artifacts rollback-report.txt
- Identifiez le job qui a échoué
- Corrigez localement puis re-push

## Métriques de performance

Temps estimé par job (sur GitHub Actions ubuntu-latest):
- security-tests: 3-5 minutes
- build-production: 5-10 minutes (avec cache: 2-4 min)
- deploy: 2-3 minutes
- smoke-tests: 1-2 minutes
- TOTAL: ~15 minutes (première fois), ~8 minutes (avec cache)

## Amélioration continue

Points d'amélioration possibles:
1. Intégration Slack/Email pour notifications
2. Déploiement blue-green pour zero-downtime
3. Tests de charge automatiques post-déploiement
4. Rollback intelligent vers version précédente (pas juste cleanup)
5. Backup automatique de la base avant déploiement
6. Monitoring des métriques business post-déploiement

Created: 2025-12-16
