# Apple A1 — la relance sur faute attributive retirée (comparaison 904E9797)

*17/09/2026 — rapport bref. Rien n'est poussé ni déployé.*

## 1. Ce que le log montre

| Essai | Reproche | Champ | Issue |
|---|---|---|---|
| 1 | « L'un allume… » | `message_poetique` | rejeté, relance |
| 2 | « L'un bâtit… » | `message_poetique` | gardé (deuxième essai, pas de troisième) |

**Un seul reproche par essai, toujours le même champ.** Le reste de l'analyse était conforme dans les deux cas. Sur la journée du 17/09, la relance déclenchée par une faute attributive a échoué **4 fois sur 4** : le modèle refait la même tournure. Le prix payé est le délai — doublé — pour un texte équivalent.

## 2. Les trois corrections

| # | Où | Avant | Après | En clair |
|---|---|---|---|---|
| 1 | `main.py`, `_analyser_comparaison` | une faute attributive relançait l'analyse (une fois) | le JSON valide est **gardé au premier essai**, quelle que soit la rédaction ; le compteur `conservees_avec_fautes` est incrémenté comme avant | On ne fait plus attendre pour rien. |
| 2 | `main.py`, même bloc | — | la relance ne subsiste que pour **JSON illisible** et **`stop_reason == 'max_tokens'`** | Elle ne sert plus qu'à ce qu'elle répare vraiment. |
| 3 | `main.py`, `construire_prompt_comparaison` | la consigne interdisait ; un seul exemple général | un exemple **dédié à `message_poetique`**, placé juste avant la description du champ : ✗ « L'un allume sa lampe quand l'autre s'endort » / ✓ « {A} allume sa lampe quand {B} s'endort » | Le champ qui fautait a son propre modèle. |

**Le compteur ne change pas** : `COMPTEUR_COMPARAISONS` compte toujours *conservées avec fautes / total*, et le seuil de lecture reste ~10 % (registre S-4). Ce qui change, c'est qu'un texte est désormais compté **au premier essai** au lieu du second.

## 3. Un défaut trouvé en chemin

L'exemple JSON du prompt enfreignait lui-même la règle qu'il illustrait :

```
"description": "L'un est très actif, l'autre contemplatif"   ← avant
"description": "{A} est très actif, {B} plus contemplatif"   ← après
```

Un exemple fautif annule la consigne qui l'accompagne. Corrigé, et désormais tenu par un contrôle : toutes les valeurs du JSON montré — hors la ligne « ✗ », qui est le contre-exemple — doivent passer le validateur.

## 4. Preuves

`bash tests/run.sh` (vide `__pycache__` avant de jouer) : **104 tests verts**.

Quatre mutations, chacune appliquée puis restaurée :

| Mutation | Contrôle qui mord |
|---|---|
| M1 — la relance sur faute attributive est réintroduite | `test_une_faute_attributive_ne_declenche_plus_de_relance`, `test_le_compteur_suit_les_analyses_conservees_avec_fautes` |
| M2 — l'exemple dédié au message poétique est retiré du prompt | `test_le_prompt_montre_un_exemple_dedie_au_message_poetique` |
| M3 — l'exemple du prompt redevient attributif | `test_le_prompt_respecte_sa_propre_regle` |
| M4 — le compteur n'est plus incrémenté | les deux contrôles de M1 |

**M3 a d'abord mordu à vide** : écrite trop vite, elle passait le texte sous une clé (`"exemple"`) que le validateur n'inspecte pas — le contrôle ne pouvait pas échouer. Puis, corrigée, elle attrapait `PROFIL A :`, un titre de structure du prompt et non une phrase destinée au lecteur. Le contrôle est maintenant borné au bloc d'exemple JSON. C'est exactement ce à quoi sert la règle « faire échouer chaque nouveau contrôle une fois ».

## 5. Registre

**S-5** inscrit dans la note V3 (§29.6 quaterdecies) : *si le compteur reste au-dessus de ~10 % après ce prompt, exempter `message_poetique` du contrôle attributif plutôt que d'insister.* C'est le seul champ où l'image poétique appelle naturellement la tournure symétrique ; un champ qu'on relance sans effet est un champ qu'on ferait mieux de ne plus vérifier de cette manière.

## 6. Ce qui reste à Denis

| # | Geste | Où |
|---|---|---|
| 1 | Migration Supabase, **puis** déploiement Render | conservation (décision L) |
| 2 | Débloquer les lignes `40731A0C` et `0F90CED0` | requêtes SQL déjà fournies |
| 3 | Gestes A2 4, 5 et 7 | « Zeopy Dev » |
