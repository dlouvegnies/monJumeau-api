# Lot A5 — Textes natifs, comparaison côté app, build

*18/09/2026 — dépôt app (5 commits) et dépôt API (1 commit). Harnais vert : **788 contrôles**, 24 harnais. Tests API : **110 verts**. **Rien n'est poussé, aucun build lancé.***

> **Aucun `eas build`, `eas submit` ni `eas update` n'a été exécuté.** Seul `npx expo prebuild` a tourné, en local, pour vérifier les Info.plist. Le build vous revient, après le lot A3 bis.

---

## 1. Ce que le lot change, en une page

| # | Avant | Après | En clair |
|---|---|---|---|
| 1 | Les autorisations ne parlaient que de dictée | Elles disent ce que **devient** le texte obtenu | La personne ne pouvait pas savoir, au moment où elle accorde, que ses mots nourrissent autre chose. |
| 2 | Le résultat d'une comparaison affichait `{A}` et `{B}` | Les marqueurs deviennent des noms, sur l'appareil | Le serveur ne connaît pas les prénoms et n'a pas le droit de les recevoir. |
| 3 | Le serveur gardait la ligne après lecture | Le téléphone lui dit qu'il peut oublier (`/compare/ack`) | Cette ligne porte les mesures de **deux** personnes. |
| 4 | Refuser une demande était impossible sans accord IA | `/compare/decline` — aucune mesure, aucune IA | La demande expirait seule au bout de 24 h, faute de pouvoir dire non. |
| 5 | Version 1.0.0, build 16 | **3.1.0, build 17** | Le numéro montré à Apple ne disait pas où en était le produit. |

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
| Lecteur = initiateur | « vous » | alias de la connexion |
| Lecteur = répondant | alias de la connexion | « vous » |
| Alias inconnu | — | **« votre proche »**, jamais « Inconnu » dans une phrase rédigée, jamais le code |

La majuscule est mise quand un marqueur ouvre une phrase. Un texte sans marqueur ressort **identique**. Un « l'un / l'autre » résiduel est **laissé tel quel** : le réécrire reviendrait à deviner de qui le modèle parlait.

**Seize contrôles**, dont les quatre demandés (deux côtés, majuscule, texte sans marqueur, « l'un/l'autre » résiduel), et un qui vérifie que le code de l'autre n'apparaît jamais dans le texte rendu.

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

## 4. Écarts

| # | Écart | Décision demandée |
|---|---|---|
| **É-1** | **La substitution ne conjugue pas.** Le modèle écrit à la troisième personne (« {A} est très actif », « {A} allume sa lampe »), et « vous » ne s'accorde pas avec elle. Mesuré : **« Vous est très actif »**, **« Vous allume sa lampe quand Hector s'endort »**, **« Là où vous accélère »**. Un contrôle du harnais l'**affirme** plutôt que de l'accommoder. | Trois issues : **(a)** remplacer `{A}` par le **prénom du lecteur**, que l'app connaît localement — rien de plus n'est envoyé au serveur, et la phrase se lit (« Denis est très actif ») ; **(b)** demander au prompt d'écrire des tournures qui marchent avec « vous » — fragile, et déjà éprouvé au lot A1 ; **(c)** l'assumer. **Recommandation : (a)** — le changement tient dans la constante `LECTEUR` de `services/comparisonResult.js` plus une lecture du prénom. **À trancher avant le build.** |
| **É-2** | **Le build 17 sera consommé par A3 bis.** Le numéro est posé, mais l'écran « Qui suis-je ? » entre dans la même 3.1.0. | Si A3 bis ajoute des commits après celui-ci, il faudra **remonter à 18** avant d'envoyer. Le contrôle du harnais exige `>= 17`, il ne s'y opposera pas. |
| **É-3** | **Android n'a pas d'explication de permission.** Le plugin n'en expose pas, et Android n'a pas d'équivalent d'Info.plist. | Rien à faire pour iOS. Au registre (S-17) si Android revient. |

---

## 5. Les contrôles, et leurs mutations

| Exigence | Contrôles | Mutations qui les font mordre |
|---|---|---|
| §1 Textes d'autorisation, version, build | 12 (`natif.check.mjs`) | phrase disparue · texte qui tutoie · promesse « exclusivement » affaiblie · build non monté |
| §2a Substitution `{A}`/`{B}` | 16 (`display.check.mjs`) | côté ignoré · majuscule supprimée · code passé dans le texte · liste non substituée · substitution neutralisée |
| §2b Accusé de réception | 11 (`degraded.check.mjs`) | accusé perdu au lieu d'être noté · rejeu qui boucle · ack envoyé avant la mise à l'abri |
| §2c Les deux phrases | 3 | phrase cessant de dire ce qui part et vers qui |
| §2d Refus sans accord | 5 app + 6 tests API | refus repassé par la route qui porte les mesures · refus redevenu bloqué · refus sans effet en base · refus permis à un tiers · ligne déjà partie devenue une erreur |
| §2e Routes sans IA | 2 | — (tenues par la confrontation liste ↔ serveur, inchangée) |

**Dix-huit mutations jouées, chacune restaurée.** Une leçon de parcours : une assertion de mon premier jet de test API était fausse, pas le code — elle attendait un `to_vector` vide alors que la ligne d'essai en porte un. Le test compare désormais aux valeurs de départ, ce qu'il voulait dire.

---

## 6. Les gestes, sur le build TestFlight

**À faire sur le build TestFlight, pas sur « Zeopy Dev ».** Deux appareils sont nécessaires pour les gestes 3 et 4.

| # | Geste | Ce qu'il faut voir |
|---|---|---|
| 1 | Installer par-dessus l'ancienne version | L'écran **« Vos données »** s'affiche — c'est le début du test de migration : les choix n'existent pas encore sur cette installation. |
| 2 | Explore, toucher le micro | Les **deux fenêtres système**, chacune avec « Le texte obtenu est ensuite analysé, avec votre accord, pour alimenter votre portrait. » |
| 3 | Comparaison avec l'iPad, accord des deux côtés | La phrase sous le bouton avant l'envoi · le résultat dit **« vous »** et **l'alias**, **sans accolades** · après les deux lectures, la **ligne serveur a disparu**. |
| 4 | Demande reçue, **accord IA refusé** | « **Refuser** » fonctionne et la demande s'en va · « **Accepter** » montre l'avis et n'envoie rien. |
| 5 | Tuer l'app, rouvrir le résultat | Il est **toujours là**, et **aucun `/compare/status`** dans les logs serveur. |

---

## 7. Ce que ce lot ne fait pas

Hors périmètre : la politique du site et les textes App Store Connect (**A6**), l'écran « Qui suis-je ? » (**A3 bis**). Aucun build n'a été lancé — ni `eas build`, ni `eas submit`, ni `eas update`.
