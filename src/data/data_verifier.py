"""
Data Verifier - Service de Vérification des Données avec Tests Statistiques
============================================================================

Ce module implémente un service de vérification des données conforme à la Zone 1
de l'architecture de sécurité : Data Security.

Fonctionnalités:
- Vérification de l'intégrité des datasets
- Tests statistiques pour détecter les anomalies
- Validation de la distribution des données
- Détection de déséquilibres de classes
- Analyse de la qualité des images

Conformité:
- Zone 1: Sécurité des Données
- Tests statistiques : Kolmogorov-Smirnov, Chi-Square, Z-score
- RGPD-friendly : Pas de stockage de données sensibles
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import numpy as np
from scipy import stats
from PIL import Image
import torch
from torch.utils.data import DataLoader, Dataset
from datetime import datetime


@dataclass
class DatasetStatistics:
    """Statistiques d'un dataset"""
    total_samples: int
    class_distribution: Dict[str, int]
    mean_image_size: Tuple[float, float]
    mean_pixel_intensity: float
    std_pixel_intensity: float
    corrupted_images: int
    duplicate_hashes: int
    timestamp: str


@dataclass
class VerificationReport:
    """Rapport de vérification complet"""
    dataset_path: str
    statistics: DatasetStatistics
    statistical_tests: Dict[str, Dict]
    anomalies_detected: List[str]
    quality_score: float
    passed: bool
    timestamp: str


class DataVerifier:
    """
    Service de vérification des données avec tests statistiques

    Ce service permet de :
    1. Vérifier l'intégrité des datasets
    2. Effectuer des tests statistiques pour détecter les anomalies
    3. Générer des rapports de qualité des données
    4. Détecter les images corrompues ou suspectes

    Exemple d'utilisation:
        verifier = DataVerifier()
        report = verifier.verify_dataset('data/train')

        if report.passed:
            print(f"Dataset valide avec score: {report.quality_score}")
        else:
            print(f"Anomalies détectées: {report.anomalies_detected}")
    """

    def __init__(
        self,
        min_samples_per_class: int = 10,
        max_class_imbalance_ratio: float = 5.0,
        min_image_size: Tuple[int, int] = (32, 32),
        max_image_size: Tuple[int, int] = (4096, 4096),
        expected_channels: int = 3,
        zscore_threshold: float = 3.0,
        ks_alpha: float = 0.05
    ):
        """
        Initialise le vérificateur de données

        Args:
            min_samples_per_class: Nombre minimum d'échantillons par classe
            max_class_imbalance_ratio: Ratio max déséquilibre entre classes
            min_image_size: Taille minimale des images (width, height)
            max_image_size: Taille maximale des images (width, height)
            expected_channels: Nombre de canaux attendus (3 pour RGB)
            zscore_threshold: Seuil Z-score pour détecter les outliers
            ks_alpha: Seuil alpha pour test Kolmogorov-Smirnov
        """
        self.min_samples_per_class = min_samples_per_class
        self.max_class_imbalance_ratio = max_class_imbalance_ratio
        self.min_image_size = min_image_size
        self.max_image_size = max_image_size
        self.expected_channels = expected_channels
        self.zscore_threshold = zscore_threshold
        self.ks_alpha = ks_alpha

    def verify_dataset(
        self,
        dataset_path: str,
        reference_stats: Optional[Dict] = None
    ) -> VerificationReport:
        """
        Vérifie un dataset complet et génère un rapport

        Args:
            dataset_path: Chemin vers le dataset
            reference_stats: Statistiques de référence (pour comparaison)

        Returns:
            VerificationReport: Rapport de vérification complet
        """
        print(f"\n=== Vérification du Dataset: {dataset_path} ===")

        # 1. Collecter les statistiques du dataset
        statistics = self._collect_statistics(dataset_path)
        print(f"✓ Statistiques collectées: {statistics.total_samples} échantillons")

        # 2. Effectuer les tests statistiques
        statistical_tests = self._run_statistical_tests(dataset_path, statistics, reference_stats)
        print(f"✓ Tests statistiques effectués: {len(statistical_tests)} tests")

        # 3. Détecter les anomalies
        anomalies = self._detect_anomalies(statistics, statistical_tests)
        print(f"✓ Anomalies détectées: {len(anomalies)}")

        # 4. Calculer le score de qualité
        quality_score = self._calculate_quality_score(statistics, statistical_tests, anomalies)
        print(f"✓ Score de qualité: {quality_score:.2f}/100")

        # 5. Déterminer si le dataset passe la validation
        passed = len(anomalies) == 0 and quality_score >= 70.0

        report = VerificationReport(
            dataset_path=dataset_path,
            statistics=statistics,
            statistical_tests=statistical_tests,
            anomalies_detected=anomalies,
            quality_score=quality_score,
            passed=passed,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

        print(f"\n{'✓ VALIDATION RÉUSSIE' if passed else '✗ VALIDATION ÉCHOUÉE'}")
        return report

    def _collect_statistics(self, dataset_path: str) -> DatasetStatistics:
        """
        Collecte les statistiques du dataset

        Args:
            dataset_path: Chemin vers le dataset

        Returns:
            DatasetStatistics: Statistiques collectées
        """
        dataset_path = Path(dataset_path)

        # Initialisation
        class_distribution = {}
        image_sizes = []
        pixel_intensities = []
        corrupted_images = 0
        image_hashes = set()
        duplicate_hashes = 0

        # Parcourir toutes les classes
        for class_dir in dataset_path.iterdir():
            if not class_dir.is_dir():
                continue

            class_name = class_dir.name
            class_count = 0

            # Parcourir toutes les images de la classe
            for img_path in class_dir.glob('*'):
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                    continue

                try:
                    # Charger l'image
                    img = Image.open(img_path)

                    # Vérifier la taille
                    image_sizes.append(img.size)

                    # Convertir en numpy pour analyse
                    img_array = np.array(img)

                    # Calculer intensité moyenne des pixels
                    if len(img_array.shape) == 3:  # Image RGB
                        pixel_intensities.append(img_array.mean())
                    elif len(img_array.shape) == 2:  # Image grayscale
                        pixel_intensities.append(img_array.mean())

                    # Calculer hash pour détecter duplicates
                    img_hash = hashlib.md5(img_array.tobytes()).hexdigest()
                    if img_hash in image_hashes:
                        duplicate_hashes += 1
                    image_hashes.add(img_hash)

                    class_count += 1

                except Exception as e:
                    corrupted_images += 1
                    print(f"⚠ Image corrompue: {img_path} - {str(e)}")

            class_distribution[class_name] = class_count

        # Calculer statistiques agrégées
        total_samples = sum(class_distribution.values())

        if image_sizes:
            mean_width = np.mean([s[0] for s in image_sizes])
            mean_height = np.mean([s[1] for s in image_sizes])
            mean_image_size = (float(mean_width), float(mean_height))
        else:
            mean_image_size = (0.0, 0.0)

        mean_pixel_intensity = float(np.mean(pixel_intensities)) if pixel_intensities else 0.0
        std_pixel_intensity = float(np.std(pixel_intensities)) if pixel_intensities else 0.0

        return DatasetStatistics(
            total_samples=total_samples,
            class_distribution=class_distribution,
            mean_image_size=mean_image_size,
            mean_pixel_intensity=mean_pixel_intensity,
            std_pixel_intensity=std_pixel_intensity,
            corrupted_images=corrupted_images,
            duplicate_hashes=duplicate_hashes,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

    def _run_statistical_tests(
        self,
        dataset_path: str,
        statistics: DatasetStatistics,
        reference_stats: Optional[Dict]
    ) -> Dict[str, Dict]:
        """
        Effectue des tests statistiques sur le dataset

        Args:
            dataset_path: Chemin vers le dataset
            statistics: Statistiques collectées
            reference_stats: Statistiques de référence (optionnel)

        Returns:
            Dict: Résultats des tests statistiques
        """
        tests = {}

        # Test 1: Chi-Square pour distribution des classes
        tests['class_balance'] = self._chi_square_test(statistics.class_distribution)

        # Test 2: Z-score pour détecter outliers dans intensités de pixels
        tests['pixel_intensity_outliers'] = self._zscore_test(dataset_path)

        # Test 3: Kolmogorov-Smirnov pour comparaison avec référence
        if reference_stats:
            tests['distribution_similarity'] = self._ks_test(dataset_path, reference_stats)

        return tests

    def _chi_square_test(self, class_distribution: Dict[str, int]) -> Dict:
        """
        Test Chi-Square pour vérifier l'équilibre des classes

        Args:
            class_distribution: Distribution des classes

        Returns:
            Dict: Résultats du test
        """
        if not class_distribution:
            return {
                'test_name': 'Chi-Square Class Balance',
                'passed': False,
                'p_value': 0.0,
                'chi2_statistic': 0.0,
                'message': 'Aucune classe détectée'
            }

        # Fréquences observées
        observed = np.array(list(class_distribution.values()))

        # Fréquences attendues (distribution uniforme)
        expected = np.full(len(observed), observed.mean())

        # Test Chi-Square
        chi2_stat, p_value = stats.chisquare(observed, expected)

        # Interprétation : p > 0.05 = distribution équilibrée
        passed = p_value > 0.05

        return {
            'test_name': 'Chi-Square Class Balance',
            'passed': passed,
            'p_value': float(p_value),
            'chi2_statistic': float(chi2_stat),
            'class_counts': class_distribution,
            'message': 'Classes équilibrées' if passed else 'Déséquilibre détecté'
        }

    def _zscore_test(self, dataset_path: str) -> Dict:
        """
        Test Z-score pour détecter les outliers dans les intensités de pixels

        Args:
            dataset_path: Chemin vers le dataset

        Returns:
            Dict: Résultats du test
        """
        dataset_path = Path(dataset_path)
        pixel_values = []

        # Échantillonner des pixels aléatoires de chaque image
        for class_dir in dataset_path.iterdir():
            if not class_dir.is_dir():
                continue

            for img_path in list(class_dir.glob('*'))[:50]:  # Limiter à 50 images par classe
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                    continue

                try:
                    img = Image.open(img_path)
                    img_array = np.array(img)

                    # Échantillonner 1000 pixels aléatoires
                    if len(img_array.shape) == 3:
                        samples = img_array.flatten()[:1000]
                    else:
                        samples = img_array.flatten()[:1000]

                    pixel_values.extend(samples)
                except:
                    continue

        if not pixel_values:
            return {
                'test_name': 'Z-Score Pixel Outliers',
                'passed': False,
                'outliers_count': 0,
                'outliers_percentage': 0.0,
                'message': 'Aucune donnée pour analyse'
            }

        # Calculer Z-scores
        pixel_values = np.array(pixel_values)
        z_scores = np.abs(stats.zscore(pixel_values))

        # Compter outliers (|z| > threshold)
        outliers = np.sum(z_scores > self.zscore_threshold)
        outliers_percentage = (outliers / len(pixel_values)) * 100

        # Seuil acceptable : < 1% d'outliers
        passed = outliers_percentage < 1.0

        return {
            'test_name': 'Z-Score Pixel Outliers',
            'passed': passed,
            'outliers_count': int(outliers),
            'outliers_percentage': float(outliers_percentage),
            'threshold': self.zscore_threshold,
            'message': f'{outliers_percentage:.2f}% outliers détectés'
        }

    def _ks_test(self, dataset_path: str, reference_stats: Dict) -> Dict:
        """
        Test Kolmogorov-Smirnov pour comparer avec distribution de référence

        Args:
            dataset_path: Chemin vers le dataset
            reference_stats: Statistiques de référence

        Returns:
            Dict: Résultats du test
        """
        # Pour simplifier, on compare les distributions de pixel intensities
        dataset_path = Path(dataset_path)
        current_intensities = []

        for class_dir in dataset_path.iterdir():
            if not class_dir.is_dir():
                continue

            for img_path in list(class_dir.glob('*'))[:30]:
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.bmp']:
                    continue

                try:
                    img = Image.open(img_path)
                    img_array = np.array(img)
                    current_intensities.append(img_array.mean())
                except:
                    continue

        if not current_intensities or 'pixel_intensities' not in reference_stats:
            return {
                'test_name': 'Kolmogorov-Smirnov Distribution Similarity',
                'passed': True,
                'ks_statistic': 0.0,
                'p_value': 1.0,
                'message': 'Pas de données de référence pour comparaison'
            }

        # Test KS
        reference_intensities = reference_stats['pixel_intensities']
        ks_stat, p_value = stats.ks_2samp(current_intensities, reference_intensities)

        # Interprétation : p > alpha = distributions similaires
        passed = p_value > self.ks_alpha

        return {
            'test_name': 'Kolmogorov-Smirnov Distribution Similarity',
            'passed': passed,
            'ks_statistic': float(ks_stat),
            'p_value': float(p_value),
            'alpha': self.ks_alpha,
            'message': 'Distributions similaires' if passed else 'Distributions divergentes'
        }

    def _detect_anomalies(
        self,
        statistics: DatasetStatistics,
        statistical_tests: Dict[str, Dict]
    ) -> List[str]:
        """
        Détecte les anomalies dans le dataset

        Args:
            statistics: Statistiques du dataset
            statistical_tests: Résultats des tests statistiques

        Returns:
            List[str]: Liste des anomalies détectées
        """
        anomalies = []

        # Anomalie 1: Trop peu d'échantillons par classe
        for class_name, count in statistics.class_distribution.items():
            if count < self.min_samples_per_class:
                anomalies.append(
                    f"Classe '{class_name}' a seulement {count} échantillons "
                    f"(minimum: {self.min_samples_per_class})"
                )

        # Anomalie 2: Déséquilibre excessif entre classes
        if statistics.class_distribution:
            max_count = max(statistics.class_distribution.values())
            min_count = min(statistics.class_distribution.values())
            if min_count > 0:
                imbalance_ratio = max_count / min_count
                if imbalance_ratio > self.max_class_imbalance_ratio:
                    anomalies.append(
                        f"Déséquilibre excessif: ratio {imbalance_ratio:.2f} "
                        f"(max: {self.max_class_imbalance_ratio})"
                    )

        # Anomalie 3: Images corrompues
        if statistics.corrupted_images > 0:
            anomalies.append(
                f"{statistics.corrupted_images} images corrompues détectées"
            )

        # Anomalie 4: Duplicates excessifs
        if statistics.duplicate_hashes > statistics.total_samples * 0.05:  # > 5%
            anomalies.append(
                f"{statistics.duplicate_hashes} duplicates détectés "
                f"({(statistics.duplicate_hashes/statistics.total_samples)*100:.1f}%)"
            )

        # Anomalie 5: Tests statistiques échoués
        for test_name, test_result in statistical_tests.items():
            if not test_result.get('passed', True):
                anomalies.append(
                    f"Test '{test_name}' échoué: {test_result.get('message', 'N/A')}"
                )

        return anomalies

    def _calculate_quality_score(
        self,
        statistics: DatasetStatistics,
        statistical_tests: Dict[str, Dict],
        anomalies: List[str]
    ) -> float:
        """
        Calcule un score de qualité global du dataset (0-100)

        Args:
            statistics: Statistiques du dataset
            statistical_tests: Résultats des tests
            anomalies: Liste des anomalies

        Returns:
            float: Score de qualité (0-100)
        """
        score = 100.0

        # Pénalités pour anomalies
        score -= len(anomalies) * 10  # -10 points par anomalie

        # Pénalités pour images corrompues
        if statistics.total_samples > 0:
            corruption_rate = statistics.corrupted_images / statistics.total_samples
            score -= corruption_rate * 50  # Max -50 points

        # Pénalités pour duplicates
        if statistics.total_samples > 0:
            duplicate_rate = statistics.duplicate_hashes / statistics.total_samples
            score -= duplicate_rate * 30  # Max -30 points

        # Bonus pour taille de dataset
        if statistics.total_samples >= 100:
            score += 5
        if statistics.total_samples >= 500:
            score += 5

        # Score minimum : 0
        return max(0.0, score)

    def save_report(self, report: VerificationReport, output_path: str):
        """
        Sauvegarde le rapport de vérification en JSON

        Args:
            report: Rapport de vérification
            output_path: Chemin de sortie
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convertir en dictionnaire
        report_dict = {
            'dataset_path': report.dataset_path,
            'statistics': asdict(report.statistics),
            'statistical_tests': report.statistical_tests,
            'anomalies_detected': report.anomalies_detected,
            'quality_score': report.quality_score,
            'passed': report.passed,
            'timestamp': report.timestamp
        }

        # Encodeur pour les types numpy non sérialisables nativement
        class _NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.bool_):
                    return bool(obj)
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        # Sauvegarder
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)

        print(f"\n✓ Rapport sauvegardé: {output_path}")


if __name__ == '__main__':
    """
    Script de test du DataVerifier
    """
    # Créer le vérificateur
    verifier = DataVerifier(
        min_samples_per_class=5,
        max_class_imbalance_ratio=5.0,
        zscore_threshold=3.0
    )

    # Vérifier le dataset de test
    test_dataset = 'data/processed/test'

    if os.path.exists(test_dataset):
        report = verifier.verify_dataset(test_dataset)

        # Sauvegarder le rapport
        verifier.save_report(
            report,
            'results/data_verification/test_dataset_report.json'
        )

        # Afficher résumé
        print(f"\n{'='*60}")
        print(f"RÉSUMÉ DE LA VÉRIFICATION")
        print(f"{'='*60}")
        print(f"Dataset: {report.dataset_path}")
        print(f"Score de qualité: {report.quality_score:.2f}/100")
        print(f"Status: {'✓ VALIDE' if report.passed else '✗ INVALIDE'}")
        print(f"Échantillons: {report.statistics.total_samples}")
        print(f"Classes: {report.statistics.class_distribution}")
        print(f"Anomalies: {len(report.anomalies_detected)}")
        if report.anomalies_detected:
            for anomaly in report.anomalies_detected:
                print(f"  - {anomaly}")
    else:
        print(f"⚠ Dataset non trouvé: {test_dataset}")
