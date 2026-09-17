"""
call_model est la SEULE porte vers un fournisseur de modèle — tous les
endpoints (portrait, bloc-context, capture/extract, research, jobs...)
passent par elle. On teste ici la construction de la charge utile, le
routage par prestataire et la tolérance aux réponses incomplètes, sans
dépendre d'un vrai réseau (respx intercepte httpx).

Renommé de test_call_claude.py au lot A1 : la fonction ne s'adresse plus à
un seul fournisseur.
"""
import json

import httpx
import pytest
import respx

import main
import model_client

pytestmark = pytest.mark.asyncio

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


@respx.mock
async def test_sends_expected_payload_shape():
    route = respx.post(ANTHROPIC_URL).mock(
        return_value=httpx.Response(200, json={
            "content": [{"text": "bonjour"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        })
    )

    response = await main.call_model(
        messages=[{"role": "user", "content": "salut"}],
        max_tokens=42,
        purpose="test_purpose",
    )

    assert response.status_code == 200
    payload = json.loads(route.calls[0].request.content)
    assert payload["model"] == "claude-sonnet-4-6"
    assert payload["max_tokens"] == 42
    assert payload["messages"] == [{"role": "user", "content": "salut"}]
    assert "system" not in payload  # absent quand non fourni — pas None, absent


@respx.mock
async def test_includes_system_prompt_when_provided():
    route = respx.post(ANTHROPIC_URL).mock(
        return_value=httpx.Response(200, json={"content": [{"text": "ok"}]})
    )
    await main.call_model(
        messages=[{"role": "user", "content": "x"}],
        max_tokens=10,
        purpose="test_purpose",
        system="Tu es un assistant.",
    )
    payload = json.loads(route.calls[0].request.content)
    assert payload["system"] == "Tu es un assistant."


@respx.mock
async def test_sends_required_headers():
    route = respx.post(ANTHROPIC_URL).mock(
        return_value=httpx.Response(200, json={"content": [{"text": "ok"}]})
    )
    await main.call_model(
        messages=[{"role": "user", "content": "x"}], max_tokens=10, purpose="p",
    )
    sent_headers = route.calls[0].request.headers
    assert sent_headers["anthropic-version"] == "2023-06-01"
    assert "x-api-key" in sent_headers


@respx.mock
async def test_tolerates_response_without_usage_field():
    """log_ai_usage ne doit jamais faire planter call_claude, même si la
    réponse Claude n'a pas de clé 'usage' (ex. réponse d'erreur)."""
    respx.post(ANTHROPIC_URL).mock(
        return_value=httpx.Response(200, json={"content": [{"text": "ok"}]})
    )
    response = await main.call_model(
        messages=[{"role": "user", "content": "x"}], max_tokens=10, purpose="p",
    )
    assert response.status_code == 200


@respx.mock
async def test_propagates_non_200_status_without_raising():
    """call_claude renvoie la réponse telle quelle même en erreur — c'est
    aux appelants de décider (voir test_portrait_llm_endpoints.py)."""
    respx.post(ANTHROPIC_URL).mock(
        return_value=httpx.Response(529, json={"error": "overloaded"})
    )
    response = await main.call_model(
        messages=[{"role": "user", "content": "x"}], max_tokens=10, purpose="p",
    )
    assert response.status_code == 529
