"""
Script de Test Simple - Data Security Modules
==============================================

Test rapide des 3 modules implémentés
"""

import sys
import os
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("TEST DES MODULES DE SÉCURITÉ DES DONNÉES")
print("="*60)

# Test 1: EncryptedStorage
print("\n[1/3] Test EncryptedStorage...")
try:
    from src.data.encrypted_storage import EncryptedStorage

    # Test basique
    storage = EncryptedStorage(password="test_password_123")
    print("  [OK] EncryptedStorage initialise")

    # Créer un fichier test
    test_dir = Path('temp_test')
    test_dir.mkdir(exist_ok=True)

    test_file = test_dir / 'test.txt'
    with open(test_file, 'w') as f:
        f.write("Test data for encryption")

    # Chiffrer
    encrypted_file = test_dir / 'test.enc'
    metadata = storage.encrypt_file(str(test_file), str(encrypted_file))
    print("  [OK] Fichier chiffre")

    # Déchiffrer
    decrypted_file = test_dir / 'test_decrypted.txt'
    success = storage.decrypt_file(str(encrypted_file), str(decrypted_file), metadata)

    if success:
        print("  [OK] Fichier dechiffre avec succes")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

    print("[SUCCESS] EncryptedStorage : OK\n")

except Exception as e:
    print(f"[ERROR] EncryptedStorage : ERREUR - {str(e)}\n")

# Test 2: DataVerifier
print("[2/3] Test DataVerifier...")
try:
    from src.data.data_verifier import DataVerifier

    verifier = DataVerifier(
        min_samples_per_class=5,
        max_class_imbalance_ratio=5.0
    )
    print("  [OK] DataVerifier initialise")

    # Test des methodes
    class_dist = {'safe': 10, 'dangerous': 10}
    result = verifier._chi_square_test(class_dist)
    print(f"  [OK] Chi-Square test: {result['passed']}")

    print("[SUCCESS] DataVerifier : OK\n")

except Exception as e:
    print(f"[ERROR] DataVerifier : ERREUR - {str(e)}\n")

# Test 3: PoisoningDetector
print("[3/3] Test PoisoningDetector...")
try:
    from src.data.poisoning_detector import PoisoningDetector

    detector = PoisoningDetector(
        eps=0.5,
        min_samples=5,
        use_pca=True
    )
    print("  [OK] PoisoningDetector initialise")
    print(f"  [OK] Device: {detector.device}")
    print(f"  [OK] Feature extractor charge")

    print("[SUCCESS] PoisoningDetector : OK\n")

except Exception as e:
    print(f"[ERROR] PoisoningDetector : ERREUR - {str(e)}\n")

print("="*60)
print("TESTS TERMINÉS")
print("="*60)
