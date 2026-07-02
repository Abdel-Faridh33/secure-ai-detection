"""
Module d'authentification JWT + RBAC
Zone 4 - Production Security

Authentification : PostgreSQL via UserManager (bcrypt), fallback in-memory (SHA-256).
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
import jwt
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "secure-ai-detection-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class UserRole(Enum):
    ADMIN = "admin"
    AGENT = "agent"
    GUEST  = "guest"


class Permission(Enum):
    PREDICT       = "predict"
    VIEW_AUDIT    = "view_audit"
    EXPORT_AUDIT  = "export_audit"
    MANAGE_USERS  = "manage_users"
    VIEW_METRICS  = "view_metrics"


ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        Permission.PREDICT,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_AUDIT,
        Permission.MANAGE_USERS,
        Permission.VIEW_METRICS,
    ],
    UserRole.AGENT: [
        Permission.PREDICT,
        Permission.VIEW_AUDIT,
        Permission.VIEW_METRICS,
    ],
    UserRole.GUEST: [
        Permission.PREDICT,
    ],
}

# ──────────────────────────────────────────────────────────────────
# Fallback in-memory (utilisé si PostgreSQL indisponible)
# ──────────────────────────────────────────────────────────────────
_admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
_agent_password = os.getenv("AGENT_PASSWORD", "agent123")

_FALLBACK_USERS = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256(_admin_password.encode()).hexdigest(),
        "role": UserRole.ADMIN.value,
        "email": "admin@secureai.local",
    },
    "agent1": {
        "username": "agent1",
        "password_hash": hashlib.sha256(_agent_password.encode()).hexdigest(),
        "role": UserRole.AGENT.value,
        "email": "agent1@secureai.local",
    },
}


def _get_user_manager():
    """Retourne un UserManager connecté à PostgreSQL, ou None si indisponible."""
    try:
        from src.database.user_manager import UserManager
        return UserManager()
    except Exception as exc:
        logger.debug(f"UserManager indisponible, fallback in-memory : {exc}")
        return None


# ──────────────────────────────────────────────────────────────────
# JWT
# ──────────────────────────────────────────────────────────────────

def create_access_token(username: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ──────────────────────────────────────────────────────────────────
# Authentification
# ──────────────────────────────────────────────────────────────────

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authentifie via PostgreSQL (bcrypt), fallback in-memory (SHA-256)."""
    manager = _get_user_manager()
    if manager:
        try:
            return manager.authenticate(username, password)
        except Exception as exc:
            logger.warning(f"Erreur authenticate DB, fallback in-memory : {exc}")

    # Fallback in-memory
    user = _FALLBACK_USERS.get(username)
    if not user:
        return None
    if hashlib.sha256(password.encode()).hexdigest() != user["password_hash"]:
        return None
    return {"username": user["username"], "role": user["role"], "email": user["email"]}


def create_user(username: str, password: str, email: str, role: str = "guest") -> Dict:
    """Crée un utilisateur en PostgreSQL, fallback in-memory."""
    if not username or len(username) < 3:
        raise ValueError("Le nom d'utilisateur doit contenir au moins 3 caractères")
    if not password or len(password) < 6:
        raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
    if not email or "@" not in email:
        raise ValueError("Email invalide")
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        role = UserRole.GUEST.value

    manager = _get_user_manager()
    if manager:
        try:
            manager.create_user(username=username, password=password, role=role, email=email)
            return {"username": username, "email": email, "role": role}
        except ValueError:
            raise
        except Exception as exc:
            logger.warning(f"Erreur create_user DB, fallback in-memory : {exc}")

    # Fallback in-memory
    if username in _FALLBACK_USERS:
        raise ValueError("Ce nom d'utilisateur existe déjà")
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    _FALLBACK_USERS[username] = {"username": username, "password_hash": password_hash, "role": role, "email": email}
    return {"username": username, "email": email, "role": role}


def get_all_users() -> List[Dict]:
    """Liste tous les utilisateurs depuis PostgreSQL, fallback in-memory."""
    manager = _get_user_manager()
    if manager:
        try:
            rows = manager.list_users(active_only=True)
            return [{
                "username":   r["username"],
                "email":      r.get("email"),
                "role":       r["role"],
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                "last_login": r["last_login"].isoformat() if r.get("last_login") else None,
            } for r in rows]
        except Exception as exc:
            logger.warning(f"Erreur list_users DB, fallback in-memory : {exc}")
    return [{"username": u["username"], "email": u["email"], "role": u["role"]}
            for u in _FALLBACK_USERS.values()]


def delete_user(username: str) -> bool:
    """Désactive un utilisateur en DB (soft delete), fallback in-memory."""
    if username == "admin":
        return False

    manager = _get_user_manager()
    if manager:
        try:
            user = manager.get_user_by_username(username)
            if not user:
                return False
            manager.update_user(user["id"], is_active=False)
            return True
        except Exception as exc:
            logger.warning(f"Erreur delete_user DB, fallback in-memory : {exc}")

    if username in _FALLBACK_USERS and username != "agent1":
        del _FALLBACK_USERS[username]
        return True
    return False


# ──────────────────────────────────────────────────────────────────
# RBAC
# ──────────────────────────────────────────────────────────────────

def check_permission(role: str, permission: Permission) -> bool:
    try:
        user_role = UserRole(role)
        return permission in ROLE_PERMISSIONS.get(user_role, [])
    except ValueError:
        return False


def get_user_permissions(role: str) -> List[str]:
    try:
        user_role = UserRole(role)
        return [p.value for p in ROLE_PERMISSIONS.get(user_role, [])]
    except ValueError:
        return []
