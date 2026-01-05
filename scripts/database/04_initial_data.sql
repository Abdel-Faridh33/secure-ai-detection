-- =====================================================================
-- INITIAL DATA: Permissions RBAC & Utilisateurs par défaut
-- Description: Données initiales pour démarrage du système
--              - Permissions RBAC par rôle
--              - Utilisateurs par défaut (migration de launch_web.py)
-- Date: 2025-12-16
-- =====================================================================

-- =====================================================================
-- 1. PERMISSIONS RBAC PAR RÔLE
-- =====================================================================

-- Rôle: VIEWER (Consultation seulement)
INSERT INTO role_permissions (role, resource, action) VALUES
    ('viewer', 'predictions', 'read'),
    ('viewer', 'audit_logs', 'read'),
    ('viewer', 'dashboard', 'read')
ON CONFLICT DO NOTHING;

-- Rôle: AGENT (Utilisation du système + consultation)
INSERT INTO role_permissions (role, resource, action) VALUES
    ('agent', 'predictions', 'read'),
    ('agent', 'predictions', 'create'),  -- Peut faire des prédictions
    ('agent', 'audit_logs', 'read'),
    ('agent', 'dashboard', 'read'),
    ('agent', 'images', 'upload'),
    ('agent', 'feedback', 'create')  -- Peut donner du feedback
ON CONFLICT DO NOTHING;

-- Rôle: OPERATOR (Opérations + monitoring)
INSERT INTO role_permissions (role, resource, action) VALUES
    ('operator', 'predictions', 'read'),
    ('operator', 'predictions', 'create'),
    ('operator', 'audit_logs', 'read'),
    ('operator', 'audit_logs', 'export'),  -- Peut exporter les logs
    ('operator', 'dashboard', 'read'),
    ('operator', 'dashboard', 'admin'),    -- Accès dashboards avancés
    ('operator', 'images', 'upload'),
    ('operator', 'models', 'read'),
    ('operator', 'models', 'switch'),      -- Peut changer de modèle
    ('operator', 'feedback', 'create'),
    ('operator', 'feedback', 'read'),      -- Peut voir tous les feedbacks
    ('operator', 'anomalies', 'read'),
    ('operator', 'anomalies', 'verify')    -- Peut marquer false positives
ON CONFLICT DO NOTHING;

-- Rôle: ADMIN (Tous les droits)
INSERT INTO role_permissions (role, resource, action) VALUES
    ('admin', 'predictions', 'read'),
    ('admin', 'predictions', 'create'),
    ('admin', 'predictions', 'delete'),
    ('admin', 'audit_logs', 'read'),
    ('admin', 'audit_logs', 'export'),
    ('admin', 'audit_logs', 'admin'),
    ('admin', 'dashboard', 'read'),
    ('admin', 'dashboard', 'admin'),
    ('admin', 'images', 'upload'),
    ('admin', 'images', 'delete'),
    ('admin', 'models', 'read'),
    ('admin', 'models', 'write'),
    ('admin', 'models', 'switch'),
    ('admin', 'models', 'delete'),
    ('admin', 'users', 'read'),
    ('admin', 'users', 'create'),
    ('admin', 'users', 'update'),
    ('admin', 'users', 'delete'),
    ('admin', 'feedback', 'read'),
    ('admin', 'feedback', 'create'),
    ('admin', 'feedback', 'delete'),
    ('admin', 'anomalies', 'read'),
    ('admin', 'anomalies', 'verify'),
    ('admin', 'anomalies', 'delete'),
    ('admin', 'system', 'admin')
ON CONFLICT DO NOTHING;

-- =====================================================================
-- 2. UTILISATEURS PAR DÉFAUT (Migration de launch_web.py)
-- =====================================================================

-- NOTE: Les mots de passe sont hashés avec bcrypt
-- Format: bcrypt hash de "admin123", "operator456", "agent789"
-- En production, ces utilisateurs doivent être changés IMMÉDIATEMENT

-- Utilisateur: admin
-- Password: admin123
-- Hash bcrypt généré avec: bcrypt.hashpw(b"admin123", bcrypt.gensalt())
INSERT INTO users (
    username,
    password_hash,
    role,
    email,
    full_name,
    is_active,
    created_at
) VALUES (
    'admin',
    '$2b$12$EyAdRO4qWIYgLdfQwCuIa.b.Ug8clpuU5BmxIWFU8GFXJJD9cxiGm',  -- admin123
    'admin',
    'admin@secure-ai-detection.local',
    'System Administrator',
    true,
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- Utilisateur: operator
-- Password: operator456
INSERT INTO users (
    username,
    password_hash,
    role,
    email,
    full_name,
    is_active,
    created_at
) VALUES (
    'operator',
    '$2b$12$Sp0Yf.JWPN0TJOG3iV5qze3wI9oU8C/3sIxpc53wMPANiL/G2xwOW',  -- operator456
    'operator',
    'operator@secure-ai-detection.local',
    'System Operator',
    true,
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- Utilisateur: agent
-- Password: agent789
INSERT INTO users (
    username,
    password_hash,
    role,
    email,
    full_name,
    is_active,
    created_at
) VALUES (
    'agent',
    '$2b$12$KwQpZ0Utahln96ULCofzGO3VIJVb2IfAcELjoFRqVZiK46yzU8FCO',  -- agent789
    'agent',
    'agent@secure-ai-detection.local',
    'Detection Agent',
    true,
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- =====================================================================
-- 3. CONFIGURATION SYSTÈME
-- =====================================================================

-- Table de configuration (pour paramètres système)
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id)
);

-- Configuration initiale
INSERT INTO system_config (key, value, description) VALUES
    ('db_version', '1.0.0', 'Version du schéma de base de données'),
    ('migration_date', NOW()::TEXT, 'Date de création de la base'),
    ('audit_retention_days', '90', 'Rétention des logs d''audit (jours)'),
    ('session_retention_days', '7', 'Rétention des sessions expirées (jours)'),
    ('max_failed_login_attempts', '5', 'Tentatives de connexion avant verrouillage'),
    ('password_min_length', '8', 'Longueur minimale des mots de passe'),
    ('jwt_expiry_minutes', '60', 'Durée de validité des tokens JWT (minutes)'),
    ('cleanup_enabled', 'true', 'Nettoyage automatique activé'),
    ('monitoring_enabled', 'true', 'Monitoring activé')
ON CONFLICT DO NOTHING;

-- =====================================================================
-- 4. VÉRIFICATIONS ET LOGS
-- =====================================================================

-- Afficher le résumé de l'initialisation
DO $$
DECLARE
    user_count INTEGER;
    perm_count INTEGER;
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO perm_count FROM role_permissions;
    SELECT COUNT(*) INTO config_count FROM system_config;

    RAISE NOTICE '=================================================';
    RAISE NOTICE 'INITIALISATION DE LA BASE DE DONNÉES COMPLÉTÉE';
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'Utilisateurs créés: %', user_count;
    RAISE NOTICE 'Permissions RBAC: %', perm_count;
    RAISE NOTICE 'Paramètres système: %', config_count;
    RAISE NOTICE '';
    RAISE NOTICE 'ATTENTION: Changez les mots de passe par défaut !';
    RAISE NOTICE '  - admin:admin123';
    RAISE NOTICE '  - operator:operator456';
    RAISE NOTICE '  - agent:agent789';
    RAISE NOTICE '=================================================';
END $$;

-- =====================================================================
-- 5. PROCÉDURES DE MAINTENANCE
-- =====================================================================

-- Procédure pour nettoyer les données anciennes
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS TABLE(
    sessions_deleted INTEGER,
    login_history_deleted INTEGER,
    predictions_archived INTEGER
) AS $$
DECLARE
    v_sessions_deleted INTEGER;
    v_login_deleted INTEGER;
    v_predictions_archived INTEGER;
    v_retention_days INTEGER;
BEGIN
    -- Récupérer la configuration de rétention
    SELECT value::INTEGER INTO v_retention_days
    FROM system_config WHERE key = 'audit_retention_days';

    -- Nettoyer les sessions expirées
    DELETE FROM active_sessions
    WHERE expires_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS v_sessions_deleted = ROW_COUNT;

    -- Nettoyer l'historique de connexion ancien
    DELETE FROM login_history
    WHERE login_time < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS v_login_deleted = ROW_COUNT;

    -- Pour les prédictions, on ne les supprime pas mais on peut
    -- les archiver dans une table séparée si nécessaire
    v_predictions_archived := 0;

    RETURN QUERY SELECT v_sessions_deleted, v_login_deleted, v_predictions_archived;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_data IS 'Nettoyage automatique des données anciennes';

-- =====================================================================
-- FIN DE L'INITIALISATION
-- =====================================================================
