"""
Le prompt de comparaison (C-37) : les deux personnes sont désignées par des
marqueurs {A} / {B}, et JAMAIS par un prénom ni un code.

Pourquoi c'est important : le serveur calcule UNE analyse, lue par les deux
appareils. S'il écrit « l'un » ou « A », l'app ne peut pas savoir de qui il
s'agit au moment d'afficher — le lecteur voit alors une phrase qui parle de
deux inconnus. Et si on mettait les prénoms dans le prompt, on enverrait des
identifiants au fournisseur, ce que la promesse « profils anonymes » interdit.

---

The comparison prompt (C-37): both people are named by {A} / {B} markers,
never by a first name or a code.
"""
import json

import main


def test_le_prompt_ne_contient_ni_code_ni_prenom():
    """Le prompt est bâti sur les deux vecteurs, rien d'autre : ni from_code,
    ni to_code, ni quoi que ce soit qui identifie quelqu'un."""
    from_vector = {"vector": {"values.family": 0.8}, "traits": ["famille"], "scores": {}}
    to_vector = {"vector": {"values.family": 0.3}, "traits": ["autonomie"], "scores": {}}
    prompt = main.construire_prompt_comparaison(from_vector, to_vector)
    for identifiant in ("PD-NHQ6-LPGS", "AB-CDEF-GHIJ", "Denis", "Hector"):
        assert identifiant not in prompt


def test_le_prompt_impose_les_marqueurs():
    """La consigne est explicite, et cite les champs concernés."""
    prompt = main.construire_prompt_comparaison({"a": 1}, {"b": 2})
    assert "{A}" in prompt and "{B}" in prompt
    assert "jamais par un prénom" in prompt
    for champ in ("description", "superpower", "tension", "questions_conversation", "message_poetique"):
        assert champ in prompt


def test_une_reponse_conforme_ne_produit_aucune_faute():
    propre = json.dumps({
        "convergences": [{"dimension": "Empathie", "description": "{A} écoute quand {B} parle."}],
        "divergences": [{"dimension": "Rythme", "description": "{A} avance vite, {B} prend le temps."}],
        "superpower": "L'écoute de {A} et la patience de {B}",
        "tension": "Le rythme de {A} face à celui de {B}",
        "questions_conversation": ["Qu'est-ce que {A} admire chez {B} ?"],
        "message_poetique": "{A} et {B}, deux rivières.",
    }, ensure_ascii=False)
    assert main.fautes_de_marqueurs(propre) == []


def test_l_un_et_l_autre_sont_refuses():
    """La tournure exacte qu'on a vue sur l'appareil."""
    fautive = json.dumps({
        "divergences": [{"dimension": "Rythme de vie",
                         "description": "L'un est très actif, l'autre contemplatif."}],
    }, ensure_ascii=False)
    fautes = main.fautes_de_marqueurs(fautive)
    assert len(fautes) == 1 and "Rythme" not in fautes[0].split(":")[0]


def test_un_A_ou_un_B_nu_est_refuse():
    fautive = json.dumps({"message_poetique": "A avance, B contemple."}, ensure_ascii=False)
    assert main.fautes_de_marqueurs(fautive) != []


def test_les_marqueurs_entre_accolades_ne_sont_pas_pris_pour_des_lettres_nues():
    """La garde ne doit pas mordre sur ce qu'elle demande."""
    assert main.fautes_de_marqueurs(json.dumps({"message_poetique": "{A} et {B}."})) == []


def test_les_champs_non_textuels_sont_ignores():
    """Une dimension qui s'appelle « A » n'est pas une faute de rédaction ;
    seuls les champs que la personne LIT sont examinés."""
    corps = json.dumps({
        "convergences": [{"dimension": "A", "score_a": 0.8, "score_b": 0.2,
                          "description": "{A} et {B} se rejoignent."}],
    }, ensure_ascii=False)
    assert main.fautes_de_marqueurs(corps) == []


def test_une_reponse_illisible_ne_leve_pas():
    """Un JSON cassé n'est pas l'affaire de cette fonction : elle rend une
    liste vide et laisse l'appelant décider."""
    assert main.fautes_de_marqueurs("ceci n'est pas du JSON") == []


# ── Frontières de mot : ce qui ressemble à une faute et n'en est pas ──────
# Vérifié le 17/09 sur la comparaison 0F90CED0, où un faux positif était
# soupçonné sur « l'autonomie ». Il n'y en avait pas : le motif porte déjà
# ses frontières de mot. Ces tests le figent.

import pytest


@pytest.mark.parametrize("texte", [
    "{A} apprécie la structure et {B} l'autonomie",
    "{A} et {B} partagent l'unité de vue",
    "L'autonomie de {A} répond à l'unanimité de {B}",
    "{A} lit l'Iliade, {B} l'Odyssée",
])
def test_ces_mots_ne_sont_pas_des_fautes(texte):
    """« l'autonomie », « l'unité », « l'unanimité » commencent comme
    « l'un »/« l'autre » sans en être : la frontière de mot les distingue."""
    assert main.fautes_de_marqueurs(json.dumps({"message_poetique": texte}, ensure_ascii=False)) == []


@pytest.mark.parametrize("texte", [
    "L'un allume, l'autre éteint",
    "l'autre jour, {A} a dit",
    "L'une avance, {B} attend",
    "l'un des deux préfère le calme",
    "{A} est direct, l'autre est nuancé",
])
def test_ces_tournures_sont_bien_des_fautes(texte):
    """Y compris en début de phrase, avec une majuscule."""
    assert main.fautes_de_marqueurs(json.dumps({"message_poetique": texte}, ensure_ascii=False)) != []


def test_l_une_est_attrapee_comme_l_un():
    """« L'une … l'autre » est la même tournure ; elle échappait au motif
    avant le 17/09 (la frontière après « un » butait sur le « e »)."""
    texte = "L'une regarde loin, {B} regarde près"
    assert main.fautes_de_marqueurs(json.dumps({"message_poetique": texte}, ensure_ascii=False)) != []


def test_le_prompt_demande_de_rester_bref():
    """Une analyse coupée ne s'affiche pas : la longueur est un choix."""
    prompt = main.construire_prompt_comparaison({"a": 1}, {"b": 2})
    assert "LONGUEUR" in prompt
    assert "deux ou trois phrases" in prompt and "trois\nquestions" in prompt


def test_la_place_de_l_analyse_vient_de_la_configuration():
    assert main.MODEL_MAX_TOKENS_COMPARE >= 4000


def test_le_journal_cite_le_fragment_fautif_pas_le_debut_du_champ():
    """Un extrait qui ne montre pas ce qu'on reproche envoie chercher au
    mauvais endroit : c'est ce qui a fait croire à un faux positif sur
    « l'autonomie » le 17/09."""
    long = ("{A} apprécie beaucoup la structure et la régularité du quotidien, "
            "tandis que l'autre préfère improviser au fil des envies.")
    fautes = main.fautes_de_marqueurs(json.dumps({"message_poetique": long}, ensure_ascii=False))
    assert len(fautes) == 1
    faute = fautes[0]
    assert "l'autre" in faute
    # Le début du champ ne doit PAS suffire à remplir l'extrait.
    assert "apprécie beaucoup la structure" not in faute
    # Et le motif trouvé est nommé, pour lever tout doute.
    assert "motif :" in faute


def test_le_fragment_cite_tient_dans_une_ligne():
    long = "x" * 300 + " l'un " + "y" * 300
    fautes = main.fautes_de_marqueurs(json.dumps({"message_poetique": long}, ensure_ascii=False))
    assert len(fautes) == 1
    assert len(fautes[0]) < 120, fautes[0]
