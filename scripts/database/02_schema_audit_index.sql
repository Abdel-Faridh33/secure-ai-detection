-- =====================================================================
-- SCHEMA: Audit Logs Index (Fast Search)
-- Description: Index des logs d'audit pour recherche rapide tout en
--              conservant les logs JSONL immuables pour conformité RGPD
-- Date: 2025-12-16
-- =====================================================================

-- Table d'index des logs d'audit
-- Note: Les logs complets restent dans les fichiers JSONL
--       Cette table sert uniquement d'index pour recherche rapide
CREATE TABLE IF NOT EXISTS audit_logs_index (
    -- Identifiant unique du log (même que dans JSONL)
    audit_id VARCHAR(20) PRIMARY KEY,

    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- prediction, attack_detected, validation_failed, etc.
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),

    -- Utilisateur (hashé pour RGPD)
    user_id_hash VARCHAR(64),
    user_role VARCHAR(20),
    client_ip INET,  -- Type INET pour stocker IPv4/IPv6

    -- Image
    image_filename VARCHAR(255),
    image_hash VARCHAR(64),  -- SHA-256
    image_size_bytes BIGINT,

    -- Prédiction
    model_type VARCHAR(50),
    model_version VARCHAR(20),
    prediction_result VARCHAR(20),  -- dangerous, safe
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
    processing_time_ms FLOAT,

    -- Sécurité
    attack_type VARCHAR(50),  -- NULL si pas d'attaque
    defense_triggered BOOLEAN DEFAULT false,

    -- Référence vers le fichier JSONL source (pour récupération complète)
    jsonl_file VARCHAR(255) NOT NULL,  -- Ex: audit_2025-12-16.jsonl
    jsonl_line_number INTEGER NOT NULL,

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour recherche ultra-rapide
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs_index(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs_index(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_logs_index(severity);
CREATE INDEX IF NOT EXISTS idx_audit_user_hash ON audit_logs_index(user_id_hash);
CREATE INDEX IF NOT EXISTS idx_audit_user_role ON audit_logs_index(user_role);
CREATE INDEX IF NOT EXISTS idx_audit_image_hash ON audit_logs_index(image_hash);
CREATE INDEX IF NOT EXISTS idx_audit_model_type ON audit_logs_index(model_type);
CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_logs_index(prediction_result);
CREATE INDEX IF NOT EXISTS idx_audit_attack_type ON audit_logs_index(attack_type) WHERE attack_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_defense_triggered ON audit_logs_index(defense_triggered) WHERE defense_triggered = true;

-- Index composite pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_audit_timestamp_event ON audit_logs_index(timestamp DESC, event_type);
CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_logs_index(user_id_hash, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_model_timestamp ON audit_logs_index(model_type, timestamp DESC);

-- Table des statistiques pré-calculées (pour dashboards)
CREATE TABLE IF NOT EXISTS audit_stats_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,

    -- Compteurs globaux
    total_predictions INTEGER DEFAULT 0,
    total_attacks_detected INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,

    -- Par type de résultat
    dangerous_count INTEGER DEFAULT 0,
    safe_count INTEGER DEFAULT 0,

    -- Par modèle
    baseline_predictions INTEGER DEFAULT 0,
    secured_predictions INTEGER DEFAULT 0,

    -- Métriques de performance
    avg_processing_time_ms FLOAT,
    avg_confidence FLOAT,

    -- Sécurité
    unique_attack_types TEXT[],  -- Array des types d'attaques détectées
    defense_activation_count INTEGER DEFAULT 0,

    -- Métadonnées
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour récupération rapide des stats
CREATE INDEX IF NOT EXISTS idx_audit_stats_date ON audit_stats_daily(date DESC);

-- Table pour le tracking des anomalies détectées
CREATE TABLE IF NOT EXISTS detected_anomalies (
    id SERIAL PRIMARY KEY,
    audit_id VARCHAR(20) REFERENCES audit_logs_index(audit_id) ON DELETE CASCADE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),

    -- Type d'anomalie
    anomaly_type VARCHAR(50) NOT NULL,  -- rate_limit, suspicious_pattern, model_drift, etc.
    severity VARCHAR(10) NOT NULL,
    score FLOAT,  -- Score d'anomalie (0-1)

    -- Détails
    description TEXT,
    metadata JSONB,  -- Données supplémentaires flexibles

    -- Actions
    action_taken VARCHAR(50),  -- blocked, logged, alerted, etc.
    is_false_positive BOOLEAN DEFAULT NULL,  -- NULL = non vérifié
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMPTZ
);

-- Index pour analyse des anomalies
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON detected_anomalies(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON detected_anomalies(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON detected_anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_false_positive ON detected_anomalies(is_false_positive);

-- Fonction pour mettre à jour les stats quotidiennes
CREATE OR REPLACE FUNCTION update_daily_stats(target_date DATE)
RETURNS VOID AS $$
BEGIN
    INSERT INTO audit_stats_daily (
        date,
        total_predictions,
        total_attacks_detected,
        total_errors,
        dangerous_count,
        safe_count,
        baseline_predictions,
        secured_predictions,
        avg_processing_time_ms,
        avg_confidence,
        unique_attack_types,
        defense_activation_count
    )
    SELECT
        target_date,
        COUNT(*) FILTER (WHERE event_type = 'prediction'),
        COUNT(*) FILTER (WHERE attack_type IS NOT NULL),
        COUNT(*) FILTER (WHERE severity IN ('error', 'critical')),
        COUNT(*) FILTER (WHERE prediction_result = 'dangerous'),
        COUNT(*) FILTER (WHERE prediction_result = 'safe'),
        COUNT(*) FILTER (WHERE model_type = 'baseline'),
        COUNT(*) FILTER (WHERE model_type LIKE 'secured%'),
        AVG(processing_time_ms),
        AVG(confidence),
        ARRAY_AGG(DISTINCT attack_type) FILTER (WHERE attack_type IS NOT NULL),
        COUNT(*) FILTER (WHERE defense_triggered = true)
    FROM audit_logs_index
    WHERE DATE(timestamp) = target_date
    ON CONFLICT (date) DO UPDATE SET
        total_predictions = EXCLUDED.total_predictions,
        total_attacks_detected = EXCLUDED.total_attacks_detected,
        total_errors = EXCLUDED.total_errors,
        dangerous_count = EXCLUDED.dangerous_count,
        safe_count = EXCLUDED.safe_count,
        baseline_predictions = EXCLUDED.baseline_predictions,
        secured_predictions = EXCLUDED.secured_predictions,
        avg_processing_time_ms = EXCLUDED.avg_processing_time_ms,
        avg_confidence = EXCLUDED.avg_confidence,
        unique_attack_types = EXCLUDED.unique_attack_types,
        defense_activation_count = EXCLUDED.defense_activation_count,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql;

-- Vue pour les recherches fréquentes (predictions récentes)
CREATE OR REPLACE VIEW recent_predictions AS
SELECT
    audit_id,
    timestamp,
    user_role,
    image_filename,
    model_type,
    prediction_result,
    confidence,
    processing_time_ms,
    attack_type IS NOT NULL as had_attack
FROM audit_logs_index
WHERE event_type = 'prediction'
    AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Vue pour les incidents de sécurité
CREATE OR REPLACE VIEW security_incidents AS
SELECT
    audit_id,
    timestamp,
    user_id_hash,
    client_ip,
    attack_type,
    defense_triggered,
    image_hash,
    jsonl_file,
    jsonl_line_number
FROM audit_logs_index
WHERE attack_type IS NOT NULL
    OR severity IN ('error', 'critical')
ORDER BY timestamp DESC;

-- Commentaires pour documentation
COMMENT ON TABLE audit_logs_index IS 'Index des logs d''audit pour recherche rapide (logs complets dans JSONL)';
COMMENT ON COLUMN audit_logs_index.jsonl_file IS 'Fichier JSONL source pour récupération du log complet';
COMMENT ON COLUMN audit_logs_index.jsonl_line_number IS 'Numéro de ligne dans le fichier JSONL';

COMMENT ON TABLE audit_stats_daily IS 'Statistiques quotidiennes pré-calculées pour dashboards';
COMMENT ON TABLE detected_anomalies IS 'Anomalies détectées par le système de monitoring';

COMMENT ON VIEW recent_predictions IS 'Vue des prédictions des dernières 24h';
COMMENT ON VIEW security_incidents IS 'Vue de tous les incidents de sécurité';
