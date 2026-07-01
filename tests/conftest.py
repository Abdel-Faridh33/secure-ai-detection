"""
Configuration globale de pytest.
Ajoute la racine du projet au sys.path pour que les imports `src.*` fonctionnent.
"""
import sys
from pathlib import Path

# Racine du projet = dossier parent de tests/
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
