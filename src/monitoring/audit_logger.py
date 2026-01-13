"""
Audit Logger - Système de logs immuables pour traçabilité légale
Zone 5 : Gouvernance et Surveillance

Fonctionnalités :
- Logs structurés au format JSON
- Append-only (immuable)
- Hachage SHA-256 des images analysées
- Traçabilité complète : qui, quoi, quand, avec quel modèle
- Export pour audits externes

Référence : Architecture de sécurité proposée - Section 3.1.2.5
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid

# Import optionnel de l'indexeur PostgreSQL
try:
    from .audit_indexer import AuditIndexer
    INDEXER_AVAILABLE = True
except ImportError:
    INDEXER_AVAILABLE = False


class EventType(Enum):
    """Types d'événements audités"""
    PREDICTION = "prediction"
    ATTACK_DETECTED = "attack_detected"
    VALIDATION_FAILED = "validation_failed"
    API_ACCESS = "api_access"
    MODEL_LOADED = "model_loaded"
    SYSTEM_ERROR = "system_error"
    SECURITY_CHECK = "security_check"
    SECURITY_ALERT = "security_alert"


class SeverityLevel(Enum):
    """Niveaux de gravité pour les événements"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SECURITY_ALERT = "security_alert"


class AuditLogger:
    """
    Logger d'audit immuable pour traçabilité légale

    Caractéristiques :
    - Logs append-only (ne peuvent pas être modifiés)
    - Format JSON structuré
    - Rotation automatique des fichiers
    - Horodatage précis (ISO 8601)
    - Hash cryptographique des données sensibles
    """

    def __init__(
        self,
        log_dir: str = "logs/audit",
        max_file_size_mb: int = 100,
        retention_days: int = 90
    ):
        """
        Initialise le système d'audit

        Args:
            log_dir: Répertoire de stockage des logs
            max_file_size_mb: Taille maximale d'un fichier de log avant rotation
            retention_days: Durée de conservation des logs (conformité RGPD)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size = max_file_size_mb * 1024 * 1024  # Conversion en bytes
        self.retention_days = retention_days

        # Configuration du logger Python standard
        self._setup_logger()

        # Fichier de log actuel
        self.current_log_file = self._get_current_log_file()

        # Compteur d'événements pour la session
        self.event_count = 0

        # Indexeur PostgreSQL (optionnel)
        self.indexer = None
        if INDEXER_AVAILABLE:
            try:
                self.indexer = AuditIndexer()
                logging.info("[AUDIT_LOGGER] PostgreSQL indexing enabled")
            except Exception as e:
                logging.warning(f"[AUDIT_LOGGER] PostgreSQL unavailable - {e}")

        logging.info(f"[AUDIT_LOGGER] Initialized - Log directory: {self.log_dir}")

    def _setup_logger(self):
        """Configure le logger Python pour les logs système"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / 'system.log'),
                logging.StreamHandler()
            ]
        )

    def _get_current_log_file(self) -> Path:
        """Retourne le fichier de log actuel (rotation par jour)"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{date_str}.jsonl"

    def _generate_audit_id(self) -> str:
        """Génère un ID unique pour chaque événement d'audit"""
        return f"AUDIT-{uuid.uuid4().hex[:12].upper()}"

    def _hash_image(self, image_data: bytes) -> str:
        """
        Calcule le hash SHA-256 d'une image
        Permet de vérifier l'intégrité sans stocker l'image

        Args:
            image_data: Données binaires de l'image

        Returns:
            Hash SHA-256 en hexadécimal
        """
        return hashlib.sha256(image_data).hexdigest()

    def _hash_sensitive_data(self, data: str) -> str:
        """Hash les données sensibles (IDs utilisateurs, etc.)"""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def log_prediction(
        self,
        image_data: bytes,
        image_filename: str,
        model_type: str,
        prediction: str,
        confidence: float,
        processing_time_ms: float,
        user_id: Optional[str] = "anonymous",
        user_role: Optional[str] = "guest",
        client_ip: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log une prédiction du modèle d'IA

        Args:
            image_data: Données binaires de l'image
            image_filename: Nom du fichier image
            model_type: Type de modèle utilisé (baseline/secured)
            prediction: Résultat de la prédiction (safe/dangerous)
            confidence: Niveau de confiance (0-1)
            processing_time_ms: Temps de traitement en ms
            user_id: ID de l'utilisateur (si authentifié)
            user_role: Rôle de l'utilisateur
            client_ip: IP du client
            additional_metadata: Métadonnées supplémentaires

        Returns:
            audit_id: ID unique de l'événement d'audit
        """
        audit_id = self._generate_audit_id()
        image_hash = self._hash_image(image_data)

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": EventType.PREDICTION.value,
            "severity": SeverityLevel.INFO.value,

            # Informations utilisateur
            "user": {
                "user_id_hash": self._hash_sensitive_data(user_id),
                "user_role": user_role,
                "client_ip": client_ip
            },

            # Informations sur l'image
            "image": {
                "filename": image_filename,
                "hash_sha256": image_hash,
                "size_bytes": len(image_data)
            },

            # Informations sur la prédiction
            "prediction": {
                "model_type": model_type,
                "model_version": "1.0.0",  # À récupérer dynamiquement
                "result": prediction,
                "confidence": round(confidence, 4),
                "processing_time_ms": round(processing_time_ms, 2)
            },

            # Métadonnées supplémentaires
            "metadata": additional_metadata or {}
        }

        # Écriture dans le fichier de log
        self._write_audit_entry(audit_entry)

        # Indexation dans PostgreSQL (si disponible)
        if self.indexer:
            self.indexer.index_prediction(
                audit_id=audit_id,
                timestamp=audit_entry["timestamp"],
                user_id_hash=audit_entry["user"]["user_id_hash"],
                user_role=user_role,
                client_ip=client_ip,
                image_filename=image_filename,
                image_hash=image_hash,
                image_size_bytes=len(image_data),
                model_type=model_type,
                model_version="1.0.0",
                prediction_result=prediction,
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                jsonl_file=str(self.current_log_file.name),
                jsonl_line_number=self.event_count + 1
            )

        self.event_count += 1
        logging.info(f"[AUDIT] Prediction logged: {audit_id} - {prediction} (confidence: {confidence:.2%})")

        return audit_id

    def log_attack_detected(
        self,
        image_data: bytes,
        image_filename: str,
        attack_type: str,
        confidence: float,
        detection_method: str,
        user_id: Optional[str] = "anonymous",
        client_ip: Optional[str] = None,
        blocked: bool = True
    ) -> str:
        """
        Log une tentative d'attaque détectée

        Args:
            image_data: Données binaires de l'image suspecte
            image_filename: Nom du fichier
            attack_type: Type d'attaque détectée (adversarial/poisoning/etc.)
            confidence: Niveau de confiance de la détection
            detection_method: Méthode de détection utilisée
            user_id: ID de l'utilisateur
            client_ip: IP du client
            blocked: Si l'attaque a été bloquée

        Returns:
            audit_id: ID unique de l'événement d'audit
        """
        audit_id = self._generate_audit_id()
        image_hash = self._hash_image(image_data)

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": EventType.ATTACK_DETECTED.value,
            "severity": SeverityLevel.SECURITY_ALERT.value,

            "user": {
                "user_id_hash": self._hash_sensitive_data(user_id),
                "client_ip": client_ip
            },

            "image": {
                "filename": image_filename,
                "hash_sha256": image_hash
            },

            "attack": {
                "type": attack_type,
                "confidence": round(confidence, 4),
                "detection_method": detection_method,
                "blocked": blocked,
                "action_taken": "REQUEST_BLOCKED" if blocked else "WARNING_LOGGED"
            }
        }

        self._write_audit_entry(audit_entry)

        logging.warning(f"[SECURITY ALERT] Attack detected: {audit_id} - {attack_type} from {client_ip}")

        return audit_id

    def log_validation_failed(
        self,
        image_filename: str,
        reason: str,
        user_id: Optional[str] = "anonymous",
        client_ip: Optional[str] = None
    ) -> str:
        """
        Log une validation d'input échouée

        Args:
            image_filename: Nom du fichier rejeté
            reason: Raison du rejet
            user_id: ID de l'utilisateur
            client_ip: IP du client

        Returns:
            audit_id: ID unique de l'événement
        """
        audit_id = self._generate_audit_id()

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": EventType.VALIDATION_FAILED.value,
            "severity": SeverityLevel.WARNING.value,

            "user": {
                "user_id_hash": self._hash_sensitive_data(user_id),
                "client_ip": client_ip
            },

            "validation": {
                "filename": image_filename,
                "reason": reason,
                "action_taken": "REQUEST_REJECTED"
            }
        }

        self._write_audit_entry(audit_entry)

        logging.warning(f"[VALIDATION] Failed: {audit_id} - {reason}")

        return audit_id

    def log_api_access(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: Optional[str] = "anonymous",
        client_ip: Optional[str] = None,
        response_time_ms: Optional[float] = None
    ) -> str:
        """
        Log un accès à l'API

        Args:
            endpoint: Endpoint appelé
            method: Méthode HTTP (GET/POST/etc.)
            status_code: Code de réponse HTTP
            user_id: ID de l'utilisateur
            client_ip: IP du client
            response_time_ms: Temps de réponse

        Returns:
            audit_id: ID unique de l'événement
        """
        audit_id = self._generate_audit_id()

        severity = SeverityLevel.INFO
        if status_code >= 400:
            severity = SeverityLevel.WARNING
        if status_code >= 500:
            severity = SeverityLevel.CRITICAL

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": EventType.API_ACCESS.value,
            "severity": severity.value,

            "user": {
                "user_id_hash": self._hash_sensitive_data(user_id),
                "client_ip": client_ip
            },

            "api": {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time_ms": round(response_time_ms, 2) if response_time_ms else None
            }
        }

        self._write_audit_entry(audit_entry)

        return audit_id

    def log_event(
        self,
        event_type: str,
        severity: SeverityLevel,
        description: str,
        user_id: Optional[str] = "unknown",
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log un événement générique (sécurité, système, etc.)

        Utilisé par le SecurityMiddleware pour logger les événements de sécurité
        tels que les blocages WAF, détection d'anomalies, etc.

        Args:
            event_type: Type d'événement (security_block, anomaly_detected, etc.)
            severity: Niveau de sévérité (INFO, WARNING, CRITICAL, SECURITY_ALERT)
            description: Description de l'événement
            user_id: ID de l'utilisateur concerné
            client_ip: IP du client
            metadata: Métadonnées supplémentaires

        Returns:
            audit_id: ID unique de l'événement d'audit
        """
        audit_id = self._generate_audit_id()

        audit_entry = {
            "audit_id": audit_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "severity": severity.value,
            "description": description,

            "user": {
                "user_id_hash": self._hash_sensitive_data(user_id),
                "client_ip": client_ip
            },

            "metadata": metadata or {}
        }

        self._write_audit_entry(audit_entry)

        # Log dans le logger Python pour visibilité
        log_level = logging.INFO
        if severity == SeverityLevel.WARNING:
            log_level = logging.WARNING
        elif severity in [SeverityLevel.CRITICAL, SeverityLevel.SECURITY_ALERT]:
            log_level = logging.CRITICAL

        logging.log(log_level, f"[SECURITY] Event: {event_type} - {description}")

        return audit_id

    def _write_audit_entry(self, entry: Dict[str, Any]):
        """
        Écrit une entrée d'audit dans le fichier
        Format JSONL (JSON Lines) - une entrée par ligne
        Append-only pour immutabilité
        """
        log_file = self._get_current_log_file()

        # Rotation du fichier si trop gros
        if log_file.exists() and log_file.stat().st_size > self.max_file_size:
            self._rotate_log_file()
            log_file = self._get_current_log_file()

        # Écriture en mode append (append-only)
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')

    def _rotate_log_file(self):
        """Rotation des fichiers de log"""
        current_file = self._get_current_log_file()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_file = self.log_dir / f"audit_{timestamp}.jsonl"

        if current_file.exists():
            current_file.rename(rotated_file)
            logging.info(f"[AUDIT_LOGGER] Log file rotated: {rotated_file}")

    def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        severity: Optional[SeverityLevel] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Requête les logs d'audit avec filtres

        Args:
            start_date: Date de début
            end_date: Date de fin
            event_type: Type d'événement à filtrer
            severity: Niveau de gravité à filtrer
            user_id: ID utilisateur à filtrer
            limit: Nombre maximum de résultats

        Returns:
            Liste des entrées d'audit correspondantes
        """
        results = []

        # Parcours de tous les fichiers de log
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)

                        # Application des filtres
                        if start_date and datetime.fromisoformat(entry['timestamp'].replace('Z', '')) < start_date:
                            continue
                        if end_date and datetime.fromisoformat(entry['timestamp'].replace('Z', '')) > end_date:
                            continue
                        if event_type and entry['event_type'] != event_type.value:
                            continue
                        if severity and entry['severity'] != severity.value:
                            continue
                        if user_id and entry.get('user', {}).get('user_id_hash') != self._hash_sensitive_data(user_id):
                            continue

                        results.append(entry)

                    except json.JSONDecodeError:
                        logging.error(f"[AUDIT_LOGGER] Invalid JSON in log file: {log_file}")
                        continue

        # Trier les résultats du plus récent au plus ancien
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Limiter les résultats après le tri
        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Calcule des statistiques sur les logs d'audit

        Returns:
            Dictionnaire avec les statistiques
        """
        stats = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_severity": {},
            "attacks_detected": 0,
            "predictions_count": 0,
            "average_confidence": 0.0,
            "date_range": {
                "first_event": None,
                "last_event": None
            }
        }

        total_confidence = 0
        prediction_count = 0

        for log_file in self.log_dir.glob("audit_*.jsonl"):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        stats["total_events"] += 1

                        # Par type
                        event_type = entry.get('event_type', 'unknown')
                        stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1

                        # Par gravité
                        severity = entry.get('severity', 'unknown')
                        stats["events_by_severity"][severity] = stats["events_by_severity"].get(severity, 0) + 1

                        # Attaques
                        if event_type == EventType.ATTACK_DETECTED.value:
                            stats["attacks_detected"] += 1

                        # Prédictions
                        if event_type == EventType.PREDICTION.value:
                            stats["predictions_count"] += 1
                            if 'prediction' in entry and 'confidence' in entry['prediction']:
                                total_confidence += entry['prediction']['confidence']
                                prediction_count += 1

                        # Date range
                        timestamp = entry.get('timestamp')
                        if not stats["date_range"]["first_event"]:
                            stats["date_range"]["first_event"] = timestamp
                        stats["date_range"]["last_event"] = timestamp

                    except json.JSONDecodeError:
                        continue

        if prediction_count > 0:
            stats["average_confidence"] = round(total_confidence / prediction_count, 4)

        return stats

    def export_audit_trail(
        self,
        output_file: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ):
        """
        Export les logs d'audit pour audit externe

        Args:
            output_file: Fichier de sortie
            start_date: Date de début
            end_date: Date de fin
            format: Format d'export (json/csv)
        """
        logs = self.query_logs(start_date=start_date, end_date=end_date, limit=1000000)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if logs:
                    # Flatten nested dicts for CSV
                    fieldnames = ['audit_id', 'timestamp', 'event_type', 'severity']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for log in logs:
                        row = {k: log.get(k, '') for k in fieldnames}
                        writer.writerow(row)

        logging.info(f"[AUDIT_LOGGER] Audit trail exported: {output_path} ({len(logs)} entries)")


# Instance globale du logger d'audit
audit_logger = AuditLogger()
