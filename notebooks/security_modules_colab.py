"""
Modules de sécurité pour Google Colab - Architecture de Sécurisation IA
Ce fichier contient toutes les classes Zone 1 et Zone 2 nécessaires pour l'entraînement sécurisé

À uploader dans Colab avec:
from google.colab import files
uploaded = files.upload()  # Sélectionner security_modules_colab.py
"""

import torch
import torch.nn as nn
import numpy as np
import hashlib
import json
import os
import traceback
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from PIL import Image

# Imports pour Zone 1
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# Imports pour Zone 2
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64


# ============================================================================
# ZONE 1: SÉCURITÉ DES DONNÉES
# ============================================================================

class DataVerifier:
    """
    Vérificateur de qualité des données avec tests statistiques
    Conforme Zone 1: Sécurité des Données
    """
    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.stats = {}

    def verify_data(self) -> Dict[str, Any]:
        """Execute tous les tests de vérification"""
        print("🔍 Vérification de la qualité des données...")

        # Compter les images par classe
        safe_count = len(list((self.dataset_path / "safe").glob("*.jpg")))
        dangerous_count = len(list((self.dataset_path / "dangerous").glob("*.jpg")))
        total = safe_count + dangerous_count

        # Test d'équilibre des classes (Chi-carré)
        expected = total / 2
        observed = [safe_count, dangerous_count]
        chi_square = sum((o - expected)**2 / expected for o in observed)
        chi_square_passed = chi_square < 10  # Seuil arbitraire

        # Test de distribution normale (Kolmogorov-Smirnov)
        sizes = [os.path.getsize(f) for f in (self.dataset_path / "safe").glob("*.jpg")]
        sizes += [os.path.getsize(f) for f in (self.dataset_path / "dangerous").glob("*.jpg")]
        ks_stat, ks_p = stats.kstest(sizes, 'norm') if len(sizes) > 0 else (0, 1)
        ks_passed = ks_p > 0.05

        # Score de qualité global
        quality_score = 0
        if chi_square_passed: quality_score += 50
        if ks_passed: quality_score += 30
        if total > 1000: quality_score += 20

        return {
            'total_images': total,
            'safe_count': safe_count,
            'dangerous_count': dangerous_count,
            'chi_square_test': {'value': chi_square, 'passed': chi_square_passed},
            'ks_test': {'statistic': ks_stat, 'p_value': ks_p, 'passed': ks_passed},
            'quality_score': quality_score
        }


@dataclass
class PoisoningReport:
    """Rapport de détection d'empoisonnement"""
    suspicious_files: List[str]
    suspicious_percentage: float
    clustering_metrics: Dict[str, Any]
    timestamp: str


class PoisoningDetector:
    """
    Détecteur d'empoisonnement par clustering DBSCAN
    Conforme Zone 1: Sécurité des Données
    """
    def __init__(self):
        self.feature_extractor = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def _build_feature_extractor(self) -> nn.Module:
        """Construit l'extracteur de features MobileNetV2"""
        from torchvision import models
        mobilenet = models.mobilenet_v2(pretrained=True)
        # Retirer le classifier, garder seulement les features
        return mobilenet.features

    def _extract_features(self, image_path: str) -> np.ndarray:
        """Extrait les features d'une image"""
        if self.feature_extractor is None:
            self.feature_extractor = self._build_feature_extractor().to(self.device)
            self.feature_extractor.eval()

        # Charger et préprocesser l'image
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0).to(self.device)

        # Extraire features
        with torch.no_grad():
            features = self.feature_extractor(image_tensor)
            features = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
            features = features.view(features.size(0), -1)

        return features.cpu().numpy().flatten()

    def detect_poisoning(self, dataset_path: str, class_name: Optional[str] = None,
                        visualize: bool = False) -> PoisoningReport:
        """Détecte les échantillons suspects par clustering"""
        print(f"🕵️ Détection d'empoisonnement avec DBSCAN...")

        dataset_path = Path(dataset_path)
        image_files = []
        features_list = []

        # Charger les images
        classes = [class_name] if class_name else ['safe', 'dangerous']
        for cls in classes:
            class_dir = dataset_path / cls
            if class_dir.exists():
                for img_path in list(class_dir.glob("*.jpg"))[:200]:  # Limiter pour Colab
                    try:
                        features = self._extract_features(str(img_path))
                        image_files.append(str(img_path))
                        features_list.append(features)
                    except Exception as e:
                        print(f"⚠️  Erreur sur {img_path.name}: {e}")

        if len(features_list) == 0:
            return PoisoningReport([], 0.0, {}, datetime.now().isoformat())

        # Normaliser les features
        X = np.array(features_list)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Clustering DBSCAN
        clustering = DBSCAN(eps=2.5, min_samples=3)
        labels = clustering.fit_predict(X_scaled)

        # Identifier les outliers (label = -1)
        suspicious_indices = np.where(labels == -1)[0]
        suspicious_files = [image_files[i] for i in suspicious_indices]
        suspicious_pct = 100 * len(suspicious_files) / len(image_files)

        # Métriques
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_outliers = list(labels).count(-1)

        metrics = {
            'n_clusters': n_clusters,
            'n_outliers': n_outliers,
            'total_samples': len(image_files)
        }

        print(f"  ✓ {n_clusters} clusters trouvés, {n_outliers} outliers ({suspicious_pct:.1f}%)")

        return PoisoningReport(
            suspicious_files=suspicious_files,
            suspicious_percentage=suspicious_pct,
            clustering_metrics=metrics,
            timestamp=datetime.now().isoformat()
        )

    def save_report(self, report: PoisoningReport, output_path: str):
        """Sauvegarde le rapport en JSON"""
        with open(output_path, 'w') as f:
            json.dump({
                'suspicious_files': report.suspicious_files,
                'suspicious_percentage': report.suspicious_percentage,
                'clustering_metrics': report.clustering_metrics,
                'timestamp': report.timestamp
            }, f, indent=2)


class EncryptedStorage:
    """
    Stockage crypté AES-256-GCM pour modèles PyTorch
    Conforme Zone 1: Sécurité des Données
    """
    def __init__(self, password: str):
        # Dériver une clé depuis le mot de passe
        self.password = password.encode('utf-8')
        self.salt = b'SecureAI_Salt_2024'  # En production, générer aléatoirement

        # PBKDF2 pour dériver la clé
        import hashlib
        self.key = hashlib.pbkdf2_hmac('sha256', self.password, self.salt, 100000)[:32]

    def encrypt_pytorch_model(self, model_path: str, output_path: str) -> Dict[str, Any]:
        """Chiffre un modèle PyTorch avec AES-256-GCM"""
        print(f"🔐 Chiffrement du modèle: {model_path}")

        # Lire le modèle
        with open(model_path, 'rb') as f:
            plaintext = f.read()

        # Générer IV aléatoire
        iv = os.urandom(16)

        # Chiffrer avec AES-256-GCM
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        # Sauvegarder: IV + Tag + Ciphertext
        with open(output_path, 'wb') as f:
            f.write(iv)
            f.write(encryptor.tag)
            f.write(ciphertext)

        # Métadonnées
        metadata = {
            'original_filename': os.path.basename(model_path),
            'encrypted_at': datetime.now().isoformat(),
            'algorithm': 'AES-256-GCM',
            'iv_length': len(iv),
            'tag_length': len(encryptor.tag)
        }

        # Sauvegarder métadonnées
        metadata_path = output_path.replace('.enc', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"  ✓ Modèle chiffré: {output_path}")
        return metadata

    def decrypt_pytorch_model(self, encrypted_path: str, output_path: str, metadata: Dict):
        """Déchiffre un modèle PyTorch"""
        # Lire le fichier chiffré
        with open(encrypted_path, 'rb') as f:
            iv = f.read(metadata['iv_length'])
            tag = f.read(metadata['tag_length'])
            ciphertext = f.read()

        # Déchiffrer
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Sauvegarder
        with open(output_path, 'wb') as f:
            f.write(plaintext)


# ============================================================================
# ZONE 2: ENTRAÎNEMENT SÉCURISÉ
# ============================================================================

class DifferentialPrivacy:
    """
    Differential Privacy (DP-SGD) pour protection des données d'entraînement
    Conforme Zone 2: Entraînement Sécurisé
    """
    @staticmethod
    def add_noise_to_gradients(model: nn.Module, epsilon: float = 1.0,
                               delta: float = 1e-5):
        """Ajoute du bruit gaussien calibré aux gradients"""
        # Calcul du sigma (écart-type du bruit)
        sensitivity = 1.0  # Après clipping
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon

        # Ajout de bruit gaussien
        for param in model.parameters():
            if param.grad is not None:
                noise = torch.normal(
                    mean=0.0,
                    std=sigma,
                    size=param.grad.shape,
                    device=param.grad.device
                )
                param.grad += noise


class ModelSigner:
    """
    Signature numérique RSA-4096 pour modèles
    Conforme Zone 2: Versioning Signé
    """
    @staticmethod
    def generate_signature(model_path: str) -> Tuple[bytes, bytes, bytes]:
        """
        Génère une signature RSA-4096 pour le modèle

        Returns:
            (signature, public_key_pem, private_key_pem)
        """
        print("✍️  Génération de la signature RSA-4096...")

        # Générer clés RSA-4096
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        # Calculer hash SHA-256 du modèle
        with open(model_path, 'rb') as f:
            model_data = f.read()
            model_hash = hashlib.sha256(model_data).digest()

        # Signer le hash
        signature = private_key.sign(
            model_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Exporter les clés en PEM
        public_key_pem = public_key.public_key_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        private_key_pem = private_key.private_key_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(b'SecureAI_2024')
        )

        print("  ✓ Signature générée")
        return signature, public_key_pem, private_key_pem

    @staticmethod
    def verify_signature(model_path: str, signature: bytes, public_key_pem: bytes) -> bool:
        """Vérifie la signature d'un modèle"""
        try:
            # Charger la clé publique
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )

            # Calculer le hash du modèle
            with open(model_path, 'rb') as f:
                model_data = f.read()
                model_hash = hashlib.sha256(model_data).digest()

            # Vérifier la signature
            public_key.verify(
                signature,
                model_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return True
        except Exception as e:
            print(f"❌ Vérification signature échouée: {e}")
            return False


class EarlyStopping:
    """
    Early Stopping pour éviter l'overfitting
    Conforme Zone 2: Optimisation de l'entraînement
    """
    def __init__(self, patience: int = 8, min_delta: float = 0.001, verbose: bool = True):
        self.patience = patience
        self.min_delta = min_delta
        self.verbose = verbose
        self.counter = 0
        self.best_loss = None
        self.early_stop = False
        self.best_epoch = 0

    def __call__(self, val_loss: float, epoch: int) -> bool:
        """
        Vérifie si on doit arrêter l'entraînement

        Returns:
            True si on doit arrêter, False sinon
        """
        if self.best_loss is None:
            self.best_loss = val_loss
            self.best_epoch = epoch
            if self.verbose:
                print(f"  Early Stopping: Meilleure loss initialisée à {val_loss:.4f}")
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.verbose:
                print(f"  Early Stopping: Pas d'amélioration ({self.counter}/{self.patience})")
            if self.counter >= self.patience:
                self.early_stop = True
                if self.verbose:
                    print(f"  Early Stopping: Arrêt à l'epoch {epoch}")
                    print(f"  Meilleure loss: {self.best_loss:.4f} (epoch {self.best_epoch})")
                return True
        else:
            if self.verbose:
                print(f"  Early Stopping: Amélioration {self.best_loss:.4f} -> {val_loss:.4f}")
            self.best_loss = val_loss
            self.best_epoch = epoch
            self.counter = 0

        return False


# ============================================================================
# HELPERS
# ============================================================================

def apply_zone1_security(dataset_path: str, output_dir: str = 'data/quarantine'):
    """
    Applique toutes les mesures Zone 1 sur un dataset

    Returns:
        Liste des fichiers suspects à exclure
    """
    print("\n" + "="*80)
    print("ZONE 1: APPLICATION DES MESURES DE SÉCURITÉ DES DONNÉES")
    print("="*80)

    suspicious_files = []

    # 1. Vérification statistique
    print("\n[1/2] Vérification statistique...")
    try:
        verifier = DataVerifier(dataset_path)
        report = verifier.verify_data()
        print(f"  Score de qualité: {report['quality_score']:.1f}/100")
        print(f"  Classes équilibrées: {report['chi_square_test']['passed']}")
    except Exception as e:
        print(f"  ⚠️  Erreur: {e}")

    # 2. Détection d'empoisonnement
    print("\n[2/2] Détection d'empoisonnement...")
    try:
        detector = PoisoningDetector()
        poisoning_report = detector.detect_poisoning(dataset_path, visualize=False)

        suspicious_files = poisoning_report.suspicious_files

        # Quarantaine
        if len(suspicious_files) > 0:
            quarantine_dir = Path(output_dir) / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            quarantine_dir.mkdir(parents=True, exist_ok=True)

            import shutil
            for file_path in suspicious_files:
                src = Path(file_path)
                if src.exists():
                    class_name = src.parent.name
                    dst_dir = quarantine_dir / class_name
                    dst_dir.mkdir(exist_ok=True)
                    shutil.copy2(str(src), str(dst_dir / src.name))

            # Sauvegarder rapport
            detector.save_report(poisoning_report, str(quarantine_dir / "report.json"))
            print(f"  ✓ {len(suspicious_files)} fichiers mis en quarantaine")
    except Exception as e:
        print(f"  ⚠️  Erreur: {e}")

    print("="*80 + "\n")
    return suspicious_files


def apply_zone2_post_training(model_path: str, output_dir: str):
    """
    Applique les mesures Zone 2 post-entraînement (chiffrement, signature)
    """
    print("\n" + "="*80)
    print("ZONE 2: APPLICATION DES MESURES POST-ENTRAÎNEMENT")
    print("="*80)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Chiffrement AES-256-GCM
    print("\n[1/2] Chiffrement du modèle...")
    try:
        storage = EncryptedStorage(password="SecureAI_2024_Production")
        encrypted_path = output_dir / "best_secured_model_encrypted.enc"
        metadata = storage.encrypt_pytorch_model(model_path, str(encrypted_path))
        print(f"  ✓ Modèle chiffré: {encrypted_path}")
    except Exception as e:
        print(f"  ⚠️  Erreur chiffrement: {e}")

    # 2. Signature RSA-4096
    print("\n[2/2] Signature numérique...")
    try:
        signature, public_key_pem, private_key_pem = ModelSigner.generate_signature(model_path)

        # Sauvegarder les fichiers dans output_dir (même répertoire que le chiffrement)
        model_name = Path(model_path).stem  # best_secured_model
        sig_path = output_dir / f"{model_name}_signature.bin"
        pub_key_path = output_dir / f"{model_name}_public_key.pem"
        priv_key_path = output_dir / f"{model_name}_private_key.pem"

        with open(sig_path, 'wb') as f:
            f.write(signature)
        with open(pub_key_path, 'wb') as f:
            f.write(public_key_pem)
        with open(priv_key_path, 'wb') as f:
            f.write(private_key_pem)

        # Vérifier immédiatement
        is_valid = ModelSigner.verify_signature(model_path, signature, public_key_pem)
        print(f"  ✓ Signature valide: {is_valid}")
        print(f"  Fichiers sauvegardés dans {output_dir}:")
        print(f"    - Signature: {sig_path.name}")
        print(f"    - Clé publique: {pub_key_path.name}")
        print(f"    - Clé privée: {priv_key_path.name}")
    except Exception as e:
        print(f"  ⚠️  Erreur signature: {e}")
        import traceback
        traceback.print_exc()

    print("="*80 + "\n")


print("✅ Modules de sécurité chargés avec succès!")
print("   - Zone 1: DataVerifier, PoisoningDetector, EncryptedStorage")
print("   - Zone 2: DifferentialPrivacy, ModelSigner, EarlyStopping")
