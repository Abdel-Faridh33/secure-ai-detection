"""
Monitoring Metrics
Métriques de surveillance
"""

from prometheus_client import Counter, Histogram, Gauge

# Métriques Prometheus
request_count = Counter('api_requests_total', 'Total API requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
model_accuracy = Gauge('model_accuracy', 'Current model accuracy')
attack_attempts = Counter('attack_attempts_total', 'Total attack attempts detected')
