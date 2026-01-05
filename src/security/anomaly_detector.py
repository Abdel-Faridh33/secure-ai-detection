"""
Détection d'anomalies en temps réel
Zone 4 - Production Security

Fonctionnalités :
- Détection de patterns d'attaques
- Analyse de comportement utilisateur
- Scoring de risque
- Alertes automatiques
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from enum import Enum


class AnomalyType(Enum):
    """Types d'anomalies détectées"""
    SUSPICIOUS_PATTERN = "suspicious_pattern"      # Pattern suspect dans les requêtes
    BURST_ACTIVITY = "burst_activity"              # Pic d'activité soudain
    REPEATED_FAILURES = "repeated_failures"        # Échecs répétés
    UNUSUAL_TIMING = "unusual_timing"              # Horaires inhabituels
    CONFIDENCE_DROP = "confidence_drop"            # Chute de confiance modèle
    MODEL_SWITCHING = "model_switching"            # Changements de modèle suspects


class RiskLevel(Enum):
    """Niveaux de risque"""
    LOW = "low"           # Niveau 1 - Surveiller
    MEDIUM = "medium"     # Niveau 2 - Alerte
    HIGH = "high"         # Niveau 3 - Bloquer
    CRITICAL = "critical" # Niveau 4 - Incident sécurité


class AnomalyDetector:
    """
    Détecteur d'anomalies en temps réel
    Analyse le comportement et détecte les patterns suspects
    """

    def __init__(self):
        # Historique des requêtes par IP
        self.request_history: Dict[str, List[Dict]] = defaultdict(list)

        # Historique des échecs par IP
        self.failure_history: Dict[str, List[datetime]] = defaultdict(list)

        # Score de risque par IP
        self.risk_scores: Dict[str, float] = defaultdict(float)

        # Anomalies détectées
        self.detected_anomalies: List[Dict] = []

    def analyze_request(
        self,
        ip: str,
        endpoint: str,
        model_type: Optional[str] = None,
        prediction: Optional[str] = None,
        confidence: Optional[float] = None,
        status_code: int = 200
    ) -> Dict:
        """
        Analyser une requête pour détecter des anomalies

        Args:
            ip: Adresse IP du client
            endpoint: Endpoint appelé
            model_type: Type de modèle utilisé (baseline/secured)
            prediction: Résultat de la prédiction
            confidence: Niveau de confiance
            status_code: Code de statut HTTP

        Returns:
            Résultat de l'analyse avec anomalies détectées
        """
        now = datetime.utcnow()
        anomalies = []
        risk_level = RiskLevel.LOW

        # Enregistrer la requête
        request_data = {
            "timestamp": now,
            "endpoint": endpoint,
            "model_type": model_type,
            "prediction": prediction,
            "confidence": confidence,
            "status_code": status_code
        }
        self.request_history[ip].append(request_data)

        # Nettoyer l'historique (garder 24h)
        cutoff_time = now - timedelta(hours=24)
        self.request_history[ip] = [
            req for req in self.request_history[ip]
            if req["timestamp"] > cutoff_time
        ]

        # 1. Détection de burst d'activité
        burst_anomaly = self._detect_burst_activity(ip)
        if burst_anomaly:
            anomalies.append(burst_anomaly)
            risk_level = max(risk_level, RiskLevel.MEDIUM, key=lambda x: list(RiskLevel).index(x))

        # 2. Détection d'échecs répétés
        if status_code >= 400:
            self.failure_history[ip].append(now)
            failure_anomaly = self._detect_repeated_failures(ip)
            if failure_anomaly:
                anomalies.append(failure_anomaly)
                risk_level = max(risk_level, RiskLevel.HIGH, key=lambda x: list(RiskLevel).index(x))

        # 3. Détection de timing inhabituel
        timing_anomaly = self._detect_unusual_timing(ip)
        if timing_anomaly:
            anomalies.append(timing_anomaly)
            risk_level = max(risk_level, RiskLevel.LOW, key=lambda x: list(RiskLevel).index(x))

        # 4. Détection de chute de confiance
        if confidence is not None:
            confidence_anomaly = self._detect_confidence_drop(ip, confidence)
            if confidence_anomaly:
                anomalies.append(confidence_anomaly)
                risk_level = max(risk_level, RiskLevel.MEDIUM, key=lambda x: list(RiskLevel).index(x))

        # 5. Détection de changements de modèle suspects
        if model_type:
            switching_anomaly = self._detect_model_switching(ip, model_type)
            if switching_anomaly:
                anomalies.append(switching_anomaly)
                risk_level = max(risk_level, RiskLevel.MEDIUM, key=lambda x: list(RiskLevel).index(x))

        # Calculer le score de risque
        risk_score = self._calculate_risk_score(ip, anomalies)
        self.risk_scores[ip] = risk_score

        # Sauvegarder les anomalies détectées
        if anomalies:
            for anomaly in anomalies:
                self.detected_anomalies.append({
                    "ip": ip,
                    "timestamp": now.isoformat() + "Z",
                    "anomaly": anomaly,
                    "risk_level": risk_level.value,
                    "risk_score": risk_score
                })

        return {
            "anomalies_detected": len(anomalies) > 0,
            "anomalies": anomalies,
            "risk_level": risk_level.value,
            "risk_score": risk_score,
            "should_block": risk_level == RiskLevel.CRITICAL
        }

    def _detect_burst_activity(self, ip: str) -> Optional[Dict]:
        """Détecter un burst d'activité (trop de requêtes en peu de temps)"""
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(minutes=5)

        recent_requests = [
            req for req in self.request_history[ip]
            if req["timestamp"] > recent_cutoff
        ]

        # Seuil : plus de 50 requêtes en 5 minutes
        if len(recent_requests) > 50:
            return {
                "type": AnomalyType.BURST_ACTIVITY.value,
                "description": f"{len(recent_requests)} requests in 5 minutes",
                "severity": "high",
                "count": len(recent_requests)
            }
        return None

    def _detect_repeated_failures(self, ip: str) -> Optional[Dict]:
        """Détecter des échecs répétés"""
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(minutes=10)

        # Nettoyer l'historique
        self.failure_history[ip] = [
            fail_time for fail_time in self.failure_history[ip]
            if fail_time > recent_cutoff
        ]

        # Seuil : plus de 10 échecs en 10 minutes
        if len(self.failure_history[ip]) > 10:
            return {
                "type": AnomalyType.REPEATED_FAILURES.value,
                "description": f"{len(self.failure_history[ip])} failures in 10 minutes",
                "severity": "high",
                "count": len(self.failure_history[ip])
            }
        return None

    def _detect_unusual_timing(self, ip: str) -> Optional[Dict]:
        """Détecter des horaires inhabituels (activité nocturne)"""
        now = datetime.utcnow()
        hour = now.hour

        # Heures inhabituelles : 2h-6h UTC
        if 2 <= hour < 6:
            recent_count = len([
                req for req in self.request_history[ip]
                if (now - req["timestamp"]).total_seconds() < 3600  # Dernière heure
            ])

            # Si plus de 5 requêtes dans l'heure durant ces heures
            if recent_count > 5:
                return {
                    "type": AnomalyType.UNUSUAL_TIMING.value,
                    "description": f"Activity during unusual hours (UTC {hour}:00)",
                    "severity": "low",
                    "hour": hour
                }
        return None

    def _detect_confidence_drop(self, ip: str, current_confidence: float) -> Optional[Dict]:
        """Détecter une chute de confiance soudaine"""
        recent_requests = self.request_history[ip][-10:]  # 10 dernières requêtes

        if len(recent_requests) < 5:
            return None

        # Calculer la confiance moyenne des requêtes précédentes
        previous_confidences = [
            req["confidence"] for req in recent_requests[:-1]
            if req.get("confidence") is not None
        ]

        if not previous_confidences:
            return None

        avg_confidence = sum(previous_confidences) / len(previous_confidences)

        # Si la confiance actuelle est 20% plus basse que la moyenne
        if current_confidence < avg_confidence - 0.2:
            return {
                "type": AnomalyType.CONFIDENCE_DROP.value,
                "description": f"Confidence drop: {avg_confidence:.2f} -> {current_confidence:.2f}",
                "severity": "medium",
                "previous_avg": avg_confidence,
                "current": current_confidence
            }
        return None

    def _detect_model_switching(self, ip: str, current_model: str) -> Optional[Dict]:
        """Détecter des changements de modèle fréquents (potentiellement suspect)"""
        recent_requests = self.request_history[ip][-20:]  # 20 dernières requêtes

        if len(recent_requests) < 10:
            return None

        # Compter les changements de modèle
        model_switches = 0
        prev_model = None

        for req in recent_requests:
            if req.get("model_type"):
                if prev_model and prev_model != req["model_type"]:
                    model_switches += 1
                prev_model = req["model_type"]

        # Si plus de 5 changements de modèle
        if model_switches > 5:
            return {
                "type": AnomalyType.MODEL_SWITCHING.value,
                "description": f"{model_switches} model switches in recent requests",
                "severity": "medium",
                "switches": model_switches
            }
        return None

    def _calculate_risk_score(self, ip: str, anomalies: List[Dict]) -> float:
        """
        Calculer un score de risque (0-100)

        Args:
            ip: Adresse IP
            anomalies: Liste des anomalies détectées

        Returns:
            Score de risque (0-100)
        """
        base_score = self.risk_scores.get(ip, 0.0)

        # Décrémenter le score de base (décroissance naturelle)
        base_score = max(0.0, base_score - 1.0)

        # Ajouter des points pour chaque anomalie
        severity_scores = {
            "low": 10,
            "medium": 25,
            "high": 40,
            "critical": 60
        }

        for anomaly in anomalies:
            severity = anomaly.get("severity", "low")
            base_score += severity_scores.get(severity, 10)

        # Limiter le score à 100
        return min(100.0, base_score)

    def get_high_risk_ips(self, threshold: float = 50.0) -> List[Dict]:
        """
        Obtenir les IPs à haut risque

        Args:
            threshold: Seuil de score de risque

        Returns:
            Liste des IPs à risque avec leurs scores
        """
        high_risk = []
        for ip, score in self.risk_scores.items():
            if score >= threshold:
                high_risk.append({
                    "ip": ip,
                    "risk_score": score,
                    "recent_anomalies": len([
                        a for a in self.detected_anomalies
                        if a["ip"] == ip
                    ])
                })

        # Trier par score décroissant
        high_risk.sort(key=lambda x: x["risk_score"], reverse=True)
        return high_risk

    def get_recent_anomalies(self, limit: int = 50) -> List[Dict]:
        """Obtenir les anomalies récentes"""
        return self.detected_anomalies[-limit:]


# Instance globale du détecteur
anomaly_detector = AnomalyDetector()
