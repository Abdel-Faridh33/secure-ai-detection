"""
Secured Model Training - Zone 2: Entraînement Sécurisé
Conforme à l'Architecture de Sécurisation IA

Ce module implémente l'entraînement sécurisé défini dans la Zone 2 :
- Adversarial Training contre attaques PGD/FGSM
- Differential Privacy pour protection données
- Environnement isolé et monitoring robustesse
- Versioning signé des modèles sécurisés

INTÉGRATION ZONE 1 - Sécurité des Données :
- Vérification des données avec tests statistiques (DataVerifier)
- Détection d'empoisonnement par clustering (PoisoningDetector)
- Stockage crypté des modèles (EncryptedStorage)
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import matplotlib.pyplot as plt
import hashlib
import hmac
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

# ZONE 1: Import des modules de sécurité des données
sys.path.append(str(Path(__file__).parent.parent.parent))
from data.data_verifier import DataVerifier
from data.poisoning_detector import PoisoningDetector
from data.encrypted_storage import EncryptedStorage

class DangerousObjectDataset:
    """Dataset personnalisé pour objets dangereux vs sûrs"""

    def __init__(self, root_dir, transform=None, excluded_files=None):
        """
        Args:
            root_dir: Chemin vers le répertoire des données
            transform: Transformations à appliquer
            excluded_files: Liste de chemins de fichiers à exclure (quarantaine)
        """
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []
        self.excluded_count = 0

        # Normaliser les chemins exclus pour comparaison
        excluded_set = set()
        if excluded_files:
            excluded_set = {str(Path(f).resolve()) for f in excluded_files}

        # Parcourir safe et dangerous
        safe_dir = self.root_dir / "safe"
        if safe_dir.exists():
            for img_path in safe_dir.glob("*.jpg"):
                # Vérifier si le fichier est dans la liste d'exclusion
                if str(img_path.resolve()) not in excluded_set:
                    self.samples.append((str(img_path), 0))
                else:
                    self.excluded_count += 1

        dangerous_dir = self.root_dir / "dangerous"
        if dangerous_dir.exists():
            for img_path in dangerous_dir.glob("*.jpg"):
                # Vérifier si le fichier est dans la liste d'exclusion
                if str(img_path.resolve()) not in excluded_set:
                    self.samples.append((str(img_path), 1))
                else:
                    self.excluded_count += 1

        print(f"Dataset securise charge: {len(self.samples)} echantillons")
        if self.excluded_count > 0:
            print(f"  Fichiers exclus (quarantaine): {self.excluded_count}")
        print(f"  - Safe: {len([s for s in self.samples if s[1] == 0])}")
        print(f"  - Dangerous: {len([s for s in self.samples if s[1] == 1])}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')

        if self.transform:
            image = self.transform(image)

        return image, label

class EarlyStopping:
    """
    Early Stopping pour éviter l'overfitting
    Arrête l'entraînement si la validation loss ne s'améliore pas pendant N epochs
    """
    def __init__(self, patience=8, min_delta=0.001, verbose=True):
        """
        Args:
            patience: Nombre d'epochs à attendre avant d'arrêter
            min_delta: Changement minimum considéré comme amélioration
            verbose: Afficher les messages
        """
        self.patience = patience
        self.min_delta = min_delta
        self.verbose = verbose
        self.counter = 0
        self.best_loss = None
        self.early_stop = False
        self.best_epoch = 0

    def __call__(self, val_loss, epoch):
        """
        Vérifie si on doit arrêter l'entraînement

        Args:
            val_loss: Loss de validation actuelle
            epoch: Numéro d'epoch actuelle

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

class SecuredTrainer:
    """
    Entraîneur de modèles sécurisés conforme à l'Architecture de Sécurisation
    Zone 2: Entraînement Sécurisé avec Adversarial Training et Differential Privacy
    """
    
    def __init__(self, config):
        self.config = config
        self.device = torch.device('cpu')  # CPU pour reproductibilité sécurisée
        
        # Initialisation logging sécurisé (Zone 5: Gouvernance)
        self.security_log = []
        self.training_metrics = []
        self._log_security_event("INIT", "Initialisation entrainement securise", "INFO")
        
        # Configuration chemins sécurisés
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.models_dir = self.project_root / "models" / "secured"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.results_dir = self.project_root / "results" / "secured_training"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Chargement sécurisé des données
        self._load_secure_datasets()
        
        # Initialisation modèle sécurisé
        self._create_secured_model()
        
        self._log_security_event("SETUP_COMPLETE", "Configuration securisee terminee", "INFO")
    
    def _log_security_event(self, event_type, message, level):
        """Système de logging sécurisé conforme Zone 5: Gouvernance"""
        timestamp = datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "level": level,
            "component": "SecuredTrainer"
        }
        self.security_log.append(event)
        print(f"[{timestamp}] {level}: {message}")
    
    def _load_secure_datasets(self):
        """Chargement sécurisé des datasets avec validation d'intégrité"""
        self._log_security_event("DATA_LOAD_START", "Chargement securise des donnees", "INFO")

        # ============================================================
        # ZONE 1: VÉRIFICATION DES DONNÉES AVEC TESTS STATISTIQUES
        # ============================================================
        print("\n" + "="*80)
        print("ZONE 1: VERIFICATION DE LA SECURITE DES DONNEES")
        print("="*80)

        train_data_dir = str(self.project_root / "data" / "prepared" / "train")

        # 1. Vérification statistique des données
        print("\n[1/2] Verification statistique des donnees d'entrainement...")
        try:
            verifier = DataVerifier(train_data_dir)
            data_report = verifier.verify_data()

            print(f"  Score de qualite: {data_report['quality_score']:.1f}/100")
            print(f"  Classes equilibrees: {data_report['chi_square_test']['passed']}")
            print(f"  Distribution normale: {data_report['ks_test']['passed']}")

            # Seuil de qualité minimum
            if data_report['quality_score'] < 60:
                self._log_security_event("DATA_QUALITY_LOW",
                    f"ALERTE: Qualite des donnees trop faible ({data_report['quality_score']:.1f}/100)",
                    "WARNING")
                print(f"  AVERTISSEMENT: Score de qualite bas!")
            else:
                self._log_security_event("DATA_QUALITY_OK",
                    f"Donnees validees - Score: {data_report['quality_score']:.1f}/100", "INFO")
                print(f"  VALIDATION: Donnees de bonne qualite")

        except Exception as e:
            self._log_security_event("DATA_VERIFICATION_ERROR",
                f"Erreur verification donnees: {str(e)}", "WARNING")
            print(f"  ATTENTION: Impossible de verifier les donnees ({str(e)})")

        # 2. Détection d'empoisonnement par clustering
        print("\n[2/2] Detection d'empoisonnement par clustering DBSCAN...")
        suspicious_files = []
        try:
            detector = PoisoningDetector()
            poisoning_report = detector.detect_poisoning(
                dataset_path=train_data_dir,
                class_name=None,
                visualize=True
            )

            outlier_pct = poisoning_report.suspicious_percentage
            print(f"  Echantillons suspects: {outlier_pct:.1f}%")
            print(f"  Clusters detectes: {poisoning_report.clustering_metrics['n_clusters']}")

            # Récupérer la liste des fichiers suspects
            suspicious_files = poisoning_report.suspicious_files

            # ============================================================
            # ZONE 1: QUARANTAINE AUTOMATIQUE DES DONNÉES SUSPECTES
            # ============================================================
            if len(suspicious_files) > 0:
                print(f"\n  Mise en quarantaine de {len(suspicious_files)} echantillons suspects...")

                # Créer le répertoire de quarantaine
                quarantine_dir = self.project_root / "data" / "quarantine" / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                quarantine_dir.mkdir(parents=True, exist_ok=True)

                # Copier (pas déplacer) les fichiers suspects en quarantaine
                import shutil
                quarantined_count = 0
                for suspicious_file in suspicious_files:
                    try:
                        src = Path(suspicious_file)
                        if src.exists():
                            # Déterminer la classe (safe/dangerous) depuis le chemin
                            class_name = src.parent.name
                            class_quarantine_dir = quarantine_dir / class_name
                            class_quarantine_dir.mkdir(exist_ok=True)

                            # Copier le fichier
                            dst = class_quarantine_dir / src.name
                            shutil.copy2(str(src), str(dst))
                            quarantined_count += 1
                    except Exception as copy_error:
                        print(f"    Erreur copie {suspicious_file}: {copy_error}")

                print(f"  {quarantined_count} fichiers copies en quarantaine: {quarantine_dir}")

                # Sauvegarder le rapport de quarantaine
                quarantine_report_path = quarantine_dir / "quarantine_report.json"
                detector.save_report(poisoning_report, str(quarantine_report_path))

                self._log_security_event("QUARANTINE_APPLIED",
                    f"{len(suspicious_files)} echantillons mis en quarantaine", "INFO")

            # Seuil de suspicion pour alerte
            if outlier_pct > 15:
                self._log_security_event("POISONING_DETECTED",
                    f"ALERTE: {outlier_pct:.1f}% de donnees suspectes detectees et mises en quarantaine!", "WARNING")
                print(f"  ALERTE: Taux d'empoisonnement suspect eleve!")
                print(f"  ACTION: {len(suspicious_files)} echantillons exclus de l'entrainement")
            else:
                self._log_security_event("POISONING_CHECK_OK",
                    f"Pas d'empoisonnement majeur detecte ({outlier_pct:.1f}% outliers)", "INFO")
                print(f"  VALIDATION: Pas d'empoisonnement majeur detecte")

        except Exception as e:
            self._log_security_event("POISONING_DETECTION_ERROR",
                f"Erreur detection empoisonnement: {str(e)}", "WARNING")
            print(f"  ATTENTION: Impossible de detecter empoisonnement ({str(e)})")

        print("="*80 + "\n")

        # ============================================================
        # CHARGEMENT DES DATASETS AVEC FILTRAGE DES DONNÉES SUSPECTES
        # ============================================================

        # Transformations d'augmentation pour robustesse
        train_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(0.5),  # Augmentation pour robustesse
            transforms.RandomRotation(10),          # Rotation légère
            transforms.ColorJitter(0.1, 0.1, 0.1), # Variation couleurs
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        val_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        # Datasets sécurisés avec EXCLUSION des fichiers suspects
        print("Chargement des datasets avec filtrage des donnees suspectes...")
        train_dataset = DangerousObjectDataset(
            root_dir=self.project_root / "data" / "prepared" / "train",
            transform=train_transform,
            excluded_files=suspicious_files  # ZONE 1: Exclure les fichiers suspects
        )

        val_dataset = DangerousObjectDataset(
            root_dir=self.project_root / "data" / "prepared" / "val",
            transform=val_transform
        )

        if len(suspicious_files) > 0:
            print(f"\nSECURITE: Entrainement avec {len(train_dataset)} echantillons VALIDES")
            print(f"          ({len(suspicious_files)} echantillons suspects EXCLUS)")

        # DataLoaders avec sécurité renforcée
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=self.config['batch_size'],
            shuffle=True,
            num_workers=0,  # Pas de workers pour sécurité
            drop_last=True  # Batch consistency pour DP
        )

        self.val_loader = DataLoader(
            val_dataset,
            batch_size=self.config['batch_size'],
            shuffle=False,
            num_workers=0
        )

        self._log_security_event("DATA_LOAD_COMPLETE",
            f"Donnees chargees - Train: {len(train_dataset)}, Val: {len(val_dataset)}", "INFO")
    
    def _create_secured_model(self):
        """Création du modèle sécurisé avec architecture robuste"""
        self._log_security_event("MODEL_CREATE_START", "Creation modele securise", "INFO")

        # MobileNetV2 avec pré-entraînement pour transfert learning sécurisé
        # Architecture légère (3.5M params) identique au baseline pour comparaison équitable
        self.model = models.mobilenet_v2(pretrained=True)

        # Freeze early layers pour transfer learning
        for param in self.model.features[:-3].parameters():
            param.requires_grad = False

        # Classifier personnalisé pour classification binaire sécurisée
        # Utilise le dropout optimisé depuis la config
        dropout_rate = self.config.get('dropout', 0.45)
        in_features = self.model.classifier[1].in_features
        self.model.classifier = nn.Sequential(
            nn.Dropout(dropout_rate),
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(256, 2)
        )

        self.model.to(self.device)
        self.model.train()
        
        # Optimiseur avec configuration sécurisée
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.config['learning_rate'],
            weight_decay=1e-4  # Régularisation pour robustesse
        )
        
        # Scheduler pour convergence stable
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', patience=3, factor=0.5
        )
        
        # Critère de perte
        self.criterion = nn.CrossEntropyLoss()
        
        self._log_security_event("MODEL_CREATE_COMPLETE", "Modele securise cree", "INFO")
    
    def _generate_adversarial_examples(self, data, labels, epsilon=0.1):
        """
        Génération d'exemples adversariaux pour Adversarial Training
        Utilise FGSM et PGD basé sur les vulnérabilités détectées
        """
        adversarial_examples = []
        
        # FGSM Attack pour entraînement
        data.requires_grad = True
        output = self.model(data)
        loss = self.criterion(output, labels)
        
        self.model.zero_grad()
        loss.backward()
        
        # Génération FGSM
        data_grad = data.grad.data
        sign_data_grad = data_grad.sign()
        fgsm_data = data + epsilon * sign_data_grad
        fgsm_data = torch.clamp(fgsm_data, 0, 1)
        
        adversarial_examples.append(fgsm_data.detach())
        
        # PGD Attack pour entraînement (plus robuste)
        pgd_data = data.clone().detach()
        pgd_data = pgd_data + torch.empty_like(pgd_data).uniform_(-epsilon, epsilon)
        pgd_data = torch.clamp(pgd_data, 0, 1).detach()
        pgd_data.requires_grad = True
        
        # 3 itérations PGD pour l'entraînement (compromis performance/sécurité)
        for _ in range(3):
            pgd_output = self.model(pgd_data)
            pgd_loss = self.criterion(pgd_output, labels)
            
            pgd_loss.backward()
            pgd_data = pgd_data + 0.02 * pgd_data.grad.sign()
            pgd_data = torch.clamp(pgd_data, data - epsilon, data + epsilon)
            pgd_data = torch.clamp(pgd_data, 0, 1).detach()
            pgd_data.requires_grad = True
        
        adversarial_examples.append(pgd_data.detach())

        return adversarial_examples

    def _add_differential_privacy_noise(self):
        """
        Ajoute du bruit gaussien calibré aux gradients pour Differential Privacy
        Implémentation de DP-SGD (Differentially Private Stochastic Gradient Descent)

        Conforme Zone 2: Differential Privacy pour protection des données d'entraînement
        """
        if not self.config.get('differential_privacy', False):
            return

        epsilon = self.config.get('epsilon_privacy', 1.0)
        delta = self.config.get('delta_privacy', 1e-5)

        # Calcul du sigma (écart-type du bruit) basé sur epsilon et delta
        # Formule: sigma = sqrt(2 * ln(1.25/delta)) / epsilon
        sensitivity = 1.0  # Sensibilité après clipping
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon

        # Ajout de bruit gaussien aux gradients
        for param in self.model.parameters():
            if param.grad is not None:
                noise = torch.normal(
                    mean=0.0,
                    std=sigma,
                    size=param.grad.shape,
                    device=param.grad.device
                )
                param.grad += noise

    def _generate_model_signature(self, model_path):
        """
        Génère une signature numérique RSA-4096 pour le modèle
        Conforme Zone 2: Versioning Signé pour traçabilité et non-répudiation

        Args:
            model_path: Chemin vers le fichier .pth du modèle

        Returns:
            Tuple (signature_bytes, public_key_pem)
        """
        # Générer une paire de clés RSA-4096
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

        public_key = private_key.public_key()

        # Calculer le hash SHA-256 du modèle
        with open(model_path, 'rb') as f:
            model_data = f.read()
            model_hash = hashlib.sha256(model_data).digest()

        # Signer le hash avec la clé privée
        signature = private_key.sign(
            model_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Exporter la clé publique en format PEM
        public_key_pem = public_key.public_key_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Sauvegarder la clé privée (sécurisée)
        private_key_path = str(model_path).replace('.pth', '_private_key.pem')
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_key_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(b'SecureAI_2024')
            ))

        return signature, public_key_pem

    def _verify_model_signature(self, model_path, signature, public_key_pem):
        """
        Vérifie la signature numérique d'un modèle

        Args:
            model_path: Chemin vers le fichier .pth
            signature: Signature bytes
            public_key_pem: Clé publique en format PEM

        Returns:
            True si signature valide, False sinon
        """
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
            print(f"Erreur vérification signature: {str(e)}")
            return False

    def _train_epoch_adversarial(self, epoch):
        """
        Entraînement d'une époque avec Adversarial Training
        Conforme Zone 2: Entraînement Sécurisé
        """
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        # Progress bar pour monitoring
        pbar = tqdm(self.train_loader, desc=f'Epoch {epoch+1}/{self.config["epochs"]}')
        
        for batch_idx, (data, target) in enumerate(pbar):
            data, target = data.to(self.device), target.to(self.device)
            
            self.optimizer.zero_grad()
            
            # Récupérer les ratios optimisés depuis config
            clean_ratio = self.config.get('clean_ratio', 0.7)
            fgsm_ratio = self.config.get('fgsm_ratio', 0.3)
            pgd_ratio = self.config.get('pgd_ratio', 0.0)
            epsilon = self.config.get('adversarial_epsilon', 0.08)

            # 1. Loss sur données propres (70% par défaut)
            clean_output = self.model(data)
            clean_loss = self.criterion(clean_output, target)

            # 2. Adversarial Training
            if self.config['adversarial_training']:
                adv_examples = self._generate_adversarial_examples(data, target, epsilon=epsilon)

                # Loss sur exemples FGSM (30% par défaut)
                fgsm_output = self.model(adv_examples[0])
                fgsm_loss = self.criterion(fgsm_output, target)

                # Loss combinée selon les ratios configurés
                if pgd_ratio > 0:
                    # Avec PGD si configuré (non recommandé pour performance)
                    pgd_output = self.model(adv_examples[1])
                    pgd_loss = self.criterion(pgd_output, target)
                    total_batch_loss = clean_ratio * clean_loss + fgsm_ratio * fgsm_loss + pgd_ratio * pgd_loss
                else:
                    # Sans PGD (configuration optimisée recommandée)
                    total_batch_loss = clean_ratio * clean_loss + fgsm_ratio * fgsm_loss
            else:
                total_batch_loss = clean_loss
            
            # Backpropagation
            total_batch_loss.backward()

            # Gradient clipping pour stabilité avec DP
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

            # ZONE 2: Ajout de bruit DP si activé
            self._add_differential_privacy_noise()

            self.optimizer.step()
            
            # Métriques
            total_loss += total_batch_loss.item()
            pred = clean_output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()
            total += target.size(0)
            
            # Mise à jour progress bar
            pbar.set_postfix({
                'Loss': f'{total_batch_loss.item():.4f}',
                'Acc': f'{100.*correct/total:.2f}%'
            })
        
        epoch_loss = total_loss / len(self.train_loader)
        epoch_acc = 100. * correct / total
        
        return epoch_loss, epoch_acc
    
    def _validate_epoch(self, epoch):
        """Validation sécurisée d'une époque"""
        self.model.eval()
        val_loss = 0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, target in self.val_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                val_loss += self.criterion(output, target).item()
                
                pred = output.argmax(dim=1, keepdim=True)
                correct += pred.eq(target.view_as(pred)).sum().item()
                total += target.size(0)
        
        val_loss /= len(self.val_loader)
        val_acc = 100. * correct / total
        
        return val_loss, val_acc
    
    def _save_secured_model(self, epoch, val_loss, val_acc, is_best=False):
        """Sauvegarde sécurisée avec versioning signé (Zone 2) + Chiffrement (Zone 1)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Checkpoint complet sécurisé
        checkpoint = {
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'epoch': epoch,
            'val_loss': val_loss,
            'val_acc': val_acc,
            'config': self.config,
            'security_version': "v2.0_secured",
            'adversarial_training': self.config['adversarial_training'],
            'differential_privacy': self.config.get('differential_privacy', False),
            'timestamp': timestamp
        }

        # Sauvegarde modèle standard (non chiffré pour compatibilité)
        model_path = self.models_dir / f"secured_model_epoch_{epoch}_{timestamp}.pth"
        torch.save(checkpoint, model_path)

        # Sauvegarde du meilleur modèle
        if is_best:
            best_model_path = self.models_dir / "best_secured_model.pth"
            torch.save(checkpoint, best_model_path)

            # ============================================================
            # ZONE 1: STOCKAGE CRYPTÉ DU MEILLEUR MODÈLE
            # ============================================================
            try:
                # Créer répertoire pour modèles chiffrés
                encrypted_dir = self.models_dir / "encrypted"
                encrypted_dir.mkdir(exist_ok=True)

                # Initialiser le système de chiffrement
                storage = EncryptedStorage(password="SecureAI_2024_Production")

                # Chiffrer le meilleur modèle
                encrypted_path = encrypted_dir / f"best_secured_model_encrypted.enc"
                metadata = storage.encrypt_pytorch_model(
                    str(best_model_path),
                    str(encrypted_path)
                )

                self._log_security_event("MODEL_ENCRYPTED",
                    f"Meilleur modele chiffre AES-256-GCM: {encrypted_path.name}", "INFO")
                print(f"  Modele chiffre sauvegarde: {encrypted_path}")

            except Exception as e:
                self._log_security_event("ENCRYPTION_ERROR",
                    f"Erreur chiffrement modele: {str(e)}", "WARNING")
                print(f"  ATTENTION: Impossible de chiffrer le modele ({str(e)})")

            # ============================================================
            # ZONE 2: SIGNATURE NUMÉRIQUE RSA-4096 DU MEILLEUR MODÈLE
            # ============================================================
            if self.config.get('secure_versioning', True):
                try:
                    print(f"\n  Generation de la signature numerique RSA-4096...")
                    signature, public_key_pem = self._generate_model_signature(str(best_model_path))

                    # Sauvegarder la signature
                    signature_path = str(best_model_path).replace('.pth', '_signature.bin')
                    with open(signature_path, 'wb') as f:
                        f.write(signature)

                    # Sauvegarder la clé publique
                    public_key_path = str(best_model_path).replace('.pth', '_public_key.pem')
                    with open(public_key_path, 'wb') as f:
                        f.write(public_key_pem)

                    # Vérifier immédiatement la signature
                    is_valid = self._verify_model_signature(str(best_model_path), signature, public_key_pem)

                    if is_valid:
                        self._log_security_event("MODEL_SIGNED",
                            f"Modele signe avec RSA-4096 et verifie avec succes", "INFO")
                        print(f"  Signature RSA-4096 generee et verifiee: {Path(signature_path).name}")
                        print(f"  Cle publique: {Path(public_key_path).name}")
                    else:
                        self._log_security_event("SIGNATURE_VERIFICATION_FAILED",
                            "ALERTE: Verification signature echouee!", "ERROR")
                        print(f"  ERREUR: Verification de la signature a echoue!")

                except Exception as e:
                    self._log_security_event("SIGNATURE_ERROR",
                        f"Erreur generation signature: {str(e)}", "WARNING")
                    print(f"  ATTENTION: Impossible de signer le modele ({str(e)})")

            self._log_security_event("BEST_MODEL_SAVED",
                f"Meilleur modele securise sauvegarde: {val_acc:.2f}%", "INFO")

        self._log_security_event("MODEL_SAVED",
            f"Modele securise sauvegarde: {model_path.name}", "INFO")

        return model_path
    
    def train_secured_model(self):
        """
        Entraînement principal du modèle sécurisé
        Conforme Zone 2: Entraînement Sécurisé de l'architecture
        """
        self._log_security_event("TRAINING_START", 
            f"Debut entrainement securise - {self.config['epochs']} epochs", "INFO")
        
        print("\n" + "="*80)
        print("ZONE 2: ENTRAINEMENT SECURISE - ADVERSARIAL TRAINING")
        print("Conforme a l'Architecture de Securisation IA")
        print("="*80)
        
        best_val_acc = 0.0
        training_history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }

        # Initialiser Early Stopping
        early_stopping = EarlyStopping(
            patience=self.config.get('early_stopping_patience', 8),
            min_delta=0.001,
            verbose=True
        )

        for epoch in range(self.config['epochs']):
            # Entraînement avec Adversarial Training
            train_loss, train_acc = self._train_epoch_adversarial(epoch)
            
            # Validation
            val_loss, val_acc = self._validate_epoch(epoch)
            
            # Scheduler step
            self.scheduler.step(val_loss)
            
            # Sauvegarde historique
            training_history['train_loss'].append(train_loss)
            training_history['train_acc'].append(train_acc)
            training_history['val_loss'].append(val_loss)
            training_history['val_acc'].append(val_acc)
            
            # Logging détaillé
            self._log_security_event("EPOCH_COMPLETE", 
                f"Epoch {epoch+1}: Train Acc={train_acc:.2f}%, Val Acc={val_acc:.2f}%", "INFO")
            
            print(f"\nEpoch {epoch+1}/{self.config['epochs']}:")
            print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
            print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
            
            # Sauvegarde du meilleur modèle
            is_best = val_acc > best_val_acc
            if is_best:
                best_val_acc = val_acc
                
            # Sauvegarde périodique sécurisée
            if (epoch + 1) % 5 == 0 or is_best:
                self._save_secured_model(epoch, val_loss, val_acc, is_best)

            # Early Stopping basé sur validation loss
            if early_stopping(val_loss, epoch):
                self._log_security_event("EARLY_STOPPING",
                    f"Arret precoce - pas d'amelioration pendant {early_stopping.patience} epochs", "INFO")
                print(f"\nEARLY STOPPING: Entrainement arrete a l'epoch {epoch+1}")
                print(f"Meilleure validation loss: {early_stopping.best_loss:.4f} (epoch {early_stopping.best_epoch+1})")
                break
        
        # Sauvegarde finale
        final_model_path = self._save_secured_model(epoch, val_loss, val_acc, False)
        
        # Génération rapport d'entraînement
        self._generate_training_report(training_history, best_val_acc)
        
        self._log_security_event("TRAINING_COMPLETE", 
            f"Entrainement termine - Meilleure accuracy: {best_val_acc:.2f}%", "INFO")
        
        return final_model_path, best_val_acc
    
    def _generate_training_report(self, history, best_acc):
        """Génération rapport conforme Zone 5: Gouvernance"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rapport JSON détaillé
        report = {
            "training_type": "secured_adversarial",
            "architecture": "Zone2_Compliant",
            "timestamp": timestamp,
            "config": self.config,
            "best_validation_accuracy": best_acc,
            "final_metrics": {
                "final_train_loss": history['train_loss'][-1],
                "final_train_acc": history['train_acc'][-1],
                "final_val_loss": history['val_loss'][-1],
                "final_val_acc": history['val_acc'][-1]
            },
            "security_features": {
                "adversarial_training": self.config['adversarial_training'],
                "differential_privacy": self.config.get('differential_privacy', False),
                "gradient_clipping": True,
                "secure_versioning": True
            },
            "training_history": history
        }
        
        # Sauvegarde rapport
        report_path = self.results_dir / f"training_report_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Graphique d'entraînement
        plt.figure(figsize=(12, 4))
        
        plt.subplot(1, 2, 1)
        plt.plot(history['train_loss'], label='Train Loss')
        plt.plot(history['val_loss'], label='Validation Loss')
        plt.title('Training Loss - Secured Model')
        plt.legend()
        
        plt.subplot(1, 2, 2)
        plt.plot(history['train_acc'], label='Train Accuracy')
        plt.plot(history['val_acc'], label='Validation Accuracy')
        plt.title('Training Accuracy - Secured Model')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(self.results_dir / f"training_curves_{timestamp}.png")
        plt.close()
        
        self._log_security_event("REPORT_GENERATED", 
            f"Rapport entrainement genere: {report_path.name}", "INFO")

def train_secured():
    """
    Fonction principale d'entraînement sécurisé
    Point d'entrée conforme à l'architecture de sécurisation Zone 2
    """
    print("ZONE 2: DEBUT ENTRAINEMENT SECURISE")
    print("Conforme a l'Architecture de Securisation IA")
    print("="*60)
    
    # Configuration sécurisée optimisée basée sur expérimentations notebook
    # Source: train_secured_colab.ipynb - Configuration FGSM OPTIMIZED
    config = {
        'epochs': 30,                       # Plus d'epochs pour convergence avec adversarial training
        'batch_size': 32,                   # Batch size identique au baseline pour comparaison
        'learning_rate': 0.0001,            # OPTIMISÉ: Réduit de 0.001 -> 0.0001 (meilleure convergence)
        'adversarial_training': True,       # Activé suite vulnérabilité détectée (47.55% degradation)
        'adversarial_epsilon': 0.08,        # OPTIMISÉ: Augmenté de 0.03 -> 0.08 (robustesse améliorée)
        'clean_ratio': 0.7,                 # OPTIMISÉ: 70% données propres (vs 50% avant)
        'fgsm_ratio': 0.3,                  # OPTIMISÉ: 30% FGSM (vs 25% avant)
        'pgd_ratio': 0.0,                   # OPTIMISÉ: PAS DE PGD (trop coûteux, peu de gain)
        'dropout': 0.45,                    # OPTIMISÉ: Augmenté de 0.3 -> 0.45 (meilleure généralisation)
        'differential_privacy': False,      # Désactivé pour performance (disponible si nécessaire)
        'epsilon_privacy': 1.0,             # Paramètre DP si activé
        'delta_privacy': 1e-5,              # Delta pour DP
        'gradient_clipping': True,          # Stabilité d'entraînement et pré-requis DP
        'secure_versioning': True,          # Versioning signé conformité Zone 2
        'early_stopping_patience': 8        # OPTIMISÉ: Arrêt précoce après 8 epochs sans amélioration
    }
    
    print("Configuration de securite:")
    for key, value in config.items():
        print(f"  - {key}: {value}")
    
    try:
        # Initialisation entraîneur sécurisé
        trainer = SecuredTrainer(config)
        
        # Entraînement sécurisé
        model_path, best_acc = trainer.train_secured_model()
        
        print(f"\nEntrainement securise termine avec succes!")
        print(f"Meilleure accuracy: {best_acc:.2f}%")
        print(f"Modele sauvegarde: {model_path}")
        
        # Recommandations de sécurité
        print("\nRecommandations de securite:")
        print("  - Tester robustesse avec attack_secured.py")
        print("  - Comparer performance avec baseline")
        print("  - Valider conformite Zone 3 (tests)")
        
    except Exception as e:
        print(f"Erreur lors de l'entrainement securise: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    train_secured()
