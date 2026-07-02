"""
API FastAPI - Système de Détection Sécurisé
Architecture de Sécurisation IA : 5 Zones

Zones intégrées :
- Zone 1 : Chargement du modèle depuis stockage chiffré AES-256-GCM
- Zone 2 : Vérification de la signature RSA-4096 du modèle
- Zone 4 : WAF + JWT/RBAC + détection d'anomalies à l'inférence
- Zone 5 : Audit trail immuable (SHA-256, logs JSON append-only)
"""

import os
import io
import sys
import json
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
from torchvision import transforms
from PIL import Image

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import uvicorn

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.monitoring.audit_logger import audit_logger, EventType, SeverityLevel
from src.monitoring.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    ai_predictions_total,
    ai_processing_seconds,
    security_attacks_blocked_total,
)
from src.api.security_endpoints import router as security_router
from src.api.security_middleware import SecurityMiddleware
from src.security.auth import verify_token
from src.data.encrypted_storage import EncryptedStorage
from models.utils.model_loader import ModelLoader

# ─────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────
app = FastAPI(
    title="Secure Object Detection API",
    description=(
        "Système de détection d'objets dangereux – modèle MobileNetV2 sécurisé "
        "(adversarial training FGSM/PGD, AES-256-GCM, signature RSA-4096, "
        "WAF, JWT/RBAC, audit trail immuable)"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# CORS – wildcard autorisé en dev (ALLOWED_ORIGINS=*)
_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:8800,http://localhost:3000")
_wildcard = _origins_raw.strip() == "*"
ALLOWED_ORIGINS = ["*"] if _wildcard else _origins_raw.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=not _wildcard,   # credentials incompatible avec wildcard
    allow_methods=["*"] if _wildcard else ["GET", "POST"],
    allow_headers=["*"] if _wildcard else ["Authorization", "Content-Type"],
)

# Zone 4 : WAF + détection d'anomalies sur chaque requête
app.add_middleware(SecurityMiddleware)

# Router sécurité (auth, tokens)
app.include_router(security_router)

# Métriques Prometheus — définies dans src/monitoring/metrics.py
request_count    = http_requests_total
request_duration = http_request_duration_seconds
prediction_count = ai_predictions_total
processing_time  = ai_processing_seconds
attack_blocked   = security_attacks_blocked_total

# ─────────────────────────────────────────────
# Modèle global (secured uniquement)
# ─────────────────────────────────────────────
_model = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

logger = logging.getLogger("secure-api")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)


def _load_secured_model() -> Optional[torch.nn.Module]:
    """
    Zone 1 + Zone 2 : charge le modèle sécurisé.

    Priorité :
      1. Stockage chiffré AES-256-GCM  (Zone 1)
      2. Fichier .pth signé RSA-4096   (Zone 2)
      3. Fichier .pth non signé        (fallback avec avertissement)
    """
    project_root = Path(__file__).resolve().parents[2]
    models_dir = project_root / "models" / "secured"

    # ── 1. Chargement depuis stockage chiffré ────────────────────
    encrypted_path = models_dir / "encrypted" / "best_secured_model_encrypted.enc"
    metadata_path = encrypted_path.with_suffix(".enc").parent / "best_secured_model_encrypted_metadata.json"

    if encrypted_path.exists() and metadata_path.exists():
        try:
            logger.info("Zone 1 : tentative de déchiffrement AES-256-GCM...")
            storage = EncryptedStorage(password=os.getenv("MODEL_ENCRYPTION_KEY", "SecureAI_2024_Production"))
            temp_path = models_dir / ".temp_decrypted.pth"
            meta = EncryptedStorage.load_metadata(str(metadata_path))
            storage.decrypt_pytorch_model(str(encrypted_path), str(temp_path), meta)
            model = ModelLoader.load_mobilenetv2_checkpoint(str(temp_path), device=str(device))
            temp_path.unlink(missing_ok=True)
            logger.info("Zone 1 : modèle chargé depuis stockage chiffré (AES-256-GCM).")
            audit_logger.log_event(
                event_type=EventType.MODEL_LOADED.value,
                severity=SeverityLevel.INFO,
                description="Secured model loaded from AES-256-GCM encrypted storage",
                metadata={"source": "encrypted", "device": str(device)},
            )
            return model
        except Exception as exc:
            logger.warning(f"Zone 1 : échec déchiffrement ({exc}), fallback .pth…")

    # ── 2. Chargement .pth avec vérification signature RSA-4096 ──
    candidate_paths = [
        models_dir / "best_secured_model.pth",
        models_dir / "final_secured_model.pth",
    ]

    for pth in candidate_paths:
        if not pth.exists():
            continue
        sig_path = pth.with_suffix(".pth").parent / (pth.stem + "_signature.bin")
        pub_path = pth.with_suffix(".pth").parent / (pth.stem + "_public_key.pem")

        signature_verified = False

        if sig_path.exists() and pub_path.exists():
            try:
                from cryptography.hazmat.primitives import serialization, hashes
                from cryptography.hazmat.primitives.asymmetric import padding

                model_bytes = pth.read_bytes()
                signature = sig_path.read_bytes()
                public_key = serialization.load_pem_public_key(pub_path.read_bytes())
                public_key.verify(
                    signature,
                    model_bytes,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    hashes.SHA256(),
                )
                signature_verified = True
                logger.info(f"Zone 2 : signature RSA-4096 vérifiée pour {pth.name}.")
                audit_logger.log_event(
                    event_type=EventType.SECURITY_CHECK.value,
                    severity=SeverityLevel.INFO,
                    description="Model RSA-4096 signature verified",
                    metadata={"model": pth.name, "algorithm": "RSA-4096-PSS-SHA256"},
                )
            except Exception as exc:
                logger.error(f"Zone 2 : signature invalide pour {pth.name} ({exc}). Modèle rejeté.")
                audit_logger.log_event(
                    event_type=EventType.SECURITY_ALERT.value,
                    severity=SeverityLevel.CRITICAL,
                    description="Model signature verification FAILED – possible tampering",
                    metadata={"model": pth.name, "error": str(exc)},
                )
                continue  # ne pas charger un modèle dont la signature est invalide
        else:
            logger.warning(f"Zone 2 : aucun fichier de signature pour {pth.name}. Chargement sans vérification.")

        try:
            model = ModelLoader.load_mobilenetv2_checkpoint(str(pth), device=str(device))
            logger.info(f"Modèle sécurisé chargé depuis {pth.name} (signé={signature_verified}).")
            audit_logger.log_event(
                event_type=EventType.MODEL_LOADED.value,
                severity=SeverityLevel.INFO,
                description="Secured model loaded from .pth",
                metadata={"model": pth.name, "signature_verified": signature_verified, "device": str(device)},
            )
            return model
        except Exception as exc:
            logger.error(f"Impossible de charger {pth}: {exc}")

    logger.critical("Aucun modèle sécurisé trouvé. L'API démarrera sans modèle.")
    audit_logger.log_event(
        event_type=EventType.SYSTEM_ERROR.value,
        severity=SeverityLevel.CRITICAL,
        description="No secured model could be loaded at startup",
        metadata={"searched": [str(p) for p in candidate_paths]},
    )
    return None


def _seed_default_users():
    """Crée les tables users si absentes, puis admin et agent1 si la table est vide."""
    try:
        from src.database.connection import get_db_connection
        db = get_db_connection()

        # Crée les tables si elles n'existent pas encore (migration idempotente)
        with db.get_cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id                    SERIAL PRIMARY KEY,
                    username              VARCHAR(50)  NOT NULL UNIQUE,
                    password_hash         VARCHAR(255) NOT NULL,
                    role                  VARCHAR(20)  NOT NULL DEFAULT 'guest'
                                              CHECK (role IN ('admin','agent','guest')),
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
                CREATE TABLE IF NOT EXISTS login_history (
                    id             SERIAL PRIMARY KEY,
                    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    ip_address     VARCHAR(45),
                    user_agent     TEXT,
                    success        BOOLEAN     NOT NULL,
                    failure_reason VARCHAR(255),
                    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
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
            """)
        logger.info("Tables utilisateurs vérifiées / créées.")

        from src.database.user_manager import UserManager
        manager = UserManager()
        if manager.list_users(active_only=False):
            return
        admin_pwd = os.getenv("ADMIN_PASSWORD", "admin123")
        agent_pwd = os.getenv("AGENT_PASSWORD", "agent123")
        manager.create_user("admin",  admin_pwd, "admin", email="admin@secureai.local")
        manager.create_user("agent1", agent_pwd, "agent", email="agent1@secureai.local")
        logger.info("Utilisateurs par défaut créés en base (admin, agent1).")
    except Exception as exc:
        logger.warning(f"Seeding utilisateurs ignoré (DB non disponible) : {exc}")


@app.on_event("startup")
async def startup():
    global _model
    logger.info(f"Démarrage API – device={device}")
    _seed_default_users()
    _model = _load_secured_model()
    if _model is None:
        logger.warning("API démarrée SANS modèle chargé – /predict retournera 503.")


# ─────────────────────────────────────────────
# Middleware d'audit (toutes les requêtes)
# ─────────────────────────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"

    user_id = "anonymous"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = verify_token(auth.split(" ", 1)[1])
        if payload:
            user_id = payload.get("sub", "anonymous")

    response = await call_next(request)

    elapsed_ms = (time.time() - start) * 1000
    endpoint = request.url.path
    if endpoint not in ("/metrics", "/health"):
        audit_logger.log_api_access(
            endpoint=endpoint,
            method=request.method,
            status_code=response.status_code,
            user_id=user_id,
            client_ip=client_ip,
            response_time_ms=elapsed_ms,
        )
        logger.info(
            f"{request.method} {endpoint} → {response.status_code} "
            f"({elapsed_ms:.0f}ms) user={user_id} ip={client_ip}"
        )

    request_count.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()
    request_duration.labels(endpoint=endpoint).observe(time.time() - start)
    return response


# ─────────────────────────────────────────────
# Endpoints de base
# ─────────────────────────────────────────────
@app.get("/", tags=["system"])
async def root():
    return {
        "service": "Secure AI Detection System",
        "model": "MobileNetV2 – Adversarial Training (FGSM/PGD)",
        "security_zones": ["Zone1-Data", "Zone2-Training", "Zone4-Inference", "Zone5-Audit"],
        "status": "running",
        "model_loaded": _model is not None,
    }


@app.get("/health", tags=["system"])
async def health():
    if _model is None:
        return JSONResponse(status_code=503, content={"status": "degraded", "reason": "model_not_loaded"})
    return {"status": "healthy", "model": "secured", "device": str(device)}


@app.get("/metrics", tags=["system"])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ─────────────────────────────────────────────
# Endpoint de prédiction (Zone 4 : inférence sécurisée)
# ─────────────────────────────────────────────
@app.post("/predict", tags=["detection"])
async def predict(
    file: UploadFile = File(...),
    request: Request = None,
):
    """
    Zone 4 – Inférence sécurisée.

    - Validation du type MIME et de l'intégrité de l'image
    - Hash SHA-256 de l'image pour audit (jamais l'image elle-même)
    - Prédiction : 'safe' ou 'dangerous'
    - Audit complet horodaté (audit_id retourné)
    """
    start = time.time()
    client_ip = request.client.host if request and request.client else "unknown"

    user_id = "anonymous"
    user_role = "guest"
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = verify_token(auth.split(" ", 1)[1])
            if payload:
                user_id = payload.get("sub", "anonymous")
                user_role = payload.get("role", "guest")

    # ── Vérification modèle disponible ───────────────────────────
    if _model is None:
        raise HTTPException(status_code=503, detail="Modèle non disponible – contactez l'administrateur.")

    # ── Validation WAF du nom de fichier (Zone 4) ────────────────
    from src.security.waf import waf as _waf
    if file.filename and not _waf.validator.is_safe_filename(file.filename):
        attack_blocked.labels(reason="suspicious_filename").inc()
        audit_logger.log_event(
            event_type="attack_detected",
            severity=SeverityLevel.SECURITY_ALERT,
            description=f"WAF: suspicious filename blocked — {file.filename}",
            user_id=user_id,
            client_ip=client_ip,
            metadata={"filename": file.filename, "reason": "suspicious_filename"},
        )
        raise HTTPException(status_code=400, detail="Nom de fichier suspect détecté par le WAF.")

    # ── Validation du fichier (Zone 4) ───────────────────────────
    if not file.content_type or not file.content_type.startswith("image/"):
        audit_logger.log_validation_failed(
            image_filename=file.filename,
            reason=f"Content-Type invalide : {file.content_type}",
            user_id=user_id,
            client_ip=client_ip,
        )
        raise HTTPException(status_code=400, detail="Le fichier doit être une image (image/*).")

    image_data = await file.read()

    try:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as exc:
        audit_logger.log_validation_failed(
            image_filename=file.filename,
            reason=f"Image illisible : {exc}",
            user_id=user_id,
            client_ip=client_ip,
        )
        raise HTTPException(status_code=400, detail="Image corrompue ou format non supporté.")

    # ── Inférence (Zone 4) ───────────────────────────────────────
    proc_start = time.time()
    with torch.no_grad():
        tensor = transform(image).unsqueeze(0).to(device)
        outputs = _model(tensor)
        probs = torch.softmax(outputs, dim=1)
        pred_class = torch.argmax(probs, dim=1).item()
        confidence = probs[0][pred_class].item()

    prediction = "safe" if pred_class == 0 else "dangerous"
    proc_ms = (time.time() - proc_start) * 1000

    # ── Détection d'entrées adversariales (Zone 4) ───────────────
    adversarial_flagged = False
    adversarial_score = 0.0
    try:
        import numpy as np
        img_array = np.array(image).astype(float)
        # Laplacian variance – les perturbations adversariales ajoutent du bruit HF
        laplacian = (
            img_array[:-2, 1:-1] + img_array[2:, 1:-1]
            + img_array[1:-1, :-2] + img_array[1:-1, 2:]
            - 4 * img_array[1:-1, 1:-1]
        )
        noise_score = float(np.var(laplacian) / (np.var(img_array) + 1e-6))
        adversarial_score = round(noise_score, 4)
        # Seuil heuristique : bruit très élevé + confiance faible
        if noise_score > 50.0 and confidence < 0.65:
            adversarial_flagged = True
            attack_blocked.labels(reason="adversarial_input_detected").inc()
            audit_logger.log_attack_detected(
                image_data=image_data,
                image_filename=file.filename,
                attack_type="adversarial_perturbation",
                confidence=min(noise_score / 100.0, 1.0),
                detection_method="laplacian_noise_analysis",
                user_id=user_id,
                client_ip=client_ip,
                blocked=False,
            )
    except Exception:
        pass

    # ── Audit (Zone 5) ───────────────────────────────────────────
    audit_id = audit_logger.log_prediction(
        image_data=image_data,
        image_filename=file.filename,
        model_type="secured",
        prediction=prediction,
        confidence=confidence,
        processing_time_ms=proc_ms,
        user_id=user_id,
        user_role=user_role,
        client_ip=client_ip,
        additional_metadata={
            "image_size": list(image.size),
            "image_mode": image.mode,
            "adversarial_flagged": adversarial_flagged,
            "adversarial_noise_score": adversarial_score,
        },
    )

    prediction_count.labels(prediction=prediction, source="api").inc()
    processing_time.observe((time.time() - proc_start))

    return {
        "model": "secured",
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "processing_time_ms": round(proc_ms, 1),
        "image_info": {"size": list(image.size), "mode": image.mode},
        "adversarial_flagged": adversarial_flagged,
        "adversarial_noise_score": adversarial_score,
        "audit_id": audit_id,
    }


# ─────────────────────────────────────────────
# Endpoints d'Audit – Zone 5 : Gouvernance
# ─────────────────────────────────────────────
@app.get("/audit/logs", tags=["audit"])
async def get_audit_logs(
    limit: int = 50,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
):
    limit = min(limit, 1000)
    et_filter = None
    sv_filter = None
    try:
        if event_type:
            et_filter = EventType(event_type)
        if severity:
            sv_filter = SeverityLevel(severity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logs = audit_logger.query_logs(event_type=et_filter, severity=sv_filter, limit=limit)
    return {"count": len(logs), "logs": logs, "filters": {"event_type": event_type, "severity": severity}}


@app.get("/audit/stats", tags=["audit"])
async def get_audit_stats():
    return {"statistics": audit_logger.get_statistics(), "generated_at": datetime.utcnow().isoformat() + "Z"}


@app.get("/audit/recent-attacks", tags=["audit"])
async def get_recent_attacks(limit: int = 20):
    attacks = audit_logger.query_logs(event_type=EventType.ATTACK_DETECTED, limit=limit)
    return {"count": len(attacks), "attacks": attacks}


@app.get("/audit/predictions/{audit_id}", tags=["audit"])
async def get_prediction_by_id(audit_id: str):
    logs = audit_logger.query_logs(limit=10000)
    for log in logs:
        if log.get("audit_id") == audit_id:
            return {"found": True, "details": log}
    raise HTTPException(status_code=404, detail=f"audit_id non trouvé : {audit_id}")


@app.post("/audit/export", tags=["audit"])
async def export_audit(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
):
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Format doit être 'json' ou 'csv'.")
    start_dt = datetime.fromisoformat(start_date.replace("Z", "")) if start_date else None
    end_dt = datetime.fromisoformat(end_date.replace("Z", "")) if end_date else None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"logs/audit/export_{ts}.{format}"
    audit_logger.export_audit_trail(output_file=out, start_date=start_dt, end_date=end_dt, format=format)
    return {"success": True, "export_file": out, "generated_at": datetime.utcnow().isoformat() + "Z"}


if __name__ == "__main__":
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=False)
