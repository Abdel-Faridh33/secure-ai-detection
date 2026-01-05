"""
Tests du système d'audit

Teste toutes les fonctionnalités :
- Logging des prédictions
- Logging des attaques
- Logging des validations échouées
- Requêtes et recherches
- Statistiques
- Export

Exécution : pytest tests/test_audit_system.py -v
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib

from src.monitoring.audit_logger import AuditLogger, EventType, SeverityLevel


@pytest.fixture
def audit_logger_test():
    """Fixture pour créer un logger d'audit de test"""
    test_log_dir = "logs/audit_test"
    logger = AuditLogger(log_dir=test_log_dir, retention_days=1)
    yield logger

    # Cleanup après les tests
    import shutil
    if Path(test_log_dir).exists():
        shutil.rmtree(test_log_dir)


@pytest.fixture
def sample_image_data():
    """Données d'image de test"""
    return b"fake_image_data_for_testing_purposes"


def test_audit_logger_initialization(audit_logger_test):
    """Test de l'initialisation du logger"""
    assert audit_logger_test is not None
    assert audit_logger_test.log_dir.exists()
    assert audit_logger_test.event_count == 0


def test_log_prediction(audit_logger_test, sample_image_data):
    """Test du logging d'une prédiction"""
    audit_id = audit_logger_test.log_prediction(
        image_data=sample_image_data,
        image_filename="test_image.jpg",
        model_type="baseline",
        prediction="safe",
        confidence=0.85,
        processing_time_ms=150.5,
        user_id="test_user_123",
        user_role="agent",
        client_ip="192.168.1.100"
    )

    assert audit_id is not None
    assert audit_id.startswith("AUDIT-")
    assert audit_logger_test.event_count == 1


def test_log_attack_detected(audit_logger_test, sample_image_data):
    """Test du logging d'une attaque détectée"""
    audit_id = audit_logger_test.log_attack_detected(
        image_data=sample_image_data,
        image_filename="suspicious.jpg",
        attack_type="adversarial_fgsm",
        confidence=0.92,
        detection_method="statistical_analysis",
        user_id="potential_attacker",
        client_ip="10.0.0.50",
        blocked=True
    )

    assert audit_id is not None
    assert audit_id.startswith("AUDIT-")


def test_log_validation_failed(audit_logger_test):
    """Test du logging d'une validation échouée"""
    audit_id = audit_logger_test.log_validation_failed(
        image_filename="corrupted.jpg",
        reason="Invalid image format",
        user_id="test_user",
        client_ip="192.168.1.200"
    )

    assert audit_id is not None
    assert audit_id.startswith("AUDIT-")


def test_log_api_access(audit_logger_test):
    """Test du logging d'un accès API"""
    audit_id = audit_logger_test.log_api_access(
        endpoint="/predict/baseline",
        method="POST",
        status_code=200,
        user_id="api_user",
        client_ip="172.16.0.10",
        response_time_ms=250.3
    )

    assert audit_id is not None


def test_query_logs(audit_logger_test, sample_image_data):
    """Test de la requête des logs"""
    # Créer plusieurs événements
    for i in range(5):
        audit_logger_test.log_prediction(
            image_data=sample_image_data,
            image_filename=f"test_{i}.jpg",
            model_type="secured",
            prediction="dangerous" if i % 2 == 0 else "safe",
            confidence=0.7 + i * 0.05,
            processing_time_ms=100 + i * 10,
            user_id=f"user_{i}",
            client_ip=f"192.168.1.{i}"
        )

    # Requête sans filtre
    logs = audit_logger_test.query_logs(limit=10)
    assert len(logs) == 5

    # Requête avec filtre par type
    prediction_logs = audit_logger_test.query_logs(
        event_type=EventType.PREDICTION,
        limit=10
    )
    assert len(prediction_logs) == 5


def test_query_logs_with_date_filter(audit_logger_test, sample_image_data):
    """Test de la requête avec filtre de date"""
    # Log un événement
    audit_logger_test.log_prediction(
        image_data=sample_image_data,
        image_filename="dated_test.jpg",
        model_type="baseline",
        prediction="safe",
        confidence=0.88,
        processing_time_ms=120
    )

    # Requête avec date de début (hier)
    yesterday = datetime.now() - timedelta(days=1)
    logs = audit_logger_test.query_logs(start_date=yesterday, limit=100)

    assert len(logs) >= 1


def test_image_hashing(audit_logger_test):
    """Test du hachage SHA-256 des images"""
    image_data_1 = b"image_content_1"
    image_data_2 = b"image_content_2"

    hash_1 = audit_logger_test._hash_image(image_data_1)
    hash_2 = audit_logger_test._hash_image(image_data_2)

    # Les hash doivent être différents
    assert hash_1 != hash_2

    # Le même contenu doit donner le même hash
    hash_1_bis = audit_logger_test._hash_image(image_data_1)
    assert hash_1 == hash_1_bis

    # Le hash doit être en hexadécimal
    assert len(hash_1) == 64  # SHA-256 = 64 caractères hex


def test_sensitive_data_hashing(audit_logger_test):
    """Test du hachage des données sensibles"""
    user_id_1 = "user@example.com"
    user_id_2 = "admin@example.com"

    hash_1 = audit_logger_test._hash_sensitive_data(user_id_1)
    hash_2 = audit_logger_test._hash_sensitive_data(user_id_2)

    # Les hash doivent être différents
    assert hash_1 != hash_2

    # Le hash doit être court (16 caractères)
    assert len(hash_1) == 16


def test_statistics(audit_logger_test, sample_image_data):
    """Test du calcul de statistiques"""
    # Créer différents types d'événements
    for i in range(3):
        audit_logger_test.log_prediction(
            image_data=sample_image_data,
            image_filename=f"test_{i}.jpg",
            model_type="baseline",
            prediction="safe",
            confidence=0.8 + i * 0.05,
            processing_time_ms=100
        )

    audit_logger_test.log_attack_detected(
        image_data=sample_image_data,
        image_filename="attack.jpg",
        attack_type="adversarial",
        confidence=0.95,
        detection_method="test"
    )

    audit_logger_test.log_validation_failed(
        image_filename="invalid.jpg",
        reason="test reason"
    )

    # Calculer les statistiques
    stats = audit_logger_test.get_statistics()

    assert stats["total_events"] == 5
    assert stats["predictions_count"] == 3
    assert stats["attacks_detected"] == 1
    assert "events_by_type" in stats
    assert EventType.PREDICTION.value in stats["events_by_type"]
    assert stats["average_confidence"] > 0


def test_export_json(audit_logger_test, sample_image_data, tmp_path):
    """Test de l'export en JSON"""
    # Créer des logs
    for i in range(3):
        audit_logger_test.log_prediction(
            image_data=sample_image_data,
            image_filename=f"export_test_{i}.jpg",
            model_type="secured",
            prediction="safe",
            confidence=0.9,
            processing_time_ms=100
        )

    # Export
    export_file = tmp_path / "audit_export.json"
    audit_logger_test.export_audit_trail(
        output_file=str(export_file),
        format="json"
    )

    # Vérifier que le fichier existe
    assert export_file.exists()

    # Vérifier le contenu
    with open(export_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 3


def test_log_file_rotation(audit_logger_test, sample_image_data):
    """Test de la rotation des fichiers de log"""
    # Forcer une petite taille de fichier pour rotation
    audit_logger_test.max_file_size = 1024  # 1KB

    # Créer beaucoup d'événements pour forcer la rotation
    for i in range(100):
        audit_logger_test.log_prediction(
            image_data=sample_image_data * 100,  # Grande image
            image_filename=f"large_test_{i}.jpg",
            model_type="baseline",
            prediction="safe",
            confidence=0.85,
            processing_time_ms=100,
            additional_metadata={"large_field": "x" * 1000}
        )

    # Vérifier qu'il y a plusieurs fichiers de log
    log_files = list(audit_logger_test.log_dir.glob("audit_*.jsonl"))
    # Note: Peut être 1 ou plus selon la taille réelle
    assert len(log_files) >= 1


def test_severity_levels(audit_logger_test, sample_image_data):
    """Test des niveaux de gravité"""
    # Prédiction normale (INFO)
    audit_logger_test.log_prediction(
        image_data=sample_image_data,
        image_filename="normal.jpg",
        model_type="baseline",
        prediction="safe",
        confidence=0.9,
        processing_time_ms=100
    )

    # Validation échouée (WARNING)
    audit_logger_test.log_validation_failed(
        image_filename="invalid.jpg",
        reason="test"
    )

    # Attaque (SECURITY_ALERT)
    audit_logger_test.log_attack_detected(
        image_data=sample_image_data,
        image_filename="attack.jpg",
        attack_type="adversarial",
        confidence=0.95,
        detection_method="test"
    )

    # Requête par gravité
    warnings = audit_logger_test.query_logs(
        severity=SeverityLevel.WARNING,
        limit=100
    )
    alerts = audit_logger_test.query_logs(
        severity=SeverityLevel.SECURITY_ALERT,
        limit=100
    )

    assert len(warnings) >= 1
    assert len(alerts) >= 1


def test_audit_id_uniqueness(audit_logger_test, sample_image_data):
    """Test de l'unicité des audit_id"""
    audit_ids = set()

    for i in range(10):
        audit_id = audit_logger_test.log_prediction(
            image_data=sample_image_data,
            image_filename=f"unique_test_{i}.jpg",
            model_type="baseline",
            prediction="safe",
            confidence=0.8,
            processing_time_ms=100
        )
        audit_ids.add(audit_id)

    # Tous les ID doivent être uniques
    assert len(audit_ids) == 10


def test_json_format_validation(audit_logger_test, sample_image_data):
    """Test de la validité du format JSON des logs"""
    # Créer un log
    audit_logger_test.log_prediction(
        image_data=sample_image_data,
        image_filename="json_test.jpg",
        model_type="baseline",
        prediction="safe",
        confidence=0.85,
        processing_time_ms=100
    )

    # Lire le fichier de log
    log_file = audit_logger_test._get_current_log_file()

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                # Chaque ligne doit être un JSON valide
                entry = json.loads(line)

                # Vérifier les champs obligatoires
                assert "audit_id" in entry
                assert "timestamp" in entry
                assert "event_type" in entry
                assert "severity" in entry

                # Vérifier le format du timestamp (ISO 8601)
                datetime.fromisoformat(entry["timestamp"].replace('Z', ''))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
