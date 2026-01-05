#!/usr/bin/env python3
"""
Script d'initialisation de la base de données PostgreSQL
Applique tous les schémas SQL et charge les données initiales

Usage:
    python scripts/init_database.py
    python scripts/init_database.py --reset  # Réinitialise complètement
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import argparse
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Charger le fichier .env (override=True pour écraser les vars système)
load_dotenv(ROOT_DIR / '.env', override=True)

# Configuration de connexion PostgreSQL (depuis .env ou défaut Docker)
# Détecte si on est dans Docker ou sur l'hôte
_in_docker = os.path.exists('/.dockerenv')
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres' if _in_docker else 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432' if _in_docker else '5433')),
    'database': os.getenv('POSTGRES_DB', 'ai_metrics'),
    'user': os.getenv('POSTGRES_USER', 'secure_ai'),
    'password': os.getenv('POSTGRES_PASSWORD', 'secure_password')
}

# Ordre d'exécution des scripts SQL
SQL_SCRIPTS = [
    '01_schema_users.sql',
    '02_schema_audit_index.sql',
    '03_schema_predictions.sql',
    '04_initial_data.sql'
]

# Couleurs pour output console
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Affiche un header formaté"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(message: str):
    """Affiche un message de succès"""
    print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")


def print_error(message: str):
    """Affiche un message d'erreur"""
    print(f"{Colors.FAIL}[ERREUR] {message}{Colors.ENDC}")


def print_warning(message: str):
    """Affiche un avertissement"""
    print(f"{Colors.WARNING}[ATTENTION] {message}{Colors.ENDC}")


def print_info(message: str):
    """Affiche une information"""
    print(f"{Colors.OKCYAN}[INFO] {message}{Colors.ENDC}")


def test_connection() -> bool:
    """Teste la connexion à PostgreSQL"""
    print_info("Test de connexion à PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        print_success(f"Connexion réussie !")
        print_info(f"Version: {version[:50]}...")
        return True

    except psycopg2.Error as e:
        print_error(f"Échec de connexion: {e}")
        print_info("Vérifiez que PostgreSQL est démarré:")
        print_info("  docker-compose -f docker-compose.dev.yml ps postgres")
        return False


def drop_all_tables(conn) -> bool:
    """Supprime toutes les tables existantes (DANGEREUX!)"""
    print_warning("Suppression de toutes les tables existantes...")

    cursor = conn.cursor()

    try:
        # Liste toutes les tables dans le schéma public
        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        tables = cursor.fetchall()

        if not tables:
            print_info("Aucune table à supprimer")
            return True

        # Désactiver les contraintes de clés étrangères temporairement
        cursor.execute("SET session_replication_role = 'replica';")

        # Supprimer chaque table
        for (table_name,) in tables:
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name)
            ))
            print_info(f"  - Table '{table_name}' supprimée")

        # Réactiver les contraintes
        cursor.execute("SET session_replication_role = 'origin';")

        # Supprimer les fonctions custom
        cursor.execute("""
            SELECT proname FROM pg_proc
            WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND prokind = 'f'
        """)
        functions = cursor.fetchall()

        for (func_name,) in functions:
            if func_name not in ['update_updated_at_column', 'cleanup_expired_sessions',
                                 'update_daily_stats', 'calculate_model_performance',
                                 'update_unique_image_stats', 'cleanup_old_data']:
                continue
            cursor.execute(sql.SQL("DROP FUNCTION IF EXISTS {} CASCADE").format(
                sql.Identifier(func_name)
            ))
            print_info(f"  - Fonction '{func_name}' supprimée")

        conn.commit()
        print_success(f"{len(tables)} tables supprimées")
        return True

    except psycopg2.Error as e:
        conn.rollback()
        print_error(f"Erreur lors de la suppression: {e}")
        return False
    finally:
        cursor.close()


def execute_sql_file(conn, filepath: Path) -> bool:
    """Exécute un fichier SQL"""
    print_info(f"Exécution de {filepath.name}...")

    cursor = conn.cursor()

    try:
        # Lire le contenu du fichier SQL
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Exécuter le script
        cursor.execute(sql_content)
        conn.commit()

        print_success(f"{filepath.name} exécuté avec succès")
        return True

    except psycopg2.Error as e:
        conn.rollback()
        print_error(f"Erreur dans {filepath.name}:")
        print_error(f"  {e}")
        return False
    except FileNotFoundError:
        print_error(f"Fichier non trouvé: {filepath}")
        return False
    finally:
        cursor.close()


def verify_installation(conn) -> bool:
    """Vérifie que l'installation s'est bien déroulée"""
    print_info("Vérification de l'installation...")

    cursor = conn.cursor()

    try:
        # Vérifier les tables principales
        expected_tables = [
            'users', 'login_history', 'active_sessions', 'role_permissions',
            'audit_logs_index', 'audit_stats_daily', 'detected_anomalies',
            'predictions', 'model_performance', 'model_comparison', 'unique_images',
            'system_config'
        ]

        cursor.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]

        missing = set(expected_tables) - set(tables)
        if missing:
            print_error(f"Tables manquantes: {', '.join(missing)}")
            return False

        print_success(f"{len(tables)} tables créées")

        # Vérifier les utilisateurs par défaut
        cursor.execute("SELECT username, role FROM users ORDER BY username")
        users = cursor.fetchall()

        if len(users) >= 3:
            print_success(f"{len(users)} utilisateurs créés:")
            for username, role in users:
                print_info(f"  - {username} ({role})")
        else:
            print_warning("Moins de 3 utilisateurs créés")

        # Vérifier les permissions RBAC
        cursor.execute("SELECT COUNT(*) FROM role_permissions")
        perm_count = cursor.fetchone()[0]
        print_success(f"{perm_count} permissions RBAC configurées")

        # Vérifier les vues
        cursor.execute("""
            SELECT viewname FROM pg_views
            WHERE schemaname = 'public'
            ORDER BY viewname
        """)
        views = [row[0] for row in cursor.fetchall()]
        print_success(f"{len(views)} vues créées: {', '.join(views)}")

        # Vérifier les fonctions
        cursor.execute("""
            SELECT proname FROM pg_proc
            WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND prokind = 'f'
        """)
        functions = [row[0] for row in cursor.fetchall()]
        print_success(f"{len(functions)} fonctions créées")

        return True

    except psycopg2.Error as e:
        print_error(f"Erreur de vérification: {e}")
        return False
    finally:
        cursor.close()


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description='Initialisation de la base de données PostgreSQL'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Supprime toutes les tables existantes avant initialisation'
    )
    args = parser.parse_args()

    print_header("INITIALISATION BASE DE DONNÉES")

    # Afficher la configuration
    print_info(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print_info(f"Database: {DB_CONFIG['database']}")
    print_info(f"User: {DB_CONFIG['user']}")

    # Test de connexion
    if not test_connection():
        sys.exit(1)

    # Connexion à la base
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print_success("Connecté à PostgreSQL")
    except psycopg2.Error as e:
        print_error(f"Impossible de se connecter: {e}")
        sys.exit(1)

    try:
        # Réinitialisation si demandé
        if args.reset:
            print_warning("Mode RESET activé - Toutes les données seront perdues!")
            confirm = input("Tapez 'YES' pour confirmer: ")
            if confirm != 'YES':
                print_info("Annulé")
                sys.exit(0)

            if not drop_all_tables(conn):
                sys.exit(1)

        # Exécuter les scripts SQL dans l'ordre
        print_header("EXÉCUTION DES SCRIPTS SQL")

        scripts_dir = ROOT_DIR / 'scripts' / 'database'

        for script_name in SQL_SCRIPTS:
            script_path = scripts_dir / script_name

            if not execute_sql_file(conn, script_path):
                print_error("Installation échouée")
                sys.exit(1)

        # Vérification finale
        print_header("VÉRIFICATION")

        if not verify_installation(conn):
            print_error("Vérification échouée")
            sys.exit(1)

        # Succès !
        print_header("✓ INSTALLATION RÉUSSIE ✓")

        print_warning("\nATTENTION : Changez les mots de passe par défaut !")
        print_info("  - admin:admin123")
        print_info("  - operator:operator456")
        print_info("  - agent:agent789")

        print_info("\nProchaines étapes:")
        print_info("  1. Changer les mots de passe (via API ou module user_manager)")
        print_info("  2. Tester l'authentification")
        print_info("  3. Migrer launch_web.py pour utiliser PostgreSQL")

    except Exception as e:
        print_error(f"Erreur inattendue: {e}")
        sys.exit(1)
    finally:
        conn.close()
        print_info("Connexion fermée")


if __name__ == '__main__':
    main()
