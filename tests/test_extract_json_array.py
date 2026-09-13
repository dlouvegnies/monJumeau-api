"""
extract_json_array est le point de passage de TOUS les endpoints qui
attendent un tableau JSON de Claude (bloc-context/select, capture/extract).
Une régression ici casse silencieusement plusieurs fonctionnalités à la fois.
"""
import pytest

from main import extract_json_array


def test_parses_clean_json_array():
    raw = '[{"a": 1}, {"a": 2}]'
    assert extract_json_array(raw) == [{"a": 1}, {"a": 2}]


def test_strips_markdown_code_fences():
    raw = '```json\n[{"a": 1}]\n```'
    assert extract_json_array(raw) == [{"a": 1}]


def test_recovers_array_surrounded_by_prose():
    # Le cas réel qui a motivé cette fonction : Claude ajoute une phrase
    # malgré la consigne "réponds uniquement avec le tableau JSON".
    raw = 'Voici le résultat : [{"a": 1}] — voilà ce que je trouve.'
    assert extract_json_array(raw) == [{"a": 1}]


def test_raises_on_non_array_json():
    with pytest.raises(ValueError):
        extract_json_array('{"a": 1}')  # objet, pas tableau


def test_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json_array("ceci n'est pas du JSON du tout")


def test_raises_when_bracketed_content_is_invalid_json():
    # Un `[...]` présent mais mal formé (quotes simples) ne doit pas
    # planter autrement qu'avec le ValueError attendu par les appelants.
    with pytest.raises(ValueError):
        extract_json_array("[{'a': 1}]")


def test_empty_array_is_valid():
    assert extract_json_array("[]") == []
