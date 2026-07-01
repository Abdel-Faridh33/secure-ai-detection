"""
WAF (Web Application Firewall) simplifié
Zone 4 - Production Security

Fonctionnalités :
- Rate limiting par IP
- Validation des entrées
- Détection de patterns suspects
- Blocage automatique d'IPs
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import re
import os

class RateLimiter:
    """
    Rate limiter simple basé sur l'IP
    Limite le nombre de requêtes par IP par fenêtre de temps
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: Nombre max de requêtes autorisées
            window_seconds: Fenêtre de temps en secondes
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}

    def is_allowed(self, ip: str) -> bool:
        """
        Vérifier si une IP peut faire une requête

        Args:
            ip: Adresse IP du client

        Returns:
            True si autorisé, False si rate limit dépassé
        """
        now = datetime.utcnow()

        # Vérifier si l'IP est bloquée
        if ip in self.blocked_ips:
            block_until = self.blocked_ips[ip]
            if now < block_until:
                return False  # Toujours bloquée
            else:
                # Débloquer l'IP
                del self.blocked_ips[ip]

        # Nettoyer les anciennes requêtes (hors fenêtre)
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > cutoff_time
        ]

        # Vérifier le nombre de requêtes
        if len(self.requests[ip]) >= self.max_requests:
            # Bloquer l'IP pour 5 minutes
            self.blocked_ips[ip] = now + timedelta(minutes=5)
            return False

        # Enregistrer la nouvelle requête
        self.requests[ip].append(now)
        return True

    def get_request_count(self, ip: str) -> int:
        """Obtenir le nombre de requêtes actuelles pour une IP"""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.window_seconds)
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > cutoff_time
        ]
        return len(self.requests[ip])

    def is_blocked(self, ip: str) -> bool:
        """Vérifier si une IP est bloquée"""
        if ip not in self.blocked_ips:
            return False
        now = datetime.utcnow()
        return now < self.blocked_ips[ip]


class InputValidator:
    """
    Validateur d'entrées pour détecter les patterns suspects
    """

    # Patterns suspects (injection, XSS, etc.)
    SUSPICIOUS_PATTERNS = [
        r"<script",                        # XSS
        r"javascript:",                    # XSS
        r"onerror\s*=",                   # XSS
        r"onclick\s*=",                   # XSS
        r"SELECT.{0,10}FROM",             # SQL Injection (tolère _, espaces, etc.)
        r"UNION.{0,10}SELECT",            # SQL Injection
        r"DROP.{0,10}TABLE",              # SQL Injection
        r"\.\./",                          # Path traversal Unix
        r"\.\.[/\\]",                     # Path traversal (Unix + Windows)
        r"/etc/passwd",                   # File inclusion
        r"cmd\.exe",                      # Command injection Windows
        r"bash[\s_+-]",                   # Command injection Unix
        r"powershell",                    # Command injection Windows
        r"eval\s*\(",                     # Code injection
        r"%00",                            # Null byte injection
    ]

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        Vérifier si un nom de fichier est sûr

        Args:
            filename: Nom du fichier à vérifier

        Returns:
            True si sûr, False si suspect
        """
        if not filename:
            return False

        # Vérifier les patterns suspects
        for pattern in InputValidator.SUSPICIOUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                return False

        # Vérifier les extensions autorisées pour les images
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return any(filename.lower().endswith(ext) for ext in allowed_extensions)

    @staticmethod
    def is_safe_string(text: str) -> bool:
        """
        Vérifier si une chaîne est sûre

        Args:
            text: Texte à vérifier

        Returns:
            True si sûr, False si suspect
        """
        if not text:
            return True

        # Vérifier les patterns suspects
        for pattern in InputValidator.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        return True

    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """
        Nettoyer une chaîne de caractères

        Args:
            text: Texte à nettoyer
            max_length: Longueur maximale

        Returns:
            Texte nettoyé
        """
        if not text:
            return ""

        # Limiter la longueur
        text = text[:max_length]

        # Supprimer les caractères dangereux
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')

        return text


class WAF:
    """
    Web Application Firewall simplifié
    Combine rate limiting et validation d'entrées
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.rate_limiter = RateLimiter(max_requests, window_seconds)
        self.validator = InputValidator()

    def check_request(self, ip: str, filename: Optional[str] = None) -> Dict:
        """
        Vérifier une requête complète

        Args:
            ip: Adresse IP du client
            filename: Nom du fichier (optionnel)

        Returns:
            Dict avec le résultat de la vérification
        """
        result = {
            "allowed": True,
            "reason": None,
            "request_count": 0
        }

        # Vérification du rate limiting
        if not self.rate_limiter.is_allowed(ip):
            result["allowed"] = False
            result["reason"] = "Rate limit exceeded"
            return result

        result["request_count"] = self.rate_limiter.get_request_count(ip)

        # Vérification du filename si fourni
        if filename and not self.validator.is_safe_filename(filename):
            result["allowed"] = False
            result["reason"] = "Suspicious filename detected"
            return result

        return result

    def is_ip_blocked(self, ip: str) -> bool:
        """Vérifier si une IP est bloquée"""
        return self.rate_limiter.is_blocked(ip)


# Instance globale du WAF – seuil configurable via RATE_LIMIT
_rate_limit = int(os.environ.get("RATE_LIMIT", 100))
waf = WAF(max_requests=_rate_limit, window_seconds=60)
