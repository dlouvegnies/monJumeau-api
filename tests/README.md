# Tests backend Zeopy (`main.py`) — portrait, enrichissement, LLM

## Installation

```bash
pip install pytest pytest-asyncio respx httpx fastapi --break-system-packages
```

## Mise en place

Copier ces 5 fichiers dans un dossier `tests/` à la racine du backend
(au même niveau que `main.py`) :

```
main.py
tests/
  conftest.py
  pytest.ini
  test_extract_json_array.py
  test_call_claude.py
  test_portrait_llm_endpoints.py
```

## Lancer

```bash
cd <racine du backend>
pytest tests/ -v
```

## Périmètre couvert

- `extract_json_array` — parsing JSON tolérant des réponses Claude
- `call_claude` — construction du payload, headers, tolérance aux réponses incomplètes
- `/portrait`, `/portrait-resume` — génération narrative, non-fuite des scores dans le prompt
- `/bloc-context/select`, `/bloc-context/compose` — ranking et composition du contexte
- `/capture/extract` — pipeline d'extraction pour l'enrichissement du portrait, y compris les échecs silencieux volontaires (RFC-0004bis CA-11)

## Volontairement hors périmètre pour l'instant

Tout le reste de `main.py` (jobs Adzuna/France Travail, média TMDB/Spotify,
restos/recettes, news RSS/embeddings, gifts, push, connections, Regard
Croisé) — non prioritaire actuellement. Ces endpoints touchent en plus
Supabase et des API tierces, ce qui demanderait une stratégie de mock
plus lourde (`respx` sur chaque domaine externe) : à traiter dans un
second temps si besoin.

`/portrait` n'a pas de `try/except` autour de `call_claude` contrairement
à `/bloc-context/*` — `test_portrait_returns_502_on_claude_error_status`
documente ce comportement actuel plutôt que de le corriger silencieusement ;
à voir si c'est voulu.
