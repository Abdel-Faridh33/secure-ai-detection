-- Secure AI Detection System - Schema PostgreSQL Zone 5
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS predictions (
    id                      SERIAL PRIMARY KEY,
    audit_id                VARCHAR(50)  NOT NULL UNIQUE,
    timestamp               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    user_id_hash            VARCHAR(64),
    user_role               VARCHAR(20),
    client_ip               VARCHAR(45),
    image_filename          VARCHAR(255),
    image_hash_sha256       VARCHAR(64)  NOT NULL,
    image_size_bytes        INTEGER,
    model_type              VARCHAR(50)  NOT NULL DEFAULT 'secured',
    model_version           VARCHAR(20),
    prediction_result       VARCHAR(20)  NOT NULL,
    confidence              FLOAT        NOT NULL,
    processing_time_ms      FLOAT,
    adversarial_flagged     BOOLEAN      DEFAULT FALSE,
    adversarial_noise_score FLOAT,
    jsonl_file              VARCHAR(255),
    jsonl_line_number       INTEGER,
    created_at              TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pred_timestamp ON predictions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_pred_result    ON predictions(prediction_result);
CREATE INDEX IF NOT EXISTS idx_pred_ip        ON predictions(client_ip);

CREATE TABLE IF NOT EXISTS security_events (
    id           SERIAL PRIMARY KEY,
    audit_id     VARCHAR(50)  NOT NULL UNIQUE,
    timestamp    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    event_type   VARCHAR(50)  NOT NULL,
    severity     VARCHAR(30)  NOT NULL,
    description  TEXT,
    user_id_hash VARCHAR(64),
    client_ip    VARCHAR(45),
    metadata     JSONB,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sec_timestamp ON security_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sec_type      ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_sec_severity  ON security_events(severity);

CREATE TABLE IF NOT EXISTS api_access_logs (
    id               SERIAL PRIMARY KEY,
    audit_id         VARCHAR(50)  NOT NULL UNIQUE,
    timestamp        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    endpoint         VARCHAR(255) NOT NULL,
    method           VARCHAR(10)  NOT NULL,
    status_code      INTEGER      NOT NULL,
    response_time_ms FLOAT,
    user_id_hash     VARCHAR(64),
    client_ip        VARCHAR(45),
    created_at       TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_timestamp ON api_access_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_endpoint  ON api_access_logs(endpoint);

CREATE TABLE IF NOT EXISTS model_integrity_checks (
    id              SERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    model_name      VARCHAR(255) NOT NULL,
    model_hash      VARCHAR(64),
    signature_valid BOOLEAN,
    algorithm       VARCHAR(50)  DEFAULT 'RSA-4096-PSS-SHA256',
    zone            VARCHAR(10)  DEFAULT 'Zone2',
    notes           TEXT
);

CREATE OR REPLACE VIEW daily_prediction_stats AS
SELECT DATE_TRUNC('day', timestamp) AS day,
    COUNT(*) AS total_predictions,
    SUM(CASE WHEN prediction_result = 'dangerous' THEN 1 ELSE 0 END) AS dangerous_count,
    SUM(CASE WHEN prediction_result = 'safe' THEN 1 ELSE 0 END) AS safe_count,
    ROUND(AVG(confidence)::NUMERIC, 4) AS avg_confidence,
    ROUND(AVG(processing_time_ms)::NUMERIC, 2) AS avg_processing_ms,
    SUM(CASE WHEN adversarial_flagged THEN 1 ELSE 0 END) AS adversarial_flagged_count
FROM predictions GROUP BY DATE_TRUNC('day', timestamp) ORDER BY day DESC;

INSERT INTO model_integrity_checks (model_name, notes)
VALUES ('schema_init', 'DB initialisee - Secure AI Detection System')
ON CONFLICT DO NOTHING;

-- ──────────────────────────────────────────────────────────────────
-- Gestion des utilisateurs (Zone 4 – RBAC)
-- ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id                    SERIAL PRIMARY KEY,
    username              VARCHAR(50)  NOT NULL UNIQUE,
    password_hash         VARCHAR(255) NOT NULL,
    role                  VARCHAR(20)  NOT NULL DEFAULT 'guest'
                              CHECK (role IN ('admin', 'agent', 'guest')),
    email                 VARCHAR(255),
    full_name             VARCHAR(255),
    is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
    is_locked             BOOLEAN      NOT NULL DEFAULT FALSE,
    failed_login_attempts INTEGER      NOT NULL DEFAULT 0,
    created_by            INTEGER,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_by            INTEGER,
    last_login            TIMESTAMPTZ,
    last_password_change  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role     ON users(role);

-- Historique de connexion (verrouillage après 5 échecs)
CREATE TABLE IF NOT EXISTS login_history (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ip_address     VARCHAR(45),
    user_agent     TEXT,
    success        BOOLEAN     NOT NULL,
    failure_reason VARCHAR(255),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_login_user_id    ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_created_at ON login_history(created_at DESC);

-- Sessions JWT actives (révocation possible)
CREATE TABLE IF NOT EXISTS active_sessions (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti      VARCHAR(255) NOT NULL UNIQUE,
    expires_at     TIMESTAMPTZ  NOT NULL,
    ip_address     VARCHAR(45),
    user_agent     TEXT,
    is_revoked     BOOLEAN      NOT NULL DEFAULT FALSE,
    revoked_at     TIMESTAMPTZ,
    revoked_reason VARCHAR(255),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_jti     ON active_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON active_sessions(user_id);

-- Nettoyage automatique des sessions expirées
CREATE OR REPLACE FUNCTION cleanup_expired_sessions() RETURNS INTEGER AS $$
DECLARE deleted_count INTEGER;
BEGIN
    DELETE FROM active_sessions WHERE expires_at < NOW() AND is_revoked = FALSE;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
