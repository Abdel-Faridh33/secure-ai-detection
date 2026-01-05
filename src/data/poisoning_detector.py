"""
Poisoning Detector - Détection d'Empoisonnement avec DBSCAN
============================================================

Ce module implémente un détecteur d'empoisonnement de données utilisant
l'algorithme DBSCAN (Density-Based Spatial Clustering of Applications with Noise).

Fonctionnalités:
- Détection d'empoisonnement par label flipping
- Détection de backdoors dans les données d'entraînement
- Clustering pour identifier les outliers suspects
- Analyse des features extraites par deep learning
- Génération de rapports détaillés

Conformité:
- Zone 1: Sécurité des Données
- Algorithme: DBSCAN (Scikit-learn)
- Extracteur de features: MobileNetV2 pré-entraîné (PyTorch)

Principe:
Les échantillons empoisonnés ont souvent des features différentes des
échantillons légitimes. DBSCAN détecte ces outliers comme du "bruit".
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class PoisoningReport:
    """Rapport de détection d'empoisonnement"""
    dataset_path: str
    total_samples: int
    suspicious_samples: int
    suspicious_percentage: float
    suspicious_files: List[str]
    clustering_metrics: Dict
    recommendations: List[str]
    timestamp: str


class PoisoningDetector:
    """
    Détecteur d'empoisonnement utilisant DBSCAN

    Ce détecteur utilise :
    1. MobileNetV2 pré-entraîné pour extraire les features (architecture alignée avec le projet)
    2. DBSCAN pour identifier les clusters et outliers
    3. Analyse statistique pour détecter les anomalies

    Exemple d'utilisation:
        detector = PoisoningDetector()
        report = detector.detect_poisoning('data/train')

        if report.suspicious_samples > 0:
            print(f"Attention: {report.suspicious_samples} échantillons suspects")
            for file in report.suspicious_files:
                print(f"  - {file}")
    """

    def __init__(
        self,
        eps: float = 0.5,
        min_samples: int = 5,
        feature_dim: int = 128,
        contamination_threshold: float = 0.05,
        use_pca: bool = True,
        pca_components: int = 50
    ):
        """
        Initialise le détecteur d'empoisonnement

        Args:
            eps: Epsilon pour DBSCAN (distance max entre voisins)
            min_samples: Nombre minimum d'échantillons pour un cluster
            feature_dim: Dimension des features extraites
            contamination_threshold: Seuil de contamination acceptable (%)
            use_pca: Utiliser PCA pour réduire la dimensionnalité
            pca_components: Nombre de composantes PCA
        """
        self.eps = eps
        self.min_samples = min_samples
        self.feature_dim = feature_dim
        self.contamination_threshold = contamination_threshold
        self.use_pca = use_pca
        self.pca_components = pca_components

        # Initialiser le feature extractor (MobileNetV2 - aligné avec le projet)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.feature_extractor = self._build_feature_extractor()
        self.feature_extractor.eval()

        # Transformations pour les images
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        print(f"✓ PoisoningDetector initialisé sur {self.device} (MobileNetV2)")

    def _build_feature_extractor(self) -> nn.Module:
        """
        Construit le feature extractor basé sur MobileNetV2

        Note: Utilise MobileNetV2 au lieu de ResNet50 pour cohérence avec
        l'architecture du projet (baseline et secured utilisent MobileNetV2)

        Returns:
            nn.Module: Modèle d'extraction de features
        """
        # Charger MobileNetV2 pré-entraîné (architecture légère et performante)
        mobilenet = models.mobilenet_v2(pretrained=True)

        # Retirer le classifier final et garder uniquement le feature extractor
        # MobileNetV2.features contient toutes les couches conv jusqu'au pooling
        feature_extractor = mobilenet.features

        return feature_extractor.to(self.device)

    def detect_poisoning(
        self,
        dataset_path: str,
        class_name: Optional[str] = None,
        visualize: bool = True
    ) -> PoisoningReport:
        """
        Détecte l'empoisonnement dans un dataset

        Args:
            dataset_path: Chemin vers le dataset
            class_name: Nom de classe spécifique à analyser (None = toutes)
            visualize: Générer des visualisations

        Returns:
            PoisoningReport: Rapport de détection
        """
        print(f"\n=== Détection d'Empoisonnement: {dataset_path} ===")

        # 1. Extraire les features de toutes les images
        features, file_paths, labels = self._extract_features(dataset_path, class_name)
        print(f"✓ Features extraites: {features.shape}")

        # 2. Normaliser les features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        # 3. Réduction de dimensionnalité (optionnel)
        if self.use_pca and features.shape[1] > self.pca_components:
            pca = PCA(n_components=self.pca_components)
            features_scaled = pca.fit_transform(features_scaled)
            print(f"✓ PCA appliquée: {features_scaled.shape}")

        # 4. Clustering DBSCAN
        dbscan = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        cluster_labels = dbscan.fit_predict(features_scaled)
        print(f"✓ DBSCAN terminé: {len(set(cluster_labels))} clusters")

        # 5. Identifier les outliers (label = -1)
        outlier_mask = cluster_labels == -1
        suspicious_indices = np.where(outlier_mask)[0]
        suspicious_files = [file_paths[i] for i in suspicious_indices]

        print(f"✓ Outliers détectés: {len(suspicious_files)}")

        # 6. Calculer métriques
        clustering_metrics = self._calculate_clustering_metrics(
            cluster_labels,
            features_scaled
        )

        # 7. Générer recommandations
        recommendations = self._generate_recommendations(
            len(suspicious_files),
            len(file_paths),
            clustering_metrics
        )

        # 8. Visualisations (optionnel)
        if visualize and len(suspicious_files) > 0:
            self._visualize_clustering(
                features_scaled,
                cluster_labels,
                dataset_path
            )

        # Créer le rapport
        report = PoisoningReport(
            dataset_path=dataset_path,
            total_samples=len(file_paths),
            suspicious_samples=len(suspicious_files),
            suspicious_percentage=(len(suspicious_files) / len(file_paths)) * 100,
            suspicious_files=suspicious_files,
            clustering_metrics=clustering_metrics,
            recommendations=recommendations,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

        # Résumé
        print(f"\n{'⚠ ÉCHANTILLONS SUSPECTS DÉTECTÉS' if len(suspicious_files) > 0 else '✓ AUCUN ÉCHANTILLON SUSPECT'}")
        print(f"Total: {report.total_samples} | Suspects: {report.suspicious_samples} ({report.suspicious_percentage:.2f}%)")

        return report

    def _extract_features(
        self,
        dataset_path: str,
        class_name: Optional[str]
    ) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Extrait les features de toutes les images

        Args:
            dataset_path: Chemin vers le dataset
            class_name: Classe spécifique (None = toutes)

        Returns:
            Tuple: (features, file_paths, labels)
        """
        dataset_path = Path(dataset_path)
        features_list = []
        file_paths = []
        labels = []

        # Parcourir les classes
        class_dirs = [dataset_path / class_name] if class_name else list(dataset_path.iterdir())

        for class_dir in class_dirs:
            if not class_dir.is_dir():
                continue

            current_label = class_dir.name

            # Parcourir les images
            for img_path in class_dir.glob('*'):
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                    continue

                try:
                    # Charger et transformer l'image
                    img = Image.open(img_path).convert('RGB')
                    img_tensor = self.transform(img).unsqueeze(0).to(self.device)

                    # Extraire features
                    with torch.no_grad():
                        features = self.feature_extractor(img_tensor)
                        features = features.squeeze().cpu().numpy()

                    features_list.append(features)
                    file_paths.append(str(img_path))
                    labels.append(current_label)

                except Exception as e:
                    print(f"⚠ Erreur avec {img_path}: {str(e)}")
                    continue

        features = np.array(features_list)
        return features, file_paths, labels

    def _calculate_clustering_metrics(
        self,
        cluster_labels: np.ndarray,
        features: np.ndarray
    ) -> Dict:
        """
        Calcule les métriques de clustering

        Args:
            cluster_labels: Labels des clusters
            features: Features normalisées

        Returns:
            Dict: Métriques
        """
        n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
        n_outliers = np.sum(cluster_labels == -1)
        n_samples = len(cluster_labels)

        # Distribution des clusters
        unique, counts = np.unique(cluster_labels, return_counts=True)
        cluster_sizes = {int(label): int(count) for label, count in zip(unique, counts)}

        # Calculer densité moyenne des clusters
        cluster_densities = {}
        for cluster_id in set(cluster_labels):
            if cluster_id == -1:
                continue

            cluster_mask = cluster_labels == cluster_id
            cluster_features = features[cluster_mask]

            if len(cluster_features) > 1:
                # Densité = inverse de distance moyenne intra-cluster
                from scipy.spatial.distance import pdist
                distances = pdist(cluster_features, metric='euclidean')
                avg_distance = np.mean(distances) if len(distances) > 0 else 0
                density = 1.0 / (avg_distance + 1e-6)
                cluster_densities[int(cluster_id)] = float(density)

        return {
            'n_clusters': n_clusters,
            'n_outliers': n_outliers,
            'n_samples': n_samples,
            'outlier_percentage': (n_outliers / n_samples) * 100,
            'cluster_sizes': cluster_sizes,
            'cluster_densities': cluster_densities
        }

    def _generate_recommendations(
        self,
        n_suspicious: int,
        n_total: int,
        metrics: Dict
    ) -> List[str]:
        """
        Génère des recommandations basées sur les résultats

        Args:
            n_suspicious: Nombre d'échantillons suspects
            n_total: Nombre total d'échantillons
            metrics: Métriques de clustering

        Returns:
            List[str]: Liste de recommandations
        """
        recommendations = []
        contamination_rate = (n_suspicious / n_total) * 100

        if contamination_rate == 0:
            recommendations.append("✓ Aucun échantillon suspect détecté - Dataset sain")

        elif contamination_rate < self.contamination_threshold * 100:
            recommendations.append(
                f"⚠ {contamination_rate:.2f}% d'échantillons suspects (sous le seuil de {self.contamination_threshold*100}%)"
            )
            recommendations.append("Recommandation: Inspecter manuellement les échantillons suspects")

        else:
            recommendations.append(
                f"🚨 ALERTE: {contamination_rate:.2f}% d'échantillons suspects (au-dessus du seuil)"
            )
            recommendations.append("Recommandation: Nettoyer le dataset avant entraînement")
            recommendations.append("Action: Retirer ou réétiqueter les échantillons suspects")

        # Recommandations sur les clusters
        if metrics['n_clusters'] < 2:
            recommendations.append("⚠ Peu de clusters détectés - Considérer ajuster eps ou min_samples")

        if metrics['n_clusters'] > n_total * 0.5:
            recommendations.append("⚠ Trop de clusters - Dataset potentiellement trop diversifié")

        return recommendations

    def _visualize_clustering(
        self,
        features: np.ndarray,
        cluster_labels: np.ndarray,
        dataset_path: str
    ):
        """
        Visualise les résultats du clustering

        Args:
            features: Features normalisées
            cluster_labels: Labels des clusters
            dataset_path: Chemin du dataset
        """
        # Réduction à 2D pour visualisation
        pca_2d = PCA(n_components=2)
        features_2d = pca_2d.fit_transform(features)

        # Créer le plot
        plt.figure(figsize=(12, 8))

        # Colorer par cluster
        unique_labels = set(cluster_labels)
        colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))

        for k, col in zip(unique_labels, colors):
            if k == -1:
                # Outliers en noir avec marqueur différent
                col = [0, 0, 0, 1]
                marker = 'x'
                label = 'Outliers (suspects)'
                size = 100
            else:
                marker = 'o'
                label = f'Cluster {k}'
                size = 50

            class_mask = cluster_labels == k
            plt.scatter(
                features_2d[class_mask, 0],
                features_2d[class_mask, 1],
                c=[col],
                marker=marker,
                s=size,
                label=label,
                alpha=0.7,
                edgecolors='k',
                linewidths=0.5
            )

        plt.title('DBSCAN Clustering - Détection d\'Empoisonnement', fontsize=16, fontweight='bold')
        plt.xlabel('PCA Component 1', fontsize=12)
        plt.ylabel('PCA Component 2', fontsize=12)
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)

        # Sauvegarder
        output_dir = Path('results/poisoning_detection')
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f'clustering_{timestamp}.png'

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Visualisation sauvegardée: {output_path}")

    def save_report(self, report: PoisoningReport, output_path: str):
        """
        Sauvegarde le rapport de détection

        Args:
            report: Rapport de détection
            output_path: Chemin de sortie
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convertir en dictionnaire
        report_dict = asdict(report)

        # Sauvegarder
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"✓ Rapport sauvegardé: {output_path}")

    def quarantine_suspicious_samples(
        self,
        report: PoisoningReport,
        quarantine_dir: str
    ):
        """
        Met en quarantaine les échantillons suspects

        Args:
            report: Rapport de détection
            quarantine_dir: Répertoire de quarantaine
        """
        import shutil

        quarantine_path = Path(quarantine_dir)
        quarantine_path.mkdir(parents=True, exist_ok=True)

        print(f"\n=== Mise en Quarantaine ===")
        print(f"Déplacement de {len(report.suspicious_files)} fichiers...")

        for file_path in report.suspicious_files:
            try:
                src = Path(file_path)
                dst = quarantine_path / src.name

                # Éviter écrasement
                counter = 1
                while dst.exists():
                    dst = quarantine_path / f"{src.stem}_{counter}{src.suffix}"
                    counter += 1

                shutil.move(str(src), str(dst))
                print(f"  ✓ {src.name} → {dst.name}")

            except Exception as e:
                print(f"  ✗ Erreur avec {file_path}: {str(e)}")

        print(f"✓ Quarantaine terminée: {quarantine_dir}")


if __name__ == '__main__':
    """
    Script de test du PoisoningDetector
    """
    # Créer le détecteur
    detector = PoisoningDetector(
        eps=0.5,
        min_samples=5,
        contamination_threshold=0.05,
        use_pca=True
    )

    # Détecter l'empoisonnement
    train_dataset = 'data/processed/train'

    if os.path.exists(train_dataset):
        report = detector.detect_poisoning(
            train_dataset,
            visualize=True
        )

        # Sauvegarder le rapport
        detector.save_report(
            report,
            'results/poisoning_detection/train_report.json'
        )

        # Mettre en quarantaine si nécessaire
        if report.suspicious_samples > 0:
            user_input = input(f"\nMettre en quarantaine les {report.suspicious_samples} échantillons suspects? (y/n): ")
            if user_input.lower() == 'y':
                detector.quarantine_suspicious_samples(
                    report,
                    'data/quarantine'
                )
    else:
        print(f"⚠ Dataset non trouvé: {train_dataset}")
