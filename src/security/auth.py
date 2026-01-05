"""
Module d'authentification JWT + RBAC simplifié
Zone 4 - Production Security

Fonctionnalités :
- Génération de tokens JWT
- Vérification de tokens
- Contrôle d'accès basé sur les rôles (RBAC)
- 3 rôles : admin, agent, guest
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
import jwt
import hashlib
import os

# Configuration JWT depuis les variables d'environnement
SECRET_KEY = os.getenv("JWT_SECRET", "secure-ai-detection-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class UserRole(Enum):
    """Rôles utilisateurs avec permissions"""
    ADMIN = "admin"      # Tous droits : prédictions, audit, gestion
    AGENT = "agent"      # Prédictions + consultation audit
    GUEST = "guest"      # Prédictions uniquement


class Permission(Enum):
    """Permissions du système"""
    PREDICT = "predict"               # Faire des prédictions
    VIEW_AUDIT = "view_audit"         # Consulter les logs d'audit
    EXPORT_AUDIT = "export_audit"     # Exporter les logs
    MANAGE_USERS = "manage_users"     # Gérer les utilisateurs
    VIEW_METRICS = "view_metrics"     # Voir les métriques


# Mapping des rôles aux permissions
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        Permission.PREDICT,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_AUDIT,
        Permission.MANAGE_USERS,
        Permission.VIEW_METRICS
    ],
    UserRole.AGENT: [
        Permission.PREDICT,
        Permission.VIEW_AUDIT,
        Permission.VIEW_METRICS
    ],
    UserRole.GUEST: [
        Permission.PREDICT
    ]
}


# Base de données simulée (En production : vraie DB)
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": UserRole.ADMIN.value,
        "email": "admin@secureai.com"
    },
    "agent1": {
        "username": "agent1",
        "password_hash": hashlib.sha256("agent123".encode()).hexdigest(),
        "role": UserRole.AGENT.value,
        "email": "agent1@secureai.com"
    },
    "guest": {
        "username": "guest",
        "password_hash": hashlib.sha256("guest123".encode()).hexdigest(),
        "role": UserRole.GUEST.value,
        "email": "guest@secureai.com"
    },
    "testadmin": {
        "username": "testadmin",
        "password_hash": hashlib.sha256("Test@123".encode()).hexdigest(),
        "role": UserRole.ADMIN.value,
        "email": "testadmin@secureai.com"
    }
}


def create_access_token(username: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Créer un token JWT pour un utilisateur

    Args:
        username: Nom d'utilisateur
        role: Rôle de l'utilisateur (admin, agent, guest)
        expires_delta: Durée de validité (défaut: 60 minutes)

    Returns:
        Token JWT encodé
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict]:
    """
    Vérifier et décoder un token JWT

    Args:
        token: Token JWT à vérifier

    Returns:
        Payload du token si valide, None sinon
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expiré
    except jwt.InvalidTokenError:
        return None  # Token invalide


def create_user(username: str, password: str, email: str, role: str = "guest") -> Dict:
    """
    Créer un nouveau compte utilisateur

    Args:
        username: Nom d'utilisateur (unique)
        password: Mot de passe en clair
        email: Email de l'utilisateur
        role: Rôle (guest par défaut)

    Returns:
        Dictionnaire utilisateur créé

    Raises:
        ValueError: Si l'utilisateur existe déjà ou si les paramètres sont invalides
    """
    # Validation
    if not username or len(username) < 3:
        raise ValueError("Le nom d'utilisateur doit contenir au moins 3 caractères")

    if not password or len(password) < 6:
        raise ValueError("Le mot de passe doit contenir au moins 6 caractères")

    if not email or "@" not in email:
        raise ValueError("Email invalide")

    if username in DEMO_USERS:
        raise ValueError("Ce nom d'utilisateur existe déjà")

    # Vérifier que le rôle est valide
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        role = UserRole.GUEST.value

    # Créer l'utilisateur
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "email": email
    }

    # Ajouter à la "base de données"
    DEMO_USERS[username] = user

    return user


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Authentifier un utilisateur (démo simplifiée)

    Args:
        username: Nom d'utilisateur
        password: Mot de passe

    Returns:
        Infos utilisateur si authentification réussie, None sinon
    """
    user = DEMO_USERS.get(username)
    if not user:
        return None

    # Vérification du mot de passe hashé
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        return None

    return user


def check_permission(role: str, permission: Permission) -> bool:
    """
    Vérifier si un rôle a une permission donnée

    Args:
        role: Rôle de l'utilisateur
        permission: Permission à vérifier

    Returns:
        True si le rôle a la permission, False sinon
    """
    try:
        user_role = UserRole(role)
        permissions = ROLE_PERMISSIONS.get(user_role, [])
        return permission in permissions
    except ValueError:
        return False


def get_user_permissions(role: str) -> List[str]:
    """
    Récupérer toutes les permissions d'un rôle

    Args:
        role: Rôle de l'utilisateur

    Returns:
        Liste des permissions
    """
    try:
        user_role = UserRole(role)
        permissions = ROLE_PERMISSIONS.get(user_role, [])
        return [p.value for p in permissions]
    except ValueError:
        return []


def get_all_users():
    """Récupérer tous les utilisateurs sans les mots de passe"""
    return [{"username": u["username"], "email": u["email"], "role": u["role"]} 
            for u in DEMO_USERS.values()]


def delete_user(username):
    """Supprimer un utilisateur"""
    if username in DEMO_USERS and username not in ['admin', 'agent1', 'guest']:
        del DEMO_USERS[username]
        return True
    return False

