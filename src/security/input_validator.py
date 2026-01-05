"""
Input Validator
Validation et sanitisation des entrées
"""

from PIL import Image
import numpy as np

class InputValidator:
    """Validateur d'entrées"""
    
    @staticmethod
    def validate_image(image_data: bytes) -> bool:
        """Valide une image uploadée"""
        try:
            img = Image.open(image_data)
            # Vérifications de sécurité
            if img.size[0] > 4096 or img.size[1] > 4096:
                return False
            return True
        except:
            return False
