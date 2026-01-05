"""
Encrypted Storage - Système de Stockage Crypté AES-256-GCM
===========================================================

Ce module implémente un système de stockage crypté pour protéger les modèles,
datasets, et données sensibles avec AES-256-GCM.

Fonctionnalités:
- Chiffrement AES-256-GCM (Galois/Counter Mode)
- Gestion sécurisée des clés avec dérivation PBKDF2
- Authentification et intégrité avec GCM tags
- API simple pour encrypt/decrypt de fichiers
- Support modèles PyTorch, images, datasets

Conformité:
- Zone 1: Sécurité des Données
- Algorithme: AES-256-GCM (NIST FIPS 140-2)
- Dérivation de clé: PBKDF2-HMAC-SHA256
- Nonce: 96 bits aléatoires (recommandation NIST)

Sécurité:
- AES-256: Standard militaire US (top secret)
- GCM: Authenticated encryption (confidentialité + intégrité)
- PBKDF2: Protection contre brute-force (100,000 itérations)
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import base64

# Cryptography
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# PyTorch (pour modèles)
import torch


@dataclass
class EncryptionMetadata:
    """Métadonnées de chiffrement"""
    filename: str
    original_size: int
    encrypted_size: int
    algorithm: str
    key_derivation: str
    salt: str  # Base64
    nonce: str  # Base64
    tag: str  # Base64
    timestamp: str
    file_hash_sha256: str


class EncryptedStorage:
    """
    Système de stockage crypté AES-256-GCM

    Ce système permet de :
    1. Chiffrer/déchiffrer des fichiers (modèles, images, datasets)
    2. Gérer les clés de manière sécurisée
    3. Garantir l'authenticité et l'intégrité des données
    4. Générer des métadonnées de chiffrement

    Exemple d'utilisation:
        # Initialiser avec mot de passe
        storage = EncryptedStorage(password="my_secure_password")

        # Chiffrer un modèle PyTorch
        metadata = storage.encrypt_file(
            'models/best_model.pth',
            'models/encrypted/best_model.enc'
        )

        # Déchiffrer
        storage.decrypt_file(
            'models/encrypted/best_model.enc',
            'models/decrypted/best_model.pth',
            metadata
        )

    Sécurité:
    - Ne jamais stocker le mot de passe en clair
    - Utiliser un mot de passe fort (>20 caractères)
    - Stocker les métadonnées séparément des fichiers chiffrés
    """

    # Constantes de sécurité (conformes NIST)
    ALGORITHM = 'AES-256-GCM'
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits (recommandation GCM)
    TAG_SIZE = 16  # 128 bits
    SALT_SIZE = 32  # 256 bits
    PBKDF2_ITERATIONS = 100000  # 100k itérations (OWASP recommandé)

    def __init__(self, password: Optional[str] = None, key: Optional[bytes] = None):
        """
        Initialise le système de stockage crypté

        Args:
            password: Mot de passe pour dériver la clé (recommandé)
            key: Clé AES-256 directe (32 bytes) - à utiliser avec précaution

        Note:
            Si ni password ni key fourni, génère une clé aléatoire
        """
        if password:
            # Dériver la clé depuis le mot de passe
            self.password = password
            self.master_key = None  # Sera dérivé à chaque opération avec salt unique
        elif key:
            if len(key) != self.KEY_SIZE:
                raise ValueError(f"La clé doit faire {self.KEY_SIZE} bytes (256 bits)")
            self.master_key = key
            self.password = None
        else:
            # Générer une clé aléatoire sécurisée
            self.master_key = os.urandom(self.KEY_SIZE)
            self.password = None
            print("⚠ Clé aléatoire générée - Sauvegarder impérativement!")

        self.backend = default_backend()

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Dérive une clé AES-256 depuis un mot de passe avec PBKDF2

        Args:
            password: Mot de passe
            salt: Salt cryptographique

        Returns:
            bytes: Clé dérivée (32 bytes)
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=self.backend
        )
        return kdf.derive(password.encode('utf-8'))

    def encrypt_file(
        self,
        input_path: str,
        output_path: str,
        metadata_path: Optional[str] = None
    ) -> EncryptionMetadata:
        """
        Chiffre un fichier avec AES-256-GCM

        Args:
            input_path: Chemin du fichier à chiffrer
            output_path: Chemin du fichier chiffré
            metadata_path: Chemin des métadonnées (optionnel)

        Returns:
            EncryptionMetadata: Métadonnées de chiffrement
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {input_path}")

        print(f"\n=== Chiffrement: {input_path.name} ===")

        # Créer répertoire de sortie
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Générer salt et nonce aléatoires
        salt = os.urandom(self.SALT_SIZE)
        nonce = os.urandom(self.NONCE_SIZE)

        # 2. Dériver/obtenir la clé
        if self.password:
            key = self._derive_key(self.password, salt)
        else:
            key = self.master_key

        # 3. Lire le fichier
        with open(input_path, 'rb') as f:
            plaintext = f.read()

        original_size = len(plaintext)
        print(f"  Taille originale: {original_size:,} bytes")

        # 4. Calculer hash SHA-256 du fichier original
        file_hash = hashlib.sha256(plaintext).hexdigest()

        # 5. Chiffrer avec AES-256-GCM
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=self.backend
        )
        encryptor = cipher.encryptor()

        # GCM fournit authenticated encryption
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        tag = encryptor.tag  # Tag d'authentification GCM

        encrypted_size = len(ciphertext)
        print(f"  Taille chiffrée: {encrypted_size:,} bytes")

        # 6. Sauvegarder le fichier chiffré
        with open(output_path, 'wb') as f:
            f.write(ciphertext)

        print(f"✓ Fichier chiffré: {output_path}")

        # 7. Créer les métadonnées
        metadata = EncryptionMetadata(
            filename=input_path.name,
            original_size=original_size,
            encrypted_size=encrypted_size,
            algorithm=self.ALGORITHM,
            key_derivation='PBKDF2-HMAC-SHA256' if self.password else 'Direct',
            salt=base64.b64encode(salt).decode('utf-8'),
            nonce=base64.b64encode(nonce).decode('utf-8'),
            tag=base64.b64encode(tag).decode('utf-8'),
            timestamp=datetime.utcnow().isoformat() + 'Z',
            file_hash_sha256=file_hash
        )

        # 8. Sauvegarder les métadonnées
        if metadata_path:
            self.save_metadata(metadata, metadata_path)
        else:
            # Par défaut : même nom avec .meta.json
            default_metadata_path = str(output_path) + '.meta.json'
            self.save_metadata(metadata, default_metadata_path)

        return metadata

    def decrypt_file(
        self,
        input_path: str,
        output_path: str,
        metadata: EncryptionMetadata,
        verify_hash: bool = True
    ) -> bool:
        """
        Déchiffre un fichier avec AES-256-GCM

        Args:
            input_path: Chemin du fichier chiffré
            output_path: Chemin du fichier déchiffré
            metadata: Métadonnées de chiffrement
            verify_hash: Vérifier l'intégrité avec SHA-256

        Returns:
            bool: True si déchiffrement réussi, False sinon
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Fichier introuvable: {input_path}")

        print(f"\n=== Déchiffrement: {input_path.name} ===")

        # Créer répertoire de sortie
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Lire le fichier chiffré
        with open(input_path, 'rb') as f:
            ciphertext = f.read()

        print(f"  Taille chiffrée: {len(ciphertext):,} bytes")

        # 2. Décoder les métadonnées
        salt = base64.b64decode(metadata.salt)
        nonce = base64.b64decode(metadata.nonce)
        tag = base64.b64decode(metadata.tag)

        # 3. Dériver/obtenir la clé
        if self.password:
            key = self._derive_key(self.password, salt)
        else:
            key = self.master_key

        # 4. Déchiffrer avec AES-256-GCM
        try:
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=self.backend
            )
            decryptor = cipher.decryptor()

            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            print(f"  Taille déchiffrée: {len(plaintext):,} bytes")

        except Exception as e:
            print(f"✗ Échec du déchiffrement: {str(e)}")
            print("  Causes possibles:")
            print("    - Mot de passe incorrect")
            print("    - Fichier corrompu")
            print("    - Tag d'authentification invalide")
            return False

        # 5. Vérifier l'intégrité (optionnel)
        if verify_hash:
            computed_hash = hashlib.sha256(plaintext).hexdigest()
            if computed_hash != metadata.file_hash_sha256:
                print(f"✗ ERREUR: Hash SHA-256 ne correspond pas!")
                print(f"  Attendu: {metadata.file_hash_sha256}")
                print(f"  Obtenu: {computed_hash}")
                return False
            print(f"✓ Intégrité vérifiée (SHA-256)")

        # 6. Sauvegarder le fichier déchiffré
        with open(output_path, 'wb') as f:
            f.write(plaintext)

        print(f"✓ Fichier déchiffré: {output_path}")
        return True

    def encrypt_pytorch_model(
        self,
        model_path: str,
        output_path: str,
        metadata_path: Optional[str] = None
    ) -> EncryptionMetadata:
        """
        Chiffre un modèle PyTorch (.pth ou .pt)

        Args:
            model_path: Chemin du modèle PyTorch
            output_path: Chemin du modèle chiffré
            metadata_path: Chemin des métadonnées

        Returns:
            EncryptionMetadata: Métadonnées de chiffrement
        """
        print(f"\n=== Chiffrement Modèle PyTorch ===")

        # Vérifier que c'est bien un modèle PyTorch
        if not model_path.endswith(('.pth', '.pt')):
            print("⚠ Extension non reconnue (.pth ou .pt attendu)")

        # Chiffrer comme n'importe quel fichier
        return self.encrypt_file(model_path, output_path, metadata_path)

    def decrypt_pytorch_model(
        self,
        encrypted_path: str,
        output_path: str,
        metadata: EncryptionMetadata
    ) -> Optional[Dict[str, Any]]:
        """
        Déchiffre un modèle PyTorch et le charge

        Args:
            encrypted_path: Chemin du modèle chiffré
            output_path: Chemin du modèle déchiffré
            metadata: Métadonnées de chiffrement

        Returns:
            Dict: État du modèle PyTorch (ou None si échec)
        """
        print(f"\n=== Déchiffrement Modèle PyTorch ===")

        # Déchiffrer
        success = self.decrypt_file(encrypted_path, output_path, metadata)

        if not success:
            return None

        # Charger le modèle PyTorch
        try:
            model_state = torch.load(output_path, map_location='cpu')
            print(f"✓ Modèle PyTorch chargé")
            return model_state
        except Exception as e:
            print(f"✗ Erreur chargement PyTorch: {str(e)}")
            return None

    def save_metadata(self, metadata: EncryptionMetadata, output_path: str):
        """
        Sauvegarde les métadonnées de chiffrement

        Args:
            metadata: Métadonnées à sauvegarder
            output_path: Chemin de sortie
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)

        print(f"✓ Métadonnées sauvegardées: {output_path}")

    @staticmethod
    def load_metadata(metadata_path: str) -> EncryptionMetadata:
        """
        Charge les métadonnées de chiffrement

        Args:
            metadata_path: Chemin des métadonnées

        Returns:
            EncryptionMetadata: Métadonnées chargées
        """
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return EncryptionMetadata(**data)

    def export_key(self, output_path: str, protect_password: Optional[str] = None):
        """
        Exporte la clé maître (ATTENTION: très sensible!)

        Args:
            output_path: Chemin de sortie
            protect_password: Mot de passe pour protéger la clé exportée

        Warning:
            Cette fonction doit être utilisée avec EXTRÊME PRÉCAUTION.
            La clé maître permet de déchiffrer TOUTES les données.
        """
        if not self.master_key:
            print("✗ Pas de clé maître à exporter (mode password)")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if protect_password:
            # Chiffrer la clé avec un mot de passe
            salt = os.urandom(self.SALT_SIZE)
            nonce = os.urandom(self.NONCE_SIZE)

            # Dériver clé de protection
            protection_key = self._derive_key(protect_password, salt)

            # Chiffrer la clé maître
            cipher = Cipher(
                algorithms.AES(protection_key),
                modes.GCM(nonce),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            encrypted_key = encryptor.update(self.master_key) + encryptor.finalize()
            tag = encryptor.tag

            # Sauvegarder
            key_data = {
                'encrypted_key': base64.b64encode(encrypted_key).decode('utf-8'),
                'salt': base64.b64encode(salt).decode('utf-8'),
                'nonce': base64.b64encode(nonce).decode('utf-8'),
                'tag': base64.b64encode(tag).decode('utf-8'),
                'protected': True
            }
        else:
            # Export en clair (DANGEREUX!)
            key_data = {
                'key': base64.b64encode(self.master_key).decode('utf-8'),
                'protected': False
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(key_data, f, indent=2)

        print(f"⚠ CLÉ EXPORTÉE: {output_path}")
        print("  ATTENTION: Protéger ce fichier avec maximum de sécurité!")


if __name__ == '__main__':
    """
    Script de démonstration du EncryptedStorage
    """
    import sys

    print("="*60)
    print("DÉMONSTRATION - Encrypted Storage AES-256-GCM")
    print("="*60)

    # Créer le système de stockage avec mot de passe
    password = "demo_password_secure_123!"
    storage = EncryptedStorage(password=password)

    # Test 1: Chiffrer un modèle PyTorch (si existe)
    model_path = 'models/baseline/best_model.pth'

    if os.path.exists(model_path):
        print("\n[TEST 1] Chiffrement d'un modèle PyTorch")
        metadata = storage.encrypt_pytorch_model(
            model_path,
            'models/encrypted/best_model.enc',
            'models/encrypted/best_model.meta.json'
        )

        # Déchiffrer
        print("\n[TEST 2] Déchiffrement du modèle")
        model_state = storage.decrypt_pytorch_model(
            'models/encrypted/best_model.enc',
            'models/decrypted/best_model.pth',
            metadata
        )

        if model_state:
            print("✓ Modèle déchiffré et chargé avec succès!")
        else:
            print("✗ Échec du déchiffrement")
    else:
        print(f"⚠ Modèle non trouvé: {model_path}")
        print("  Créer un fichier test à la place...")

        # Créer un fichier test
        test_dir = Path('models/test')
        test_dir.mkdir(parents=True, exist_ok=True)

        test_file = test_dir / 'test_data.txt'
        with open(test_file, 'w') as f:
            f.write("Données sensibles de test pour chiffrement AES-256-GCM\n")
            f.write("="*60 + "\n")
            f.write("Ce fichier doit être protégé cryptographiquement.\n")

        print(f"\n[TEST] Chiffrement d'un fichier test")
        metadata = storage.encrypt_file(
            str(test_file),
            'models/encrypted/test_data.enc',
            'models/encrypted/test_data.meta.json'
        )

        print(f"\n[TEST] Déchiffrement du fichier test")
        success = storage.decrypt_file(
            'models/encrypted/test_data.enc',
            'models/decrypted/test_data.txt',
            metadata
        )

        if success:
            print("✓ Fichier déchiffré avec succès!")

            # Vérifier le contenu
            with open('models/decrypted/test_data.txt', 'r') as f:
                content = f.read()
            print("\nContenu déchiffré:")
            print(content)
        else:
            print("✗ Échec du déchiffrement")

    print("\n" + "="*60)
    print("DÉMONSTRATION TERMINÉE")
    print("="*60)
