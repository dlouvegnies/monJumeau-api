"""
Le prompt de curation des actualités (lot A6, 18/09/2026) : la ligne PROFIL
n'apparaît que si l'app envoie des traits.

Pourquoi c'est important : l'app n'envoie plus `profile_traits` — c'était une
liste figée de l'ancien encodeur, la même pour tout le monde. Le serveur
remplaçait alors la liste vide par « curieux, ouvert » : un profil inventé,
identique pour tous, qui poussait le modèle vers des actualités choisies pour
quelqu'un d'autre.

---

The news-curation prompt (lot A6): the PROFIL line appears only when the app
sends traits.
"""
import inspect

import main

ARTICLES = "1. [Le Monde] Un titre — une description"


def test_sans_traits_aucune_ligne_profil():
    """Liste vide : ni ligne PROFIL, ni profil par défaut."""
    prompt = main.construire_prompt_actus([], {"metier": "Infirmière", "ville": "Lyon"}, {}, ARTICLES)
    assert "PROFIL" not in prompt
    assert "curieux, ouvert" not in prompt
    # Ce qui reste de la personne est toujours là.
    assert "Métier: Infirmière" in prompt
    assert "Ville: Lyon" in prompt
    assert ARTICLES in prompt


def test_avec_traits_la_ligne_profil_reste():
    """Si un jour l'app envoie de vrais traits, ils sont dits."""
    prompt = main.construire_prompt_actus(["Curieuse", "Engagée"], {}, {}, ARTICLES)
    assert "PROFIL : Curieuse, Engagée" in prompt


def test_historique_inchange():
    """Les titres aimés ou écartés entrent toujours, cinq au plus."""
    liked = [f"aimé {i}" for i in range(7)]
    prompt = main.construire_prompt_actus([], {}, {"liked": liked, "disliked": ["écarté"]}, ARTICLES)
    assert "Appréciés : aimé 0, aimé 1, aimé 2, aimé 3, aimé 4" in prompt
    assert "aimé 5" not in prompt
    assert "Non appréciés : écarté" in prompt


def test_rien_du_tout_ne_plante_pas():
    """Contexte et retours absents (None) : un prompt, pas une exception."""
    prompt = main.construire_prompt_actus([], None, None, ARTICLES)
    assert "PROFIL" not in prompt and ARTICLES in prompt


def test_la_route_passe_par_la_fonction():
    """La route bâtit son prompt ici, et nulle part ailleurs : le défaut
    « curieux, ouvert » ne subsiste nulle part dans le code (la docstring
    de la fonction le cite entre guillemets, jamais comme littéral)."""
    source_route = inspect.getsource(main.get_personalized_news)
    assert "construire_prompt_actus(" in source_route
    assert "'curieux, ouvert'" not in inspect.getsource(main)
