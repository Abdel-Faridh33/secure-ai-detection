"""
Gestionnaire des utilisateurs avec authentification sécurisée

Fournit toutes les opérations CRUD sur les utilisateurs:
- Création, lecture, mise à jour, suppression
- Authentification avec bcrypt
- Gestion des sessions JWT
- Historique de connexion
- Vérification des permissions (RBAC)
"""

import bcrypt
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from psycopg2 import extras

from .connection import get_db_connection

logger = logging.getLogger(__name__)


class UserManager:
    """Gestionnaire des utilisateurs avec authentification sécurisée"""

    def __init__(self):
        """Initialise le gestionnaire"""
        self.db = get_db_connection()

    # ==================== CRÉATION ET MODIFICATION ====================

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        """
        Crée un nouvel utilisateur

        Args:
            username: Nom d'utilisateur unique
            password: Mot de passe en clair (sera hashé)
            role: Rôle (admin, operator, agent, viewer)
            email: Email optionnel
            full_name: Nom complet optionnel
            created_by: ID de l'utilisateur créateur

        Returns:
            ID du nouvel utilisateur ou None si erreur

        Raises:
            ValueError: Si le username existe déjà ou paramètres invalides
        """
        # Validation
        if len(username) < 3:
            raise ValueError("Le username doit faire au moins 3 caractères")

        if len(password) < 8:
            raise ValueError("Le mot de passe doit faire au moins 8 caractères")

        if role not in ['admin', 'agent', 'guest']:
            raise ValueError(f"Rôle invalide: {role}")

        # Hash du mot de passe avec bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            query = """
                INSERT INTO users (
                    username, password_hash, role, email, full_name,
                    is_active, created_by, created_at, last_password_change
                ) VALUES (
                    %s, %s, %s, %s, %s, true, %s, NOW(), NOW()
                )
                RETURNING id
            """
            user_id = self.db.execute_insert(
                query,
                (username, password_hash, role, email, full_name, created_by)
            )

            logger.info(f"Utilisateur créé: {username} (ID: {user_id}, Role: {role})")
            return user_id

        except Exception as e:
            if 'duplicate key' in str(e).lower():
                raise ValueError(f"Le username '{username}' existe déjà")
            logger.error(f"Erreur création utilisateur: {e}")
            raise

    def update_user(
        self,
        user_id: int,
        updated_by: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Met à jour un utilisateur

        Args:
            user_id: ID de l'utilisateur
            updated_by: ID de l'utilisateur qui fait la modification
            **kwargs: Champs à mettre à jour (email, full_name, role, is_active, etc.)

        Returns:
            True si mis à jour, False sinon

        Example:
            manager.update_user(5, email="new@email.com", full_name="John Doe")
        """
        allowed_fields = ['email', 'full_name', 'role', 'is_active']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            logger.warning("Aucun champ à mettre à jour")
            return False

        # Construire la requête dynamiquement
        set_clause = ", ".join([f"{field} = %s" for field in updates.keys()])
        values = list(updates.values()) + [updated_by, user_id]

        query = f"""
            UPDATE users
            SET {set_clause}, updated_by = %s, updated_at = NOW()
            WHERE id = %s
        """

        try:
            self.db.execute_query(query, tuple(values), fetch=False)
            logger.info(f"Utilisateur {user_id} mis à jour: {updates}")
            return True
        except Exception as e:
            logger.error(f"Erreur mise à jour utilisateur: {e}")
            return False

    def change_password(self, user_id: int, new_password: str) -> bool:
        """
        Change le mot de passe d'un utilisateur

        Args:
            user_id: ID de l'utilisateur
            new_password: Nouveau mot de passe en clair

        Returns:
            True si changé, False sinon
        """
        if len(new_password) < 8:
            raise ValueError("Le mot de passe doit faire au moins 8 caractères")

        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        query = """
            UPDATE users
            SET password_hash = %s,
                last_password_change = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """

        try:
            self.db.execute_query(query, (password_hash, user_id), fetch=False)
            logger.info(f"Mot de passe changé pour utilisateur {user_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur changement mot de passe: {e}")
            return False

    # ==================== AUTHENTIFICATION ====================

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authentifie un utilisateur

        Args:
            username: Nom d'utilisateur
            password: Mot de passe en clair
            ip_address: IP du client
            user_agent: User-Agent du client

        Returns:
            Dictionnaire avec infos utilisateur si succès, None sinon
            Format: {
                'id': int,
                'username': str,
                'role': str,
                'email': str,
                'full_name': str
            }
        """
        query = """
            SELECT id, username, password_hash, role, email, full_name,
                   is_active, is_locked, failed_login_attempts
            FROM users
            WHERE username = %s
        """

        try:
            result = self.db.execute_query_dict(query, (username,))

            if not result:
                self._log_login_attempt(None, ip_address, user_agent, False, "Username not found")
                logger.warning(f"Tentative de connexion avec username inconnu: {username}")
                return None

            user = result[0]

            # Vérifications
            if user['is_locked']:
                self._log_login_attempt(user['id'], ip_address, user_agent, False, "Account locked")
                logger.warning(f"Tentative de connexion sur compte verrouillé: {username}")
                return None

            if not user['is_active']:
                self._log_login_attempt(user['id'], ip_address, user_agent, False, "Account inactive")
                logger.warning(f"Tentative de connexion sur compte inactif: {username}")
                return None

            # Vérification du mot de passe
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                # Incrémenter les tentatives échouées
                self._increment_failed_attempts(user['id'])
                self._log_login_attempt(user['id'], ip_address, user_agent, False, "Invalid password")
                logger.warning(f"Mot de passe incorrect pour: {username}")
                return None

            # Authentification réussie !
            self._reset_failed_attempts(user['id'])
            self._update_last_login(user['id'])
            self._log_login_attempt(user['id'], ip_address, user_agent, True, None)

            logger.info(f"Authentification réussie: {username} (role: {user['role']})")

            # Retourner les infos utilisateur (sans le password_hash)
            return {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'email': user['email'],
                'full_name': user['full_name']
            }

        except Exception as e:
            logger.error(f"Erreur authentification: {e}")
            return None

    def _log_login_attempt(
        self,
        user_id: Optional[int],
        ip_address: Optional[str],
        user_agent: Optional[str],
        success: bool,
        failure_reason: Optional[str]
    ):
        """Enregistre une tentative de connexion"""
        query = """
            INSERT INTO login_history (user_id, ip_address, user_agent, success, failure_reason)
            VALUES (%s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_query(
                query,
                (user_id, ip_address, user_agent, success, failure_reason),
                fetch=False
            )
        except Exception as e:
            logger.error(f"Erreur log login: {e}")

    def _increment_failed_attempts(self, user_id: int):
        """Incrémente le compteur de tentatives échouées et verrouille si nécessaire"""
        query = """
            UPDATE users
            SET failed_login_attempts = failed_login_attempts + 1,
                is_locked = CASE
                    WHEN failed_login_attempts + 1 >= 5 THEN true
                    ELSE is_locked
                END
            WHERE id = %s
        """
        self.db.execute_query(query, (user_id,), fetch=False)

    def _reset_failed_attempts(self, user_id: int):
        """Réinitialise le compteur de tentatives échouées"""
        query = "UPDATE users SET failed_login_attempts = 0 WHERE id = %s"
        self.db.execute_query(query, (user_id,), fetch=False)

    def _update_last_login(self, user_id: int):
        """Met à jour la date de dernière connexion"""
        query = "UPDATE users SET last_login = NOW() WHERE id = %s"
        self.db.execute_query(query, (user_id,), fetch=False)

    # ==================== PERMISSIONS (RBAC) ====================

    def has_permission(self, user_id: int, resource: str, action: str) -> bool:
        """
        Vérifie si un utilisateur a une permission

        Args:
            user_id: ID de l'utilisateur
            resource: Ressource (ex: 'predictions', 'users', 'audit_logs')
            action: Action (ex: 'read', 'write', 'delete', 'admin')

        Returns:
            True si autorisé, False sinon

        Example:
            if manager.has_permission(user_id, 'users', 'delete'):
                # Autoriser la suppression d'utilisateur
        """
        query = """
            SELECT EXISTS(
                SELECT 1 FROM role_permissions rp
                JOIN users u ON u.role = rp.role
                WHERE u.id = %s
                    AND rp.resource = %s
                    AND rp.action = %s
            )
        """
        result = self.db.execute_query(query, (user_id, resource, action))
        return result[0][0] if result else False

    def get_user_permissions(self, user_id: int) -> List[Dict[str, str]]:
        """
        Récupère toutes les permissions d'un utilisateur

        Returns:
            Liste de {resource, action}
        """
        query = """
            SELECT rp.resource, rp.action
            FROM role_permissions rp
            JOIN users u ON u.role = rp.role
            WHERE u.id = %s
            ORDER BY rp.resource, rp.action
        """
        return self.db.execute_query_dict(query, (user_id,))

    # ==================== RÉCUPÉRATION ====================

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par son ID"""
        query = """
            SELECT id, username, role, email, full_name, is_active,
                   created_at, last_login
            FROM users
            WHERE id = %s
        """
        result = self.db.execute_query_dict(query, (user_id,))
        return result[0] if result else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par son username"""
        query = """
            SELECT id, username, role, email, full_name, is_active,
                   created_at, last_login
            FROM users
            WHERE username = %s
        """
        result = self.db.execute_query_dict(query, (username,))
        return result[0] if result else None

    def list_users(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Liste tous les utilisateurs

        Args:
            active_only: Si True, seulement les utilisateurs actifs

        Returns:
            Liste de dictionnaires utilisateur
        """
        query = """
            SELECT id, username, role, email, full_name, is_active,
                   created_at, last_login
            FROM users
        """
        if active_only:
            query += " WHERE is_active = true"

        query += " ORDER BY username"

        return self.db.execute_query_dict(query)

    # ==================== SESSIONS JWT ====================

    def create_session(
        self,
        user_id: int,
        token_jti: str,
        expires_in_minutes: int = 60,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Crée une session JWT active"""
        query = """
            INSERT INTO active_sessions (
                user_id, token_jti, expires_at, ip_address, user_agent
            ) VALUES (
                %s, %s, NOW() + INTERVAL '%s minutes', %s, %s
            )
            RETURNING id
        """
        return self.db.execute_insert(
            query,
            (user_id, token_jti, expires_in_minutes, ip_address, user_agent)
        )

    def is_session_valid(self, token_jti: str) -> bool:
        """Vérifie si une session JWT est valide"""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM active_sessions
                WHERE token_jti = %s
                    AND expires_at > NOW()
                    AND is_revoked = false
            )
        """
        result = self.db.execute_query(query, (token_jti,))
        return result[0][0] if result else False

    def revoke_session(self, token_jti: str, reason: str = "Logout"):
        """Révoque une session JWT"""
        query = """
            UPDATE active_sessions
            SET is_revoked = true,
                revoked_at = NOW(),
                revoked_reason = %s
            WHERE token_jti = %s
        """
        self.db.execute_query(query, (reason, token_jti), fetch=False)

    def cleanup_expired_sessions(self) -> int:
        """
        Nettoie les sessions expirées

        Returns:
            Nombre de sessions supprimées
        """
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT cleanup_expired_sessions()")
            return cursor.fetchone()[0]
