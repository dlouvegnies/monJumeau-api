# Lot A5 — Textes natifs, comparaison côté app, build

*18/09/2026 — dépôt app (8 commits) et dépôt API (3 commits). Harnais vert : **802 contrôles**, 24 harnais. Tests API : **112 verts**. **Rien n'est poussé, aucun build lancé, le numéro de build n'a pas bougé.***

> **Aucun `eas build`, `eas submit` ni `eas update` n'a été exécuté.** Seul `npx expo prebuild` a tourné, en local, pour vérifier les Info.plist. Le build vous revient, après le lot A3 bis.

---

## 1. Ce que le lot change, en une page

| # | Avant | Après | En clair |
|---|---|---|---|
| 1 | Les autorisations ne parlaient que de dictée | Elles disent ce que **devient** le texte obtenu | La personne ne pouvait pas savoir, au moment où elle accorde, que ses mots nourrissent autre chose. |
| 2 | Le résultat d'une comparaison affichait `{A}` et `{B}` | Les marqueurs deviennent **le pseudo du lecteur** et l'alias du proche, sur l'appareil | Le serveur ne connaît pas les noms et n'a pas le droit de les recevoir. Un nom s'accorde avec les verbes ; « vous » non. |
| 3 | Le serveur gardait la ligne après lecture | Le téléphone lui dit qu'il peut oublier (`/compare/ack`) | Cette ligne porte les mesures de **deux** personnes. |
| 4 | Refuser une demande était impossible sans accord IA | `/compare/decline` — aucune mesure, aucune IA | La demande expirait seule au bout de 24 h, faute de pouvoir dire non. |
| 5 | Version 1.0.0, build 16 | **3.1.0, build 17** | Le numéro montré à Apple ne disait pas où en était le produit. |
| 6 | Un refus laissait les mesures sur le serveur | Le refus les **efface**, dans le même ordre que le statut | Vérifié en base sur la ligne `E7BA15D6` : `from_vector` survivait au refus. |
| 7 | L'avis IA s'affichait deux fois sur Proches | **Un seul**, en tête d'écran | Un avis qui se répète se lit comme deux problèmes. |

---

## 2. Les textes d'autorisation (§1)

Les deux chaînes gagnent la même phrase :

> **Le texte obtenu est ensuite analysé, avec votre accord, pour alimenter votre portrait.**

`speechRecognitionPermission` dit maintenant « **exclusivement** sur votre appareil », comme sa jumelle — elle disait « entièrement ».

### Vérifié dans l'Info.plist généré

`npx expo prebuild --clean --platform ios`, puis lecture du fichier produit :

| Clé | Ce qu'on y lit |
|---|---|
| `NSMicrophoneUsageDescription` | le texte complet, **avec** la phrase |
| `NSSpeechRecognitionUsageDescription` | idem |
| `CFBundleShortVersionString` | `3.1.0` |
| `CFBundleVersion` | `17` |

`ios/` et `android/` sont ignorés par git : l'arbre reste propre après le prebuild.

### Android : rien à faire, et pourquoi

Le plugin déclare bien la permission (`android/app/src/main/AndroidManifest.xml:4` → `RECORD_AUDIO`), mais il **n'expose aucune chaîne d'explication** : ses seules options sont `microphonePermission`, `speechRecognitionPermission` et `androidSpeechServicePackages` (`node_modules/expo-speech-recognition/app.plugin.js:67-69`). La condition « si le plugin l'expose » n'est donc pas remplie.

À savoir pour plus tard : Android n'a **pas** d'équivalent des chaînes d'Info.plist — le système affiche un texte générique, et toute explication doit être montrée par l'app *avant* de demander. Ce serait un ajout d'écran, pas un texte de configuration. **Au registre (S-17)** si Android revient à l'ordre du jour.

**Changement natif** : ces textes ne partent **pas** par une mise à jour OTA. Ils demandent un build. `runtimeVersion` suit `appVersion`, donc passer en 3.1.0 coupe aussi les OTA de la 1.0.0 — voulu.

---

## 3. La comparaison côté app (§2)

### a. `{A}` et `{B}` deviennent des noms

À un seul endroit : `services/comparisonResult.js`, au même endroit que l'orientation des scores et **sur la même source** (`comparisons.initiated_by_me`) — pour qu'un résultat relu des mois plus tard dise encore la même chose.

| Côté | `{A}` | `{B}` |
|---|---|---|
| Lecteur = initiateur | **son pseudo** | alias de la connexion |
| Lecteur = répondant | alias de la connexion | **son pseudo** |
| Alias inconnu | — | **« votre proche »**, jamais « Inconnu » dans une phrase rédigée, jamais le code |
| **Pseudo vide** | — | **rien n'est substitué** : l'écran demande d'abord (voir ci-dessous) |

La majuscule est mise quand un marqueur ouvre une phrase. Un texte sans marqueur ressort **identique**. Un « l'un / l'autre » résiduel est **laissé tel quel** : le réécrire reviendrait à deviner de qui le modèle parlait.

**Dix-neuf contrôles**, dont les quatre demandés, les deux cas (pseudo renseigné / pseudo vide), et deux qui tiennent la promesse de confidentialité : le code de l'autre n'apparaît jamais dans le texte rendu, et **le pseudo n'entre dans aucun corps de requête**.

**Le pseudo ne quitte pas l'appareil.** C'est la raison d'être des marqueurs : le serveur écrit `{A}` et `{B}` précisément pour ne pas avoir à connaître les noms. Ce changement n'ajoute aucun envoi — un contrôle balaie `screens/`, `services/` et `utils/` pour le prouver, et il reste vrai après la correction.

**Si le pseudo est vide** : l'écran du résultat demande **une seule fois** « Comment veux-tu être nommé(e) dans ce texte ? », enregistre la réponse dans le contexte, puis affiche. Pas de repli silencieux sur « vous » ou « Toi » : un mot de remplacement se figerait dans toutes les phrases du texte.

### b. L'accusé de réception

**Où le résultat est enregistré, et pourquoi là** : dans `comparisons.result` (`database/db.js#updateComparisonStatus`). Ce n'est pas une assertion sur la personne — c'est un objet **partagé entre deux portraits** — donc il ne passe pas par le journal. La table n'est **pas dérivée** : elle survit à un rejeu, et la sauvegarde l'emporte. Le résultat est donc à l'abri **avant** qu'on demande au serveur d'oublier le sien.

**L'ordre, et il compte** :

| # | Geste | Pourquoi dans cet ordre |
|---|---|---|
| 1 | Arrêter de sonder | Ce qui suit rend la question sans objet |
| 2 | Enregistrer en local | Si l'app tombe ici, le résultat est perdu — mais il est encore chez le serveur |
| 3 | `POST /compare/ack` | Le serveur peut oublier : le résultat est à l'abri |

**Si l'ack échoue** : il est noté, et rejoué au **prochain démarrage**, une passe. Jamais en boucle dans la session — une file qui se relance sans fin transforme une panne de réseau en batterie vide, et le serveur a de toute façon son propre ménage (30 jours, décision L).

**Plus aucun `/compare/status` une fois le résultat local** : le sondage s'arrête, et rouvrir une comparaison terminée n'interroge plus rien. Sans cette garde, on sondait une ligne que le serveur venait justement d'effacer. Un contrôle vérifie qu'un **seul** endroit de l'app interroge cette route.

### c. Les deux phrases

Dans `CONSENT_TEXTS`, **bloc qui tutoie** (celui de l'avis A4), avec le même commentaire : elles sont lues **dans un écran**, où l'app tutoie, alors que la fenêtre de consentement et les Réglages sont des textes système et vouvoient.

| Où | Phrase |
|---|---|
| Sous « Accepter » (demande reçue) | « En acceptant, les mesures de ton portrait sont envoyées à Anthropic pour l'analyse. Aucun nom n'est transmis. » |
| Dans la demande d'envoi | « Ton proche devra accepter ; vos mesures ne partent qu'à ce moment-là. » |

Elles disent ce qui part **avant** le geste, pas après.

### d. Refuser sans accord (S-11)

`POST /compare/decline {comparison_id, my_code}` — aucun vecteur, aucun appel de modèle. Idempotente comme l'ack : refuser deux fois ne change rien, refuser une ligne déjà partie répond succès. Les deux côtés peuvent l'appeler (celui qui a demandé peut se raviser).

Côté app, « Refuser » y est aiguillé **avant** la garde d'accord — c'est ce qui fait qu'il marche sans accord IA. Un contrôle vérifie que ce chemin n'appelle que cette route, n'envoie aucun vecteur, et ne dépend pas de `avisIA`.

### e. Routes sans IA — pour le registre App Privacy (A6)

`AI_ROUTES`, `AI_ROUTES_EXCLUDED` et leurs descriptions sont **inchangés**. La confrontation liste ↔ serveur reste verte sans modification.

| Route | Ce qui part | IA ? | Pourquoi ni dans la liste, ni dans les exclusions |
|---|---|---|---|
| `/compare/request` | deux codes | non | Aucune donnée du portrait |
| `/compare/ack` | l'identifiant de comparaison, le code | non | Dit au serveur d'oublier |
| `/compare/decline` | l'identifiant de comparaison, le code | non | Dit non, sans rien envoyer |
| `/compare/status/{id}` | rien (lecture) | non | Relève le résultat déjà calculé |

`AI_ROUTES_EXCLUDED` ne couvre que les routes **qui font appeler une IA** et qu'on a décidé de ne pas verrouiller (sa docstring le dit). Ces quatre-là n'en appellent aucune : elles n'y ont pas leur place. **À reprendre tel quel dans le registre App Privacy d'A6.**

---

## 4. Ce que les gestes ont trouvé (18/09, sur Zeopy Dev avec l'iPad)

**Les gestes 3, 4 et 5 sont passés.** Deux ack observés puis plus aucun `/compare/status` · résultat intact après redémarrage · « Accepter » sans accord n'envoie rien · « Refuser » appelle bien `/compare/decline` et la ligne passe à `rejected`. **Les gestes 1 et 2 (migration TestFlight, fenêtres micro) attendent le build.**

Cinq corrections, toutes faites.

### É-1 — la substitution ne conjuguait pas : **tranché, issue (a)**

Constaté sur de vraies phrases : « **Vous allume sa lampe quand IPAD_M5 éteint la sienne** », « **vous s'allume le soir** ». Le modèle écrit à la troisième personne ; un pronom de politesse ne s'accorde pas avec elle, un nom si.

Le lecteur est nommé par son **pseudo**, lu localement. Un seul endroit, dans `services/comparisonResult.js`. Le contrôle qui affirmait « Vous est très actif » est remplacé par les deux cas demandés.

### Correction 2 — le même lecteur nommé deux fois différemment

Il était « **Vous** » dans le verbatim et « **Toi** » sous son archétype, à dix centimètres d'écart. Un seul nom désormais, depuis la **même source** (`view.monNom`) : verbatim, archétype, légende du graphique et libellés de barres.

### Correction 3 — les libellés, et une nuance qui compte

| Avant | Après | Pourquoi |
|---|---|---|
| `VOS ARCHÉTYPES` | `VOS DEUX ARCHÉTYPES` | Lève l'ambiguïté |
| `Ensemble vous êtes` | `Ensemble, vous êtes tous les deux` | Idem |
| `Ces questions sont faites pour vous !` | `Ces questions sont faites pour vous deux !` | Idem |
| `Toi` (sous l'archétype) | le **pseudo** | Correction 2 |
| `Toi` (légende du graphique) | le **pseudo** | Idem |
| `` `Toi vs ${alias}` `` (deux barres) | `` `${pseudo} vs ${alias}` `` | Idem |

**La nuance, et je la signale plutôt que de l'appliquer en silence** : ces trois libellés n'étaient **pas** du vouvoiement. Le « vous » y est **pluriel** — les archétypes de vous **deux** — et un pluriel reste correct quand on tutoie quelqu'un : « toi et Hector, **vous** êtes ». Écrire « TES ARCHÉTYPES » pour deux personnes serait fautif.

Le vrai défaut était donc l'**ambiguïté** : rien ne distinguait le pluriel de la politesse, et l'écran se lisait comme s'il vouvoyait. Les libellés lèvent cette ambiguïté sans écrire de français fautif. Un contrôle exige que **tout « vous » restant soit explicitement dit à deux**.

Le reste de l'écran a été passé en revue, libellé par libellé : « Comparaison », « Score de compatibilité », « Super-pouvoir », « Tension créative », « Partager cette comparaison » — aucun ne vouvoie.

### D-1 — l'avis IA s'affichait deux fois

Sur « Mon réseau de jumeaux », le même message et le même bouton apparaissaient sous **« Demandes de comparaison reçues »** *et* sous **« Les connexions »**. Un avis qui se répète se lit comme deux problèmes différents.

**Un seul avis, en tête d'écran** : c'est la comparaison, entière, qui demande l'accord — pas telle ou telle section.

**Les onze autres écrans d'A4 ont été comptés**, un par un :

| Écran | Avis montés |
|---|---|
| Explore · Chat · Parler à une IA · Portrait · Portrait narratif · Métiers · Recherche · Bloc de contexte · Actualités · Recommandations · Édition de thème · Regard Croisé | **1 chacun** |
| **Proches** | **2 → 1** |

Un contrôle compte les occurrences sur chacun.

### D-2 — les mesures survivaient au refus

Vérifié en base : la ligne `E7BA15D6`, passée à `rejected`, portait encore son `from_vector`. Les mesures d'un portrait dormaient sur le serveur alors que l'autre personne avait dit non.

| Point | Ce qui a été fait |
|---|---|
| Un seul `UPDATE` | Le statut **et** les deux vecteurs, ensemble. En deux ordres, une panne entre les deux laisserait exactement la ligne qu'on corrige. |
| La ligne n'est pas supprimée | L'autre appareil doit pouvoir lire `rejected` pour dire « Demande refusée » plutôt que de laisser croire à une expiration. |
| Pas d'ack sur le refus | Il n'y a pas de résultat à transmettre, et en attendre un obligerait à garder les vecteurs plus longtemps, pour rien. |

**Trouvé en vérifiant le ménage, et corrigé** : `cleanup_old_requests` supprimait les `rejected` **immédiatement**, sans condition d'âge. L'autre appareil pouvait donc ne jamais lire le refus. Ils partent désormais après **30 jours**, comme les autres — la ligne reste lisible, sans ses mesures. Le test du ménage affirmait l'ancienne règle ; il est réécrit pour la nouvelle, avec une refusée du jour qui **reste** et une refusée de 31 jours qui part.

### D-3 — le bloc du pseudo passait sous l'encoche

Il s'affiche **seul**, avant l'en-tête : il n'héritait donc d'aucune marge haute, et son titre chevauchait l'heure et les indicateurs réseau.

**La « zone sûre » de ce projet est une marge fixe, pas un composant.** `paddingTop: 56` est employé à **45 endroits** ; `SafeAreaView` à **zéro** — la seule occurrence du mot est le commentaire de `screens/ParlerAUneIAScreen.js:425` qui dit que le projet n'en met pas. Le bloc porte donc la même marge que l'en-tête de cet écran-ci. En introduire un ici ferait **deux façons de tenir la même promesse** ; un contrôle vérifie qu'il n'en apparaît aucun.

**Périmètre tenu** : ce bloc seul. Le reste de l'écran n'est pas touché.

### D-4 — la flèche est voulue ; c'est la silhouette qui est le repli

**Aucune correction, et c'est le diagnostic qui le dit.** Les deux pictogrammes sont de vraies icônes Phosphor. Rien n'est absent, rien ne se replie sur un caractère par défaut.

| Archétype | Icône | D'où elle vient |
|---|---|---|
| contient « Explorateur » | **flèche** (`ArrowRight`) | correspondance **voulue**, `CompareResultScreen.js:24` |
| ne contient aucun des 8 mots-clés | **silhouette** (`UserCircle`) | le **repli** |

C'est donc l'inverse de ce que l'écran laissait croire : le proche avait un archétype reconnu, le lecteur non.

**Ce qui est vrai en revanche, et que je signale** : la table ne connaît que **huit** mots-clés (Explorateur, Gardien, Créateur, Sage, Visionnaire, Empathique, Leader, Philosophe), alors que le modèle écrit des archétypes **libres** — « L'Architecte Ambitieux », « La Curieuse Tranquille », « Les Bâtisseurs ». Le repli tombe donc la plupart du temps, et deux archétypes différents portent souvent la même silhouette. **Au registre (S-20)** : soit on élargit la table, soit on demande au prompt de choisir parmi une liste fermée d'archétypes — la seconde option est la seule qui garantisse une icône juste.

---

## 4 bis. Écarts restants

| # | Écart | Décision demandée |
|---|---|---|
| **É-2** | **Le build 17 sera consommé par A3 bis.** L'écran « Qui suis-je ? » entre dans la même 3.1.0. **Le numéro n'a pas été touché par cette passe.** | Remonter à 18 avant d'envoyer si A3 bis ajoute des commits. Le contrôle exige `>= 17`, il ne s'y opposera pas. |
| **É-3** | **Android n'a pas d'explication de permission.** Le plugin n'en expose pas, et Android n'a pas d'équivalent d'Info.plist. | Rien à faire pour iOS. Au registre (S-17) si Android revient. |
| **É-4** | **Le pseudo sert maintenant à deux choses** : se nommer dans l'app, et se nommer dans un texte de comparaison. Si A3 bis (« Qui suis-je ? ») en change le sens ou le libellé, les deux usages bougent ensemble. | À garder en tête en écrivant A3 bis. `saveUserName` / `getUserName` restent la seule porte. |

---

## 5. Les contrôles, et leurs mutations

| Exigence | Contrôles | Mutations qui les font mordre |
|---|---|---|
| §1 Textes d'autorisation, version, build | 12 (`natif.check.mjs`) | phrase disparue · texte qui tutoie · promesse « exclusivement » affaiblie · build non monté |
| §2a Substitution `{A}`/`{B}`, pseudo, libellés | 22 (`display.check.mjs`) | côté ignoré · majuscule supprimée · code passé dans le texte · liste non substituée · substitution neutralisée |
| §2b Accusé de réception | 11 (`degraded.check.mjs`) | accusé perdu au lieu d'être noté · rejeu qui boucle · ack envoyé avant la mise à l'abri |
| §2c Les deux phrases | 3 | phrase cessant de dire ce qui part et vers qui |
| §2d Refus sans accord | 5 app + 6 tests API | refus repassé par la route qui porte les mesures · refus redevenu bloqué · refus sans effet en base · refus permis à un tiers · ligne déjà partie devenue une erreur |
| §2e Routes sans IA | 2 | — (tenues par la confrontation liste ↔ serveur, inchangée) |
| D-1 Un seul avis par écran | 2 | — (le comptage est lui-même la preuve : 2 → 1 sur Proches) |
| D-2 Le refus efface les mesures | 4 tests API | mesures survivant au refus · statut et vecteurs en deux ordres · ménage emportant les refus du jour |
| D-3 La marge haute du bloc du pseudo | 4 | marge retirée · marge déclarée mais n'enveloppant rien · second mécanisme (SafeAreaView) introduit |

**Vingt-quatre mutations jouées, chacune restaurée.** Trois leçons de parcours :

1. Une assertion de mon premier jet de test API était **fausse, pas le code** — elle attendait un `to_vector` vide alors que la ligne d'essai en porte un.
2. Le contrôle de langage (lot A4) a attrapé une aide inexistante que je venais d'employer dans un contrôle (`fichiers` dans `display.check.mjs`). Il sert.
3. **Deux tests affirmaient l'ancienne règle** et ont dû être réécrits, pas contournés : celui qui disait « Vous est très actif », et celui qui exigeait qu'une comparaison refusée disparaisse immédiatement.

---

## 6. Les gestes

**Passés le 18/09 sur Zeopy Dev, avec l'iPad** : 3 (comparaison des deux côtés), 4 (refus sans accord), 5 (résultat après redémarrage). **À refaire après les corrections ci-dessus**, puisqu'elles touchent l'écran de résultat.

| # | Geste | Ce qu'il faut voir | État |
|---|---|---|---|
| 1 | Installer par-dessus l'ancienne version | L'écran **« Vos données »** s'affiche — début du test de migration. | **Attend le build** |
| 2 | Explore, toucher le micro | Les **deux fenêtres système**, chacune avec « Le texte obtenu est ensuite analysé, avec votre accord, pour alimenter votre portrait. » | **Attend le build** |
| 3 | Comparaison avec l'iPad, accord des deux côtés | La phrase sous le bouton · le résultat dit **ton pseudo** et l'alias, **sans accolades** et **avec les verbes accordés** · le **même nom** sous l'archétype, dans la légende et dans les barres · après les deux lectures, la ligne serveur a disparu. | Passé le 18/09, **à refaire** |
| 3 bis | Si aucun pseudo n'est enregistré | L'écran demande **une fois** « Comment veux-tu être nommé(e) dans ce texte ? », puis affiche. Il ne redemande plus ensuite. **Le titre doit commencer sous l'encoche**, pas par-dessus l'heure. | Passé le 18/09, **à refaire** (marge haute) |
| 4 | Demande reçue, **accord IA refusé** | **Un seul** avis, en haut de l'écran · « Refuser » fonctionne · en base, la ligne est `rejected` **et ses deux vecteurs sont vides**. | Passé, **à refaire** (avis et vecteurs) |
| 5 | Tuer l'app, rouvrir le résultat | Il est toujours là, et **aucun `/compare/status`** dans les logs serveur. | Passé le 18/09 |

---

## 7. Ce que ce lot ne fait pas

Hors périmètre : la politique du site et les textes App Store Connect (**A6**), l'écran « Qui suis-je ? » (**A3 bis**). Aucun build n'a été lancé — ni `eas build`, ni `eas submit`, ni `eas update`.
