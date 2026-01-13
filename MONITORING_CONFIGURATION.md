# 📊 Configuration du Monitoring - Dev vs Production

## Vue d'ensemble

Le système de monitoring utilise **Prometheus** (collecte des métriques) et **Grafana** (visualisation) avec des configurations **séparées** pour les environnements de développement et de production.

---

## 🏗️ Architecture

### Mode Développement
```
┌─────────────┐
│   dev:8000  │  ← Service unique exposant les 2 modèles
│  (container)│
└──────┬──────┘
       │ /metrics
       ▼
┌─────────────────┐
│  Prometheus Dev │  ← Scrape dev:8000
│   (port 9890)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Grafana Dev   │  ← http://localhost:3500
│   (port 3500)   │
└─────────────────┘
```

### Mode Production
```
┌──────────────────┐      ┌──────────────────┐
│ baseline-api:8000│      │ secured-api:8000 │  ← Services séparés
└────────┬─────────┘      └─────────┬────────┘
         │ /metrics                 │ /metrics
         └──────────┬───────────────┘
                    ▼
         ┌─────────────────────┐
         │  Prometheus Prod    │  ← Scrape les 2 APIs
         │     (port 9090)     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │    Grafana Prod     │  ← http://localhost:3000
         │     (port 3000)     │
         └─────────────────────┘
```

---

## 📁 Fichiers de Configuration

### Prometheus

| Fichier | Environnement | Targets |
|---------|--------------|---------|
| `configs/monitoring/prometheus.yml` | **Development** | `dev:8000` |
| `configs/monitoring/prometheus.prod.yml` | **Production** | `baseline-api:8000`, `secured-api:8000` |

### Grafana

| Fichier | Environnement | Prometheus URL |
|---------|--------------|----------------|
| `configs/monitoring/grafana-datasources/datasources.yml` | **Les deux** | `http://prometheus:9090` |

**Note**: Le nom `prometheus` est résolu par Docker DNS vers le bon container selon l'environnement.

### Dashboard

| Fichier | Description |
|---------|-------------|
| `configs/monitoring/grafana-dashboards/ai-detection-dashboard.json` | Dashboard partagé (dev + prod) |

---

## 🚀 Démarrage

### Mode Développement

```bash
# Démarrer l'environnement dev
make up

# Services actifs:
# - dev:8000           (API)
# - prometheus:9090    (port externe: 9890)
# - grafana:3000       (port externe: 3500)
```

**Accès**:
- Grafana: http://localhost:3500 (admin/admin)
- Prometheus: http://localhost:9890

### Mode Production

```bash
# Démarrer l'environnement prod
make prod

# Services actifs:
# - baseline-api:8000  (port externe: 8001)
# - secured-api:8000   (port externe: 8002)
# - prometheus:9090
# - grafana:3000
```

**Accès**:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

---

## 🔍 Vérification

### Vérifier les Targets Prometheus

**Dev**:
```bash
curl http://localhost:9890/api/v1/targets
```

Résultat attendu:
```json
{
  "activeTargets": [
    {
      "labels": {"job": "dev-api", "instance": "dev:8000"},
      "health": "up"
    },
    {
      "labels": {"job": "prometheus", "instance": "localhost:9090"},
      "health": "up"
    }
  ]
}
```

**Production**:
```bash
curl http://localhost:9090/api/v1/targets
```

Résultat attendu:
```json
{
  "activeTargets": [
    {
      "labels": {"job": "baseline-api", "instance": "baseline-api:8000"},
      "health": "up"
    },
    {
      "labels": {"job": "secured-api", "instance": "secured-api:8000"},
      "health": "up"
    },
    {
      "labels": {"job": "prometheus", "instance": "localhost:9090"},
      "health": "up"
    }
  ]
}
```

### Vérifier les Métriques disponibles

**Dev**:
```bash
curl http://localhost:9890/api/v1/query?query=ai_model_accuracy
```

**Production**:
```bash
curl http://localhost:9090/api/v1/query?query=ai_model_accuracy
```

Résultat attendu:
```json
{
  "status": "success",
  "data": {
    "result": [
      {
        "metric": {"model_type": "baseline"},
        "value": [timestamp, "96.08"]
      },
      {
        "metric": {"model_type": "secured"},
        "value": [timestamp, "96.08"]
      }
    ]
  }
}
```

---

## 🔧 Dépannage

### Dashboard Grafana affiche "No Data"

**Causes possibles**:

1. **Prometheus n'est pas connecté**
   ```bash
   # Vérifier la datasource dans Grafana
   curl http://localhost:3500/api/datasources -u admin:admin

   # Devrait retourner: "url": "http://prometheus:9090"
   ```

2. **Les targets sont down**
   ```bash
   # Dev
   curl http://localhost:9890/api/v1/targets

   # Prod
   curl http://localhost:9090/api/v1/targets
   ```

3. **Pas assez de données historiques**
   - Attendez quelques minutes (scrape interval = 10s)
   - Ou générez du trafic API

4. **Mauvaise configuration Prometheus**
   ```bash
   # Dev - Vérifier que dev:8000 est configuré
   docker exec secure-ai-prometheus1 cat /etc/prometheus/prometheus.yml

   # Prod - Vérifier que baseline-api et secured-api sont configurés
   docker exec prometheus-prod1 sh -c "cat /etc/prometheus/prometheus.yml"
   ```

### Redémarrer Prometheus après modification de config

**Dev**:
```bash
docker-compose -f docker/docker-compose.dev.yml up -d prometheus
```

**Production**:
```bash
docker-compose -f docker/docker-compose.prod.yml up -d prometheus
```

### Grafana ne peut pas se connecter à Prometheus

**Vérifier le réseau Docker**:
```bash
# Dev
docker exec secure-ai-grafana1 sh -c "ping -c 1 prometheus"

# Prod
docker exec grafana-prod1 sh -c "ping -c 1 prometheus"
```

Si le ping échoue, vérifiez que les containers sont sur le même réseau:
```bash
docker network inspect secure-ai-network
```

---

## 📊 Métriques Collectées

### Métriques HTTP
- `http_requests_total` - Nombre total de requêtes (par méthode, endpoint, status)
- `http_request_duration_seconds` - Durée des requêtes (histogram)

### Métriques IA
- `ai_model_accuracy` - Précision du modèle (par model_type: baseline/secured)
- `ai_model_predictions_total` - Nombre de prédictions (par model_type et prediction: safe/dangerous)
- `ai_model_processing_seconds` - Temps de traitement des prédictions (histogram)

### Métriques Système (Python)
- `python_gc_collections_total` - Garbage collection
- `process_cpu_seconds_total` - CPU utilisé
- `process_resident_memory_bytes` - Mémoire utilisée

---

## 🎯 Prochaines Étapes

Pour améliorer le monitoring:

1. **Ajouter des métriques de sécurité**:
   - Nombre d'attaques détectées
   - Taux de faux positifs
   - Score de robustesse

2. **Configurer les alertes**:
   - Éditer `configs/monitoring/alert_rules.yml`
   - Ajouter un Alertmanager

3. **Optimiser le dashboard**:
   - Ajouter des panels spécifiques à la sécurité
   - Comparer baseline vs secured en temps réel

4. **Ajouter Node Exporter**:
   - Métriques système (CPU, RAM, disque)
   - Décommenter dans `prometheus.yml`

---

## 📚 Références

- [Guide de lecture du dashboard](GUIDE_LECTURE_DASHBOARD_GRAFANA.md)
- [Documentation Prometheus](https://prometheus.io/docs/)
- [Documentation Grafana](https://grafana.com/docs/)
