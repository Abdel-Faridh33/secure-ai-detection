#!/usr/bin/env python3
"""
Script de test de la base de données
Vérifie que tous les modules fonctionnent correctement
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env', override=True)

from src.database import UserManager, PredictionLogger, get_db_connection

def test_connection():
    """Test la connexion PostgreSQL"""
    print("\n=== TEST CONNEXION ===")
    db = get_db_connection()
    if db.test_connection():
        print("[OK] Connexion PostgreSQL reussie")
        return True
    else:
        print("[ERREUR] Connexion echouee")
        return False

def test_user_manager():
    """Test le UserManager"""
    print("\n=== TEST USER MANAGER ===")
    manager = UserManager()

    # Test authentification
    user = manager.authenticate("admin", "admin123")
    if user:
        print(f"[OK] Authentification reussie: {user['username']} (role: {user['role']})")
    else:
        print("[ERREUR] Authentification echouee")
        return False

    # Test permissions
    can_delete = manager.has_permission(user['id'], 'users', 'delete')
    print(f"[OK] Permission 'users/delete': {can_delete}")

    # Lister utilisateurs
    users = manager.list_users()
    print(f"[OK] {len(users)} utilisateurs dans la DB:")
    for u in users:
        print(f"     - {u['username']} ({u['role']})")

    return True

def test_prediction_logger():
    """Test le PredictionLogger"""
    print("\n=== TEST PREDICTION LOGGER ===")
    logger = PredictionLogger()

    # Enregistrer une prédiction de test
    pred_id = logger.log_prediction(
        model_type="secured",
        model_version="1.0.0",
        image_hash="test_hash_123456",
        prediction_result="dangerous",
        confidence=0.95,
        processing_time_ms=100.0,
        image_filename="test_image.jpg",
        image_size_bytes=123456
    )

    if pred_id:
        print(f"[OK] Prediction enregistree: ID={pred_id}")
    else:
        print("[ERREUR] Echec enregistrement prediction")
        return False

    # Récupérer stats
    stats = logger.get_model_stats("secured", "1.0.0")
    print(f"[OK] Stats modele 'secured':")
    print(f"     - Total predictions: {stats.get('total_predictions', 0)}")
    print(f"     - Avg confidence: {stats.get('avg_confidence', 0):.2f}")

    # Ajouter feedback
    success = logger.add_user_feedback(pred_id, "correct", "Test feedback")
    if success:
        print(f"[OK] Feedback ajoute a la prediction {pred_id}")

    return True

def main():
    """Fonction principale"""
    print("=" * 60)
    print(" TEST DE L'ARCHITECTURE HYBRIDE POSTGRESQL ".center(60))
    print("=" * 60)

    all_ok = True

    # Test 1: Connexion
    if not test_connection():
        all_ok = False

    # Test 2: UserManager
    if not test_user_manager():
        all_ok = False

    # Test 3: PredictionLogger
    if not test_prediction_logger():
        all_ok = False

    # Résumé
    print("\n" + "=" * 60)
    if all_ok:
        print(" TOUS LES TESTS REUSSIS ".center(60, "="))
    else:
        print(" CERTAINS TESTS ONT ECHOUE ".center(60, "="))
    print("=" * 60)

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
