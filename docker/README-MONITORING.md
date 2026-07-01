# Stack de Monitoring - Guide Rapide

## 🚀 Démarrage Rapide (3 étapes)

### 1. Lancer la stack
```bash
cd docker
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Vérifier que tout fonctionne
```bash
# Windows PowerShell
.\test-monitoring.ps1

# Linux/Mac
./test-monitoring.sh
```

### 3. Accéder aux interfaces

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Grafana** | http://localhost:3000 | admin / admin123 |
| **Prometheus** | http://localhost:9090 | - |
| **AlertManager** | http://localhost:9093 | - |

---

## 📊 Dashboards Pré-configurés

Une fois connecté à Grafana :
1. **Dashboards** > **Browse**
2. Dossier : **Secure AI Detection**
3. 2 dashboards disponibles :
   - **API Performance Dashboard** - Métriques temps réel
   - **Security Monitoring Dashboard** - Logs et alertes

---

## 🛑 Arrêt de la stack

```bash
cd docker
docker-compose -f docker-compose.monitoring.yml down
```

---

## 📚 Documentation Complète

Voir : `../MONITORING_GUIDE.md`

---

## 🔧 Structure des Fichiers

```
docker/
├── docker-compose.monitoring.yml   # Configuration principale
├── prometheus/
│   ├── prometheus.yml              # Config Prometheus
│   └── alerts.yml                  # Règles d'alertes
├── alertmanager/
│   └── alertmanager.yml            # Config AlertManager
├── loki/
│   └── loki-config.yml             # Config Loki
├── promtail/
│   └── promtail-config.yml         # Config Promtail
└── grafana/
    ├── provisioning/
    │   ├── datasources/            # Auto-config datasources
    │   └── dashboards/             # Auto-config dashboards
    └── dashboards/                 # Dashboards JSON
        ├── api-performance.json
        └── security-monitoring.json
```

---

## ⚡ Commandes Utiles

```bash
# Voir les logs en temps réel
docker-compose -f docker-compose.monitoring.yml logs -f

# Redémarrer un service
docker-compose -f docker-compose.monitoring.yml restart grafana

# Voir l'état des containers
docker-compose -f docker-compose.monitoring.yml ps

# Arrêter et tout supprimer (⚠️ perte de données)
docker-compose -f docker-compose.monitoring.yml down -v
```

---

## 💡 Que Surveiller ?

### Performance API
- Temps de réponse (doit être <2s)
- Taux d'erreur (doit être <5%)
- Throughput (requêtes/sec)

### Sécurité
- Alertes de sécurité (doit être 0)
- Événements critiques (doit être 0)
- Rate limit blocks (si nombreux = attaque potentielle)

### Modèles IA
- Précision du modèle sécurisé (>94%)
- Temps de traitement (<5s)
- Distribution des prédictions

---

**Note** : L'API doit être lancée pour que les métriques remontent dans Prometheus/Grafana.

Lancer l'API :
```bash
python src/api/app.py
# ou
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```
