"""
Gestionnaire de connexion PostgreSQL
Fournit des connexions poolées et des méthodes utilitaires
"""

import os
import psycopg2
from psycopg2 import pool, extras
from typing import Optional, Dict, Any
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Gestionnaire de connexion PostgreSQL avec connection pooling

    Utilise un pool de connexions pour améliorer les performances
    et gérer automatiquement la réutilisation des connexions.
    """

    _instance: Optional['DatabaseConnection'] = None
    _pool: Optional[pool.SimpleConnectionPool] = None

    def __new__(cls):
        """Singleton pattern pour réutiliser le même pool"""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialise le pool de connexions si nécessaire"""
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """Crée le pool de connexions"""
        config = self._get_db_config()

        try:
            # Créer un pool de 5 à 20 connexions
            self._pool = pool.SimpleConnectionPool(
                minconn=5,
                maxconn=20,
                **config
            )
            logger.info(f"Pool de connexions créé: {config['host']}:{config['port']}/{config['database']}")

        except psycopg2.Error as e:
            logger.error(f"Impossible de créer le pool de connexions: {e}")
            raise

    @staticmethod
    def _get_db_config() -> Dict[str, Any]:
        """Récupère la configuration depuis les variables d'environnement"""
        return {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5433')),
            'database': os.getenv('POSTGRES_DB', 'ai_metrics'),
            'user': os.getenv('POSTGRES_USER', 'secure_ai'),
            'password': os.getenv('POSTGRES_PASSWORD', 'secure_password'),
            'connect_timeout': 10
        }

    @contextmanager
    def get_connection(self):
        """
        Context manager pour obtenir une connexion du pool

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ...")
        """
        conn = None
        try:
            conn = self._pool.getconn()
            conn.autocommit = False
            yield conn
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Erreur de connexion DB: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """
        Context manager pour obtenir un curseur directement

        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT ...")
                results = cursor.fetchall()

        Args:
            cursor_factory: Type de curseur (ex: RealDictCursor pour dict)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except psycopg2.Error:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """
        Exécute une requête SQL simple

        Args:
            query: Requête SQL
            params: Paramètres de la requête (tuple)
            fetch: Si True, retourne les résultats (SELECT)

        Returns:
            Liste de tuples si fetch=True, None sinon
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            return None

    def execute_query_dict(self, query: str, params: tuple = None):
        """
        Exécute une requête et retourne les résultats comme dictionnaires

        Args:
            query: Requête SQL
            params: Paramètres de la requête

        Returns:
            Liste de dictionnaires
        """
        with self.get_cursor(cursor_factory=extras.RealDictCursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_insert(self, query: str, params: tuple = None, returning: bool = True):
        """
        Exécute un INSERT et retourne l'ID généré

        Args:
            query: Requête INSERT (doit inclure RETURNING id)
            params: Paramètres
            returning: Si True, retourne la valeur du RETURNING

        Returns:
            ID inséré si returning=True
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            if returning:
                return cursor.fetchone()[0]
            return None

    def test_connection(self) -> bool:
        """
        Teste la connexion à la base de données

        Returns:
            True si connexion OK, False sinon
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except psycopg2.Error as e:
            logger.error(f"Test de connexion échoué: {e}")
            return False

    def close_all_connections(self):
        """Ferme toutes les connexions du pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("Toutes les connexions fermées")

    def __del__(self):
        """Nettoyage lors de la destruction"""
        self.close_all_connections()


# Instance globale singleton
_db_instance: Optional[DatabaseConnection] = None


def get_db_connection() -> DatabaseConnection:
    """
    Récupère l'instance singleton de DatabaseConnection

    Returns:
        Instance de DatabaseConnection

    Usage:
        from src.database import get_db_connection

        db = get_db_connection()
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
    return _db_instance
