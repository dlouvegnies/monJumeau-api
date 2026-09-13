"""
Configuration pytest partagée.

À placer dans un dossier `tests/` à la RACINE du backend, au même niveau
que `main.py` (ce fichier fait `import main`).

Les variables d'environnement sont fixées AVANT l'import de main.py, car
main.py les lit une seule fois au chargement du module (CLAUDE_API_KEY,
APP_SECRET, SUPABASE_URL, etc. sont des constantes de module — pas relues
à chaque requête).
"""
import os
import sys

# pytest ajoute le dossier tests/ à sys.path, pas la racine du projet où
# vit main.py — sans cette ligne, `import main` échoue avec
# ModuleNotFoundError même lancé depuis la racine du projet.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("CLAUDE_API_KEY", "test-claude-key")
os.environ.setdefault("APP_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_URL", "https://example.invalid")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")

import pytest
from fastapi.testclient import TestClient

import main  # noqa: E402  (import volontairement après le réglage des env vars)


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def auth_headers():
    """Header x-app-secret valide, aligné sur la valeur lue par main.py au
    démarrage (voir APP_SECRET ci-dessus)."""
    return {"x-app-secret": main.APP_SECRET}
