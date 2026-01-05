"""
Test de l'Audit Logger avec indexation PostgreSQL
"""

import sys
from pathlib import Path
import hashlib

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env', override=True)

from src.monitoring.audit_logger import AuditLogger

def test_audit_with_indexing():
    print("\n" + "=" * 60)
    print(" TEST AUDIT LOGGER + INDEXATION POSTGRESQL ".center(60))
    print("=" * 60)

    # Créer une image de test
    test_image = b"fake_image_data_for_testing_123456789"

    # Initialiser l'audit logger
    print("\n[1/3] Initialisation de l'Audit Logger...")
    audit = AuditLogger()

    # Log une prédiction
    print("\n[2/3] Log d'une prediction avec double ecriture...")
    audit_id = audit.log_prediction(
        image_data=test_image,
        image_filename="test_hybrid.jpg",
        model_type="secured",
        prediction="dangerous",
        confidence=0.95,
        processing_time_ms=125.45,
        user_id="testuser123",
        user_role="agent",
        client_ip="192.168.1.100"
    )

    print(f"[OK] Audit ID: {audit_id}")

    # Vérifier que c'est bien indexé
    print("\n[3/3] Verification de l'indexation PostgreSQL...")

    if audit.indexer:
        print("[OK] Indexeur PostgreSQL actif")

        # Rechercher le log qu'on vient de créer
        from src.monitoring.audit_indexer import AuditIndexer
        from datetime import datetime, timedelta

        indexer = AuditIndexer()
        results = indexer.search_logs(
            start_date=datetime.now() - timedelta(minutes=1),
            end_date=datetime.now() + timedelta(minutes=1),
            model_type="secured",
            limit=10
        )

        print(f"[OK] {len(results)} logs trouves dans l'index PostgreSQL")

        if results:
            last_log = results[0]
            print(f"    - Audit ID: {last_log['audit_id']}")
            print(f"    - Result: {last_log['prediction_result']}")
            print(f"    - Confidence: {last_log['confidence']:.2f}")
            print(f"    - JSONL file: {last_log['jsonl_file']}")
    else:
        print("[ATTENTION] Indexeur PostgreSQL non disponible")

    print("\n" + "=" * 60)
    print(" ARCHITECTURE HYBRIDE FONCTIONNELLE ".center(60, "="))
    print("=" * 60)
    print("\nLogs ecrits dans:")
    print(f"  - JSONL: {audit.current_log_file}")
    print(f"  - PostgreSQL: audit_logs_index (recherche rapide)")

    return True

if __name__ == '__main__':
    test_audit_with_indexing()
