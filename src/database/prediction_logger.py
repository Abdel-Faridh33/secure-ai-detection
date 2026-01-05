"""
Logger de prédictions pour historique long terme

Enregistre toutes les prédictions dans PostgreSQL pour :
- Analytics au-delà de 30 jours (limite Prometheus)
- Rapports personnalisés SQL
- Comparaison de modèles
- Détection de drift
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json

from .connection import get_db_connection

logger = logging.getLogger(__name__)


class PredictionLogger:
    """Logger de prédictions avec historique illimité"""

    def __init__(self):
        """Initialise le logger"""
        self.db = get_db_connection()

    # ==================== ENREGISTREMENT ====================

    def log_prediction(
        self,
        model_type: str,
        model_version: str,
        image_hash: str,
        prediction_result: str,
        confidence: float,
        processing_time_ms: float,
        user_id: Optional[int] = None,
        image_filename: Optional[str] = None,
        image_size_bytes: Optional[int] = None,
        client_ip: Optional[str] = None,
        attack_detected: bool = False,
        attack_type: Optional[str] = None,
        defense_triggered: bool = False,
        defense_type: Optional[str] = None,
        audit_id: Optional[str] = None,
        raw_logits: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Enregistre une prédiction

        Args:
            model_type: Type de modèle (baseline, secured, etc.)
            model_version: Version du modèle
            image_hash: Hash SHA-256 de l'image
            prediction_result: Résultat ('dangerous' ou 'safe')
            confidence: Confiance (0-1)
            processing_time_ms: Temps de traitement en ms
            user_id: ID de l'utilisateur (si authentifié)
            image_filename: Nom du fichier image
            image_size_bytes: Taille de l'image
            client_ip: IP du client
            attack_detected: Attaque détectée ?
            attack_type: Type d'attaque (si détectée)
            defense_triggered: Défense activée ?
            defense_type: Type de défense
            audit_id: ID du log d'audit correspondant
            raw_logits: Logits bruts du modèle (JSON)
            metadata: Métadonnées supplémentaires (JSON)

        Returns:
            ID de la prédiction ou None si erreur
        """
        # Validation
        if prediction_result not in ['dangerous', 'safe']:
            raise ValueError(f"prediction_result invalide: {prediction_result}")

        if not (0 <= confidence <= 1):
            raise ValueError(f"confidence doit être entre 0 et 1: {confidence}")

        query = """
            INSERT INTO predictions (
                timestamp,
                processing_time_ms,
                user_id,
                client_ip,
                model_type,
                model_version,
                image_filename,
                image_hash,
                image_size_bytes,
                prediction_result,
                confidence,
                raw_logits,
                attack_detected,
                attack_type,
                defense_triggered,
                defense_type,
                audit_id,
                metadata
            ) VALUES (
                NOW(),
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """

        try:
            prediction_id = self.db.execute_insert(
                query,
                (
                    processing_time_ms,
                    user_id,
                    client_ip,
                    model_type,
                    model_version,
                    image_filename,
                    image_hash,
                    image_size_bytes,
                    prediction_result,
                    confidence,
                    json.dumps(raw_logits) if raw_logits else None,
                    attack_detected,
                    attack_type,
                    defense_triggered,
                    defense_type,
                    audit_id,
                    json.dumps(metadata) if metadata else None
                )
            )

            logger.debug(f"Prédiction enregistrée: ID={prediction_id}, result={prediction_result}, confidence={confidence:.2f}")
            return prediction_id

        except Exception as e:
            logger.error(f"Erreur enregistrement prédiction: {e}")
            return None

    def add_user_feedback(
        self,
        prediction_id: int,
        feedback: str,
        comment: Optional[str] = None
    ) -> bool:
        """
        Ajoute un feedback utilisateur à une prédiction

        Args:
            prediction_id: ID de la prédiction
            feedback: Feedback ('correct', 'incorrect', 'uncertain')
            comment: Commentaire optionnel

        Returns:
            True si ajouté, False sinon
        """
        if feedback not in ['correct', 'incorrect', 'uncertain']:
            raise ValueError(f"Feedback invalide: {feedback}")

        query = """
            UPDATE predictions
            SET user_feedback = %s,
                user_feedback_comment = %s,
                user_feedback_at = NOW()
            WHERE id = %s
        """

        try:
            self.db.execute_query(query, (feedback, comment, prediction_id), fetch=False)
            logger.info(f"Feedback ajouté à prédiction {prediction_id}: {feedback}")
            return True
        except Exception as e:
            logger.error(f"Erreur ajout feedback: {e}")
            return False

    # ==================== RÉCUPÉRATION ====================

    def get_prediction(self, prediction_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une prédiction par son ID"""
        query = "SELECT * FROM predictions WHERE id = %s"
        result = self.db.execute_query_dict(query, (prediction_id,))
        return result[0] if result else None

    def get_recent_predictions(
        self,
        limit: int = 100,
        model_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les prédictions récentes

        Args:
            limit: Nombre max de résultats
            model_type: Filtrer par type de modèle
            user_id: Filtrer par utilisateur

        Returns:
            Liste de prédictions
        """
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []

        if model_type:
            query += " AND model_type = %s"
            params.append(model_type)

        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        return self.db.execute_query_dict(query, tuple(params))

    def get_predictions_by_image(self, image_hash: str) -> List[Dict[str, Any]]:
        """Récupère toutes les prédictions pour une image spécifique"""
        query = """
            SELECT * FROM predictions
            WHERE image_hash = %s
            ORDER BY timestamp DESC
        """
        return self.db.execute_query_dict(query, (image_hash,))

    # ==================== ANALYTICS ====================

    def get_model_stats(
        self,
        model_type: str,
        model_version: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Récupère les statistiques d'un modèle

        Returns:
            Dictionnaire avec:
            - total_predictions
            - avg_confidence
            - dangerous_count
            - safe_count
            - avg_processing_time_ms
            - accuracy_rate (si feedback disponible)
        """
        query = """
            SELECT
                COUNT(*) as total_predictions,
                AVG(confidence) as avg_confidence,
                COUNT(*) FILTER (WHERE prediction_result = 'dangerous') as dangerous_count,
                COUNT(*) FILTER (WHERE prediction_result = 'safe') as safe_count,
                AVG(processing_time_ms) as avg_processing_time_ms,
                COUNT(*) FILTER (WHERE attack_detected = true) as attacks_detected,
                COUNT(*) FILTER (WHERE user_feedback = 'correct') as correct_feedback,
                COUNT(*) FILTER (WHERE user_feedback = 'incorrect') as incorrect_feedback,
                CASE
                    WHEN COUNT(*) FILTER (WHERE user_feedback IS NOT NULL) > 0
                    THEN COUNT(*) FILTER (WHERE user_feedback = 'correct')::FLOAT /
                         COUNT(*) FILTER (WHERE user_feedback IS NOT NULL)
                    ELSE NULL
                END as accuracy_rate
            FROM predictions
            WHERE model_type = %s
        """
        params = [model_type]

        if model_version:
            query += " AND model_version = %s"
            params.append(model_version)

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        result = self.db.execute_query_dict(query, tuple(params))
        return result[0] if result else {}

    def compare_models(
        self,
        model_a_type: str,
        model_b_type: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Compare deux modèles sur une période

        Args:
            model_a_type: Type du modèle A
            model_b_type: Type du modèle B
            days: Nombre de jours à analyser

        Returns:
            Dictionnaire de comparaison
        """
        start_date = datetime.now() - timedelta(days=days)

        stats_a = self.get_model_stats(model_a_type, start_date=start_date)
        stats_b = self.get_model_stats(model_b_type, start_date=start_date)

        return {
            'period_days': days,
            'model_a': {
                'type': model_a_type,
                'stats': stats_a
            },
            'model_b': {
                'type': model_b_type,
                'stats': stats_b
            },
            'delta': {
                'confidence': (stats_b.get('avg_confidence', 0) or 0) - (stats_a.get('avg_confidence', 0) or 0),
                'processing_time_ms': (stats_b.get('avg_processing_time_ms', 0) or 0) - (stats_a.get('avg_processing_time_ms', 0) or 0),
                'predictions': stats_b.get('total_predictions', 0) - stats_a.get('total_predictions', 0)
            }
        }

    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Récupère les statistiques quotidiennes

        Args:
            days: Nombre de jours

        Returns:
            Liste de stats par jour
        """
        query = """
            SELECT
                DATE(timestamp) as date,
                model_type,
                COUNT(*) as total_predictions,
                AVG(confidence) as avg_confidence,
                COUNT(*) FILTER (WHERE prediction_result = 'dangerous') as dangerous_count,
                COUNT(*) FILTER (WHERE prediction_result = 'safe') as safe_count,
                AVG(processing_time_ms) as avg_processing_time_ms
            FROM predictions
            WHERE timestamp > NOW() - INTERVAL '%s days'
            GROUP BY DATE(timestamp), model_type
            ORDER BY date DESC, model_type
        """
        return self.db.execute_query_dict(query, (days,))

    def detect_model_drift(
        self,
        model_type: str,
        window_days: int = 7
    ) -> Dict[str, Any]:
        """
        Détecte un drift potentiel du modèle

        Compare les performances des 7 derniers jours vs les 7 jours précédents

        Returns:
            Dictionnaire avec analyse de drift
        """
        now = datetime.now()
        recent_start = now - timedelta(days=window_days)
        previous_start = now - timedelta(days=window_days * 2)

        recent_stats = self.get_model_stats(
            model_type,
            start_date=recent_start,
            end_date=now
        )

        previous_stats = self.get_model_stats(
            model_type,
            start_date=previous_start,
            end_date=recent_start
        )

        # Calculer les deltas
        confidence_delta = (recent_stats.get('avg_confidence', 0) or 0) - (previous_stats.get('avg_confidence', 0) or 0)

        # Seuils de drift (à ajuster selon le modèle)
        CONFIDENCE_THRESHOLD = 0.05
        drift_detected = abs(confidence_delta) > CONFIDENCE_THRESHOLD

        return {
            'model_type': model_type,
            'window_days': window_days,
            'drift_detected': drift_detected,
            'recent_period': {
                'start': recent_start.isoformat(),
                'end': now.isoformat(),
                'stats': recent_stats
            },
            'previous_period': {
                'start': previous_start.isoformat(),
                'end': recent_start.isoformat(),
                'stats': previous_stats
            },
            'deltas': {
                'confidence': confidence_delta,
                'confidence_threshold': CONFIDENCE_THRESHOLD
            }
        }

    # ==================== MAINTENANCE ====================

    def calculate_performance_metrics(
        self,
        model_type: str,
        model_version: str,
        period_start: datetime,
        period_end: datetime,
        granularity: str = 'day'
    ) -> bool:
        """
        Calcule et enregistre les métriques de performance dans model_performance

        Args:
            model_type: Type de modèle
            model_version: Version
            period_start: Début de période
            period_end: Fin de période
            granularity: Granularité ('hour', 'day', 'week', 'month')

        Returns:
            True si calculé, False sinon
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    "SELECT calculate_model_performance(%s, %s, %s, %s, %s)",
                    (model_type, model_version, period_start, period_end, granularity)
                )

            logger.info(f"Métriques calculées pour {model_type} {model_version}")
            return True

        except Exception as e:
            logger.error(f"Erreur calcul métriques: {e}")
            return False
