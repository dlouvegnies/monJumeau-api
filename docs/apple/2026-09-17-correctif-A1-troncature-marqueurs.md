# 17/09/2026 — Comparaison 0F90CED0 : marqueurs et troncature

| | |
|---|---|
| API | `ec12191` → **`2be5967`**, **85 tests verts** |
| App | inchangée |
| État | Rien n'est poussé ni déployé. |

---

## 1. Les marqueurs — **il n'y a pas de faux positif**

Vérifié en exécutant le validateur sur les chaînes elles-mêmes, pas en relisant le motif :

| Texte | Verdict | |
|---|---|---|
| `{A} apprécie la structure et {B} l'autonomie` | **propre** | ton constat 2 est écarté |
| `{A} et {B} partagent l'unité de vue` | propre | |
| `{A} lit l'Iliade, {B} l'Odyssée` | propre | |
| `L'un allume, l'autre éteint` | **faute** | ton constat 1, bien attrapé |
| `l'autre jour, {A} a dit` | **faute** | volontaire : la tournure ne dit pas de qui on parle |

Les motifs portaient déjà leurs frontières de mot (`\bl['’]un\b`), et `\b` après `un` interdit qu'une lettre suive : « l'autonomie » n'a jamais pu être pris pour « l'autre ». **Si le journal a bien listé `questions_conversation[0]`, c'est que le texte réel différait de celui que tu as recopié — envoie-moi la ligne exacte du log et je regarde.** Ce que je peux affirmer : ces formes-là passent, et des tests les figent désormais.

**Une vraie lacune, en revanche** : `L'une … l'autre` échappait au motif — `\bl['’]un\b` bute sur le `e` de « une ». Corrigé en `une?`, avec test et mutation.

---

## 2. La troncature — le compte exact, pas l'hypothèse

| Mesure | Valeur |
|---|---|
| Longueur de la réponse | **≥ 5644 caractères** (position de l'erreur « Unterminated string ») |
| Plafond de jetons de l'époque | **2000** |
| Rapport | **2,82 caractère par jeton** |

Pour du français, un jeton vaut typiquement 2,5 à 3,5 caractères. **2,82 tombe en plein dans cette fourchette** : la réponse a consommé ses 2000 jetons, donc `stop_reason = max_tokens`. L'hypothèse de la troncature est confirmée par le calcul.

*Je n'avais pas le `stop_reason` du log — il n'était pas journalisé. **Il l'est maintenant**, avec la longueur, à chaque essai : la prochaine fois, la cause sera lue et non déduite.*

---

## 3. La racine, et c'est une confusion de ma part

`fautes_de_marqueurs` rend une **liste vide** sur un texte illisible. Je l'avais documenté (« laisse l'appelant décider ») — mais **l'appelant ne décidait pas** : « aucune faute de marqueur » était pris pour « exploitable ». Une réponse tronquée passait donc la vérification et se retrouvait en base.

### Ce qui est corrigé

| # | Correction |
|---|---|
| 1 | **`json.loads` avant toute écriture.** Échec → relance dans le budget, puis le filet (`failed`, vecteurs à null, push des deux côtés). |
| 2 | **`stop_reason == 'max_tokens'` est un échec pour lui-même.** Une troncature ne casse pas toujours le JSON : le modèle peut s'arrêter après une accolade fermante et rendre un objet **valide mais amputé** — sans divergences, sans questions. `stop_reason` est le seul indice fiable. |
| 3 | **`/compare/status` ne fait plus 500.** Un `result` illisible referme la comparaison et le dit, au lieu de planter à chaque sondage. |
| 4 | **La place est un choix** : `MODEL_MAX_TOKENS_COMPARE` (défaut **4000**), et le prompt demande d'être bref — deux ou trois phrases par description, trois questions. |

**Cinq mutations**, rouges puis restaurées : `json.loads` retiré · troncature ignorée · `/compare/status` qui replante · `l'une` invisible · plafond redescendu à 2000.

*Au passage : un cache `__pycache__` périmé masquait deux de ces mutations — elles passaient au vert sur du bytecode d'une version antérieure. Les mutations sont désormais jouées cache vidé. C'est le genre de piège qui fait croire qu'un contrôle mord alors qu'il dort.*

---

## 4. Le cas à connaître pour A5

**Oui, un texte imparfait peut être affiché.** « Une relance puis on garde » veut dire exactement cela : si le second essai respecte le JSON mais écrit encore « l'un / l'autre », le résultat est **conservé et affiché tel quel**.

**La substitution `{A}`/`{B}` ne corrigera pas « l'un / l'autre »** — il n'y a rien à substituer. Trois voies possibles au lot A5, à trancher :

| Voie | En clair |
|---|---|
| Laisser passer | Le lecteur voit « l'un … l'autre » : imparfait, mais compréhensible dans le contexte. |
| Masquer le champ fautif | On n'affiche pas la phrase qui ne dit pas de qui elle parle. |
| Marquer le résultat | Le serveur ajoute un drapeau `redaction_imparfaite`, et l'app choisit. |

Je n'ai pas tranché : ce n'est pas le périmètre de ce correctif.

**Pour 0F90CED0 précisément** : je n'ai pas l'issue de l'essai 2, faute de log conservé. Ce que le code fait désormais est écrit ci-dessus ; ce qu'il a fait ce jour-là, seul ton journal Render le dit.

---

## 5. Débloquer 0F90CED0

```sql
-- Regarder d'abord
select id, status, length(result) as taille_result, created_at
from comparisons where id = '0F90CED0';

-- Refermer proprement
update comparisons
   set status = 'failed', result = null, from_vector = null, to_vector = null
 where id = '0F90CED0';
```

**Et le contrôle sur toutes les lignes dont le `result` n'est pas un JSON valide** — Postgres sait le dire :

```sql
select id, status, length(result) as taille_result, created_at
from comparisons
where result is not null
  and result not in ('')
  and (result::jsonb) is null;   -- lève si invalide : voir la variante ci-dessous
```

Si cette forme échoue (Postgres refuse le cast plutôt que de rendre null), utiliser :

```sql
select id, status, length(result) as taille_result, created_at
from comparisons
where result is not null
  and not (result ~ '^\s*\{[\s\S]*\}\s*$'
           and jsonb_typeof(nullif(result, '')::jsonb) = 'object');
```

Et, plus simplement, repérer les candidats probables — un JSON coupé ne finit pas par `}` :

```sql
select id, status, length(result) as taille_result, right(result, 40) as fin
from comparisons
where result is not null and rtrim(result) not like '%}';
```

**Pour les refermer toutes d'un coup**, une fois la liste vérifiée :

```sql
update comparisons
   set status = 'failed', result = null, from_vector = null, to_vector = null
 where result is not null and rtrim(result) not like '%}';
```

---

## 6. Ce que je retiens

J'ai écrit une fonction qui rend « rien à signaler » sur une entrée qu'elle ne comprend pas, et je l'ai appelée sans distinguer les deux. « Aucune faute » et « je n'ai pas pu regarder » sont deux réponses différentes ; les confondre, c'est prendre le silence pour un accord.
