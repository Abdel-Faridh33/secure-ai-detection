"""
Module de gestion de la base de données PostgreSQL

Ce module fournit:
- Connexion à PostgreSQL
- Gestion des utilisateurs (UserManager)
- Logger de prédictions (PredictionLogger)
- Intégration avec audit_logger pour indexation
"""

from .connection import DatabaseConnection, get_db_connection
from .user_manager import UserManager
from .prediction_logger import PredictionLogger

__all__ = [
    'DatabaseConnection',
    'get_db_connection',
    'UserManager',
    'PredictionLogger'
]
