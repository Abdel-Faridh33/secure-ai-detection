"""
Response Filter
Filtrage des réponses pour éviter les fuites
"""

class ResponseFilter:
    """Filtre de réponses"""
    
    @staticmethod
    def filter_response(response: dict) -> dict:
        """Filtre les informations sensibles"""
        # Retirer les informations internes
        filtered = response.copy()
        sensitive_keys = ['internal_score', 'model_version', 'debug_info']
        for key in sensitive_keys:
            filtered.pop(key, None)
        return filtered
