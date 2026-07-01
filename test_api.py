#!/usr/bin/env python3
"""
Script de test pour l'API Secure AI Detection
"""

import requests
import io
from PIL import Image

def create_test_image():
    """Crée une image de test simple"""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_api():
    """Teste l'API avec une image"""
    base_url = "http://localhost:9800"

    print("Test de l'API Secure AI Detection")
    print("=" * 40)

    # Test health
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # Test avec image (modèle sécurisé uniquement)
    try:
        print(f"\nTest modele secured...")

        # Créer une image de test
        test_image = create_test_image()

        files = {"file": ("test.png", test_image, "image/png")}
        response = requests.post(f"{base_url}/predict", files=files)

        if response.status_code == 200:
            result = response.json()
            print(f"Prediction: {result['prediction']}")
            print(f"   Confiance: {result['confidence']}")
            print(f"   Temps: {result['processing_time_ms']}ms")
            print(f"   Image: {result['image_info']['size']}")
        else:
            print(f"Erreur: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Test secured failed: {e}")

    print("\nTests termines!")

if __name__ == "__main__":
    test_api()