#!/usr/bin/env python3
"""
Script pour ouvrir automatiquement l'interface web
"""

import webbrowser
import urllib.request
import urllib.error
import sys

def check_services():
    """Vérifie que les services sont disponibles"""

    services = {
        "Interface Web": "http://localhost:8080",
        "API Backend": "http://localhost:9800/health"
    }

    print("🔍 Vérification des services...")

    for name, url in services.items():
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print(f"✅ {name}: Disponible")
                else:
                    print(f"⚠️  {name}: Erreur HTTP {response.status}")
        except urllib.error.URLError as e:
            print(f"❌ {name}: Non accessible ({url})")
        except Exception as e:
            print(f"❌ {name}: Erreur inconnue")

    print()

def main():
    """Lance l'interface web et vérifie les services"""

    print("""
╔══════════════════════════════════════════════════════════╗
║               🛡️ Secure AI Detection                     ║
║                Interface Web Intelligente                ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  🌐 Interface Web: http://localhost:8080                 ║
║  🔌 API Backend:   http://localhost:9800                 ║
║  📊 Monitoring:    http://localhost:3000                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Vérification des services
    check_services()

    # Ouverture de l'interface
    web_url = "http://localhost:8080"

    print(f"🚀 Ouverture de l'interface web...")
    try:
        webbrowser.open(web_url)
        print(f"✅ Interface ouverte: {web_url}")

        print("""
📋 Guide rapide:
   1. Chargez une image (JPG, PNG, GIF)
   2. Cliquez sur "Analyser l'image"
   3. Consultez les résultats de détection

🔧 Commandes utiles:
   • make status    - Voir l'état des services
   • make logs      - Voir les logs en temps réel
   • make stop      - Arrêter tous les services
        """)

    except Exception as e:
        print(f"❌ Erreur lors de l'ouverture: {e}")
        print(f"🖥️  Ouvrez manuellement: {web_url}")

if __name__ == "__main__":
    main()