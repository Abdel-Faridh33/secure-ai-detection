#!/usr/bin/env python3
"""
Serveur web simple pour l'interface de démonstration
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Configuration
PORT = 8080
HOST = 'localhost'

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Handler personnalisé avec CORS pour permettre les appels API"""

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    """Lance le serveur web"""

    # Change vers le répertoire web
    web_dir = Path(__file__).parent
    os.chdir(web_dir)

    # Configuration du serveur
    with socketserver.TCPServer((HOST, PORT), CustomHTTPRequestHandler) as httpd:
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                 Interface Web - Secure AI                ║
╠══════════════════════════════════════════════════════════╣
║  🌐 URL: http://{HOST}:{PORT}                          ║
║  📁 Répertoire: {web_dir}                               ║
║                                                          ║
║  💡 L'interface se lancera automatiquement...           ║
║  🛑 Ctrl+C pour arrêter le serveur                      ║
╚══════════════════════════════════════════════════════════╝
        """)

        # Ouvre automatiquement le navigateur
        url = f"http://{HOST}:{PORT}"
        try:
            webbrowser.open(url)
            print(f"✅ Navigateur ouvert sur {url}")
        except Exception as e:
            print(f"⚠️ Impossible d'ouvrir le navigateur: {e}")
            print(f"📖 Ouvrez manuellement: {url}")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Serveur arrêté par l'utilisateur")
            httpd.shutdown()

if __name__ == "__main__":
    main()