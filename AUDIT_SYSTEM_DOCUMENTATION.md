# 📝 Documentation du Système d'Audit Trail

## 🎯 Vue d'ensemble

Le système d'audit trail implémente la **Zone 5 (Gouvernance et Surveillance)** de l'architecture de sécurité proposée. Il fournit une traçabilité complète et immuable de toutes les opérations du système de détection d'objets dangereux.

### Conformité et Légalité

Dans un contexte de **système de maintien de l'ordre**, le système d'audit permet de :
- ✅ **Traçabilité légale** : Prouver en justice le bon fonctionnement du système
- ✅ **Conformité RGPD** : Logs immuables avec conservation limitée (90 jours)
- ✅ **Audit externe** : Export des logs pour audits de sécurité
- ✅ **Détection d'abus** : Identifier les tentatives de manipulation

---

## 🏗️ Architecture

### Composants Principaux

```
src/monitoring/
└── audit_logger.py          # Module principal d'audit
    ├── AuditLogger          # Classe principale
    ├── EventType (Enum)     # Types d'événements
    └── SeverityLevel (Enum) # Niveaux de gravité
```

### Types d'Événements Audités

| Type d'événement | Description | Gravité par défaut |
|------------------|-------------|-------------------|
| `PREDICTION` | Prédiction du modèle IA | INFO |
| `ATTACK_DETECTED` | Attaque adversariale détectée | SECURITY_ALERT |
| `VALIDATION_FAILED` | Validation d'input échouée | WARNING |
| `API_ACCESS` | Accès à l'API | INFO/WARNING/CRITICAL |
| `MODEL_LOADED` | Chargement d'un modèle | INFO |
| `SYSTEM_ERROR` | Erreur système | CRITICAL |

### Niveaux de Gravité

- `INFO` : Événement normal
- `WARNING` : Événement suspect
- `CRITICAL` : Erreur critique
- `SECURITY_ALERT` : Alerte de sécurité (attaque détectée)

---

## 🔐 Caractéristiques de Sécurité

### 1. Logs Immuables (Append-Only)

Les logs sont écrits en **mode append uniquement** :
- ❌ **Impossible de modifier** un log existant
- ❌ **Impossible de supprimer** un log
- ✅ **Traçabilité garantie** pour la justice

### 2. Hachage Cryptographique

#### Images
```python
# Hash SHA-256 de l'image analysée
image_hash = hashlib.sha256(image_data).hexdigest()
# Exemple : "a3d5f8e9..." (64 caractères)
```

**Avantage** : Traçabilité sans stocker l'image (RGPD-friendly)

#### Données Sensibles
```python
# Hash court des IDs utilisateurs
user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
# Exemple : "e4b2a8c1f9d6..." (16 caractères)
```

**Avantage** : Pseudonymisation pour protéger la vie privée

### 3. Horodatage Précis

Format **ISO 8601** avec UTC :
```
"timestamp": "2025-10-11T14:32:45.123456Z"
```

### 4. Format Structuré (JSON Lines)

Chaque log est une ligne JSON indépendante :
```json
{"audit_id": "AUDIT-A3F5E9D2", "timestamp": "2025-10-11T14:32:45Z", ...}
{"audit_id": "AUDIT-B7C2F1A8", "timestamp": "2025-10-11T14:32:46Z", ...}
```

**Avantages** :
- Facile à parser
- Streaming possible
- Résistant à la corruption (une ligne = un événement)

---

## 📊 Structure des Logs

### Exemple : Log de Prédiction

```json
{
  "audit_id": "AUDIT-A3F5E9D2",
  "timestamp": "2025-10-11T14:32:45.123456Z",
  "event_type": "prediction",
  "severity": "info",

  "user": {
    "user_id_hash": "e4b2a8c1f9d6...",
    "user_role": "agent",
    "client_ip": "192.168.1.100"
  },

  "image": {
    "filename": "suspect_object.jpg",
    "hash_sha256": "a3d5f8e9b2c1...",
    "size_bytes": 245678
  },

  "prediction": {
    "model_type": "secured",
    "model_version": "1.0.0",
    "result": "dangerous",
    "confidence": 0.9234,
    "processing_time_ms": 125.45
  },

  "metadata": {
    "image_format": "JPEG",
    "image_size": [1920, 1080],
    "image_mode": "RGB"
  }
}
```

### Exemple : Log d'Attaque Détectée

```json
{
  "audit_id": "AUDIT-B7C2F1A8",
  "timestamp": "2025-10-11T14:35:12.456789Z",
  "event_type": "attack_detected",
  "severity": "security_alert",

  "user": {
    "user_id_hash": "f9a3b7e2c5d1...",
    "client_ip": "10.0.0.50"
  },

  "image": {
    "filename": "suspicious.jpg",
    "hash_sha256": "b8f2c9a7e3d5..."
  },

  "attack": {
    "type": "adversarial_fgsm",
    "confidence": 0.9512,
    "detection_method": "statistical_analysis",
    "blocked": true,
    "action_taken": "REQUEST_BLOCKED"
  }
}
```

---

## 🚀 Utilisation de l'API

### Endpoints Disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/audit/logs` | GET | Récupérer les logs récents |
| `/audit/stats` | GET | Statistiques sur les logs |
| `/audit/search` | GET | Recherche avancée |
| `/audit/recent-attacks` | GET | Attaques récentes |
| `/audit/predictions/{audit_id}` | GET | Détails d'une prédiction |
| `/audit/export` | POST | Export pour audit externe |

---

### 1. Récupérer les Logs Récents

**Requête** :
```bash
GET http://localhost:9800/audit/logs?limit=50&event_type=prediction&severity=info
```

**Paramètres** :
- `limit` : Nombre de logs (max 1000, défaut 50)
- `event_type` : Filtrer par type (optionnel)
  - `prediction`, `attack_detected`, `validation_failed`, `api_access`
- `severity` : Filtrer par gravité (optionnel)
  - `info`, `warning`, `critical`, `security_alert`

**Réponse** :
```json
{
  "count": 42,
  "logs": [
    { "audit_id": "AUDIT-...", ...},
    { "audit_id": "AUDIT-...", ...}
  ],
  "filters_applied": {
    "event_type": "prediction",
    "severity": "info",
    "limit": 50
  }
}
```

---

### 2. Statistiques Globales

**Requête** :
```bash
GET http://localhost:9800/audit/stats
```

**Réponse** :
```json
{
  "statistics": {
    "total_events": 1523,
    "events_by_type": {
      "prediction": 1200,
      "attack_detected": 15,
      "validation_failed": 108,
      "api_access": 200
    },
    "events_by_severity": {
      "info": 1400,
      "warning": 108,
      "security_alert": 15
    },
    "attacks_detected": 15,
    "predictions_count": 1200,
    "average_confidence": 0.8765,
    "date_range": {
      "first_event": "2025-10-01T00:00:00Z",
      "last_event": "2025-10-11T14:32:45Z"
    }
  },
  "generated_at": "2025-10-11T14:35:00Z"
}
```

---

### 3. Recherche Avancée

**Requête** :
```bash
GET http://localhost:9800/audit/search?start_date=2025-10-01T00:00:00Z&end_date=2025-10-11T23:59:59Z&event_type=attack_detected&limit=100
```

**Paramètres** :
- `start_date` : Date de début (ISO 8601)
- `end_date` : Date de fin (ISO 8601)
- `event_type` : Type d'événement
- `user_id` : ID utilisateur (optionnel)
- `limit` : Nombre de résultats (défaut 100)

**Réponse** :
```json
{
  "count": 15,
  "results": [
    { "audit_id": "AUDIT-...", "event_type": "attack_detected", ...}
  ],
  "query": {
    "start_date": "2025-10-01T00:00:00Z",
    "end_date": "2025-10-11T23:59:59Z",
    "event_type": "attack_detected",
    "limit": 100
  }
}
```

---

### 4. Attaques Récentes (Monitoring Sécurité)

**Requête** :
```bash
GET http://localhost:9800/audit/recent-attacks?limit=20
```

**Réponse** :
```json
{
  "count": 3,
  "attacks": [
    {
      "audit_id": "AUDIT-B7C2F1A8",
      "timestamp": "2025-10-11T14:35:12Z",
      "attack": {
        "type": "adversarial_fgsm",
        "confidence": 0.95,
        "blocked": true
      },
      "user": {
        "client_ip": "10.0.0.50"
      }
    }
  ],
  "severity": "CRITICAL"
}
```

---

### 5. Détails d'une Prédiction Spécifique

**Requête** :
```bash
GET http://localhost:9800/audit/predictions/AUDIT-A3F5E9D2
```

**Réponse** :
```json
{
  "found": true,
  "details": {
    "audit_id": "AUDIT-A3F5E9D2",
    "timestamp": "2025-10-11T14:32:45Z",
    "event_type": "prediction",
    "user": {...},
    "image": {...},
    "prediction": {...}
  }
}
```

**Cas d'usage** :
- Enquête judiciaire : "Quelle prédiction a été faite pour l'image X à 14h32 ?"
- Traçabilité complète avec hash de l'image et tous les détails

---

### 6. Export pour Audit Externe

**Requête** :
```bash
POST http://localhost:9800/audit/export
Content-Type: application/json

{
  "start_date": "2025-10-01T00:00:00Z",
  "end_date": "2025-10-11T23:59:59Z",
  "format": "json"
}
```

**Paramètres** :
- `format` : `json` ou `csv`
- `start_date` : Date de début (optionnel)
- `end_date` : Date de fin (optionnel)

**Réponse** :
```json
{
  "success": true,
  "export_file": "logs/audit/export_audit_20251011_143500.json",
  "format": "json",
  "generated_at": "2025-10-11T14:35:00Z"
}
```

Le fichier exporté contient tous les logs au format choisi, prêt pour un audit externe.

---

## 🧪 Tests

### Exécution des Tests

```bash
# Tous les tests du système d'audit
pytest tests/test_audit_system.py -v

# Test spécifique
pytest tests/test_audit_system.py::test_log_prediction -v

# Avec couverture de code
pytest tests/test_audit_system.py --cov=src.monitoring.audit_logger --cov-report=html
```

### Tests Couverts

- ✅ Logging de prédictions
- ✅ Logging d'attaques détectées
- ✅ Logging de validations échouées
- ✅ Hachage SHA-256 des images
- ✅ Hachage des données sensibles
- ✅ Requêtes et filtres
- ✅ Statistiques
- ✅ Export JSON
- ✅ Rotation des fichiers
- ✅ Unicité des audit_id
- ✅ Format JSON valide

---

## 📁 Structure des Fichiers de Logs

### Répertoire de Logs

```
logs/audit/
├── audit_2025-10-11.jsonl      # Logs du jour
├── audit_2025-10-10.jsonl      # Logs d'hier
├── audit_20251009_143000.jsonl # Fichier roté
├── system.log                  # Logs système du logger
└── export_audit_*.json         # Exports pour audits
```

### Rotation Automatique

- **Par jour** : Un nouveau fichier `audit_YYYY-MM-DD.jsonl` chaque jour
- **Par taille** : Rotation si le fichier dépasse 100 MB (configurable)
- **Conservation** : 90 jours par défaut (conformité RGPD)

---

## ⚖️ Aspects Légaux et Conformité

### Conformité RGPD

| Exigence RGPD | Implémentation |
|---------------|----------------|
| **Droit à l'oubli** | Suppression automatique après 90 jours |
| **Minimisation des données** | Hash des IDs utilisateurs (pseudonymisation) |
| **Sécurité** | Logs immuables, hachage cryptographique |
| **Traçabilité** | Tous les accès et opérations loggés |
| **Auditabilité** | Export pour audits externes |

### Preuves Judiciaires

Le système d'audit permet de fournir des **preuves admissibles en justice** :

1. **Traçabilité** :
   - Qui a effectué l'analyse ? → `user_id_hash`, `client_ip`
   - Quand ? → `timestamp` précis au microsecond
   - Avec quel modèle ? → `model_type`, `model_version`

2. **Intégrité** :
   - Hash SHA-256 de l'image analysée
   - Logs append-only (non modifiables)
   - Horodatage certifié (UTC)

3. **Non-répudiation** :
   - Audit ID unique par événement
   - IP du client enregistrée
   - Métadonnées complètes

### Exemple de Scénario Judiciaire

**Question** : "Le système a-t-il bien détecté l'objet dangereux à 14h32 le 11 octobre 2025 ?"

**Réponse** :
```bash
# Recherche par date et heure
GET /audit/search?start_date=2025-10-11T14:32:00Z&end_date=2025-10-11T14:33:00Z

# Résultat :
{
  "audit_id": "AUDIT-A3F5E9D2",
  "timestamp": "2025-10-11T14:32:45.123456Z",
  "prediction": {
    "result": "dangerous",
    "confidence": 0.9234,
    "model_type": "secured",
    "model_version": "1.0.0"
  },
  "image": {
    "hash_sha256": "a3d5f8e9b2c1..." # Preuve d'intégrité
  }
}
```

**Preuve** : Hash de l'image + timestamp + résultat = Preuve irréfutable

---

## 🔧 Configuration

### Paramètres du AuditLogger

```python
from src.monitoring.audit_logger import AuditLogger

# Configuration personnalisée
audit_logger = AuditLogger(
    log_dir="logs/audit",        # Répertoire des logs
    max_file_size_mb=100,         # Taille max avant rotation (MB)
    retention_days=90             # Durée de conservation (jours)
)
```

### Variables d'Environnement (Optionnel)

```bash
# .env
AUDIT_LOG_DIR=logs/audit
AUDIT_MAX_FILE_SIZE_MB=100
AUDIT_RETENTION_DAYS=90
AUDIT_ENABLE_EXPORT=true
```

---

## 📈 Monitoring et Alertes

### Métriques à Surveiller

1. **Taux d'attaques détectées**
   ```bash
   GET /audit/stats
   # Si attacks_detected > seuil → Alerte sécurité
   ```

2. **Taux de validations échouées**
   ```bash
   # Si > 10% → Possible attaque coordonnée
   ```

3. **Taille des logs**
   ```bash
   # Si croissance anormale → Enquête requise
   ```

### Intégration Grafana (À venir)

Dashboard Grafana avec :
- Graphique des prédictions par heure
- Graphique des attaques détectées
- Top 10 des IPs suspectes
- Taux de confiance moyen

---

## 🎓 Justification Académique

Ce système d'audit implémente les principes de l'architecture proposée :

### Zone 5 : Gouvernance et Surveillance ✅

| Principe | Implémentation |
|----------|----------------|
| **Logs centralisés** | ✅ Tous les logs dans `logs/audit/` |
| **Format structuré** | ✅ JSON Lines (JSONL) |
| **Immutabilité** | ✅ Append-only |
| **Traçabilité** | ✅ Audit ID + timestamp + hash |
| **Conformité** | ✅ RGPD (90 jours, pseudonymisation) |
| **Export** | ✅ JSON/CSV pour audits externes |

### Défense en Profondeur ✅

- **Zone 1** (Data) : Validation loggée
- **Zone 4** (Production) : Accès API loggés
- **Zone 5** (Gouvernance) : Audit complet

### Zero Trust ✅

- Tous les accès sont loggés (pas de confiance implicite)
- IP du client enregistrée
- User ID hashé (pseudonymisation)

---

## 📚 Références

- **Architecture proposée** : Section 3.1.2.5 - Zone 5 (Gouvernance)
- **RGPD** : Article 32 - Sécurité du traitement
- **ISO 27001** : Gestion des logs d'audit
- **NIST SP 800-92** : Guide to Computer Security Log Management

---

## 🚀 Prochaines Améliorations

1. **Authentification JWT** :
   - Remplacer `user_id="anonymous"` par vrai user authentifié
   - Ajouter `user_role` réel (agent/supervisor/admin)

2. **Signature numérique** :
   - Signer chaque log avec une clé privée
   - Vérification d'intégrité avec clé publique

3. **Blockchain pour immutabilité** :
   - Hash des logs dans une blockchain privée
   - Preuve cryptographique d'immuabilité

4. **Alertes en temps réel** :
   - Intégration PagerDuty/Slack
   - Alertes automatiques si > 5 attaques/minute

5. **Dashboard Grafana** :
   - Visualisation en temps réel
   - Dashboards par rôle utilisateur

---

## 🆘 Support et Contribution

**Documentation complète** : Ce fichier
**Tests** : `tests/test_audit_system.py`
**Code source** : `src/monitoring/audit_logger.py`
**API intégrée** : `src/api/app.py` (endpoints `/audit/*`)

Pour toute question ou contribution, consulter le README principal du projet.

---

**Version** : 1.0.0
**Date de création** : 11 octobre 2025
**Auteur** : Équipe Secure AI Detection
**Licence** : MIT
