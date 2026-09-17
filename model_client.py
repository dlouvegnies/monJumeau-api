"""
ZEOPY — model_client.py  (chantier Apple, lot A1 — 17/09/2026)

Le SEUL module qui parle à un fournisseur de modèle de langage.

Pourquoi un module à part : tant que chaque route appelait Anthropic
elle-même, personne ne pouvait répondre à « qu'est-ce qui part, et vers
qui ? » sans relire tout le fichier. Ici, la réponse tient en une liste :
`call_model` pour les textes, `embed_texts` pour les vecteurs. Un test du
dépôt échoue si une URL de fournisseur, une clé d'API ou un ancien
`call_claude(` réapparaît ailleurs.

Le prestataire et le modèle viennent de la CONFIGURATION, jamais du code —
avec, pour chaque `purpose`, la possibilité de surcharger le prestataire.
Les valeurs par défaut reproduisent exactement le comportement d'avant ce
lot : un déploiement sans nouvelle variable ne change rien.

---

ZEOPY — model_client.py  (Apple work, lot A1 — 17/09/2026)

The ONLY module that talks to a language-model provider.

Why a separate module: as long as every route called Anthropic itself,
nobody could answer "what leaves, and to whom?" without re-reading the whole
file. Here the answer is a list: `call_model` for text, `embed_texts` for
vectors. A repository test fails if a provider URL, an API key or an old
`call_claude(` shows up anywhere else.

Provider and model come from CONFIGURATION, never from the code — with a
per-`purpose` provider override. The defaults reproduce exactly what this
lot inherited: a deployment without new variables changes nothing.
"""
import asyncio
import os

import httpx

# ── Configuration ─────────────────────────────────────────────────────────
ANTHROPIC = "anthropic"
MISTRAL = "mistral"

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_EMBED_URL = "https://api.mistral.ai/v1/embeddings"

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

# Défauts : le comportement d'aujourd'hui, à l'identique.
MODEL_PROVIDER_DEFAULT = os.environ.get("MODEL_PROVIDER_DEFAULT", ANTHROPIC)
MODEL_NAME_ANTHROPIC = os.environ.get("MODEL_NAME_ANTHROPIC", "claude-sonnet-4-6")
MODEL_NAME_MISTRAL = os.environ.get("MODEL_NAME_MISTRAL", "mistral-large-latest")
MODEL_NAME_EMBED = os.environ.get("MODEL_NAME_EMBED", "mistral-embed")

# $ par million de jetons (entrée, sortie).
PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
}

_usage_logger = None


def set_usage_logger(fn):
    """Registers who records an API call's cost. Injected rather than
    imported, so this module never depends on the database layer.

    @param fn: async (client_ref, purpose, model, usage) -> None.
    @returns: None.

    ---

    Enregistre qui consigne le coût d'un appel. Injecté plutôt qu'importé,
    pour que ce module ne dépende jamais de la couche base de données.

    @param fn: async (client_ref, purpose, model, usage) -> None.
    @returns: None.
    """
    global _usage_logger
    _usage_logger = fn


def provider_for(purpose: str) -> str:
    """The provider to use for one purpose.

    Read in this order: `MODEL_PROVIDER_<PURPOSE>`, then
    `MODEL_PROVIDER_DEFAULT`, then Anthropic. An unknown purpose simply
    falls back to the default — a new feature never fails for want of a
    variable.

    @param purpose: Feature name, e.g. "capture_extract".
    @returns: 'anthropic' or 'mistral'.

    ---

    Le prestataire à utiliser pour un usage donné.

    Lu dans cet ordre : `MODEL_PROVIDER_<PURPOSE>`, puis
    `MODEL_PROVIDER_DEFAULT`, puis Anthropic. Un usage inconnu retombe
    simplement sur le défaut — une fonctionnalité nouvelle n'échoue jamais
    faute de variable.

    @param purpose: Nom de la fonctionnalité, ex. "capture_extract".
    @returns: 'anthropic' ou 'mistral'.
    """
    par_usage = os.environ.get(f"MODEL_PROVIDER_{(purpose or '').upper()}")
    choisi = (par_usage or MODEL_PROVIDER_DEFAULT or ANTHROPIC).strip().lower()
    return choisi if choisi in (ANTHROPIC, MISTRAL) else ANTHROPIC


def model_for(provider: str) -> str:
    """The model name of a provider, from configuration.

    @param provider: 'anthropic' or 'mistral'.
    @returns: The model name.

    ---

    Le nom de modèle d'un prestataire, depuis la configuration.

    @param provider: 'anthropic' ou 'mistral'.
    @returns: Le nom du modèle.
    """
    return MODEL_NAME_MISTRAL if provider == MISTRAL else MODEL_NAME_ANTHROPIC


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of one call, in dollars. An unpriced model costs zero rather
    than raising: a missing price never breaks an answer in flight.

    @param model: Model name.
    @param input_tokens: Tokens sent.
    @param output_tokens: Tokens received.
    @returns: The cost in dollars.

    ---

    Coût d'un appel, en dollars. Un modèle sans tarif coûte zéro plutôt que
    de lever : un prix manquant ne casse jamais une réponse en cours.

    @param model: Nom du modèle.
    @param input_tokens: Jetons envoyés.
    @param output_tokens: Jetons reçus.
    @returns: Le coût en dollars.
    """
    tarif = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * tarif["input"] + output_tokens * tarif["output"]) / 1_000_000


class ModelResponse:
    """A model's answer, always in Anthropic's shape.

    Call sites read `.status_code` and `.json()["content"][0]["text"]`. The
    Mistral adapter translates into this same shape, so switching provider
    changes nothing at the call sites — which is the whole point of having
    a switch.

    ---

    La réponse d'un modèle, toujours dans la forme d'Anthropic.

    Les points d'appel lisent `.status_code` et
    `.json()["content"][0]["text"]`. L'adaptateur Mistral traduit vers cette
    même forme, si bien que changer de prestataire ne change rien aux points
    d'appel — c'est tout l'intérêt d'avoir un interrupteur.
    """

    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


async def _appeler_anthropic(*, messages, max_tokens, system, model, timeout):
    """Anthropic adapter. Returns the httpx response untouched: the
    behaviour inherited by this lot, byte for byte.

    ---

    Adaptateur Anthropic. Rend la réponse httpx telle quelle : le
    comportement dont ce lot hérite, à l'octet près.
    """
    charge = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system is not None:
        charge["system"] = system
    async with httpx.AsyncClient() as client:
        return await client.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=charge,
            timeout=timeout,
        )


async def _appeler_mistral(*, messages, max_tokens, system, model, timeout):
    """Mistral adapter (chat completions), translated into Anthropic's
    shape. Written and tested, NOT activated: no purpose routes here until
    a quality check per purpose says so.

    ---

    Adaptateur Mistral (chat completions), traduit vers la forme
    d'Anthropic. Écrit et testé, PAS activé : aucun usage n'y est routé
    tant qu'une validation de qualité par usage ne l'a pas dit.
    """
    tours = ([{"role": "system", "content": system}] if system else []) + list(messages)
    async with httpx.AsyncClient() as client:
        brute = await client.post(
            MISTRAL_CHAT_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": model, "max_tokens": max_tokens, "messages": tours},
            timeout=timeout,
        )
    if brute.status_code != 200:
        return ModelResponse(brute.status_code, {}, brute.text)
    corps = brute.json()
    texte = ((corps.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    jetons = corps.get("usage") or {}
    return ModelResponse(200, {
        "content": [{"type": "text", "text": texte}],
        "usage": {
            "input_tokens": jetons.get("prompt_tokens", 0),
            "output_tokens": jetons.get("completion_tokens", 0),
        },
    }, texte)


async def call_model(*, purpose: str, messages, max_tokens, system: str = None,
                     client_ref=None, timeout: float = 30.0):
    """Calls a language model. The single door.

    @param purpose: What the call is for, e.g. "capture_extract". Identifies
        the feature in the cost log, and selects the provider override.
    @param messages: Turns, in Anthropic's shape.
    @param max_tokens: Ceiling on the answer.
    @param system: System instruction, optional.
    @param client_ref: Anonymous caller reference, for the cost log.
    @param timeout: Seconds.
    @returns: A response exposing `.status_code` and `.json()`, always in
        Anthropic's shape.

    ---

    Appelle un modèle de langage. La porte unique.

    @param purpose: Ce à quoi sert l'appel, ex. "capture_extract". Identifie
        la fonctionnalité dans le journal des coûts, et choisit la surcharge
        de prestataire.
    @param messages: Les tours, dans la forme d'Anthropic.
    @param max_tokens: Plafond de la réponse.
    @param system: Consigne système, facultative.
    @param client_ref: Référence anonyme de l'appelant, pour le journal des coûts.
    @param timeout: Secondes.
    @returns: Une réponse exposant `.status_code` et `.json()`, toujours dans
        la forme d'Anthropic.
    """
    prestataire = provider_for(purpose)
    modele = model_for(prestataire)
    adaptateur = _appeler_mistral if prestataire == MISTRAL else _appeler_anthropic
    reponse = await adaptateur(
        messages=messages, max_tokens=max_tokens, system=system,
        model=modele, timeout=timeout,
    )
    if _usage_logger is not None:
        try:
            usage = (reponse.json() or {}).get("usage") or {}
            asyncio.create_task(_usage_logger(client_ref, purpose, modele, usage))
        except Exception as e:
            print(f"[ai_usage] extraction usage échouée ({purpose}): {e}")
    return reponse


async def embed_texts(texts: list) -> list:
    """Turns texts into vectors (Mistral: there is no Anthropic equivalent).
    The model comes from configuration.

    @param texts: The texts to embed.
    @returns: One vector per text, or an empty list on failure.

    ---

    Transforme des textes en vecteurs (Mistral : Anthropic n'a pas
    d'équivalent). Le modèle vient de la configuration.

    @param texts: Les textes à vectoriser.
    @returns: Un vecteur par texte, ou une liste vide en cas d'échec.
    """
    if not texts:
        return []
    try:
        async with httpx.AsyncClient() as client:
            reponse = await client.post(
                MISTRAL_EMBED_URL,
                headers={
                    "Authorization": f"Bearer {MISTRAL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": MODEL_NAME_EMBED, "input": texts, "encoding_format": "float"},
                timeout=30.0,
            )
            corps = reponse.json()
            if "data" not in corps:
                print(f"⚠️ Mistral Embed erreur: {corps}")
                return []
            return [item["embedding"] for item in corps["data"]]
    except Exception as e:
        print(f"❌ Erreur embed_texts: {str(e)}")
        return []
