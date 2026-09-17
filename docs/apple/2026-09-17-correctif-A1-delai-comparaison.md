# 17/09/2026 — Comparaison bloquée en production (40731A0C) : diagnostic et correctif

| | |
|---|---|
| Symptôme | `httpx.ReadTimeout` dans `_appeler_anthropic`, « Task exception was never retrieved ». Ligne restée en `analyzing`, vecteurs non effacés, deux téléphones sondant `/compare/status` sans fin. |
| API | `b643341` → **`ec12191`**, **67 tests verts** |
| App | `ca66330` → ce commit, **532 contrôles verts** |
| État | Rien n'est poussé ni déployé. |

---

## 1. Le délai — **ce n'est pas la régression**

Mesuré sur les deux versions, pas supposé :

| Version | Délai effectif |
|---|---|
| `27562f4` — `call_claude(..., timeout: float = 30.0)`, et `analyze_comparison` n'en passait aucun | **30 s** |
| Mon lot A1 — `call_model(..., timeout: float = 30.0)`, idem | **30 s** |

**Le délai était identique avant et après.** Mon lot ne l'a pas raccourci.

**Ce que mon lot a changé et qui rend la coupure plus probable** : le prompt a gagné la règle des marqueurs (la génération est un peu plus longue), et la relance ajoute un second appel. Mais la cause de fond est plus ancienne : **30 s est trop court pour une génération de 2000 jetons**, et ça l'était déjà avant.

### Ce qui est corrigé

| Variable | Défaut | En clair |
|---|---|---|
| `MODEL_TIMEOUT_SECONDS` | **120** | Combien de temps on attend une génération. |
| `MODEL_TIMEOUT_SECONDS_ANTHROPIC` | = ci-dessus | Par prestataire, si l'un est plus lent. |
| `MODEL_TIMEOUT_SECONDS_MISTRAL` | = ci-dessus | Idem. |
| `MODEL_TIMEOUT_SECONDS_EMBED` | **30** | Vectoriser est rapide : inutile d'attendre deux minutes un échec. |
| `COMPARE_BUDGET_SECONDS` | **300** | Budget total d'une analyse, **relance comprise**. |

Un appel lent coûte une attente ; un appel coupé coûte une comparaison perdue et deux téléphones dans le vide. Le choix est asymétrique, le défaut aussi.

**La relance ne double plus l'attente sans limite** : le budget total borne les deux essais, et la relance est abandonnée s'il reste moins de 20 s — deux personnes patientent au bout du fil.

**Le contrôle** : un test parcourt `model_client.py` et **échoue si un `client.post` ne nomme pas son délai**. C'est ainsi qu'une comparaison meurt en silence : en héritant du défaut d'httpx.

---

## 2. Le filet — rien ne meurt plus en silence

`analyze_comparison` enveloppe désormais tout. **Quelle que soit la cause** — délai dépassé, réponse illisible après relance, base indisponible — la comparaison se referme par `_clore_comparaison_en_echec` :

1. statut **`failed`** ;
2. `from_vector` et `to_vector` à **`null`, dans la même écriture** ;
3. la cause **au journal** ;
4. **un push par côté** : « La comparaison n'a pas pu être réalisée, vous pouvez la relancer. »

Et la tâche de fond est créée avec `add_done_callback(_recuperer_exception)` : plus de « Task exception was never retrieved », et la cause arrive au journal au lieu de se perdre.

*Ce trou est antérieur à mon lot — `analyze_comparison` n'a jamais eu de `try/except`. Mais mon lot l'a rendu plus coûteux : la ligne reste bloquée **avec** ses deux vecteurs, alors que tout le chantier 3 vise à ne pas les garder.*

---

## 3. Côté app — l'écran ne connaissait pas `failed`

**Il ne le gérait pas.** `startPolling` ne traitait que `completed` et `rejected` : sur `failed`, il sondait toutes les 3 secondes un statut qui ne changerait jamais, sans rien afficher.

Corrigé : le sondage s'arrête, l'écran dit « Comparaison interrompue — La comparaison n'a pas pu être réalisée. Vous pouvez la relancer. » (vouvoiement), et propose **« Relancer depuis le réseau »**.

**Quatre contrôles au harnais**, trois mutations rouges puis restaurées : l'écran qui réignore le statut · un message qui tutoie · le bouton qui disparaît.

---

## 4. La ligne 40731A0C — à débloquer maintenant

Dans Supabase → SQL Editor. **Regarder d'abord** :

```sql
select id, status, created_at,
       (from_vector is not null) as vecteur_a_present,
       (to_vector   is not null) as vecteur_b_present
from comparisons
where id = '40731A0C';
```

**Puis, au choix.** La refermer proprement — les deux téléphones verront le message « Comparaison interrompue » dès qu'ils auront la nouvelle version de l'app :

```sql
update comparisons
   set status = 'failed',
       from_vector = null,
       to_vector   = null
 where id = '40731A0C';
```

Ou la supprimer — les deux téléphones cesseront de sonder à la première réponse 404 :

```sql
delete from comparisons where id = '40731A0C';
```

**Je recommande la première** : elle efface les deux vecteurs *et* laisse une trace de ce qui s'est passé.

**Et pour vérifier qu'aucune autre ne traîne :**

```sql
select id, status, created_at,
       (from_vector is not null or to_vector is not null) as vecteurs_encore_la
from comparisons
where status in ('analyzing', 'pending')
order by created_at;
```

---

## 5. Pour déployer

Inchangé par rapport au rapport A1 : **migration Supabase d'abord, puis le serveur**. Les nouvelles variables sont **facultatives** — leurs défauts sont ceux de ce correctif (120 s, 300 s de budget). Côté app, la gestion de `failed` part avec le prochain build.

**Ordre conseillé** : déployer le serveur *avant* de débloquer la ligne, pour que le filet soit en place si l'analyse est relancée.

---

## 6. Ce que je retiens

J'ai repris le délai hérité sans le questionner, parce qu'il « ne changeait rien ». C'était vrai, et insuffisant : déplacer du code est l'occasion de regarder ce qu'on déplace. Un défaut de 30 secondes sur une génération de 2000 jetons n'était pas un choix, c'était un reste — et il attendait son jour.
