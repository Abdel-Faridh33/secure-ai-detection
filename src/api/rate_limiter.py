"""
Rate Limiter
Limitation du taux de requêtes
"""

from collections import defaultdict
import time

class RateLimiter:
    """Limiteur de taux simple"""
    
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Vérifie si la requête est autorisée"""
        now = time.time()
        
        # Nettoyer les anciennes requêtes
        self.requests[client_id] = [
            req for req in self.requests[client_id] 
            if req > now - self.window
        ]
        
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(now)
            return True
        
        return False
