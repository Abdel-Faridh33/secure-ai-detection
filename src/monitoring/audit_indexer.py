"""
Audit Indexer - Extension pour indexation PostgreSQL
Indexe les logs d'audit dans PostgreSQL pour recherche rapide
tout en conservant les logs JSONL immuables

Architecture Hybride:
- JSONL: Logs immuables (conformité RGPD)
- PostgreSQL: Index pour recherche rapide (100x plus rapide)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditIndexer:
    """
    Indexeur PostgreSQL pour les logs d'audit

    Fonctionne en complément d'AuditLogger:
    - AuditLogger écrit dans JSONL (immuable)
    - AuditIndexer indexe dans PostgreSQL (recherche)
    """

    def __init__(self, db_connection=None):
        """
        Initialise l'indexeur

        Args:
            db_connection: Instance DatabaseConnection (optionnel)
        """
        self.db = db_connection
        self.enabled = False

        if self.db is None:
            try:
                from src.database import get_db_connection
                self.db = get_db_connection()
                self.enabled = True
                logger.info("✅ AuditIndexer: PostgreSQL activé")
            except Exception as e:
                logger.warning(f"⚠️ AuditIndexer: PostgreSQL non disponible - {e}")
                self.enabled = False

    def index_prediction(
        self,
        audit_id: str,
        timestamp: str,
        user_id_hash: str,
        user_role: str,
        client_ip: Optional[str],
        image_filename: str,
        image_hash: str,
        image_size_bytes: int,
        model_type: str,
        model_version: str,
        prediction_result: str,
        confidence: float,
        processing_time_ms: float,
        attack_type: Optional[str] = None,
        defense_triggered: bool = False,
        jsonl_file: str = None,
        jsonl_line_number: int = None
    ) -> bool:
        """
        Indexe une prédiction dans PostgreSQL

        Args:
            audit_id: ID unique de l'audit
            timestamp: Timestamp ISO 8601
            user_id_hash: Hash de l'ID utilisateur
            user_role: Rôle de l'utilisateur
            client_ip: IP du client
            image_filename: Nom du fichier image
            image_hash: Hash SHA-256 de l'image
            image_size_bytes: Taille de l'image
            model_type: Type de modèle
            model_version: Version du modèle
            prediction_result: Résultat (dangerous/safe)
            confidence: Confiance (0-1)
            processing_time_ms: Temps de traitement
            attack_type: Type d'attaque (si détectée)
            defense_triggered: Défense activée?
            jsonl_file: Fichier JSONL source
            jsonl_line_number: Numéro de ligne dans JSONL

        Returns:
            True si indexé, False sinon
        """
        if not self.enabled:
            return False

        try:
            # Convertir timestamp ISO en timestamptz PostgreSQL
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            query = """
                INSERT INTO audit_logs_index (
                    audit_id, timestamp, event_type, severity,
                    user_id_hash, user_role, client_ip,
                    image_filename, image_hash, image_size_bytes,
                    model_type, model_version,
                    prediction_result, confidence, processing_time_ms,
                    attack_type, defense_triggered,
                    jsonl_file, jsonl_line_number
                ) VALUES (
                    %s, %s, 'prediction', 'info',
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
                ON CONFLICT (audit_id) DO NOTHING
            """

            self.db.execute_query(
                query,
                (
                    audit_id, ts,
                    user_id_hash, user_role, client_ip,
                    image_filename, image_hash, image_size_bytes,
                    model_type, model_version,
                    prediction_result, confidence, processing_time_ms,
                    attack_type, defense_triggered,
                    jsonl_file, jsonl_line_number
                ),
                fetch=False
            )

            logger.debug(f"Audit indexé: {audit_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur indexation audit: {e}")
            return False

    def index_attack(
        self,
        audit_id: str,
        timestamp: str,
        user_id_hash: str,
        user_role: str,
        client_ip: Optional[str],
        attack_type: str,
        image_hash: str,
        model_type: str,
        defense_triggered: bool = True,
        jsonl_file: str = None,
        jsonl_line_number: int = None
    ) -> bool:
        """
        Indexe une attaque détectée dans PostgreSQL

        Args:
            audit_id: ID unique de l'audit
            timestamp: Timestamp ISO 8601
            user_id_hash: Hash de l'ID utilisateur
            user_role: Rôle
            client_ip: IP du client
            attack_type: Type d'attaque (FGSM, PGD, etc.)
            image_hash: Hash de l'image
            model_type: Type de modèle
            defense_triggered: Défense activée?
            jsonl_file: Fichier JSONL source
            jsonl_line_number: Numéro de ligne

        Returns:
            True si indexé, False sinon
        """
        if not self.enabled:
            return False

        try:
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            query = """
                INSERT INTO audit_logs_index (
                    audit_id, timestamp, event_type, severity,
                    user_id_hash, user_role, client_ip,
                    image_hash, model_type,
                    attack_type, defense_triggered,
                    jsonl_file, jsonl_line_number
                ) VALUES (
                    %s, %s, 'attack_detected', 'critical',
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                )
                ON CONFLICT (audit_id) DO NOTHING
            """

            self.db.execute_query(
                query,
                (
                    audit_id, ts,
                    user_id_hash, user_role, client_ip,
                    image_hash, model_type,
                    attack_type, defense_triggered,
                    jsonl_file, jsonl_line_number
                ),
                fetch=False
            )

            logger.info(f"Attaque indexée: {audit_id} - {attack_type}")
            return True

        except Exception as e:
            logger.error(f"Erreur indexation attaque: {e}")
            return False

    def update_daily_stats(self, date_str: str = None):
        """
        Met à jour les statistiques quotidiennes

        Args:
            date_str: Date au format YYYY-MM-DD (défaut: aujourd'hui)
        """
        if not self.enabled:
            return

        try:
            if date_str is None:
                date_str = datetime.now().strftime('%Y-%m-%d')

            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT update_daily_stats(%s)", (date_str,))

            logger.info(f"Stats quotidiennes mises à jour: {date_str}")

        except Exception as e:
            logger.error(f"Erreur mise à jour stats: {e}")

    def search_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        user_role: Optional[str] = None,
        model_type: Optional[str] = None,
        attack_only: bool = False,
        limit: int = 100
    ) -> list:
        """
        Recherche dans les logs indexés (RAPIDE!)

        Args:
            start_date: Date de début
            end_date: Date de fin
            event_type: Type d'événement
            user_role: Rôle utilisateur
            model_type: Type de modèle
            attack_only: Seulement les attaques
            limit: Nombre max de résultats

        Returns:
            Liste de dictionnaires de logs
        """
        if not self.enabled:
            return []

        try:
            query = "SELECT * FROM audit_logs_index WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)

            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)

            if user_role:
                query += " AND user_role = %s"
                params.append(user_role)

            if model_type:
                query += " AND model_type = %s"
                params.append(model_type)

            if attack_only:
                query += " AND attack_type IS NOT NULL"

            query += f" ORDER BY timestamp DESC LIMIT {limit}"

            return self.db.execute_query_dict(query, tuple(params) if params else None)

        except Exception as e:
            logger.error(f"Erreur recherche logs: {e}")
            return []
