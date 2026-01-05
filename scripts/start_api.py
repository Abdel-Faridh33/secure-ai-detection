#!/usr/bin/env python3
"""
Script pour démarrer l'API FastAPI
"""

import sys
import os
import uvicorn

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, '/workspace/src')

def main():
    print("🚀 Démarrage de l'API Secure AI Detection...")
    print("📡 API disponible sur: http://localhost:8000")
    print("📖 Documentation: http://localhost:8000/docs")
    print("💻 Container port: 9800 -> 8000")
    print()

    try:
        # Import de l'application
        from api.app import app

        # Démarrage du serveur
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["/workspace/src"],
            log_level="info"
        )

    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Vérifiez que le module API est disponible")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()