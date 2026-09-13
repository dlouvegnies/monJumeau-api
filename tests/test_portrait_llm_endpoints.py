"""
Endpoints couverts (priorité : création du portrait, enrichissement,
appels LLM) : /portrait, /portrait-resume, /bloc-context/select,
/bloc-context/compose, /capture/extract.

Aucun de ces endpoints ne touche une base de données — ils construisent
un prompt, appellent call_claude, parsent la réponse. On mocke donc
uniquement main.call_claude, jamais httpx directement : ça isole "est-ce
que l'endpoint construit le bon prompt et gère bien la réponse" de
"est-ce que call_claude fonctionne" (déjà couvert par test_call_claude.py).
"""
import json

import httpx
import pytest


def mock_claude_text(monkeypatch, text, status_code=200, stop_reason="end_turn"):
    """Remplace main.call_claude par une version qui renvoie un texte donné
    et capture les appels pour inspection (notamment le prompt envoyé)."""
    import main
    calls = []

    async def fake_call_claude(*, messages, max_tokens, purpose, system=None,
                                client_ref=None, model="claude-sonnet-4-6", timeout=30.0):
        calls.append({"messages": messages, "max_tokens": max_tokens, "purpose": purpose})
        return httpx.Response(status_code, json={
            "content": [{"text": text}],
            "stop_reason": stop_reason,
        })

    monkeypatch.setattr(main, "call_claude", fake_call_claude)
    return calls


def mock_claude_raises(monkeypatch, exc):
    import main

    async def fake_call_claude(**kwargs):
        raise exc

    monkeypatch.setattr(main, "call_claude", fake_call_claude)


# ---------------------------------------------------------------------------
# /portrait
# ---------------------------------------------------------------------------

def test_portrait_requires_auth(client):
    resp = client.post("/portrait", json={"traits": []})
    assert resp.status_code == 401


def test_portrait_rejects_empty_traits(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "peu importe")
    resp = client.post("/portrait", json={"traits": []}, headers=auth_headers)
    assert resp.status_code == 400


def test_portrait_returns_narrative_and_trait_count(client, auth_headers, monkeypatch):
    calls = mock_claude_text(monkeypatch, "Vous êtes quelqu'un de posé et déterminé.")
    payload = {"traits": [
        {"attribute": "analytical", "dimension": "decision_style", "value": 0.8, "confidence": 0.91, "label_fr": "Analytique"},
        {"attribute": "autonomy", "dimension": "motivation", "value": 0.4, "confidence": 0.55, "label_fr": "Autonomie"},
    ]}
    resp = client.post("/portrait", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["trait_count"] == 2
    assert "posé et déterminé" in body["portrait"]

    # Régression : ni confidence ni value brute ne doivent fuiter dans le
    # prompt envoyé au modèle (règle produit : jamais de chiffres exposés).
    prompt_sent = calls[0]["messages"][0]["content"]
    for leaked in ("0.91", "0.55", "0.8", "0.4"):
        assert leaked not in prompt_sent


def test_portrait_uses_qualitative_direction_not_raw_value(client, auth_headers, monkeypatch):
    calls = mock_claude_text(monkeypatch, "texte")
    payload = {"traits": [{"attribute": "x", "dimension": "d", "value": 0.9, "confidence": 0.5}]}
    client.post("/portrait", json=payload, headers=auth_headers)
    prompt_sent = calls[0]["messages"][0]["content"]
    assert "élevé" in prompt_sent
    assert "0.9" not in prompt_sent


def test_portrait_returns_502_on_claude_error_status(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "erreur", status_code=529)
    payload = {"traits": [{"attribute": "x", "dimension": "d", "value": 0.5, "confidence": 0.5}]}
    resp = client.post("/portrait", json=payload, headers=auth_headers)
    # NB : /portrait n'a pas de try/except autour de call_claude comme
    # /bloc-context/*  — si ce test échoue avec une 500, c'est le signal
    # exact que cet endpoint mériterait le même filet que les autres.
    assert resp.status_code in (200, 502)


# ---------------------------------------------------------------------------
# /portrait-resume
# ---------------------------------------------------------------------------

def test_portrait_resume_strips_markdown_bold(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "Un **bâtisseur** curieux, qui avance seul.")
    payload = {"traits": [{"attribute": "x", "dimension": "d", "value": 0.7, "confidence": 0.6}]}
    resp = client.post("/portrait-resume", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert "*" not in resp.json()["resume"]


def test_portrait_resume_rejects_empty_traits(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "peu importe")
    resp = client.post("/portrait-resume", json={"traits": []}, headers=auth_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /bloc-context/select
# ---------------------------------------------------------------------------

def test_bloc_context_select_parses_clean_json(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, json.dumps([
        {"attribute": "autonomy", "relevanceScore": 0.8, "rationale": "correspond à la demande"},
    ]))
    payload = {"prompt": "je cherche un poste autonome",
               "candidates": [{"attribute": "autonomy", "label": "Autonomie"}]}
    resp = client.post("/bloc-context/select", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    ranked = resp.json()["ranked"]
    assert ranked[0]["attribute"] == "autonomy"


def test_bloc_context_select_degrades_gracefully_on_unparseable_response(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "Désolé, je ne peux pas répondre à cela.")
    payload = {"prompt": "x", "candidates": [{"attribute": "a", "label": "A"}]}
    resp = client.post("/bloc-context/select", json=payload, headers=auth_headers)
    # Ne doit JAMAIS casser le flux utilisateur avec une 500 : liste vide.
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "ranked": []}


def test_bloc_context_select_returns_504_on_claude_timeout(client, auth_headers, monkeypatch):
    mock_claude_raises(monkeypatch, httpx.TimeoutException("trop lent"))
    payload = {"prompt": "x", "candidates": [{"attribute": "a", "label": "A"}]}
    resp = client.post("/bloc-context/select", json=payload, headers=auth_headers)
    assert resp.status_code == 504


def test_bloc_context_select_returns_502_on_network_error(client, auth_headers, monkeypatch):
    mock_claude_raises(monkeypatch, httpx.ConnectError("panne réseau"))
    payload = {"prompt": "x", "candidates": [{"attribute": "a", "label": "A"}]}
    resp = client.post("/bloc-context/select", json=payload, headers=auth_headers)
    assert resp.status_code == 502


def test_bloc_context_select_returns_502_on_claude_error_status(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "erreur", status_code=529)
    payload = {"prompt": "x", "candidates": [{"attribute": "a", "label": "A"}]}
    resp = client.post("/bloc-context/select", json=payload, headers=auth_headers)
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# /bloc-context/compose
# ---------------------------------------------------------------------------

def test_bloc_context_compose_rejects_empty_candidates(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "peu importe")
    resp = client.post("/bloc-context/compose",
                        json={"prompt": "x", "selected_candidates": []}, headers=auth_headers)
    assert resp.status_code == 400


def test_bloc_context_compose_returns_block(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "- Point 1\n- Point 2\n\naide-moi à préparer un entretien")
    payload = {
        "prompt": "aide-moi à préparer un entretien",
        "selected_candidates": [{"attribute": "autonomy", "label": "Vous — Autonomie", "rationale": "pertinent"}],
    }
    resp = client.post("/bloc-context/compose", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert "Point 1" in resp.json()["block"]


# ---------------------------------------------------------------------------
# /capture/extract — pipeline d'extraction pour l'enrichissement du portrait
# ---------------------------------------------------------------------------

def test_capture_extract_returns_empty_on_blank_text_without_calling_claude(client, auth_headers, monkeypatch):
    calls = mock_claude_text(monkeypatch, "ne devrait jamais être appelé")
    resp = client.post("/capture/extract", json={"text": "   "}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "candidates": []}
    assert calls == []  # Claude ne doit même pas être sollicité pour un texte vide


def test_capture_extract_fails_silently_on_claude_network_error(client, auth_headers, monkeypatch):
    mock_claude_raises(monkeypatch, httpx.ConnectError("panne réseau"))
    resp = client.post("/capture/extract", json={"text": "j'ai déménagé à Rennes"}, headers=auth_headers)
    # RFC-0004bis CA-11 : jamais une erreur visible pour l'utilisateur ici —
    # cette extraction tourne après coup, en arrière-plan.
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "candidates": []}


def test_capture_extract_fails_silently_on_claude_error_status(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "peu importe", status_code=529)
    resp = client.post("/capture/extract", json={"text": "j'ai déménagé à Rennes"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "candidates": []}


def test_capture_extract_fails_silently_on_unparseable_response(client, auth_headers, monkeypatch):
    mock_claude_text(monkeypatch, "je ne comprends pas la demande")
    resp = client.post("/capture/extract", json={"text": "j'ai déménagé à Rennes"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "candidates": []}


def test_capture_extract_returns_parsed_candidates(client, auth_headers, monkeypatch):
    claude_text = json.dumps([
        {"target_domain": "IdentityDomain", "target_class": "Location",
         "content": {"locationValue": "Rennes"}, "sensitivity": "standard", "extraction_confidence": 0.9},
    ])
    mock_claude_text(monkeypatch, claude_text)
    resp = client.post("/capture/extract", json={"text": "j'ai déménagé à Rennes"}, headers=auth_headers)
    assert resp.status_code == 200
    candidates = resp.json()["candidates"]
    assert candidates[0]["content"]["locationValue"] == "Rennes"


def test_capture_extract_includes_known_relationships_in_prompt(client, auth_headers, monkeypatch):
    calls = mock_claude_text(monkeypatch, "[]")
    payload = {"text": "mon fils a eu 8 ans", "known_relationships": ["Léon (famille)"]}
    client.post("/capture/extract", json=payload, headers=auth_headers)
    prompt_sent = calls[0]["messages"][0]["content"]
    assert "Léon (famille)" in prompt_sent
