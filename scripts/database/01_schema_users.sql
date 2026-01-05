-- =====================================================================
-- SCHEMA: Users Management (Authentication + RBAC)
-- Description: Table pour gérer les utilisateurs du système avec
--              authentification sécurisée et contrôle d'accès basé sur les rôles
-- Date: 2025-12-16
-- =====================================================================

-- Table principale des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- Hachage bcrypt du mot de passe
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'operator', 'agent', 'viewer')),

    -- Métadonnées
    email VARCHAR(255),
    full_name VARCHAR(100),

    -- Gestion d'état
    is_active BOOLEAN DEFAULT true,
    is_locked BOOLEAN DEFAULT false,
    failed_login_attempts INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    last_password_change TIMESTAMPTZ DEFAULT NOW(),

    -- Audit
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

-- Index pour optimiser les recherches
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Table d'historique des connexions
CREATE TABLE IF NOT EXISTS login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    login_time TIMESTAMPTZ DEFAULT NOW(),
    ip_address VARCHAR(45),  -- Support IPv6
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(255)
);

-- Index pour recherche rapide de l'historique
CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_time ON login_history(login_time);
CREATE INDEX IF NOT EXISTS idx_login_history_success ON login_history(success);

-- Table des sessions actives (JWT tokens)
CREATE TABLE IF NOT EXISTS active_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,  -- JWT ID unique
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(255)
);

-- Index pour validation rapide des tokens
CREATE INDEX IF NOT EXISTS idx_sessions_token_jti ON active_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON active_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON active_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_is_revoked ON active_sessions(is_revoked);

-- Table des permissions par rôle (RBAC)
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    resource VARCHAR(50) NOT NULL,  -- Ex: 'predictions', 'users', 'audit_logs'
    action VARCHAR(20) NOT NULL,    -- Ex: 'read', 'write', 'delete', 'admin'
    UNIQUE(role, resource, action)
);

-- Index pour vérification rapide des permissions
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role);

-- Trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Fonction pour nettoyer les sessions expirées
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM active_sessions
    WHERE expires_at < NOW() AND is_revoked = false;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Commentaires pour documentation
COMMENT ON TABLE users IS 'Table principale des utilisateurs avec authentification sécurisée';
COMMENT ON COLUMN users.password_hash IS 'Hash bcrypt du mot de passe (jamais stocké en clair)';
COMMENT ON COLUMN users.role IS 'Rôle utilisateur: admin, operator, agent, ou viewer';
COMMENT ON COLUMN users.is_locked IS 'Compte verrouillé après trop de tentatives échouées';

COMMENT ON TABLE login_history IS 'Historique de toutes les tentatives de connexion (succès et échecs)';
COMMENT ON TABLE active_sessions IS 'Sessions JWT actives pour validation et révocation';
COMMENT ON TABLE role_permissions IS 'Matrice des permissions par rôle (RBAC)';
