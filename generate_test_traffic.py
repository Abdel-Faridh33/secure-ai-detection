#!/usr/bin/env python3
"""
Script pour générer du trafic de test sur l'API
Cela permet de remplir les graphiques Grafana avec des données
"""

import requests
import time
import random
import base64
import numpy as np
from PIL import Image
import io
import json

# Configuration
API_URL = "http://localhost:9800"
NUM_REQUESTS = 50  # Nombre de requêtes à générer
DELAY = 0.5  # Délai entre les requêtes (secondes)

def test_health():
    """Test du endpoint /health"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"ERREUR health check: {e}")
        return False

def test_predict(model_type):
    """Test du endpoint /predict"""
    try:
        # Creer une vraie image PNG
        img_array = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Envoyer comme multipart/form-data
        files = {'file': ('test.png', buffer, 'image/png')}

        response = requests.post(
            f"{API_URL}/predict/{model_type}",
            files=files,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return True, result.get('prediction', 'unknown')
        else:
            return False, None

    except Exception as e:
        print(f"ERREUR prediction ({model_type}): {e}")
        return False, None

def main():
    print("=" * 60)
    print("GENERATION DE TRAFIC DE TEST")
    print("=" * 60)
    print(f"\nAPI: {API_URL}")
    print(f"Nombre de requêtes: {NUM_REQUESTS}")
    print(f"Délai entre requêtes: {DELAY}s")
    print("\n" + "-" * 60 + "\n")

    # Verifier que l'API est accessible
    print("Verification de l'API...")
    if not test_health():
        print("ERREUR: L'API n'est pas accessible. Verifiez qu'elle est demarree.")
        return
    print("OK: API accessible\n")

    # Statistiques
    stats = {
        'health': {'success': 0, 'error': 0},
        'baseline': {'success': 0, 'error': 0, 'safe': 0, 'dangerous': 0},
        'secured': {'success': 0, 'error': 0, 'safe': 0, 'dangerous': 0}
    }

    print("Generation du trafic...\n")

    for i in range(NUM_REQUESTS):
        # Alterner entre différents types de requêtes
        request_type = random.choice(['health', 'predict_baseline', 'predict_secured'])

        if request_type == 'health':
            success = test_health()
            if success:
                stats['health']['success'] += 1
                print(f"[{i+1}/{NUM_REQUESTS}] OK Health check")
            else:
                stats['health']['error'] += 1
                print(f"[{i+1}/{NUM_REQUESTS}] ERROR Health check")

        elif request_type == 'predict_baseline':
            success, prediction = test_predict('baseline')
            if success:
                stats['baseline']['success'] += 1
                if prediction == 'safe':
                    stats['baseline']['safe'] += 1
                else:
                    stats['baseline']['dangerous'] += 1
                print(f"[{i+1}/{NUM_REQUESTS}] OK Baseline prediction - {prediction}")
            else:
                stats['baseline']['error'] += 1
                print(f"[{i+1}/{NUM_REQUESTS}] ERROR Baseline prediction")

        elif request_type == 'predict_secured':
            success, prediction = test_predict('secured')
            if success:
                stats['secured']['success'] += 1
                if prediction == 'safe':
                    stats['secured']['safe'] += 1
                else:
                    stats['secured']['dangerous'] += 1
                print(f"[{i+1}/{NUM_REQUESTS}] OK Secured prediction - {prediction}")
            else:
                stats['secured']['error'] += 1
                print(f"[{i+1}/{NUM_REQUESTS}] ERROR Secured prediction")

        time.sleep(DELAY)

    # Afficher les statistiques
    print("\n" + "=" * 60)
    print("STATISTIQUES FINALES")
    print("=" * 60)

    print(f"\nHealth Checks:")
    print(f"   Succes: {stats['health']['success']}")
    print(f"   Erreurs: {stats['health']['error']}")

    print(f"\nBaseline Model:")
    print(f"   Succes: {stats['baseline']['success']}")
    print(f"   Erreurs: {stats['baseline']['error']}")
    print(f"   - Safe: {stats['baseline']['safe']}")
    print(f"   - Dangerous: {stats['baseline']['dangerous']}")

    print(f"\nSecured Model:")
    print(f"   Succes: {stats['secured']['success']}")
    print(f"   Erreurs: {stats['secured']['error']}")
    print(f"   - Safe: {stats['secured']['safe']}")
    print(f"   - Dangerous: {stats['secured']['dangerous']}")

    total = stats['health']['success'] + stats['baseline']['success'] + stats['secured']['success']
    errors = stats['health']['error'] + stats['baseline']['error'] + stats['secured']['error']

    print(f"\nTotal:")
    print(f"   Requetes reussies: {total}/{NUM_REQUESTS}")
    print(f"   Taux de succes: {(total/(total+errors)*100):.1f}%")

    print("\n" + "=" * 60)
    print("Generation de trafic terminee!")
    print("\nOuvrez Grafana pour voir les graphiques:")
    print(f"   http://localhost:3500")
    print("   (admin/admin)")
    print("=" * 60)

if __name__ == "__main__":
    main()
