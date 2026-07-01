# 🗄️ Base de Données PostgreSQL - Architecture Hybride

Documentation complète du système de base de données hybride.

## 📋 Vue d'Ensemble

L'architecture hybride combine PostgreSQL et stockage fichier pour un équilibre optimal entre performance, sécurité et conformité.

### Stockage PostgreSQL

- **Utilisateurs** : Authentification, RBAC, sessions
- **Index des logs** : Recherche rapide dans l'audit trail
- **Historique des prédictions** : Analytics long terme (>30 jours)

### Stockage Fichier (conservé)

- **Logs JSONL** : Audit trail immuable (conformité RGPD)
- **Modèles PyTorch** : Fichiers `.pth`
- **Images** : Dataset sur filesystem
- **Résultats** : Expériences ML en JSON

---

## 🚀 Installation

### 1. Démarrer PostgreSQL

```bash
# Démarrer le conteneur Docker
docker-compose -f docker-compose.dev.yml up -d postgres

# Vérifier que PostgreSQL est actif
docker-compose -f docker-compose.dev.yml ps postgres
```

### 2. Initialiser la base de données

```bash
# Installation complète (création schémas + données initiales)
python scripts/init_database.py

# Réinitialisation complète (ATTENTION: Supprime toutes les données!)
python scripts/init_database.py --reset
```

### 3. Vérifier l'installation

L'output devrait afficher :

```
=================================================
     INITIALISATION BASE DE DONNÉES
=================================================

✓ Connexion réussie !
✓ 01_schema_users.sql exécuté avec succès
✓ 02_schema_audit_index.sql exécuté avec succès
✓ 03_schema_predictions.sql exécuté avec succès
✓ 04_initial_data.sql exécuté avec succès

✓ 12 tables créées
✓ 3 utilisateurs créés:
  - admin (admin)
  - agent (agent)
  - operator (operator)
✓ 28 permissions RBAC configurées
```

---

## 📊 Schéma de Base de Données

### Tables Principales

| Table | Description | Lignes typiques |
|-------|-------------|-----------------|
| `users` | Utilisateurs + auth | 10-100 |
| `login_history` | Historique connexions | 1K-10K |
| `active_sessions` | Sessions JWT actives | 10-100 |
| `role_permissions` | Matrice RBAC | ~30 |
| `audit_logs_index` | Index logs audit | 100K-1M+ |
| `predictions` | Historique prédictions | 100K-1M+ |
| `model_performance` | Métriques agrégées | 100-1K |
| `unique_images` | Déduplication images | 10K-100K |

### Vues Utiles

| Vue | Usage |
|-----|-------|
| `recent_predictions` | Prédictions 24h |
| `security_incidents` | Incidents sécurité |
| `predictions_with_user` | Prédictions + infos user |
| `model_drift_analysis` | Analyse drift (30j) |

### Fonctions Utiles

| Fonction | Description |
|----------|-------------|
| `cleanup_expired_sessions()` | Nettoie sessions expirées |
| `update_daily_stats(DATE)` | Recalcule stats journalières |
| `calculate_model_performance(...)` | Calcule métriques modèle |

---

## 💻 Utilisation des Modules Python

### UserManager - Gestion des utilisateurs

```python
from src.database import UserManager

manager = UserManager()

# Créer un utilisateur
user_id = manager.create_user(
    username="john_doe",
    password="SecureP@ss123",
    role="agent",
    email="john@example.com",
    full_name="John Doe"
)

# Authentification
user = manager.authenticate(
    username="john_doe",
    password="SecureP@ss123",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)

if user:
    print(f"Bienvenue {user['full_name']} (rôle: {user['role']})")

# Vérifier permissions (RBAC)
if manager.has_permission(user_id, 'predictions', 'create'):
    # Autoriser la prédiction
    pass

# Lister tous les utilisateurs
users = manager.list_users(active_only=True)
for u in users:
    print(f"{u['username']} - {u['role']}")

# Changer mot de passe
manager.change_password(user_id, "NewSecureP@ss456")

# Gestion des sessions JWT
session_id = manager.create_session(
    user_id=user_id,
    token_jti="unique-jwt-id",
    expires_in_minutes=60,
    ip_address="192.168.1.100"
)

# Vérifier validité session
is_valid = manager.is_session_valid("unique-jwt-id")

# Révoquer session (logout)
manager.revoke_session("unique-jwt-id", reason="User logout")
```

### PredictionLogger - Historique des prédictions

```python
from src.database import PredictionLogger

logger = PredictionLogger()

# Enregistrer une prédiction
prediction_id = logger.log_prediction(
    model_type="secured",
    model_version="1.0.0",
    image_hash="a3d5f8e9b2c1...",
    prediction_result="dangerous",
    confidence=0.9234,
    processing_time_ms=125.45,
    user_id=user_id,
    image_filename="suspect.jpg",
    image_size_bytes=245678,
    client_ip="192.168.1.100",
    attack_detected=False,
    audit_id="AUDIT-ABC123"
)

# Ajouter feedback utilisateur
logger.add_user_feedback(
    prediction_id=prediction_id,
    feedback="correct",
    comment="Détection précise"
)

# Récupérer prédictions récentes
recent = logger.get_recent_predictions(
    limit=50,
    model_type="secured",
    user_id=user_id
)

# Statistiques d'un modèle
stats = logger.get_model_stats(
    model_type="secured",
    model_version="1.0.0"
)
print(f"Total prédictions: {stats['total_predictions']}")
print(f"Confiance moyenne: {stats['avg_confidence']:.2f}")
print(f"Accuracy: {stats['accuracy_rate']:.2%}")

# Analyser la dérive du modèle sécurisé
drift_stats = logger.get_model_stats(
    model_type="secured",
    model_version="latest",
    days=7
)
print(f"Confiance moyenne (7j): {drift_stats['avg_confidence']:.3f}")

# Détecter drift du modèle
drift = logger.detect_model_drift(
    model_type="secured",
    window_days=7
)
if drift['drift_detected']:
    print("⚠️  DRIFT DÉTECTÉ!")
    print(f"Delta: {drift['deltas']['confidence']:+.3f}")
```

---

## 🔐 Utilisateurs par Défaut

**ATTENTION :** Changez ces mots de passe immédiatement en production !

| Username | Password | Rôle | Permissions |
|----------|----------|------|-------------|
| `admin` | `admin123` | admin | Toutes |
| `operator` | `operator456` | operator | Opérations + monitoring |
| `agent` | `agent789` | agent | Prédictions + consultation |

### Changer les mots de passe

```python
from src.database import UserManager

manager = UserManager()

# Changer le mot de passe admin
admin = manager.get_user_by_username("admin")
manager.change_password(admin['id'], "VotreNouveauMotDePasse123!")
```

---

## 🛡️ Permissions RBAC

### Matrice des permissions

| Resource | admin | operator | agent | viewer |
|----------|-------|----------|-------|--------|
| **predictions** |  |  |  |  |
| - read | ✅ | ✅ | ✅ | ✅ |
| - create | ✅ | ✅ | ✅ | ❌ |
| - delete | ✅ | ❌ | ❌ | ❌ |
| **audit_logs** |  |  |  |  |
| - read | ✅ | ✅ | ✅ | ✅ |
| - export | ✅ | ✅ | ❌ | ❌ |
| - admin | ✅ | ❌ | ❌ | ❌ |
| **users** |  |  |  |  |
| - read | ✅ | ❌ | ❌ | ❌ |
| - create | ✅ | ❌ | ❌ | ❌ |
| - update | ✅ | ❌ | ❌ | ❌ |
| - delete | ✅ | ❌ | ❌ | ❌ |
| **models** |  |  |  |  |
| - read | ✅ | ✅ | ❌ | ❌ |
| - switch | ✅ | ✅ | ❌ | ❌ |
| - write | ✅ | ❌ | ❌ | ❌ |

---

## 📈 Requêtes SQL Utiles

### Statistiques utilisateurs

```sql
-- Utilisateurs actifs
SELECT username, role, last_login
FROM users
WHERE is_active = true
ORDER BY last_login DESC;

-- Tentatives de connexion échouées
SELECT u.username, COUNT(*) as failed_attempts
FROM login_history lh
JOIN users u ON lh.user_id = u.id
WHERE lh.success = false
    AND lh.login_time > NOW() - INTERVAL '24 hours'
GROUP BY u.username
ORDER BY failed_attempts DESC;
```

### Analytics prédictions

```sql
-- Top 10 images les plus prédites
SELECT image_hash, total_predictions, consensus_result
FROM unique_images
ORDER BY total_predictions DESC
LIMIT 10;

-- Performance par modèle (7 derniers jours)
SELECT
    model_type,
    COUNT(*) as predictions,
    AVG(confidence) as avg_confidence,
    AVG(processing_time_ms) as avg_time_ms
FROM predictions
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY model_type;

-- Distribution des résultats par jour
SELECT
    DATE(timestamp) as date,
    prediction_result,
    COUNT(*) as count
FROM predictions
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), prediction_result
ORDER BY date DESC;
```

### Sécurité et monitoring

```sql
-- Incidents de sécurité (24h)
SELECT * FROM security_incidents
WHERE timestamp > NOW() - INTERVAL '24 hours';

-- Anomalies non vérifiées
SELECT * FROM detected_anomalies
WHERE is_false_positive IS NULL
ORDER BY detected_at DESC;

-- Stats quotidiennes
SELECT * FROM audit_stats_daily
ORDER BY date DESC
LIMIT 30;
```

---

## 🔧 Maintenance

### Nettoyage automatique

```python
from src.database import UserManager

manager = UserManager()

# Nettoyer sessions expirées
deleted = manager.cleanup_expired_sessions()
print(f"{deleted} sessions expirées supprimées")
```

### Calcul des métriques

```python
from src.database import PredictionLogger
from datetime import datetime, timedelta

logger = PredictionLogger()

# Calculer métriques quotidiennes
today = datetime.now().date()
yesterday = today - timedelta(days=1)

logger.calculate_performance_metrics(
    model_type="secured",
    model_version="1.0.0",
    period_start=datetime.combine(yesterday, datetime.min.time()),
    period_end=datetime.combine(today, datetime.min.time()),
    granularity="day"
)
```

### Backup

```bash
# Backup complet
docker exec secure-ai-postgres pg_dump -U secure_ai ai_metrics > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i secure-ai-postgres psql -U secure_ai ai_metrics < backup_20251216.sql
```

---

## 🐛 Dépannage

### Connexion impossible

```bash
# Vérifier que PostgreSQL est démarré
docker-compose -f docker-compose.dev.yml ps postgres

# Voir les logs
docker-compose -f docker-compose.dev.yml logs postgres

# Redémarrer
docker-compose -f docker-compose.dev.yml restart postgres
```

### Erreur "relation does not exist"

La base n'est pas initialisée. Lancez :

```bash
python scripts/init_database.py
```

### Tester la connexion

```python
from src.database import get_db_connection

db = get_db_connection()
if db.test_connection():
    print("✅ Connexion OK")
else:
    print("❌ Connexion échouée")
```

---

## 📚 Ressources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg2 Guide](https://www.psycopg.org/docs/)
- [bcrypt Documentation](https://github.com/pyca/bcrypt/)

---

*Architecture hybride PostgreSQL+fichiers pour Secure AI Detection System*
