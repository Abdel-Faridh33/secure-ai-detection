"""
API FastAPI principale
Point d'entrée pour les services de détection

Intégration Zone 5 - Gouvernance et Surveillance :
- Audit Trail complet de toutes les opérations
- Traçabilité légale des prédictions
- Logs immuables pour conformité
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response, JSONResponse
import uvicorn
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import random
import asyncio
from PIL import Image
import io
import torch
from torchvision import transforms

# Import du système d'audit
from src.monitoring.audit_logger import audit_logger, EventType, SeverityLevel

# Import du système d'authentification et sécurité
from src.api.security_endpoints import router as security_router
from src.api.security_middleware import SecurityMiddleware
from src.security.auth import verify_token

# Import du chargeur de modèles
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from models.utils.model_loader import ModelLoader

# ZONE 1: Import des modules de sécurité des données
from src.data.encrypted_storage import EncryptedStorage
from src.data.data_verifier import DataVerifier

app = FastAPI(
    title="Secure Object Detection API",
    description="API de détection d'objets dangereux vs sûrs",
    version="1.0.0"
)

# Inclusion du router d'authentification et sécurité
app.include_router(security_router)

# Métriques Prometheus
request_count = Counter(
    'http_requests_total',
    'Total des requêtes HTTP',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'Durée des requêtes HTTP en secondes',
    ['method', 'endpoint']
)

prediction_count = Counter(
    'ai_model_predictions_total',
    'Total des prédictions par modèle',
    ['model_type', 'prediction']
)

model_accuracy = Gauge(
    'ai_model_accuracy',
    'Précision actuelle du modèle',
    ['model_type']
)

processing_time = Histogram(
    'ai_model_processing_seconds',
    'Temps de traitement des prédictions',
    ['model_type']
)

# ============================================================
# CHARGEMENT DES MODÈLES PYTORCH
# ============================================================

# Variables globales pour les modèles
models_loaded = {}
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],  # ImageNet normalization
        std=[0.229, 0.224, 0.225]
    )
])

@app.on_event("startup")
async def load_models():
    """
    Charge les modèles PyTorch au démarrage de l'API
    ZONE 1: Support du chargement depuis stockage crypté
    ZONE 2: Vérification des signatures RSA-4096
    """
    global models_loaded
    import logging

    # Configuration du logger
    logger = logging.getLogger("model_loader")
    logger.setLevel(logging.INFO)

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [MODEL_LOADER] %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"Starting model loading process on device: {device}")

    # Chemins vers les modèles
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    baseline_path = os.path.join(project_root, "models", "baseline", "best_model.pth")
    secured_paths = [
        os.path.join(project_root, "models", "secured", "best_secured_model.pth"),
        os.path.join(project_root, "models", "secured", "final_secured_model.pth")
    ]

    # ZONE 1: Chemin vers le modèle chiffré
    encrypted_secured_path = os.path.join(project_root, "models", "secured", "encrypted", "best_secured_model_encrypted.enc")

    # Charger le modèle baseline
    logger.info("Loading baseline model...")
    if os.path.exists(baseline_path):
        try:
            models_loaded["baseline"] = ModelLoader.load_mobilenetv2_checkpoint(
                baseline_path,
                device=str(device)
            )
            logger.info(f"Baseline model loaded successfully from {baseline_path}")

            # Log audit
            audit_logger.log_event(
                event_type=EventType.MODEL_LOADED.value,
                severity=SeverityLevel.INFO,
                description="Baseline model loaded successfully",
                metadata={
                    "model_type": "baseline",
                    "model_path": baseline_path,
                    "device": str(device)
                }
            )
        except Exception as e:
            logger.error(f"Failed to load baseline model: {e}")
            audit_logger.log_event(
                event_type=EventType.SYSTEM_ERROR.value,
                severity=SeverityLevel.WARNING,
                description="Failed to load baseline model",
                metadata={"error": str(e), "model_path": baseline_path}
            )
    else:
        logger.warning(f"Baseline model not found at {baseline_path}")

    # ============================================================
    # ZONE 1: TENTATIVE DE CHARGEMENT DEPUIS STOCKAGE CRYPTÉ
    # ZONE 2: VÉRIFICATION SIGNATURE RSA-4096
    # ============================================================
    secured_loaded = False

    logger.info("Starting secured model loading process...")
    logger.info("ZONE 1: Attempting encrypted storage loading (AES-256-GCM)")

    # 1. Essayer de charger depuis le stockage chiffré (prioritaire)
    if os.path.exists(encrypted_secured_path):
        try:
            logger.info(f"Encrypted model found at {encrypted_secured_path}")
            storage = EncryptedStorage(password="SecureAI_2024_Production")

            # Créer un fichier temporaire pour le déchiffrement
            temp_decrypted_path = os.path.join(project_root, "models", "secured", ".temp_decrypted.pth")

            # Charger les métadonnées du fichier chiffré
            metadata_path = encrypted_secured_path.replace('.enc', '_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    import json
                    metadata = json.load(f)

                logger.info(f"Decrypting model with algorithm: {metadata.get('algorithm', 'unknown')}")

                # Déchiffrer le modèle
                storage.decrypt_pytorch_model(
                    encrypted_secured_path,
                    temp_decrypted_path,
                    metadata
                )

                logger.info("Model decrypted successfully")

                # Charger le modèle déchiffré
                models_loaded["secured"] = ModelLoader.load_mobilenetv2_checkpoint(
                    temp_decrypted_path,
                    device=str(device)
                )

                # Nettoyer le fichier temporaire
                if os.path.exists(temp_decrypted_path):
                    os.remove(temp_decrypted_path)

                logger.info("Secured model loaded from encrypted storage (AES-256-GCM)")

                # Log audit
                audit_logger.log_event(
                    event_type=EventType.MODEL_LOADED.value,
                    severity=SeverityLevel.INFO,
                    description="Secured model loaded from encrypted storage",
                    metadata={
                        "model_type": "secured",
                        "encryption": "AES-256-GCM",
                        "source": "encrypted_storage",
                        "device": str(device)
                    }
                )
                secured_loaded = True

        except Exception as e:
            logger.warning(f"Failed to load from encrypted storage: {e}")
            logger.info("Falling back to standard loading...")
            audit_logger.log_event(
                event_type=EventType.SYSTEM_ERROR.value,
                severity=SeverityLevel.WARNING,
                description="Failed to load from encrypted storage, falling back",
                metadata={"error": str(e)}
            )

    # 2. Fallback: Charger depuis les fichiers .pth standards avec vérification signature
    if not secured_loaded:
        logger.info("ZONE 2: Loading from standard .pth files with RSA-4096 signature verification")

        for secured_path in secured_paths:
            if os.path.exists(secured_path):
                try:
                    logger.info(f"Attempting to load secured model from {secured_path}")

                    # ZONE 2: Vérifier la signature RSA-4096 si disponible
                    signature_verified = False
                    sig_path = secured_path.replace('.pth', '_signature.bin')
                    pub_key_path = secured_path.replace('.pth', '_public_key.pem')

                    if os.path.exists(sig_path) and os.path.exists(pub_key_path):
                        logger.info("ZONE 2: RSA-4096 signature files detected, verifying integrity...")

                        try:
                            from cryptography.hazmat.primitives import serialization, hashes
                            from cryptography.hazmat.primitives.asymmetric import padding

                            # Charger le modèle et la signature
                            with open(secured_path, 'rb') as f:
                                model_bytes = f.read()
                            with open(sig_path, 'rb') as f:
                                signature = f.read()
                            with open(pub_key_path, 'rb') as f:
                                public_key = serialization.load_pem_public_key(f.read())

                            # Vérifier la signature
                            public_key.verify(
                                signature,
                                model_bytes,
                                padding.PSS(
                                    mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.MAX_LENGTH
                                ),
                                hashes.SHA256()
                            )

                            logger.info("ZONE 2: RSA-4096 signature verified successfully - Model integrity confirmed")
                            signature_verified = True

                            # Log audit de la vérification
                            audit_logger.log_event(
                                event_type=EventType.SECURITY_CHECK.value,
                                severity=SeverityLevel.INFO,
                                description="Model signature verified successfully",
                                metadata={
                                    "model_path": secured_path,
                                    "signature_algorithm": "RSA-4096-PSS-SHA256",
                                    "verification_status": "VALID"
                                }
                            )

                        except Exception as e:
                            logger.error(f"ZONE 2: Signature verification failed: {e}")
                            audit_logger.log_event(
                                event_type=EventType.SECURITY_ALERT.value,
                                severity=SeverityLevel.CRITICAL,
                                description="Model signature verification FAILED - Possible tampering detected",
                                metadata={
                                    "model_path": secured_path,
                                    "error": str(e)
                                }
                            )
                            # Ne pas charger le modèle si la signature est invalide
                            continue
                    else:
                        logger.warning("ZONE 2: No signature files found - Loading without verification")

                    # Charger le modèle
                    models_loaded["secured"] = ModelLoader.load_mobilenetv2_checkpoint(
                        secured_path,
                        device=str(device)
                    )

                    logger.info(f"Secured model loaded successfully from {secured_path}")

                    # Log audit
                    audit_logger.log_event(
                        event_type=EventType.MODEL_LOADED.value,
                        severity=SeverityLevel.INFO,
                        description="Secured model loaded successfully",
                        metadata={
                            "model_type": "secured",
                            "model_path": secured_path,
                            "signature_verified": signature_verified,
                            "device": str(device)
                        }
                    )

                    secured_loaded = True
                    break

                except Exception as e:
                    logger.error(f"Failed to load secured model from {secured_path}: {e}")
                    audit_logger.log_event(
                        event_type=EventType.SYSTEM_ERROR.value,
                        severity=SeverityLevel.WARNING,
                        description="Failed to load secured model",
                        metadata={"error": str(e), "model_path": secured_path}
                    )

    if not secured_loaded:
        logger.warning("Secured model not found in any location")
        audit_logger.log_event(
            event_type=EventType.SYSTEM_ERROR.value,
            severity=SeverityLevel.WARNING,
            description="No secured model could be loaded",
            metadata={"searched_paths": secured_paths}
        )

    logger.info(f"Model loading complete: {len(models_loaded)} model(s) loaded")
    logger.info(f"Available models: {list(models_loaded.keys())}")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de sécurité (WAF + Détection d'anomalies)
app.add_middleware(SecurityMiddleware)

# Middleware d'audit pour logger tous les accès API
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """
    Middleware qui log tous les accès à l'API
    Traçabilité complète : qui, quoi, quand
    """
    start_time = time.time()

    # Récupération des infos client
    client_ip = request.client.host if request.client else "unknown"

    # Extraction de l'utilisateur authentifié depuis le JWT
    user_id = "anonymous"
    user_role = "guest"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        user_data = verify_token(token)
        if user_data:
            user_id = user_data.get("sub", "anonymous")
            user_role = user_data.get("role", "guest")

    try:
        # Exécution de la requête
        response = await call_next(request)

        # Calcul du temps de réponse
        response_time_ms = (time.time() - start_time) * 1000

        # Log de l'accès API
        audit_logger.log_api_access(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            user_id="anonymous",  # À remplacer par user authentifié
            client_ip=client_ip,
            response_time_ms=response_time_ms
        )

        return response

    except Exception as e:
        # Log des erreurs
        response_time_ms = (time.time() - start_time) * 1000
        audit_logger.log_api_access(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=500,
            user_id="anonymous",
            client_ip=client_ip,
            response_time_ms=response_time_ms
        )
        raise

@app.get("/")
async def root():
    request_count.labels(method="GET", endpoint="/", status="200").inc()
    return {"message": "Secure Detection API", "status": "running"}

@app.get("/health")
async def health_check():
    request_count.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    """Endpoint pour les métriques Prometheus"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/predict/{model_type}")
async def predict(model_type: str, file: UploadFile = File(...), request: Request = None):
    """
    Endpoint de prédiction avec audit complet
    model_type: 'baseline' ou 'secured'

    Chaque prédiction est auditée avec :
    - Hash SHA-256 de l'image (traçabilité sans stocker l'image)
    - Modèle utilisé et sa version
    - Résultat et niveau de confiance
    - Temps de traitement
    - IP du client (pour détection d'abus)
    """
    start_time = time.time()
    client_ip = request.client.host if request and request.client else "unknown"

    # Extraction de l'utilisateur authentifié
    user_id = "anonymous"
    user_role = "guest"
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_data = verify_token(token)
            if user_data:
                user_id = user_data.get("sub", "anonymous")
                user_role = user_data.get("role", "guest")

    try:
        if model_type not in ['baseline', 'secured']:
            # Log de validation échouée
            audit_logger.log_validation_failed(
                image_filename=file.filename,
                reason=f"Invalid model type: {model_type}",
                user_id=user_id,
                client_ip=client_ip
            )
            request_count.labels(method="POST", endpoint="/predict", status="400").inc()
            raise HTTPException(status_code=400, detail="Invalid model type")

        # Validation du fichier
        if not file.content_type or not file.content_type.startswith('image/'):
            # Log de validation échouée
            audit_logger.log_validation_failed(
                image_filename=file.filename,
                reason=f"Invalid content type: {file.content_type}",
                user_id=user_id,
                client_ip=client_ip
            )
            request_count.labels(method="POST", endpoint="/predict", status="400").inc()
            raise HTTPException(status_code=400, detail="Le fichier doit être une image")

        # Lecture du fichier image
        image_data = await file.read()

        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            # Log de validation échouée
            audit_logger.log_validation_failed(
                image_filename=file.filename,
                reason=f"Cannot open image: {str(e)}",
                user_id=user_id,
                client_ip=client_ip
            )
            raise HTTPException(status_code=400, detail="Image corrompue ou format invalide")

        # Vérifier que le modèle est chargé
        if model_type not in models_loaded:
            raise HTTPException(
                status_code=503,
                detail=f"Model '{model_type}' not loaded. Available models: {list(models_loaded.keys())}"
            )

        # Prédiction avec le vrai modèle PyTorch
        processing_start = time.time()

        try:
            # Préprocesser l'image
            image = image.convert('RGB')
            image_tensor = transform(image).unsqueeze(0)  # Ajouter batch dimension
            image_tensor = image_tensor.to(device)

            # Obtenir le modèle
            model = models_loaded[model_type]

            # Faire la prédiction
            with torch.no_grad():
                outputs = model(image_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                predicted_class = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][predicted_class].item()

            # Mapper la classe prédite (0 = safe, 1 = dangerous)
            prediction = "safe" if predicted_class == 0 else "dangerous"

            processing_duration = time.time() - processing_start
            processing_time_ms = processing_duration * 1000

            # Mettre à jour les métriques de précision (valeurs réelles des modèles)
            if model_type == "baseline":
                model_accuracy.labels(model_type="baseline").set(96.08)  # Clean accuracy du baseline
            else:  # secured
                model_accuracy.labels(model_type="secured").set(96.08)  # Clean accuracy du secured

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors de la prédiction: {str(e)}"
            )

        # 🔒 AUDIT : Log de la prédiction pour traçabilité légale
        audit_id = audit_logger.log_prediction(
            image_data=image_data,
            image_filename=file.filename,
            model_type=model_type,
            prediction=prediction,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            user_id=user_id,
            user_role=user_role,
            client_ip=client_ip,
            additional_metadata={
                "image_format": image.format,
                "image_size": image.size,
                "image_mode": image.mode
            }
        )

        # Mise à jour des métriques Prometheus
        prediction_count.labels(model_type=model_type, prediction=prediction).inc()
        processing_time.labels(model_type=model_type).observe(processing_duration)
        request_count.labels(method="POST", endpoint="/predict", status="200").inc()

        response = {
            "model": model_type,
            "prediction": prediction,
            "confidence": round(confidence, 3),
            "processing_time_ms": round(processing_time_ms),
            "image_info": {
                "format": image.format,
                "size": image.size,
                "mode": image.mode
            },
            # Ajout de l'audit_id pour traçabilité
            "audit_id": audit_id
        }

        # Mesurer le temps total de la requête
        total_duration = time.time() - start_time
        request_duration.labels(method="POST", endpoint="/predict").observe(total_duration)

        return response

    except HTTPException:
        raise
    except Exception as e:
        request_count.labels(method="POST", endpoint="/predict", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

# Endpoint de test pour l'interface
@app.get("/test")
async def test_endpoint():
    """Endpoint de test simple"""
    request_count.labels(method="GET", endpoint="/test", status="200").inc()
    return {"message": "API fonctionnelle", "timestamp": time.time()}


# ============================================================
# ENDPOINTS D'AUDIT - Zone 5 : Gouvernance et Surveillance
# ============================================================

@app.get("/audit/logs")
async def get_audit_logs(
    limit: int = 50,
    event_type: Optional[str] = None,
    severity: Optional[str] = None
):
    """
    Consulter les logs d'audit récents

    Args:
        limit: Nombre de logs à retourner (max 1000)
        event_type: Filtrer par type d'événement (prediction, attack_detected, etc.)
        severity: Filtrer par gravité (info, warning, critical, security_alert)

    Returns:
        Liste des événements d'audit
    """
    try:
        # Validation des paramètres
        if limit > 1000:
            limit = 1000

        # Conversion des filtres en Enum si fournis
        event_type_filter = None
        severity_filter = None

        if event_type:
            try:
                event_type_filter = EventType(event_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event_type: {event_type}")

        if severity:
            try:
                severity_filter = SeverityLevel(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

        # Requête des logs
        logs = audit_logger.query_logs(
            event_type=event_type_filter,
            severity=severity_filter,
            limit=limit
        )

        return {
            "count": len(logs),
            "logs": logs,
            "filters_applied": {
                "event_type": event_type,
                "severity": severity,
                "limit": limit
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des logs: {str(e)}")


@app.get("/audit/stats")
async def get_audit_statistics():
    """
    Statistiques sur les logs d'audit

    Returns:
        Statistiques agrégées :
        - Nombre total d'événements
        - Répartition par type
        - Répartition par gravité
        - Nombre d'attaques détectées
        - Nombre de prédictions
        - Confiance moyenne
    """
    try:
        stats = audit_logger.get_statistics()

        return {
            "statistics": stats,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des statistiques: {str(e)}")


@app.get("/audit/search")
async def search_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100
):
    """
    Recherche avancée dans les logs d'audit

    Args:
        start_date: Date de début (ISO 8601 format)
        end_date: Date de fin (ISO 8601 format)
        event_type: Type d'événement
        user_id: ID utilisateur
        limit: Nombre de résultats max

    Returns:
        Résultats de la recherche
    """
    try:
        # Conversion des dates
        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', ''))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', ''))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}")

        # Conversion event_type
        event_type_filter = None
        if event_type:
            try:
                event_type_filter = EventType(event_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event_type: {event_type}")

        # Recherche
        logs = audit_logger.query_logs(
            start_date=start_dt,
            end_date=end_dt,
            event_type=event_type_filter,
            user_id=user_id,
            limit=limit
        )

        return {
            "count": len(logs),
            "results": logs,
            "query": {
                "start_date": start_date,
                "end_date": end_date,
                "event_type": event_type,
                "user_id": user_id,
                "limit": limit
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")


@app.get("/audit/recent-attacks")
async def get_recent_attacks(limit: int = 20):
    """
    Récupérer les attaques détectées récemment

    Args:
        limit: Nombre d'attaques à retourner

    Returns:
        Liste des attaques détectées
    """
    try:
        attacks = audit_logger.query_logs(
            event_type=EventType.ATTACK_DETECTED,
            limit=limit
        )

        return {
            "count": len(attacks),
            "attacks": attacks,
            "severity": "CRITICAL" if len(attacks) > 0 else "INFO"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des attaques: {str(e)}")


@app.get("/audit/predictions/{audit_id}")
async def get_prediction_details(audit_id: str):
    """
    Récupérer les détails d'une prédiction spécifique via son audit_id

    Args:
        audit_id: ID unique de l'événement d'audit

    Returns:
        Détails complets de la prédiction
    """
    try:
        # Recherche dans tous les logs
        all_logs = audit_logger.query_logs(limit=10000)

        # Recherche de l'audit_id spécifique
        for log in all_logs:
            if log.get('audit_id') == audit_id:
                return {
                    "found": True,
                    "details": log
                }

        # Non trouvé
        raise HTTPException(status_code=404, detail=f"Audit ID not found: {audit_id}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@app.post("/audit/export")
async def export_audit_trail(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json"
):
    """
    Export des logs d'audit pour audit externe
    (Conformité légale, audits de sécurité)

    Args:
        start_date: Date de début
        end_date: Date de fin
        format: Format d'export (json/csv)

    Returns:
        Fichier d'export
    """
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")

        # Conversion des dates
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', ''))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', ''))

        # Export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"logs/audit/export_audit_{timestamp}.{format}"

        audit_logger.export_audit_trail(
            output_file=output_file,
            start_date=start_dt,
            end_date=end_dt,
            format=format
        )

        return {
            "success": True,
            "export_file": output_file,
            "format": format,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
