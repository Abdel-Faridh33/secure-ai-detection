#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de démarrage complet pour la démo Secure AI Detection
"""

import subprocess
import time
import webbrowser
import sys
import os

def run_command(cmd, description=""):
    """Execute une commande shell"""
    if description:
        print(f"⏳ {description}...")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description} - Succès")
            return True
        else:
            print(f"❌ {description} - Erreur: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - Timeout")
        return False
    except Exception as e:
        print(f"❌ {description} - Exception: {e}")
        return False

def check_docker():
    """Vérifie que Docker est disponible"""
    return run_command("docker --version", "Vérification de Docker")

def main():
    """Lance la démo complète"""
    print("=" * 60)
    print("        🛡️ SECURE AI DETECTION - DEMO COMPLETE")
    print("=" * 60)
    print()

    # Vérification Docker
    if not check_docker():
        print("❌ Docker n'est pas disponible. Assurez-vous que Docker Desktop est lancé.")
        sys.exit(1)

    # Liste des services à démarrer
    services = [
        ("make dev", "Démarrage de l'environnement de développement"),
        ("make web", "Démarrage de l'interface web"),
    ]

    print("🚀 Démarrage des services...")

    for cmd, desc in services:
        if not run_command(cmd, desc):
            print(f"⚠️  Erreur lors du démarrage de: {desc}")
            # Continue malgré les erreurs

    print("\n⏱️  Attente que les services se stabilisent...")
    time.sleep(5)

    # Démarrage de l'API
    print("🔌 Démarrage de l'API...")
    run_command("make start-api", "Démarrage de l'API FastAPI")

    print("\n⏱️  Attente du démarrage de l'API...")
    time.sleep(3)

    # Vérification des services
    print("\n🔍 Vérification des services...")
    services_status = [
        ("http://localhost:8080", "Interface Web"),
        ("http://localhost:9800/health", "API Backend"),
        ("http://localhost:3000", "Grafana"),
    ]

    for url, name in services_status:
        # Test simple avec curl
        if run_command(f'curl -s -f {url} >nul 2>&1', f"Test {name}"):
            pass
        else:
            print(f"⚠️  {name} peut ne pas être encore prêt")

    # Ouverture de l'interface
    print("\n🌐 Ouverture de l'interface web...")
    try:
        webbrowser.open("http://localhost:8080")
        print("✅ Interface web ouverte dans le navigateur")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'ouverture: {e}")
        print("📖 Ouvrez manuellement: http://localhost:8080")

    print("\n" + "=" * 60)
    print("🎉 DEMO PRETE !")
    print("=" * 60)
    print("📊 Services disponibles:")
    print("   • Interface Web:  http://localhost:8080")
    print("   • API Backend:    http://localhost:9800")
    print("   • Documentation:  http://localhost:9800/docs")
    print("   • Grafana:        http://localhost:3000 (admin/admin)")
    print("   • Prometheus:     http://localhost:9890")
    print()
    print("🛠️  Commandes utiles:")
    print("   • make status     - Voir l'état des services")
    print("   • make logs       - Voir les logs en temps réel")
    print("   • make stop       - Arrêter tous les services")
    print("   • python test_api.py - Tester l'API")
    print()
    print("🎯 Utilisez l'interface web pour tester la détection d'objets !")
    print("=" * 60)

if __name__ == "__main__":
    main()