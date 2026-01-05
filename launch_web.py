#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ouvrir l'interface web Secure AI Detection
"""

import webbrowser
import sys

def main():
    print("=== Secure AI Detection - Interface Web ===")
    print()
    print("Services disponibles:")
    print("  Interface Web: http://localhost:8080")
    print("  API Backend:   http://localhost:9800")
    print("  Monitoring:    http://localhost:3000")
    print()

    web_url = "http://localhost:8080"

    try:
        print("Ouverture de l'interface web...")
        webbrowser.open(web_url)
        print(f"Interface ouverte: {web_url}")

        print()
        print("Guide rapide:")
        print("  1. Selectionnez une image (JPG, PNG, GIF)")
        print("  2. Choisissez le modele (Baseline ou Securise)")
        print("  3. Cliquez sur 'Analyser l'image'")
        print("  4. Consultez les resultats de detection")
        print()
        print("Commandes utiles:")
        print("  make status - Voir l'etat des services")
        print("  make logs   - Voir les logs en temps reel")
        print("  make stop   - Arreter tous les services")

    except Exception as e:
        print(f"Erreur: {e}")
        print(f"Ouvrez manuellement: {web_url}")

if __name__ == "__main__":
    main()