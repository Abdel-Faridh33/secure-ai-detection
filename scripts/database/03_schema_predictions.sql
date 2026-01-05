-- =====================================================================
-- SCHEMA: Predictions History (Long-term Analytics)
-- Description: Historique long terme des prédictions pour analytics
--              au-delà de la rétention Prometheus (30 jours)
-- Date: 2025-12-16
-- =====================================================================

-- Table principale de l'historique des prédictions
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,

    -- Timestamps
    timestamp TIMESTAMPTZ NOT NULL,
    processing_time_ms FLOAT,

    -- Utilisateur
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    client_ip INET,

    -- Modèle
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    model_path TEXT,

    -- Image
    image_filename VARCHAR(255),
    image_hash VARCHAR(64) NOT NULL,  -- SHA-256 pour déduplication
    image_size_bytes BIGINT,

    -- Résultat de prédiction
    prediction_result VARCHAR(20) NOT NULL CHECK (prediction_result IN ('dangerous', 'safe')),
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    raw_logits JSONB,  -- Logits bruts du modèle pour analyse

    -- Attaque/Défense
    attack_detected BOOLEAN DEFAULT false,
    attack_type VARCHAR(50),
    defense_triggered BOOLEAN DEFAULT false,
    defense_type VARCHAR(50),

    -- Référence vers audit trail
    audit_id VARCHAR(20),  -- Lien vers audit_logs_index

    -- Métadonnées supplémentaires (flexible)
    metadata JSONB,

    -- Feedback utilisateur (pour amélioration continue)
    user_feedback VARCHAR(20) CHECK (user_feedback IN ('correct', 'incorrect', 'uncertain')),
    user_feedback_comment TEXT,
    user_feedback_at TIMESTAMPTZ,

    -- Indexation
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index principaux pour requêtes analytiques
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_user_id ON predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model_type ON predictions(model_type);
CREATE INDEX IF NOT EXISTS idx_predictions_model_version ON predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_predictions_result ON predictions(prediction_result);
CREATE INDEX IF NOT EXISTS idx_predictions_image_hash ON predictions(image_hash);
CREATE INDEX IF NOT EXISTS idx_predictions_attack_detected ON predictions(attack_detected) WHERE attack_detected = true;
CREATE INDEX IF NOT EXISTS idx_predictions_audit_id ON predictions(audit_id);

-- Index composite pour analytics fréquents
CREATE INDEX IF NOT EXISTS idx_predictions_model_timestamp ON predictions(model_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_user_timestamp ON predictions(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_result_timestamp ON predictions(prediction_result, timestamp DESC);

-- Index GIN pour recherche JSONB
CREATE INDEX IF NOT EXISTS idx_predictions_metadata ON predictions USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_predictions_logits ON predictions USING GIN (raw_logits);

-- Table des performances du modèle par période
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,

    -- Période
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    granularity VARCHAR(10) NOT NULL CHECK (granularity IN ('hour', 'day', 'week', 'month')),

    -- Modèle
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(20) NOT NULL,

    -- Métriques globales
    total_predictions INTEGER NOT NULL,
    avg_confidence FLOAT,
    avg_processing_time_ms FLOAT,

    -- Par classe
    dangerous_count INTEGER,
    dangerous_avg_confidence FLOAT,
    safe_count INTEGER,
    safe_avg_confidence FLOAT,

    -- Qualité
    low_confidence_count INTEGER,  -- confidence < 0.5
    high_confidence_count INTEGER,  -- confidence > 0.9

    -- Sécurité
    attacks_detected INTEGER DEFAULT 0,
    defenses_triggered INTEGER DEFAULT 0,

    -- Feedback utilisateur (si disponible)
    correct_predictions INTEGER DEFAULT 0,
    incorrect_predictions INTEGER DEFAULT 0,
    accuracy_rate FLOAT,  -- calculated from feedback

    -- Métadonnées
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(period_start, period_end, model_type, model_version)
);

-- Index pour récupération rapide des performances
CREATE INDEX IF NOT EXISTS idx_performance_period ON model_performance(period_start DESC, period_end DESC);
CREATE INDEX IF NOT EXISTS idx_performance_model ON model_performance(model_type, model_version);
CREATE INDEX IF NOT EXISTS idx_performance_granularity ON model_performance(granularity);

-- Table de comparaison des modèles
CREATE TABLE IF NOT EXISTS model_comparison (
    id SERIAL PRIMARY KEY,

    -- Période de comparaison
    comparison_date DATE NOT NULL,

    -- Modèle A (baseline)
    model_a_type VARCHAR(50) NOT NULL,
    model_a_version VARCHAR(20) NOT NULL,
    model_a_predictions INTEGER,
    model_a_avg_confidence FLOAT,
    model_a_accuracy FLOAT,

    -- Modèle B (secured)
    model_b_type VARCHAR(50) NOT NULL,
    model_b_version VARCHAR(20) NOT NULL,
    model_b_predictions INTEGER,
    model_b_avg_confidence FLOAT,
    model_b_accuracy FLOAT,

    -- Delta
    confidence_delta FLOAT,  -- B - A
    accuracy_delta FLOAT,    -- B - A

    -- Robustesse
    model_a_attacks_survived INTEGER,
    model_b_attacks_survived INTEGER,
    robustness_delta FLOAT,

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(comparison_date, model_a_type, model_b_type)
);

-- Index pour comparaisons
CREATE INDEX IF NOT EXISTS idx_comparison_date ON model_comparison(comparison_date DESC);

-- Table des images uniques (déduplication)
CREATE TABLE IF NOT EXISTS unique_images (
    image_hash VARCHAR(64) PRIMARY KEY,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    total_predictions INTEGER DEFAULT 1,

    -- Statistiques
    dangerous_predictions INTEGER DEFAULT 0,
    safe_predictions INTEGER DEFAULT 0,

    -- Consensus
    consensus_result VARCHAR(20),  -- Résultat majoritaire
    consensus_confidence FLOAT,     -- Confiance moyenne

    -- Métadonnées
    avg_size_bytes BIGINT,
    common_filename VARCHAR(255),

    -- Anomalies
    is_suspicious BOOLEAN DEFAULT false,  -- Résultats contradictoires
    suspicion_reason TEXT
);

-- Index pour analyse des images
CREATE INDEX IF NOT EXISTS idx_unique_images_last_seen ON unique_images(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_unique_images_total_preds ON unique_images(total_predictions DESC);
CREATE INDEX IF NOT EXISTS idx_unique_images_suspicious ON unique_images(is_suspicious) WHERE is_suspicious = true;

-- Fonction pour calculer les performances d'un modèle
CREATE OR REPLACE FUNCTION calculate_model_performance(
    p_model_type VARCHAR,
    p_model_version VARCHAR,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ,
    p_granularity VARCHAR
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO model_performance (
        period_start,
        period_end,
        granularity,
        model_type,
        model_version,
        total_predictions,
        avg_confidence,
        avg_processing_time_ms,
        dangerous_count,
        dangerous_avg_confidence,
        safe_count,
        safe_avg_confidence,
        low_confidence_count,
        high_confidence_count,
        attacks_detected,
        defenses_triggered,
        correct_predictions,
        incorrect_predictions,
        accuracy_rate
    )
    SELECT
        p_start_time,
        p_end_time,
        p_granularity,
        p_model_type,
        p_model_version,
        COUNT(*),
        AVG(confidence),
        AVG(processing_time_ms),
        COUNT(*) FILTER (WHERE prediction_result = 'dangerous'),
        AVG(confidence) FILTER (WHERE prediction_result = 'dangerous'),
        COUNT(*) FILTER (WHERE prediction_result = 'safe'),
        AVG(confidence) FILTER (WHERE prediction_result = 'safe'),
        COUNT(*) FILTER (WHERE confidence < 0.5),
        COUNT(*) FILTER (WHERE confidence > 0.9),
        COUNT(*) FILTER (WHERE attack_detected = true),
        COUNT(*) FILTER (WHERE defense_triggered = true),
        COUNT(*) FILTER (WHERE user_feedback = 'correct'),
        COUNT(*) FILTER (WHERE user_feedback = 'incorrect'),
        CASE
            WHEN COUNT(*) FILTER (WHERE user_feedback IS NOT NULL) > 0
            THEN COUNT(*) FILTER (WHERE user_feedback = 'correct')::FLOAT /
                 COUNT(*) FILTER (WHERE user_feedback IS NOT NULL)
            ELSE NULL
        END
    FROM predictions
    WHERE model_type = p_model_type
        AND model_version = p_model_version
        AND timestamp BETWEEN p_start_time AND p_end_time
    ON CONFLICT (period_start, period_end, model_type, model_version) DO UPDATE SET
        total_predictions = EXCLUDED.total_predictions,
        avg_confidence = EXCLUDED.avg_confidence,
        avg_processing_time_ms = EXCLUDED.avg_processing_time_ms,
        dangerous_count = EXCLUDED.dangerous_count,
        dangerous_avg_confidence = EXCLUDED.dangerous_avg_confidence,
        safe_count = EXCLUDED.safe_count,
        safe_avg_confidence = EXCLUDED.safe_avg_confidence,
        low_confidence_count = EXCLUDED.low_confidence_count,
        high_confidence_count = EXCLUDED.high_confidence_count,
        attacks_detected = EXCLUDED.attacks_detected,
        defenses_triggered = EXCLUDED.defenses_triggered,
        correct_predictions = EXCLUDED.correct_predictions,
        incorrect_predictions = EXCLUDED.incorrect_predictions,
        accuracy_rate = EXCLUDED.accuracy_rate,
        calculated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Fonction pour mettre à jour les stats d'image unique
CREATE OR REPLACE FUNCTION update_unique_image_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO unique_images (
        image_hash,
        first_seen,
        last_seen,
        total_predictions,
        dangerous_predictions,
        safe_predictions
    ) VALUES (
        NEW.image_hash,
        NEW.timestamp,
        NEW.timestamp,
        1,
        CASE WHEN NEW.prediction_result = 'dangerous' THEN 1 ELSE 0 END,
        CASE WHEN NEW.prediction_result = 'safe' THEN 1 ELSE 0 END
    )
    ON CONFLICT (image_hash) DO UPDATE SET
        last_seen = NEW.timestamp,
        total_predictions = unique_images.total_predictions + 1,
        dangerous_predictions = unique_images.dangerous_predictions +
            CASE WHEN NEW.prediction_result = 'dangerous' THEN 1 ELSE 0 END,
        safe_predictions = unique_images.safe_predictions +
            CASE WHEN NEW.prediction_result = 'safe' THEN 1 ELSE 0 END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour mise à jour automatique des stats d'images
CREATE TRIGGER update_image_stats_trigger
    AFTER INSERT ON predictions
    FOR EACH ROW
    EXECUTE FUNCTION update_unique_image_stats();

-- Vue pour les prédictions récentes avec détails utilisateur
CREATE OR REPLACE VIEW predictions_with_user AS
SELECT
    p.id,
    p.timestamp,
    u.username,
    u.role,
    p.model_type,
    p.model_version,
    p.image_filename,
    p.prediction_result,
    p.confidence,
    p.processing_time_ms,
    p.attack_detected,
    p.user_feedback
FROM predictions p
LEFT JOIN users u ON p.user_id = u.id
ORDER BY p.timestamp DESC;

-- Vue pour analyse de drift du modèle
CREATE OR REPLACE VIEW model_drift_analysis AS
SELECT
    DATE(timestamp) as date,
    model_type,
    model_version,
    AVG(confidence) as avg_confidence,
    STDDEV(confidence) as stddev_confidence,
    COUNT(*) FILTER (WHERE confidence < 0.5) as low_confidence_count,
    COUNT(*) as total_predictions,
    COUNT(*) FILTER (WHERE attack_detected = true) as attacks_count
FROM predictions
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), model_type, model_version
ORDER BY date DESC, model_type;

-- Commentaires pour documentation
COMMENT ON TABLE predictions IS 'Historique long terme des prédictions pour analytics (au-delà de Prometheus 30j)';
COMMENT ON TABLE model_performance IS 'Métriques de performance des modèles agrégées par période';
COMMENT ON TABLE model_comparison IS 'Comparaisons A/B entre modèles baseline et secured';
COMMENT ON TABLE unique_images IS 'Déduplication et statistiques des images uniques';

COMMENT ON VIEW predictions_with_user IS 'Prédictions avec détails utilisateur joints';
COMMENT ON VIEW model_drift_analysis IS 'Analyse de drift du modèle (30 derniers jours)';
