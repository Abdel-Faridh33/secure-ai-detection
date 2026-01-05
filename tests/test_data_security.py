"""
Tests Unitaires - Data Security Modules
========================================

Tests pour les modules de sécurité des données :
- DataVerifier : Vérification des données avec tests statistiques
- PoisoningDetector : Détection d'empoisonnement avec DBSCAN
- EncryptedStorage : Stockage crypté AES-256-GCM

Conformité: Zone 1 - Data Security
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import json

# Import des modules à tester
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.data_verifier import DataVerifier, DatasetStatistics, VerificationReport
from src.data.poisoning_detector import PoisoningDetector, PoisoningReport
from src.data.encrypted_storage import EncryptedStorage, EncryptionMetadata


# ============================================================================
# FIXTURES - Données de test
# ============================================================================

@pytest.fixture
def temp_test_dir():
    """Crée un répertoire temporaire pour les tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_dataset(temp_test_dir):
    """Crée un dataset de test avec 2 classes"""
    dataset_path = Path(temp_test_dir) / 'test_dataset'

    # Créer 2 classes
    for class_name in ['safe', 'dangerous']:
        class_dir = dataset_path / class_name
        class_dir.mkdir(parents=True, exist_ok=True)

        # Créer 10 images par classe
        for i in range(10):
            # Image aléatoire RGB 100x100
            img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(class_dir / f'image_{i:03d}.jpg')

    return str(dataset_path)


@pytest.fixture
def sample_model(temp_test_dir):
    """Crée un modèle PyTorch de test"""
    model_path = Path(temp_test_dir) / 'test_model.pth'

    # Créer un simple state dict
    model_state = {
        'model_state_dict': {
            'layer1.weight': torch.randn(10, 5),
            'layer1.bias': torch.randn(10),
        },
        'epoch': 10,
        'accuracy': 0.95
    }

    torch.save(model_state, model_path)
    return str(model_path)


# ============================================================================
# TESTS - DataVerifier
# ============================================================================

class TestDataVerifier:
    """Tests pour le DataVerifier"""

    def test_initialization(self):
        """Test d'initialisation du DataVerifier"""
        verifier = DataVerifier(
            min_samples_per_class=5,
            max_class_imbalance_ratio=3.0
        )

        assert verifier.min_samples_per_class == 5
        assert verifier.max_class_imbalance_ratio == 3.0
        assert verifier.zscore_threshold == 3.0

    def test_verify_dataset(self, sample_dataset):
        """Test de vérification d'un dataset"""
        verifier = DataVerifier(min_samples_per_class=5)

        report = verifier.verify_dataset(sample_dataset)

        # Vérifications
        assert isinstance(report, VerificationReport)
        assert report.statistics.total_samples == 20  # 2 classes x 10 images
        assert 'safe' in report.statistics.class_distribution
        assert 'dangerous' in report.statistics.class_distribution
        assert report.statistics.class_distribution['safe'] == 10
        assert report.statistics.class_distribution['dangerous'] == 10

    def test_chi_square_test(self, sample_dataset):
        """Test du Chi-Square pour équilibre des classes"""
        verifier = DataVerifier()

        # Classes équilibrées
        class_dist = {'safe': 10, 'dangerous': 10}
        result = verifier._chi_square_test(class_dist)

        assert result['test_name'] == 'Chi-Square Class Balance'
        assert result['passed'] == True  # Classes équilibrées

        # Classes déséquilibrées
        class_dist_unbalanced = {'safe': 100, 'dangerous': 10}
        result_unbalanced = verifier._chi_square_test(class_dist_unbalanced)

        assert result_unbalanced['passed'] == False  # Déséquilibre détecté

    def test_detect_anomalies(self, sample_dataset):
        """Test de détection d'anomalies"""
        verifier = DataVerifier(
            min_samples_per_class=15,  # Plus que ce que le dataset a (10)
            max_class_imbalance_ratio=2.0
        )

        statistics = DatasetStatistics(
            total_samples=20,
            class_distribution={'safe': 10, 'dangerous': 10},
            mean_image_size=(100.0, 100.0),
            mean_pixel_intensity=127.5,
            std_pixel_intensity=50.0,
            corrupted_images=0,
            duplicate_hashes=0,
            timestamp='2025-10-11T00:00:00Z'
        )

        statistical_tests = {
            'class_balance': {'passed': True, 'message': 'OK'}
        }

        anomalies = verifier._detect_anomalies(statistics, statistical_tests)

        # Devrait détecter anomalie : pas assez d'échantillons par classe
        assert len(anomalies) > 0
        assert any('échantillons' in a for a in anomalies)

    def test_quality_score(self):
        """Test de calcul du score de qualité"""
        verifier = DataVerifier()

        # Dataset parfait
        stats_perfect = DatasetStatistics(
            total_samples=500,
            class_distribution={'safe': 250, 'dangerous': 250},
            mean_image_size=(224.0, 224.0),
            mean_pixel_intensity=127.0,
            std_pixel_intensity=50.0,
            corrupted_images=0,
            duplicate_hashes=0,
            timestamp='2025-10-11T00:00:00Z'
        )

        score_perfect = verifier._calculate_quality_score(
            stats_perfect,
            {},
            []  # Pas d'anomalies
        )

        assert score_perfect >= 90.0  # Score élevé

        # Dataset avec problèmes
        stats_bad = DatasetStatistics(
            total_samples=50,
            class_distribution={'safe': 25, 'dangerous': 25},
            mean_image_size=(100.0, 100.0),
            mean_pixel_intensity=127.0,
            std_pixel_intensity=50.0,
            corrupted_images=5,  # Images corrompues
            duplicate_hashes=10,  # Duplicates
            timestamp='2025-10-11T00:00:00Z'
        )

        score_bad = verifier._calculate_quality_score(
            stats_bad,
            {},
            ['Anomalie 1', 'Anomalie 2']
        )

        assert score_bad < 70.0  # Score faible

    def test_save_report(self, sample_dataset, temp_test_dir):
        """Test de sauvegarde du rapport"""
        verifier = DataVerifier()
        report = verifier.verify_dataset(sample_dataset)

        output_path = Path(temp_test_dir) / 'report.json'
        verifier.save_report(report, str(output_path))

        # Vérifier que le fichier existe
        assert output_path.exists()

        # Vérifier le contenu JSON
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert 'dataset_path' in data
        assert 'quality_score' in data
        assert 'passed' in data


# ============================================================================
# TESTS - PoisoningDetector
# ============================================================================

class TestPoisoningDetector:
    """Tests pour le PoisoningDetector"""

    def test_initialization(self):
        """Test d'initialisation du PoisoningDetector"""
        detector = PoisoningDetector(
            eps=0.5,
            min_samples=5,
            contamination_threshold=0.05
        )

        assert detector.eps == 0.5
        assert detector.min_samples == 5
        assert detector.contamination_threshold == 0.05
        assert detector.device in [torch.device('cuda'), torch.device('cpu')]

    def test_feature_extractor(self):
        """Test du feature extractor ResNet50"""
        detector = PoisoningDetector()

        # Créer une image de test
        img_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)

        # Transformer l'image
        img_tensor = detector.transform(img).unsqueeze(0).to(detector.device)

        # Extraire features
        with torch.no_grad():
            features = detector.feature_extractor(img_tensor)

        # Vérifier la shape
        assert features.shape[0] == 1  # Batch size
        assert len(features.shape) == 4  # (batch, channels, height, width)

    def test_detect_poisoning_small_dataset(self, sample_dataset):
        """Test de détection sur un petit dataset (peut ne pas détecter d'outliers)"""
        detector = PoisoningDetector(
            eps=0.5,
            min_samples=3,
            use_pca=True,
            pca_components=10
        )

        # Exécuter détection (sans visualisation pour les tests)
        report = detector.detect_poisoning(
            sample_dataset,
            visualize=False
        )

        # Vérifications de base
        assert isinstance(report, PoisoningReport)
        assert report.total_samples == 20
        assert report.suspicious_percentage >= 0.0
        assert isinstance(report.recommendations, list)

    def test_clustering_metrics(self):
        """Test de calcul des métriques de clustering"""
        detector = PoisoningDetector()

        # Créer des labels de clusters simulés
        cluster_labels = np.array([0, 0, 0, 1, 1, 1, -1, -1])  # 2 clusters + 2 outliers
        features = np.random.randn(8, 10)

        metrics = detector._calculate_clustering_metrics(cluster_labels, features)

        assert metrics['n_clusters'] == 2
        assert metrics['n_outliers'] == 2
        assert metrics['n_samples'] == 8
        assert metrics['outlier_percentage'] == 25.0  # 2/8 = 25%

    def test_generate_recommendations(self):
        """Test de génération de recommandations"""
        detector = PoisoningDetector(contamination_threshold=0.05)

        # Cas 1: Aucun échantillon suspect
        recs_clean = detector._generate_recommendations(
            n_suspicious=0,
            n_total=100,
            metrics={'n_clusters': 2}
        )

        assert any('Aucun échantillon suspect' in r for r in recs_clean)

        # Cas 2: Contamination élevée
        recs_contaminated = detector._generate_recommendations(
            n_suspicious=20,
            n_total=100,
            metrics={'n_clusters': 3}
        )

        assert any('ALERTE' in r for r in recs_contaminated)

    def test_save_report(self, temp_test_dir):
        """Test de sauvegarde du rapport"""
        detector = PoisoningDetector()

        report = PoisoningReport(
            dataset_path='test_dataset',
            total_samples=100,
            suspicious_samples=5,
            suspicious_percentage=5.0,
            suspicious_files=['image1.jpg', 'image2.jpg'],
            clustering_metrics={'n_clusters': 2},
            recommendations=['Test recommendation'],
            timestamp='2025-10-11T00:00:00Z'
        )

        output_path = Path(temp_test_dir) / 'poisoning_report.json'
        detector.save_report(report, str(output_path))

        # Vérifier
        assert output_path.exists()

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert data['total_samples'] == 100
        assert data['suspicious_samples'] == 5


# ============================================================================
# TESTS - EncryptedStorage
# ============================================================================

class TestEncryptedStorage:
    """Tests pour le EncryptedStorage"""

    def test_initialization_with_password(self):
        """Test d'initialisation avec mot de passe"""
        storage = EncryptedStorage(password="test_password_123")

        assert storage.password == "test_password_123"
        assert storage.master_key is None  # Pas de clé maître en mode password

    def test_initialization_with_key(self):
        """Test d'initialisation avec clé directe"""
        key = os.urandom(32)  # 256 bits
        storage = EncryptedStorage(key=key)

        assert storage.master_key == key
        assert storage.password is None

    def test_initialization_invalid_key_size(self):
        """Test d'initialisation avec clé de mauvaise taille"""
        key = os.urandom(16)  # 128 bits (trop petit)

        with pytest.raises(ValueError):
            EncryptedStorage(key=key)

    def test_key_derivation(self):
        """Test de dérivation de clé avec PBKDF2"""
        storage = EncryptedStorage(password="test_password")

        salt = os.urandom(32)
        key1 = storage._derive_key("test_password", salt)
        key2 = storage._derive_key("test_password", salt)

        # Même mot de passe + même salt = même clé
        assert key1 == key2
        assert len(key1) == 32  # 256 bits

        # Salt différent = clé différente
        salt2 = os.urandom(32)
        key3 = storage._derive_key("test_password", salt2)
        assert key1 != key3

    def test_encrypt_decrypt_file(self, temp_test_dir):
        """Test de chiffrement/déchiffrement d'un fichier"""
        storage = EncryptedStorage(password="secure_password_123!")

        # Créer un fichier test
        test_file = Path(temp_test_dir) / 'test.txt'
        test_content = "Données sensibles de test\nLigne 2\nLigne 3"

        with open(test_file, 'w') as f:
            f.write(test_content)

        # Chiffrer
        encrypted_file = Path(temp_test_dir) / 'test.enc'
        metadata = storage.encrypt_file(
            str(test_file),
            str(encrypted_file)
        )

        # Vérifications métadonnées
        assert isinstance(metadata, EncryptionMetadata)
        assert metadata.algorithm == 'AES-256-GCM'
        assert metadata.original_size == len(test_content.encode('utf-8'))

        # Déchiffrer
        decrypted_file = Path(temp_test_dir) / 'test_decrypted.txt'
        success = storage.decrypt_file(
            str(encrypted_file),
            str(decrypted_file),
            metadata,
            verify_hash=True
        )

        assert success == True

        # Vérifier contenu
        with open(decrypted_file, 'r') as f:
            decrypted_content = f.read()

        assert decrypted_content == test_content

    def test_decrypt_wrong_password(self, temp_test_dir):
        """Test de déchiffrement avec mauvais mot de passe"""
        # Chiffrer avec un mot de passe
        storage_encrypt = EncryptedStorage(password="correct_password")

        test_file = Path(temp_test_dir) / 'secret.txt'
        with open(test_file, 'w') as f:
            f.write("Secret data")

        encrypted_file = Path(temp_test_dir) / 'secret.enc'
        metadata = storage_encrypt.encrypt_file(str(test_file), str(encrypted_file))

        # Tenter de déchiffrer avec mauvais mot de passe
        storage_decrypt = EncryptedStorage(password="wrong_password")

        decrypted_file = Path(temp_test_dir) / 'secret_decrypted.txt'
        success = storage_decrypt.decrypt_file(
            str(encrypted_file),
            str(decrypted_file),
            metadata
        )

        # Devrait échouer
        assert success == False

    def test_encrypt_pytorch_model(self, sample_model, temp_test_dir):
        """Test de chiffrement d'un modèle PyTorch"""
        storage = EncryptedStorage(password="model_password_123")

        encrypted_model = Path(temp_test_dir) / 'model.enc'
        metadata = storage.encrypt_pytorch_model(
            sample_model,
            str(encrypted_model)
        )

        assert metadata.algorithm == 'AES-256-GCM'
        assert encrypted_model.exists()

    def test_decrypt_pytorch_model(self, sample_model, temp_test_dir):
        """Test de déchiffrement d'un modèle PyTorch"""
        storage = EncryptedStorage(password="model_password_456")

        # Chiffrer
        encrypted_model = Path(temp_test_dir) / 'model.enc'
        metadata = storage.encrypt_pytorch_model(
            sample_model,
            str(encrypted_model)
        )

        # Déchiffrer
        decrypted_model = Path(temp_test_dir) / 'model_decrypted.pth'
        model_state = storage.decrypt_pytorch_model(
            str(encrypted_model),
            str(decrypted_model),
            metadata
        )

        # Vérifier
        assert model_state is not None
        assert 'model_state_dict' in model_state
        assert 'epoch' in model_state
        assert model_state['epoch'] == 10

    def test_metadata_save_load(self, temp_test_dir):
        """Test de sauvegarde/chargement des métadonnées"""
        storage = EncryptedStorage(password="test")

        # Créer métadonnées de test
        metadata = EncryptionMetadata(
            filename='test.txt',
            original_size=100,
            encrypted_size=128,
            algorithm='AES-256-GCM',
            key_derivation='PBKDF2-HMAC-SHA256',
            salt='c2FsdA==',
            nonce='bm9uY2U=',
            tag='dGFn',
            timestamp='2025-10-11T00:00:00Z',
            file_hash_sha256='abc123'
        )

        # Sauvegarder
        metadata_path = Path(temp_test_dir) / 'metadata.json'
        storage.save_metadata(metadata, str(metadata_path))

        # Charger
        loaded_metadata = EncryptedStorage.load_metadata(str(metadata_path))

        assert loaded_metadata.filename == 'test.txt'
        assert loaded_metadata.algorithm == 'AES-256-GCM'
        assert loaded_metadata.original_size == 100


# ============================================================================
# TESTS D'INTÉGRATION
# ============================================================================

class TestIntegration:
    """Tests d'intégration combinant plusieurs modules"""

    def test_full_data_security_pipeline(self, sample_dataset, temp_test_dir):
        """Test complet du pipeline de sécurité des données"""

        # 1. Vérifier le dataset
        verifier = DataVerifier()
        verification_report = verifier.verify_dataset(sample_dataset)

        assert verification_report.passed == True
        print(f"✓ Dataset vérifié - Score: {verification_report.quality_score}")

        # 2. Détecter l'empoisonnement
        detector = PoisoningDetector(eps=0.5, min_samples=3)
        poisoning_report = detector.detect_poisoning(
            sample_dataset,
            visualize=False
        )

        print(f"✓ Détection terminée - Suspects: {poisoning_report.suspicious_samples}")

        # 3. Chiffrer les résultats
        storage = EncryptedStorage(password="integration_test_password")

        # Sauvegarder les rapports
        verification_path = Path(temp_test_dir) / 'verification.json'
        verifier.save_report(verification_report, str(verification_path))

        poisoning_path = Path(temp_test_dir) / 'poisoning.json'
        detector.save_report(poisoning_report, str(poisoning_path))

        # Chiffrer les rapports
        enc_verif = Path(temp_test_dir) / 'verification.enc'
        metadata_verif = storage.encrypt_file(
            str(verification_path),
            str(enc_verif)
        )

        enc_poison = Path(temp_test_dir) / 'poisoning.enc'
        metadata_poison = storage.encrypt_file(
            str(poisoning_path),
            str(enc_poison)
        )

        print(f"✓ Rapports chiffrés avec AES-256-GCM")

        # Vérifier que tout est créé
        assert enc_verif.exists()
        assert enc_poison.exists()


# ============================================================================
# EXÉCUTION DES TESTS
# ============================================================================

if __name__ == '__main__':
    """Exécuter les tests avec pytest"""
    pytest.main([__file__, '-v', '--tb=short'])
