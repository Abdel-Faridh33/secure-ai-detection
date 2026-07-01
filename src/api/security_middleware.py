"""
Middleware de sécurité pour l'API
Zone 4 - Production Security

Intégration :
- WAF (rate limiting + validation)
- Détection d'anomalies en temps réel
- Logs de sécurité
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time

from src.security.waf import waf
from src.security.anomaly_detector import anomaly_detector
from src.monitoring.audit_logger import audit_logger, SeverityLevel
from src.monitoring.metrics import security_attacks_blocked_total


WAF_EXEMPT_PATHS = {
    "/security/waf/status",
    "/security/waf/blocked-ips",
    "/security/waf/unblock",
    "/security/login",
    "/security/register",
    "/docs",
    "/openapi.json",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware de sécurité qui protège tous les endpoints
    """

    async def dispatch(self, request: Request, call_next):
        """
        Traiter chaque requête avec les checks de sécurité
        """
        start_time = time.time()

        # Récupérer l'IP du client
        client_ip = request.client.host if request.client else "unknown"

        path = str(request.url.path)

        # 1. Vérification WAF (rate limiting + validation)
        # Exemption pour les endpoints d'administration WAF (évite de bloquer l'admin)
        if path in WAF_EXEMPT_PATHS:
            return await call_next(request)

        filename = None
        waf_result = waf.check_request(ip=client_ip, filename=filename)

        if not waf_result["allowed"]:
            reason = waf_result.get("reason", "rate_limit")
            # Incrémenter le compteur Prometheus AVANT de retourner la réponse
            security_attacks_blocked_total.labels(reason=reason).inc()
            audit_logger.log_event(
                event_type="security_block",
                severity=SeverityLevel.SECURITY_ALERT,
                description=f"WAF blocked request: {reason}",
                user_id="unknown",
                client_ip=client_ip,
                metadata={
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "reason": reason,
                    "request_count": waf_result["request_count"]
                }
            )

            # Retourner une réponse 429 avec headers CORS pour que le browser puisse lire le statut
            origin = request.headers.get("origin", "")
            cors_headers = {}
            if origin:
                cors_headers["Access-Control-Allow-Origin"] = origin
                cors_headers["Access-Control-Allow-Credentials"] = "true"
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": waf_result["reason"],
                    "retry_after": 300
                },
                headers=cors_headers
            )

        try:
            # Exécuter la requête
            response = await call_next(request)

            # Calculer le temps de traitement
            processing_time_ms = (time.time() - start_time) * 1000

            # 2. Détection d'anomalies en temps réel
            anomaly_result = anomaly_detector.analyze_request(
                ip=client_ip,
                endpoint=str(request.url.path),
                status_code=response.status_code
            )

            # Si anomalies critiques détectées
            if anomaly_result["should_block"]:
                # Log d'alerte de sécurité
                audit_logger.log_event(
                    event_type="anomaly_critical",
                    severity=SeverityLevel.CRITICAL,
                    description=f"Critical anomaly detected - blocking IP",
                    user_id="unknown",
                    client_ip=client_ip,
                    metadata={
                        "anomalies": anomaly_result["anomalies"],
                        "risk_score": anomaly_result["risk_score"],
                        "risk_level": anomaly_result["risk_level"]
                    }
                )

                # Bloquer la réponse
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Access denied",
                        "detail": "Suspicious activity detected",
                        "risk_level": anomaly_result["risk_level"]
                    }
                )

            # Log d'anomalies détectées (non-critiques)
            if anomaly_result["anomalies_detected"]:
                audit_logger.log_event(
                    event_type="anomaly_detected",
                    severity=SeverityLevel.WARNING,
                    description=f"Anomalies detected but allowed",
                    user_id="unknown",
                    client_ip=client_ip,
                    metadata={
                        "anomalies": anomaly_result["anomalies"],
                        "risk_score": anomaly_result["risk_score"]
                    }
                )

            return response

        except Exception as e:
            # Log d'erreur
            processing_time_ms = (time.time() - start_time) * 1000

            audit_logger.log_event(
                event_type="system_error",
                severity=SeverityLevel.CRITICAL,
                description=f"Error processing request: {str(e)}",
                user_id="unknown",
                client_ip=client_ip,
                metadata={
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "error": str(e)
                }
            )

            raise


