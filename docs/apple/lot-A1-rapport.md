# Lot A1 — Serveur : porte unique, prompt de comparaison, conservation

| Élément | Valeur |
|---|---|
| Dépôt | `/Users/denislouvegnies/Pilote/monJumeau-api`, `27562f4` → **`590fa2c`**, 4 commits, arbre propre |
| Tests | `python3 -m pytest tests/ -q` → **57 passed** |
| État | **Rien n'est poussé ni déployé.** La migration n'est pas appliquée. |

---

## Préambule — « Métiers compatibles » avec l'interrupteur éteint

**Aucun appel `/jobs` ne part.** `useFocusEffect` appelle `load(false)` (`screens/JobsMatchingScreen.js:257`) ; avec `forceRefresh` faux, la fonction lit le cache et **sort ligne 293** (`return`), c'est-à-dire **avant** l'unique appel `/jobs` de la **ligne 315**. Ce que tu as revu est la présentation déjà calculée, relue depuis `AsyncStorage`.

**Ce n'est donc pas un défaut A2.** Signal visible sans log : l'écran affiche l'état « depuis le cache » (`setFromCache(true)`, ligne 292) et la date de génération.

---

## 1. Fichiers touchés

| Fichier | Ce qui a été fait | En clair |
|---|---|---|
| `model_client.py` **(neuf)** | `call_model`, les deux adaptateurs, `embed_texts`, la configuration, les tarifs | Le seul endroit qui parle à un fournisseur. |
| `main.py` | 14 points d'appel passent de `call_claude` à `call_model`, **sans autre changement** ; le prompt de comparaison devient une fonction ; `fautes_de_marqueurs` ; `/compare/ack` ; purge des vecteurs ; nettoyage étendu | Le gros du lot, mais aucun appel ne change de forme. |
| `migrations/2026-09-17-comparisons-conservation.sql` **(neuf)** | Deux colonnes et un index | À appliquer avant de déployer. |
| `research_endpoint.py` **(retiré)** | Presse-papier mort portant un appel Anthropic direct | Voir l'écart 1. |
| `tests/test_model_client.py` | Renommé depuis `test_call_claude.py` | La fonction ne s'adresse plus à un seul fournisseur. |
| `tests/test_model_routing.py` **(neuf)** | 9 tests | Routage et balayage du dépôt. |
| `tests/test_compare_prompt.py` **(neuf)** | 8 tests | Les marqueurs. |
| `tests/test_comparison_retention.py` **(neuf)** | 8 tests | La conservation. |
| `tests/test_portrait_llm_endpoints.py` | 4 attentes périmées remises à jour | Voir l'écart 2. |

---

## 2. Variables de configuration

**Aucune n'est obligatoire.** Sans elles, le comportement est exactement celui d'avant le lot.

| Variable | Défaut | En clair |
|---|---|---|
| `MODEL_PROVIDER_DEFAULT` | `anthropic` | Qui répond, pour tout ce qui n'est pas surchargé. |
| `MODEL_NAME_ANTHROPIC` | `claude-sonnet-4-6` | Le modèle Anthropic, qui n'est plus écrit dans le code. |
| `MODEL_NAME_MISTRAL` | `mistral-large-latest` | Prêt, mais rien n'y est routé. |
| `MODEL_NAME_EMBED` | `mistral-embed` | Le modèle des vecteurs d'actualités. |
| `MODEL_PROVIDER_<PURPOSE>` | *(absente)* | Bascule **un seul** usage, ex. `MODEL_PROVIDER_CAPTURE_EXTRACT=mistral`. |

Les `purpose` existants : `recommend`, `recipe_simplify_query`, `recipe_translate`, `news_personalize`, `portrait_narrative`, `portrait_resume`, `bloc_context_select`, `bloc_context_compose`, `prompt_reformulate`, `capture_extract`, `bloc_context_send`, `research_synthesis`, `jobs_presentation`, `compare_generate`.

Une valeur inconnue (faute de frappe) **retombe sur Anthropic** plutôt que d'envoyer les données nulle part.

---

## 3. La migration

```bash
psql "$SUPABASE_DB_URL" -f migrations/2026-09-17-comparisons-conservation.sql
```
ou, dans Supabase → SQL Editor, coller le contenu et exécuter. **Ré-exécutable sans risque** (`IF NOT EXISTS`).

Elle ajoute `from_fetched_at` et `to_fetched_at` (timestamptz, null), les commente dans la base même, et crée un index `(status, created_at)` pour que le balayage quotidien ne parcoure pas toute la table.

---

## 4. Les tests

```bash
cd /Users/denislouvegnies/Pilote/monJumeau-api && python3 -m pytest tests/ -q
```

| Fichier | Tests | Ce qu'ils tiennent |
|---|---|---|
| `test_model_routing.py` | 9 | Défaut, surcharge par usage, usage inconnu, valeur inconnue, Anthropic inchangé, Mistral traduit, Mistral en erreur, **balayage du dépôt** et son garde-fou anti-vide |
| `test_compare_prompt.py` | 8 | Ni code ni prénom dans le prompt, consigne présente, réponse conforme, « l'un »/« l'autre » refusés, « A »/« B » nus refusés, marqueurs non confondus, champs non lus ignorés, JSON cassé sans exception |
| `test_comparison_retention.py` | 8 | Vecteurs à null après analyse réussie **et** ratée, un ack, deux ack, idempotence, tiers refusé, balayage quotidien, survie d'une comparaison récente |
| `test_model_client.py` | 5 | La charge utile et la tolérance aux réponses incomplètes |
| `test_portrait_llm_endpoints.py` | 20 | Les endpoints, inchangés |
| `test_extract_json_array.py` | 7 | Inchangé |
| **Total** | **57** | |

---

## 5. Ce que Denis doit faire pour déployer, dans cet ordre

| # | Geste | Pourquoi dans cet ordre |
|---|---|---|
| **1** | **Appliquer la migration** sur Supabase | Le code écrit `from_fetched_at` / `to_fetched_at` ; sans les colonnes, `/compare/ack` échouerait. La migration seule ne casse rien : l'ancien code ignore des colonnes qu'il ne connaît pas. |
| **2** | **Déployer** le serveur (Render) | Aucune variable nouvelle n'est nécessaire. |
| **3** | *(facultatif)* Ajouter les variables du §2 | Seulement pour changer un défaut. Rien à faire aujourd'hui. |

**Rien à faire côté app** : `/compare/ack` n'est pas encore appelée (lot A5). Les lignes disparaîtront donc par le filet des 30 jours en attendant.

---

## 6. La vérification manuelle, après déploiement

Lancer une comparaison entre deux appareils, et lire la table `comparisons` (Supabase → Table Editor) à **trois moments** :

| Moment | Ce qu'on doit voir |
|---|---|
| **Après acceptation des deux** | `from_vector` et `to_vector` **présents**, `status` = `analyzing` |
| **Après l'analyse** (quelques secondes) | `from_vector` et `to_vector` **à `null`**, `result` **présent**, `status` = `completed` |
| **Après deux `ack`** | **La ligne n'existe plus** — à provoquer à la main tant que l'app n'appelle pas la route : `curl -X POST .../compare/ack -H "x-app-secret: …" -d '{"comparison_id":"…","my_code":"…"}'` une fois par code |

Et lire une carte du résultat : les phrases doivent contenir **`{A}` et `{B}`**, pas « l'un » ni « l'autre ». L'app ne les remplace pas encore (lot A5) : c'est normal de voir les accolades.

---

## 7. Écarts par rapport à la consigne

| # | Écart | Pourquoi |
|---|---|---|
| 1 | **`research_endpoint.py` retiré** | Le balayage du dépôt a mordu dès sa naissance : ce fichier portait un appel Anthropic **direct**, clé comprise, que mon audit d'hier n'avait pas relevé. Il est **inerte** — un presse-papier (« À coller dans main.py »), jamais importé, et qui ne s'importerait même pas (`app`, `BaseModel`, `verify_secret` non définis). Le `/research` vivant est `main.py:3218`. **Aucune route n'est supprimée** ; le fichier reste dans l'historique git. |
| 2 | **4 tests réparés avant de commencer** | La base `27562f4` était **rouge** : quatre tests figeaient la forme entière de `/capture/extract`, qui rend `method` et `status` depuis le lot 2b. Avec une base rouge, on ne peut pas dire si un changement casse quelque chose. |
| 3 | **`call_claude` a disparu, sans alias** | La consigne l'autorisait « le temps du lot ». Les 14 points d'appel passent sans changer d'arguments : un alias n'aurait servi à rien et aurait affaibli le balayage. |
| 4 | **Le prompt est devenu une fonction** | `construire_prompt_comparaison(from_vector, to_vector)` : sa signature dit ce qu'elle prend — les deux vecteurs et **rien d'autre**. C'est ce qui rend testable « aucun code ni prénom n'y entre ». |
| 5 | **Un statut `failed` apparaît** | Quand l'analyse ne rend rien d'exploitable, la ligne passe à `failed` et les vecteurs partent. Sans cela, un échec les aurait gardés pour toujours — exactement le défaut qu'on corrige. `/compare/status` ne s'en trouve pas changé : il rend `status` tel quel, et l'app traite déjà tout ce qui n'est pas `completed` comme « pas encore ». |
| 6 | **`embed_texts` a déménagé** | La consigne dit qu'il « reste ». Il reste, mais dans `model_client.py` : il porte l'URL de Mistral, que le balayage interdit ailleurs. Son modèle vient désormais de la configuration, comme demandé. |

---

## 8. Ce qui n'a pas été fait, volontairement

Pas de bascule vers Mistral (l'adaptateur existe, **aucun usage n'y est routé**). Aucune route supprimée. Aucun autre prompt touché. `/compare/status` inchangé.
