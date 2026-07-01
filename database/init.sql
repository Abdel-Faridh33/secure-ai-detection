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
