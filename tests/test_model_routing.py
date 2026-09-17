"""
Le routage des appels de modèle : prestataire et modèle viennent de la
CONFIGURATION, jamais du code, et un seul module parle aux fournisseurs.

Né du lot A1 (décision R) : avant, chaque route appelait Anthropic
elle-même, avec l'URL et la clé sur place. Personne ne pouvait dire ce qui
partait ni vers qui sans relire tout le fichier.

---

Model-call routing: provider and model come from CONFIGURATION, never from
the code, and a single module talks to providers.
"""
import os
import pathlib
import re

import httpx
import pytest
import respx

import model_client

pytestmark = pytest.mark.asyncio

RACINE = pathlib.Path(__file__).resolve().parent.parent


def test_le_defaut_reproduit_le_comportement_herite(monkeypatch):
    """Sans aucune variable nouvelle, rien ne change : Anthropic, et le
    modèle d'avant ce lot."""
    monkeypatch.delenv("MODEL_PROVIDER_DEFAULT", raising=False)
    monkeypatch.setattr(model_client, "MODEL_PROVIDER_DEFAULT", "anthropic")
    assert model_client.provider_for("capture_extract") == "anthropic"
    assert model_client.model_for("anthropic") == model_client.MODEL_NAME_ANTHROPIC


def test_surcharge_par_usage(monkeypatch):
    """Un usage peut basculer seul, sans toucher aux autres."""
    monkeypatch.setenv("MODEL_PROVIDER_CAPTURE_EXTRACT", "mistral")
    assert model_client.provider_for("capture_extract") == "mistral"
    assert model_client.provider_for("portrait_narrative") == "anthropic"


def test_usage_inconnu_retombe_sur_le_defaut(monkeypatch):
    """Une fonctionnalité nouvelle n'échoue jamais faute de variable."""
    monkeypatch.delenv("MODEL_PROVIDER_CE_QUI_NEXISTE_PAS", raising=False)
    assert model_client.provider_for("ce_qui_nexiste_pas") == "anthropic"
    assert model_client.provider_for("") == "anthropic"
    assert model_client.provider_for(None) == "anthropic"


def test_une_valeur_inconnue_ne_casse_rien(monkeypatch):
    """Une faute de frappe dans la configuration retombe sur Anthropic
    plutôt que d'envoyer les données nulle part."""
    monkeypatch.setenv("MODEL_PROVIDER_PORTRAIT_NARRATIVE", "openai")
    assert model_client.provider_for("portrait_narrative") == "anthropic"


@respx.mock
async def test_anthropic_reste_le_chemin_par_defaut(monkeypatch):
    """Le chemin hérité, inchangé : même URL, même forme de réponse."""
    monkeypatch.setattr(model_client, "MODEL_PROVIDER_DEFAULT", "anthropic")
    route = respx.post(model_client.ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(200, json={
            "content": [{"text": "bonjour"}],
            "usage": {"input_tokens": 3, "output_tokens": 4},
        })
    )
    r = await model_client.call_model(
        purpose="essai", messages=[{"role": "user", "content": "salut"}], max_tokens=10,
    )
    assert route.called
    assert r.status_code == 200
    assert r.json()["content"][0]["text"] == "bonjour"


@respx.mock
async def test_mistral_est_ecrit_et_traduit_vers_la_forme_dAnthropic(monkeypatch):
    """L'adaptateur Mistral existe et rend la MÊME forme : c'est ce qui
    permettra de basculer un usage sans toucher à son point d'appel."""
    monkeypatch.setenv("MODEL_PROVIDER_ESSAI_MISTRAL", "mistral")
    route = respx.post(model_client.MISTRAL_CHAT_URL).mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "réponse de Mistral"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 9},
        })
    )
    r = await model_client.call_model(
        purpose="essai_mistral", messages=[{"role": "user", "content": "salut"}],
        max_tokens=10, system="consigne",
    )
    assert route.called
    envoye = respx.calls.last.request
    assert b'"role": "system"' in envoye.content or b'"role":"system"' in envoye.content
    assert r.status_code == 200
    assert r.json()["content"][0]["text"] == "réponse de Mistral"
    assert r.json()["usage"] == {"input_tokens": 7, "output_tokens": 9}


@respx.mock
async def test_mistral_en_erreur_ne_leve_pas(monkeypatch):
    """Une erreur du fournisseur remonte comme un statut, jamais comme une
    exception : les points d'appel testent déjà `.status_code`."""
    monkeypatch.setenv("MODEL_PROVIDER_ESSAI_ERREUR", "mistral")
    respx.post(model_client.MISTRAL_CHAT_URL).mock(return_value=httpx.Response(500, text="boum"))
    r = await model_client.call_model(
        purpose="essai_erreur", messages=[{"role": "user", "content": "salut"}], max_tokens=10,
    )
    assert r.status_code == 500
    assert r.json() == {}


def test_aucun_fournisseur_nest_nomme_hors_du_module():
    """LE contrôle du lot : une URL de fournisseur, une clé d'API ou un
    ancien `call_claude(` ne peut vivre que dans model_client.py.

    Ce qui l'empêche : qu'une route rouvre un jour un appel direct, et que
    la question « qu'est-ce qui part, et vers qui ? » redevienne sans
    réponse.
    """
    interdits = ["api.anthropic.com", "api.mistral.ai", "x-api-key", "call_claude("]
    autorises = {"model_client.py"}
    fautifs = []
    for chemin in RACINE.rglob("*.py"):
        rel = chemin.relative_to(RACINE).as_posix()
        if rel.startswith(("tests/", "__pycache__/")) or "/__pycache__/" in rel:
            continue
        if rel in autorises:
            continue
        code = chemin.read_text(encoding="utf8")
        for ligne_n, ligne in enumerate(code.split("\n"), 1):
            nue = ligne.strip()
            if nue.startswith("#"):
                continue
            for mot in interdits:
                if mot in ligne:
                    fautifs.append(f"{rel}:{ligne_n} : {mot}")
    assert fautifs == [], fautifs


def test_le_controle_ne_passe_pas_a_vide():
    """Le balayage doit voir de vrais fichiers, sinon il ne prouve rien."""
    fichiers = [c for c in RACINE.rglob("*.py")
                if not c.relative_to(RACINE).as_posix().startswith(("tests/", "__pycache__/"))]
    assert len(fichiers) >= 3
    assert (RACINE / "model_client.py").exists()
    contenu = (RACINE / "model_client.py").read_text(encoding="utf8")
    assert "api.anthropic.com" in contenu and "api.mistral.ai" in contenu
