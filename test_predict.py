#!/usr/bin/env python3
"""Test rapide de l'endpoint /predict"""

import requests
import base64
import numpy as np
from PIL import Image
import io
import json

API_URL = "http://localhost:9800"

def create_test_image():
    """Crée une image de test 32x32"""
    img_array = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return img_base64

def test_predict(model_type):
    """Test une prediction"""
    print(f"\nTest prediction avec model_type={model_type}...")

    try:
        # Créer une vraie image PNG
        img_array = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Envoyer comme multipart/form-data
        files = {'file': ('test.png', buffer, 'image/png')}

        print(f"  Envoi de la requete...")
        response = requests.post(
            f"{API_URL}/predict/{model_type}",
            files=files,
            timeout=30
        )

        print(f"  Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"  SUCCESS!")
            print(f"  Prediction: {result.get('prediction', 'N/A')}")
            print(f"  Confidence: {result.get('confidence', 'N/A')}")
            return True
        else:
            print(f"  ERREUR: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE L'ENDPOINT /PREDICT")
    print("=" * 60)

    # Test baseline
    success1 = test_predict("baseline")

    # Test secured
    success2 = test_predict("secured")

    print("\n" + "=" * 60)
    if success1 and success2:
        print("RESULTAT: OK - Les deux modeles fonctionnent!")
    elif success1 or success2:
        print("RESULTAT: PARTIEL - Un seul modele fonctionne")
    else:
        print("RESULTAT: ERREUR - Aucun modele ne fonctionne")
    print("=" * 60)
