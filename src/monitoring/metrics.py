"""
Métriques Prometheus partagées — importées par app.py et security_middleware.py.
Définies ici une seule fois pour éviter ValueError: Duplicated timeseries.
"""

from prometheus_client import Counter, Histogram

http_requests_total = Counter(
    "http_requests_total",
    "Total des requêtes HTTP",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Durée des requêtes HTTP en secondes",
    ["endpoint"],
)

ai_predictions_total = Counter(
    "ai_predictions_total",
    "Total des prédictions IA par classe",
    ["prediction", "source"],
)

ai_processing_seconds = Histogram(
    "ai_processing_seconds",
    "Temps d'inférence du modèle MobileNetV2",
)

security_attacks_blocked_total = Counter(
    "security_attacks_blocked_total",
    "Requêtes bloquées par le WAF (rate limiting, payload suspect, adversarial)",
    ["reason"],
)
