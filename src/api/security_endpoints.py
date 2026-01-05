"""
Endpoints de sécurité pour l'API
Zone 4 - Production Security

Intégration des modules :
- Authentification JWT
- WAF (Rate limiting + validation)
- Détection d'anomalies en temps réel
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import timedelta

# Import des modules de sécurité
from src.security.auth import (
    authenticate_user,
    create_user,
    create_access_token,
    verify_token,
    check_permission,
    get_user_permissions,
    UserRole,
    Permission
)
from src.security.waf import waf
from src.security.anomaly_detector import anomaly_detector

# Router pour les endpoints de sécurité
router = APIRouter(prefix="/security", tags=["Security"])

# Schéma de sécurité HTTP Bearer
security = HTTPBearer()


# ============================================================
# MODÈLES PYDANTIC
# ============================================================

class LoginRequest(BaseModel):
    """Requête de connexion"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """Requête d'inscription"""
    username: str
    password: str
    email: str
    role: Optional[str] = "guest"


class LoginResponse(BaseModel):
    """Réponse de connexion"""
    access_token: str
    token_type: str
    role: str
    permissions: list


class WAFStatusResponse(BaseModel):
    """Statut du WAF"""
    rate_limit_enabled: bool
    max_requests: int
    window_seconds: int
    current_request_count: int
    is_blocked: bool


class AnomalyResponse(BaseModel):
    """Réponse d'analyse d'anomalies"""
    anomalies_detected: bool
    anomalies: list
    risk_level: str
    risk_score: float


# ============================================================
# DÉPENDANCES
# ============================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dépendance pour obtenir l'utilisateur actuel depuis le token JWT
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "username": payload.get("sub"),
        "role": payload.get("role")
    }


def require_permission(permission: Permission):
    """
    Factory qui crée une dépendance pour vérifier qu'un utilisateur a une permission
    """
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        if not check_permission(current_user["role"], permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value} required"
            )
        return current_user
    return permission_checker


# ============================================================
# ENDPOINTS D'AUTHENTIFICATION
# ============================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Endpoint de connexion
    Retourne un token JWT si l'authentification réussit

    Users de démo :
    - admin / admin123 (role: admin)
    - agent1 / agent123 (role: agent)
    - guest / guest123 (role: guest)
    """
    user = authenticate_user(request.username, request.password)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Créer le token JWT
    access_token = create_access_token(
        username=user["username"],
        role=user["role"],
        expires_delta=timedelta(hours=1)
    )

    # Obtenir les permissions
    permissions = get_user_permissions(user["role"])

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"],
        permissions=permissions
    )


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """
    Endpoint d'inscription
    Crée un nouveau compte utilisateur et retourne un token JWT

    Args:
        username: Nom d'utilisateur (min 3 caractères, unique)
        password: Mot de passe (min 6 caractères)
        email: Email valide
        role: Rôle (guest par défaut, admin nécessite privilèges)
    """
    try:
        # Seul un admin peut créer des comptes admin ou agent
        # Pour l'instant, tous les nouveaux comptes sont "guest"
        safe_role = "guest"

        # Créer l'utilisateur
        user = create_user(
            username=request.username,
            password=request.password,
            email=request.email,
            role=safe_role
        )

        # Créer le token JWT pour connexion automatique
        access_token = create_access_token(
            username=user["username"],
            role=user["role"],
            expires_delta=timedelta(hours=1)
        )

        # Obtenir les permissions
        permissions = get_user_permissions(user["role"])

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            role=user["role"],
            permissions=permissions
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création du compte: {str(e)}"
        )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Obtenir les informations de l'utilisateur actuel
    Nécessite un token JWT valide
    """
    permissions = get_user_permissions(current_user["role"])

    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "permissions": permissions
    }


@router.get("/permissions")
async def get_permissions(current_user: dict = Depends(get_current_user)):
    """
    Obtenir les permissions de l'utilisateur actuel
    """
    permissions = get_user_permissions(current_user["role"])

    return {
        "role": current_user["role"],
        "permissions": permissions
    }


# ============================================================
# ENDPOINTS WAF
# ============================================================

@router.get("/waf/status", response_model=WAFStatusResponse)
async def get_waf_status(request: Request):
    """
    Obtenir le statut du WAF pour l'IP actuelle
    """
    client_ip = request.client.host if request.client else "unknown"

    request_count = waf.rate_limiter.get_request_count(client_ip)
    is_blocked = waf.is_ip_blocked(client_ip)

    return WAFStatusResponse(
        rate_limit_enabled=True,
        max_requests=waf.rate_limiter.max_requests,
        window_seconds=waf.rate_limiter.window_seconds,
        current_request_count=request_count,
        is_blocked=is_blocked
    )


@router.get("/waf/blocked-ips")
async def get_blocked_ips(current_user: dict = Depends(require_permission(Permission.VIEW_AUDIT))):
    """
    Obtenir la liste des IPs bloquées par le WAF
    Nécessite la permission VIEW_AUDIT
    """
    blocked_ips = [
        {
            "ip": ip,
            "blocked_until": block_until.isoformat() + "Z"
        }
        for ip, block_until in waf.rate_limiter.blocked_ips.items()
    ]

    return {
        "count": len(blocked_ips),
        "blocked_ips": blocked_ips
    }


# ============================================================
# ENDPOINTS DÉTECTION D'ANOMALIES
# ============================================================

@router.get("/anomalies/recent")
async def get_recent_anomalies(
    limit: int = 50,
    current_user: dict = Depends(require_permission(Permission.VIEW_AUDIT))
):
    """
    Obtenir les anomalies détectées récemment
    Nécessite la permission VIEW_AUDIT
    """
    anomalies = anomaly_detector.get_recent_anomalies(limit=limit)

    return {
        "count": len(anomalies),
        "anomalies": anomalies
    }


@router.get("/anomalies/high-risk-ips")
async def get_high_risk_ips(
    threshold: float = 50.0,
    current_user: dict = Depends(require_permission(Permission.VIEW_AUDIT))
):
    """
    Obtenir les IPs à haut risque
    Nécessite la permission VIEW_AUDIT
    """
    high_risk_ips = anomaly_detector.get_high_risk_ips(threshold=threshold)

    return {
        "count": len(high_risk_ips),
        "threshold": threshold,
        "high_risk_ips": high_risk_ips
    }


@router.get("/anomalies/ip/{ip}")
async def get_ip_risk_score(
    ip: str,
    current_user: dict = Depends(require_permission(Permission.VIEW_AUDIT))
):
    """
    Obtenir le score de risque d'une IP spécifique
    Nécessite la permission VIEW_AUDIT
    """
    risk_score = anomaly_detector.risk_scores.get(ip, 0.0)

    # Récupérer les anomalies de cette IP
    ip_anomalies = [
        a for a in anomaly_detector.detected_anomalies
        if a["ip"] == ip
    ]

    return {
        "ip": ip,
        "risk_score": risk_score,
        "anomaly_count": len(ip_anomalies),
        "recent_anomalies": ip_anomalies[-10:]  # 10 dernières
    }


# ============================================================
# ENDPOINTS DE MONITORING SÉCURITÉ
# ============================================================

@router.get("/dashboard")
async def get_security_dashboard(
    current_user: dict = Depends(require_permission(Permission.VIEW_AUDIT))
):
    """
    Dashboard de sécurité global
    Nécessite la permission VIEW_AUDIT
    """
    # Statistiques WAF
    total_blocked_ips = len(waf.rate_limiter.blocked_ips)

    # Statistiques anomalies
    recent_anomalies = anomaly_detector.get_recent_anomalies(limit=100)
    high_risk_ips = anomaly_detector.get_high_risk_ips(threshold=50.0)

    # Compter les anomalies par type
    anomaly_types = {}
    for anomaly in recent_anomalies:
        anomaly_type = anomaly["anomaly"]["type"]
        anomaly_types[anomaly_type] = anomaly_types.get(anomaly_type, 0) + 1

    return {
        "waf": {
            "blocked_ips": total_blocked_ips,
            "rate_limit_enabled": True
        },
        "anomalies": {
            "recent_count": len(recent_anomalies),
            "high_risk_ips": len(high_risk_ips),
            "types": anomaly_types
        },
        "security_score": max(0, 100 - (len(high_risk_ips) * 10))  # Score simplifié
    }


# ============================================================
# ENDPOINTS D'ADMINISTRATION DES UTILISATEURS
# ============================================================

@router.get("/users")
async def list_users(current_user: dict = Depends(require_permission(Permission.MANAGE_USERS))):
    """
    Lister tous les utilisateurs (réservé aux admins)
    """
    from src.security.auth import get_all_users
    users = get_all_users()
    return users


@router.delete("/users/{username}")
async def remove_user(username: str, current_user: dict = Depends(require_permission(Permission.MANAGE_USERS))):
    """
    Supprimer un utilisateur (réservé aux admins)
    """
    from src.security.auth import delete_user
    
    if delete_user(username):
        return {"message": f"User {username} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found or cannot be deleted")
