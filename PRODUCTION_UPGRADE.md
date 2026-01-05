# Upgrade Production - Configuration Complete

## Changements Effectues

### 1. Sauvegarde
- Ancienne version: docker-compose.prod.MINIMAL.yml (100 lignes, 5 services)
- Nouvelle version: docker-compose.prod.yml (203 lignes, 8 services)

### 2. Services Ajoutes

#### PostgreSQL (CRITIQUE)
- Image: postgres:15-alpine
- Port: 127.0.0.1:5432
- Volume: postgres-data-prod (persistant)
- Health check: pg_isready
- Limites: 1 CPU, 1GB RAM

**Usage**:
- Audit trail des predictions
- Logs de securite
- Tracabilite legale

#### Redis (CRITIQUE)
- Image: redis:7-alpine
- Port: 127.0.0.1:6379
- Volume: redis-data-prod (persistant)
- Mode: AOF (append-only file)
- Password: Configure dans .env
- Limites: 0.5 CPU, 512MB RAM

**Usage**:
- Rate limiting WAF
- Cache des predictions
- Sessions utilisateurs

#### Web Interface (IMPORTANT)
- Image: nginx:alpine
- Port: 8080
- Content: web/ directory
- Mode: read-only

**Usage**:
- Interface utilisateur graphique
- Demonstration du systeme

### 3. Services Modifies

#### baseline-api
- Ajout: POSTGRES_* variables
- Ajout: REDIS_* variables
- Ajout: depends_on postgres, redis

#### secured-api
- Ajout: POSTGRES_* variables
- Ajout: REDIS_* variables
- Ajout: depends_on postgres, redis

#### nginx
- Ajout: Volume web/

#### prometheus
- Ajout: Commandes de retention (30 jours)

#### grafana
- Ajout: Provisioning datasources et dashboards

### 4. Variables Environnement (.env)

#### Ajoutees:
- REDIS_PASSWORD (securise)
- POSTGRES_HOST=postgres (pour Docker)

#### Modifiees:
- POSTGRES_HOST: localhost → postgres
- POSTGRES_PORT: 5433 → 5432
- Ajout suffixe "_change_in_prod" sur tous les passwords

## Architecture Finale

### Services Production (8)
1. baseline-api     - API baseline
2. secured-api      - API securisee
3. nginx            - Load balancer HTTPS + web
4. web              - Interface utilisateur
5. postgres         - Base de donnees
6. redis            - Cache
7. prometheus       - Metriques
8. grafana          - Dashboards

### Ports Exposes
- 80/443  - Nginx HTTPS
- 8080    - Interface Web
- 8001    - API Baseline (direct)
- 8002    - API Secured (direct)
- 9090    - Prometheus
- 3000    - Grafana
- 5432    - PostgreSQL (localhost uniquement)
- 6379    - Redis (localhost uniquement)

### Volumes Persistants
- postgres-data-prod  - Donnees PostgreSQL
- redis-data-prod     - Donnees Redis (AOF)
- prometheus-data     - Metriques historiques
- grafana-data        - Dashboards et config

## Lancement

### Commande
```bash
make prod
# ou
docker-compose -f docker/docker-compose.prod.yml up -d
```

### Ordre de demarrage (automatique)
1. postgres, redis (bases)
2. baseline-api, secured-api (depends_on)
3. nginx (depends_on APIs)
4. web, prometheus, grafana (independants)

### Health Checks
- PostgreSQL: Verifie connexion toutes les 10s
- Redis: Verifie ping toutes les 10s
- APIs: Via endpoints /health

## Verification

### 1. Services actifs
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Attendu: 8 containers "Up"

### 2. Logs
```bash
docker-compose -f docker/docker-compose.prod.yml logs -f
```

### 3. Tests PostgreSQL
```bash
docker exec secure-ai-db-prod1 psql -U secure_ai -d ai_metrics -c "\dt"
```

### 4. Tests Redis
```bash
docker exec secure-ai-redis-prod1 redis-cli ping
```

### 5. Tests APIs
```bash
curl https://localhost/health
curl https://localhost/api/baseline/
curl https://localhost/api/secured/
```

## Securite

### Mots de passe par defaut (A CHANGER!)
- POSTGRES_PASSWORD: secure_password_change_in_prod
- REDIS_PASSWORD: redis_secure_password_change_in_prod
- GRAFANA_PASSWORD: admin_change_in_prod
- JWT_SECRET: (deja securise)

### Recommandations
1. Changer TOUS les mots de passe avant deploiement reel
2. Utiliser un gestionnaire de secrets (Vault, AWS Secrets)
3. Ne JAMAIS committer .env dans Git

## Rollback

Si probleme, revenir a la version minimale:
```bash
docker-compose -f docker/docker-compose.prod.yml down
cp docker/docker-compose.prod.MINIMAL.yml docker/docker-compose.prod.yml
docker-compose -f docker/docker-compose.prod.yml up -d
```

## Prochaines Etapes

1. Tester le deploiement complet
2. Verifier les logs d'audit PostgreSQL
3. Tester le rate limiting Redis
4. Configurer les backups automatiques
5. Ajuster les limites de ressources si necessaire

Cree le 2025-12-16
