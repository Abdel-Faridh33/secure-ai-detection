#!/usr/bin/env python3
"""
Script de génération de trafic pour tester le monitoring
Génère des requêtes vers l'API sécurisée pour observer les métriques dans Grafana
"""

import requests
import time
import random
import glob
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:9800"
REQUESTS_COUNT = 50
DELAY_BETWEEN_REQUESTS = 1.0  # secondes

# Chemins vers les images de test
IMAGE_PATHS = {
    "safe": "data/augmented/test/safe/*.jpg",
    "dangerous": "data/augmented/test/dangerous/*.jpg",
    "adversarial": "data/adversarial/*.jpg"
}

def print_header():
    """Affiche l'en-tête du script"""
    print("=" * 70)
    print("GÉNÉRATION DE TRAFIC API - Monitoring Test".center(70))
    print("=" * 70)
    print(f"URL de l'API: {API_BASE_URL}")
    print(f"Nombre de requêtes: {REQUESTS_COUNT}")
    print(f"Délai entre requêtes: {DELAY_BETWEEN_REQUESTS}s")
    print("=" * 70)
    print()

def test_health():
    """Test l'endpoint /health"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Health check: {response.json()}")
            return True
        else:
            print(f"[FAIL] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Health check error: {e}")
        return False

def test_metrics():
    """Test l'endpoint /metrics"""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Metrics endpoint accessible")
            return True
        else:
            print(f"[FAIL] Metrics endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Metrics endpoint error: {e}")
        return False

def load_test_images():
    """Charge la liste des images de test disponibles"""
    images = {
        "safe": [],
        "dangerous": [],
        "adversarial": []
    }

    for category, pattern in IMAGE_PATHS.items():
        found = glob.glob(pattern)
        images[category] = found
        print(f"  - {category}: {len(found)} images trouvées")

    return images

def make_prediction_request(image_path):
    """Effectue une requête de prédiction avec une image vers l'API sécurisée"""
    endpoint = f"{API_BASE_URL}/predict"

    try:
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}

            start_time = time.time()
            response = requests.post(endpoint, files=files, timeout=30)
            duration = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "duration": duration,
                    "audit_id": result.get("audit_id"),
                    "prediction": result.get("prediction"),
                    "confidence": result.get("confidence"),
                    "processing_time": result.get("processing_time_ms")
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "duration": duration,
                    "error": response.text[:200]
                }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Image not found: {image_path}",
            "duration": 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "duration": 0
        }

def generate_traffic(images):
    """Génère du trafic vers l'API sécurisée"""
    print("\n" + "=" * 70)
    print("DÉMARRAGE DE LA GÉNÉRATION DE TRAFIC".center(70))
    print("=" * 70 + "\n")

    all_images = []
    for category, img_list in images.items():
        for img in img_list:
            all_images.append((category, img))

    if not all_images:
        print("✗ Aucune image trouvée pour les tests!")
        return

    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "total_duration": 0,
        "categories": {
            "safe": 0,
            "dangerous": 0,
            "adversarial": 0
        }
    }

    for i in range(REQUESTS_COUNT):
        category, image_path = random.choice(all_images)

        result = make_prediction_request(image_path)

        stats["total"] += 1
        if result["success"]:
            stats["success"] += 1
            stats["total_duration"] += result["duration"]
            stats["categories"][category] += 1

            print(f"[{i+1}/{REQUESTS_COUNT}] [OK] SECURED - "
                  f"{category.upper()} - "
                  f"Prediction: {result.get('prediction', 'N/A')} - "
                  f"Confidence: {result.get('confidence', 0):.3f} - "
                  f"Duration: {result['duration']:.3f}s - "
                  f"Audit ID: {result.get('audit_id', 'N/A')}")
        else:
            stats["failed"] += 1
            print(f"[{i+1}/{REQUESTS_COUNT}] [FAIL] SECURED - "
                  f"{category.upper()} - "
                  f"Error: {result.get('error', result.get('status_code', 'Unknown'))}")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\n" + "=" * 70)
    print("STATISTIQUES FINALES".center(70))
    print("=" * 70)
    print(f"Total de requêtes:     {stats['total']}")
    print(f"Succès:                {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"Échecs:                {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
    if stats['success'] > 0:
        print(f"Durée moyenne:         {stats['total_duration']/stats['success']:.3f}s")
    print(f"\nRequêtes par catégorie d'image:")
    print(f"  - Safe:              {stats['categories']['safe']}")
    print(f"  - Dangerous:         {stats['categories']['dangerous']}")
    print(f"  - Adversarial:       {stats['categories']['adversarial']}")
    print("=" * 70)
    print(f"\n[OK] Trafic genere avec succes!")
    print(f"\nConsultez les dashboards:")
    print(f"  - Grafana:     http://localhost:3000 (admin/admin)")
    print(f"  - Prometheus:  http://localhost:9890")
    print(f"  - API Docs:    http://localhost:9800/docs")
    print("=" * 70)

def main():
    """Fonction principale"""
    print_header()

    print("Tests préliminaires...")
    if not test_health():
        print("\n[FAIL] L'API n'est pas accessible. Veuillez demarrer l'API avant de generer du trafic.")
        return

    if not test_metrics():
        print("\n[WARN] L'endpoint /metrics n'est pas accessible. Les metriques Prometheus ne seront pas disponibles.")

    print("\n[OK] Tests preliminaires reussis!\n")

    print("Chargement des images de test...")
    images = load_test_images()

    total_images = sum(len(img_list) for img_list in images.values())
    if total_images == 0:
        print("\n[FAIL] Aucune image de test trouvee!")
        return

    print(f"\n[OK] {total_images} images chargees!\n")

    try:
        input("Appuyez sur Entrée pour commencer la génération de trafic (Ctrl+C pour annuler)...")
    except KeyboardInterrupt:
        print("\n\nAnnulation...")
        return

    try:
        generate_traffic(images)
    except KeyboardInterrupt:
        print("\n\n[STOP] Generation interrompue par l'utilisateur")

if __name__ == "__main__":
    main()
