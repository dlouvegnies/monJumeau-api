# 17/09/2026 — 0A139396 : deux essais pour rien

| | |
|---|---|
| Fait | Analyse aboutie (`end_turn`, ~3600 caractères, résultat affiché), mais **deux essais** : les deux jugés fautifs, le second gardé. Temps doublé pour l'utilisateur, compteur à **100 %** dès la première analyse. |
| API | `79ea51f` → **`bffa46d`**, **101 tests verts** |
| État | Rien n'est poussé ni déployé. |

---

## Le diagnostic, en une phrase

Ce n'était pas le nombre d'essais : **le validateur reprochait des tournures parfaitement lisibles**, et le prompt poussait le modèle à les contourner.

---

## 1. Le validateur distingue maintenant deux cas

« l'un » et « l'autre » ne sont pas fautifs en soi. Ils le deviennent quand ils **attribuent** quelque chose à quelqu'un — parce que l'app ne saura pas à qui mettre « vous ».

| Tournure | Verdict | Pourquoi |
|---|---|---|
| « Ni l'un ni l'autre ne cède facilement » | **autorisée** | Ne désigne personne : rien à substituer, rien de perdu. |
| « L'un et l'autre avancent à leur rythme » | autorisée | idem |
| « L'un comme l'autre cherchent la clarté » | autorisée | idem |
| « Ils s'ajustent l'un à l'autre » | autorisée | idem |
| « Ils se nourrissent l'un de l'autre » | autorisée | idem |
| « Chacun avance à son pas » | autorisée | idem |
| **« l'un démarre au crépuscule, l'autre à l'aube »** | **faute** | Attribue une action à chacun, sans dire à qui. |
| « {A} structure, l'autre préfère improviser » | faute | Le second membre reste orphelin. |

**Détail qui compte** : les tournures symétriques sont mises de côté en les remplaçant par des **espaces de même longueur**, pas en les supprimant. Les positions de ce qui reste restent justes — donc le fragment cité au journal désigne toujours le bon endroit. Un test le vérifie sur une phrase mixte.

---

## 2. Le prompt montre, au lieu d'interdire

```
  ✗ "l'un démarre au crépuscule, l'autre à l'aube"
  ✓ "{A} démarre au crépuscule, {B} à l'aube"
```

…et, explicitement : *« En revanche, les tournures SYMÉTRIQUES sont les bienvenues, car elles ne désignent personne en particulier […] Écrivez-les naturellement. »*

Une interdiction seule pousse le modèle vers des contorsions ; un exemple l'aligne.

---

## 3. Les deux essais, rejoués

**Je n'ai pas le texte des deux essais** — le log complet n'était pas dans le message. J'ai donc rejoué **les phrases dont je dispose** : les six formes symétriques que tu as citées, plus la phrase attributive de ton exemple.

| | Ancien validateur | Nouveau |
|---|---|---|
| Fautes relevées | **7 sur 7** | **1 sur 7** |

Les six tournures symétriques passent ; seule la phrase attributive est retenue. **Si tu me colles les deux essais du log, je les rejoue tels quels** et je complète ce tableau.

---

## 4. La relance et le compteur

La relance ne se déclenche plus que sur une **faute attributive**, et une seule fois — c'est désormais tout ce que le validateur rend. Le compteur reste en place : c'est lui qui dira si le prompt a porté. Le seuil de ~10 % est au registre (note V3 §29.6 terdecies).

---

## 5. Les mutations

Quatre, rouges puis restaurées, jouées par la commande officielle `bash tests/run.sh` (qui vide le bytecode) :

| Mutation | Effet |
|---|---|
| Les symétriques redeviennent des fautes — **le défaut du jour** | 7 tests rouges |
| La garde devient trop large : une faute attributive passe | 6 rouges |
| L'effacement supprime au lieu de blanchir (positions décalées) | 2 rouges |
| Le prompt reprend l'interdiction sèche, sans exemples | 1 rouge |

Les deux sens sont tenus : le validateur ne reproche plus ce qui est correct, **et** il n'excuse pas ce qui ne l'est pas.

---

## Ce que je retiens

J'avais écrit une règle par interdiction — « jamais l'un, jamais l'autre » — parce que c'était plus simple à vérifier. Mais une règle simple à vérifier n'est pas une règle juste : elle a rejeté deux analyses correctes et fait attendre quelqu'un deux fois plus longtemps. La bonne question n'était pas « ce mot est-il présent ? » mais « l'app saura-t-elle à qui mettre *vous* ? ».
