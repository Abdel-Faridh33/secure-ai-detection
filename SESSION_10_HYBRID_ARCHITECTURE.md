# 🗄️ SESSION 10 - Architecture Hybride de Stockage

**Date :** 16 décembre 2025
**Durée :** En cours
**Objectif :** Implémenter une architecture hybride optimale combinant PostgreSQL et stockage fichier
**Status :** 🔄 EN COURS

---

## 📊 Contexte et Analyse

### Situation Actuelle

**Configuration existante :**
- PostgreSQL et Redis configurés dans Docker mais **NON UTILISÉS**
- Stockage principal : fichiers JSON/JSONL
- Base de données : `ai_metrics` (vide)
- Credentials : Hardcodés dans `launch_web.py`

**Problèmes Identifiés :**

1. **🔒 Sécurité** : Credentials en dur dans le code
   ```python
   # launch_web.py
   VALID_USERS = {
       "admin": "admin123",
       "operator": "operator456",
       "agent": "agent789"
   }
   ```

2. **⚡ Performance** : Recherche logs non optimisée
   - Parcours linéaire de tous les fichiers JSONL
   - Pas d'index pour requêtes complexes
   - Lenteur sur millions de logs

3. **📈 Analytics** : Pas d'historique exploitable
   - Prometheus garde seulement 30 jours
   - Impossible d'analyser plusieurs mois
   - Pas de rapports personnalisés SQL

---

## 🎯 Architecture Hybride Proposée

```
┌─────────────────────────────────────────────────────────────┐
│              ARCHITECTURE HYBRIDE OPTIMALE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📦 PostgreSQL (Données Structurées + Index)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ users                  (auth + RBAC)             │   │
│  │ ✅ audit_logs_index       (recherche rapide)        │   │
│  │ ✅ predictions            (historique illimité)     │   │
│  │ ⚪ image_annotations      (optionnel si >100k)      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  📁 Stockage Fichier (Immuabilité + Performance)            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ logs/*.jsonl           (conformité RGPD)         │   │
│  │ ✅ models/*.pth           (modèles PyTorch)         │   │
│  │ ✅ data/images/*          (filesystem optimisé)     │   │
│  │ ✅ results/*.json         (expériences ML)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  📊 Prometheus + Loki (Métriques Temps Réel)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ Métriques temps réel   (rétention 30j)           │   │
│  │ ✅ Alertes automatiques                             │   │
│  │ ✅ Dashboards Grafana                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Plan d'Implémentation

### Phase 1 : Schémas SQL ⏳

**Fichiers à créer :**
- `scripts/database/01_schema_users.sql`
- `scripts/database/02_schema_audit_index.sql`
- `scripts/database/03_schema_predictions.sql`
- `scripts/database/04_initial_data.sql`

**Tables :**

1. **users** - Authentification + RBAC
   ```sql
   CREATE TABLE users (
       id SERIAL PRIMARY KEY,
       username VARCHAR(50) UNIQUE NOT NULL,
       password_hash VARCHAR(255) NOT NULL,
       role VARCHAR(20) NOT NULL,
       created_at TIMESTAMPTZ DEFAULT NOW(),
       last_login TIMESTAMPTZ,
       is_active BOOLEAN DEFAULT true
   );
   ```

2. **audit_logs_index** - Index pour recherche rapide
   ```sql
   CREATE TABLE audit_logs_index (
       audit_id VARCHAR(20) PRIMARY KEY,
       timestamp TIMESTAMPTZ NOT NULL,
       event_type VARCHAR(50) NOT NULL,
       user_id_hash VARCHAR(64),
       image_hash VARCHAR(64),
       result VARCHAR(20),
       confidence FLOAT,
       jsonl_file VARCHAR(255),
       jsonl_line_number INTEGER
   );
   -- Index pour recherche rapide
   CREATE INDEX idx_timestamp ON audit_logs_index(timestamp);
   CREATE INDEX idx_event_type ON audit_logs_index(event_type);
   CREATE INDEX idx_user_hash ON audit_logs_index(user_id_hash);
   ```

3. **predictions** - Historique long terme
   ```sql
   CREATE TABLE predictions (
       id SERIAL PRIMARY KEY,
       timestamp TIMESTAMPTZ NOT NULL,
       user_id INTEGER REFERENCES users(id),
       model_version VARCHAR(20),
       result VARCHAR(20),
       confidence FLOAT,
       processing_time_ms FLOAT,
       image_hash VARCHAR(64),
       audit_id VARCHAR(20) REFERENCES audit_logs_index(audit_id)
   );
   ```

### Phase 2 : Modules Python ⏳

**Fichiers à créer :**
- `src/database/__init__.py`
- `src/database/connection.py`
- `src/database/user_manager.py`
- `src/database/prediction_logger.py`

**Fichiers à modifier :**
- `src/monitoring/audit_logger.py` (double écriture)
- `src/api/app.py` (auth PostgreSQL)
- `launch_web.py` (auth PostgreSQL)

### Phase 3 : Scripts d'Initialisation ⏳

**Fichiers à créer :**
- `scripts/init_database.py` - Initialisation complète
- `scripts/migrate_users.py` - Migration utilisateurs hardcodés
- `docker/postgres/init.sql` - Init auto au démarrage

### Phase 4 : Tests ⏳

**Fichiers à créer :**
- `tests/test_user_manager.py`
- `tests/test_hybrid_storage.py`
- `tests/test_audit_indexing.py`

---

## ✨ Avantages de l'Architecture Hybride

### 🔒 Sécurité

| Avant | Après |
|-------|-------|
| Mots de passe en clair | Hachage bcrypt |
| Users hardcodés | DB dynamique |
| Pas de gestion des rôles | RBAC complet |

### ⚡ Performance

| Opération | Avant | Après |
|-----------|-------|-------|
| Recherche 1M logs | ~30s | ~0.3s (100x) |
| Filtrage par date | Parcours complet | Index SQL |
| Agrégations | Impossible | SQL natif |

### 📊 Analytics

| Capacité | Avant | Après |
|----------|-------|-------|
| Historique | 30 jours | Illimité |
| Rapports SQL | Non | Oui |
| Trend analysis | Non | Oui |

### ⚖️ Conformité

| Aspect | Statut |
|--------|--------|
| Logs JSONL immuables | ✅ Conservés |
| Traçabilité | ✅ Améliorée (double) |
| RGPD | ✅ Conforme |
| Audit trail | ✅ Renforcé |

---

## 📋 État d'Avancement

- [x] Analyse architecture actuelle
- [x] Identification problèmes
- [x] Conception architecture hybride
- [x] Planification phases
- [ ] Création schémas SQL
- [ ] Développement modules Python
- [ ] Migration authentification
- [ ] Tests et validation

---

## 🎓 Leçons Apprises

### Pourquoi Hybride ?

**PostgreSQL excelle pour :**
- ✅ Données structurées relationnelles
- ✅ Recherches complexes avec index
- ✅ Transactions ACID
- ✅ Rapports SQL

**Fichiers excellent pour :**
- ✅ Logs immuables (append-only)
- ✅ Modèles ML (binaires volumineux)
- ✅ Images (filesystem optimisé)
- ✅ Conformité légale (audit trail)

**Le meilleur des deux mondes** = Architecture hybride ! 🎯

---

*Prochaines étapes : Création des schémas SQL et implémentation des modules Python de gestion utilisateurs et d'indexation des logs.*
