# A6 — Inventaire des tables, avant de décider des purges

*18/09/2026 — audit en lecture seule. Aucun fichier modifié hors ce rapport, aucun ordre SQL, aucune connexion à la base.*

## 0. Avant de lire : la liste `information_schema` n'est pas arrivée

La demande contenait encore le texte « [COLLER ICI LE RÉSULTAT SQL] » : je n'ai **pas** eu la liste réelle des tables. J'ai reconstitué l'inventaire à partir de trois sources. Il faudra le croiser avec la liste réelle avant de s'en servir dans la politique.

| Source | Date | Ce qu'elle couvre | En clair |
|---|---|---|---|
| `main.py`, `model_client.py` (ce dépôt) | 18/09, `c7e5f89` | Chaque appel `sb_get` / `sb_post` / `sb_patch` / `sb_delete` et les appels `httpx` directs vers `/rest/v1/…` | Ce que l'API lit et écrit aujourd'hui. |
| `../monJumeau/schema_public.sql` (dépôt de l'app, versionné) | `pg_dump` du 17/08 | 9 tables `public`, colonnes, contraintes, `ON DELETE CASCADE` | Le schéma tel qu'il était il y a un mois. |
| `migrations/2026-09-17-comparisons-conservation.sql` | 17/09 | Ajoute `from_fetched_at`, `to_fetched_at` à `comparisons` | La seule migration écrite. |

Ce que ces sources ne disent **pas**, et que la liste réelle devra trancher :

- **`ai_usage_log`** n'existe pas dans le schéma du 17/08 (créée avec le commit `bc04c3b` du 02/09, sans doute depuis le tableau de bord). Je connais les colonnes que le code **écrit**, pas celles qui existent (par exemple une colonne `created_at` par défaut).
- **`v_cost_*`** : aucune définition nulle part dans les trois dépôts (`grep v_cost` ne trouve que ta note). Je ne peux pas dire ce qu'elles sélectionnent. Il faut `SELECT pg_get_viewdef('v_cost_per_user')` (et pareil pour les deux autres).
- **Les `ON DELETE CASCADE` de `rc_*`** (`schema_public.sql:649`, `:657`) : ils sont vrais au 17/08. Toute la durée de vie de `rc_responses` en dépend (§5.1). À vérifier dans `information_schema.referential_constraints`.
- **Toute table créée depuis le 17/08** que je ne connais pas.

Requête à coller, pour que le croisement soit complet :

```sql
select table_name, table_type from information_schema.tables where table_schema = 'public' order by 1;
select table_name, column_name, data_type from information_schema.columns where table_schema = 'public' order by 1, ordinal_position;
select tc.table_name, kcu.column_name, rc.delete_rule
  from information_schema.referential_constraints rc
  join information_schema.table_constraints tc on tc.constraint_name = rc.constraint_name
  join information_schema.key_column_usage kcu on kcu.constraint_name = rc.constraint_name
 where tc.table_schema = 'public';
select viewname, definition from pg_views where schemaname = 'public';
```

Il y a aussi une table **hors Supabase** : `device_tokens`, en SQLite sur le disque du serveur Render (`main.py:319-338`). Elle est dans l'inventaire.

---

## 1. Le tableau

`my_code` : le code jumeau, tiré au hasard à l'installation. Il n'a pas de table à lui, mais c'est lui qui relie tout à une personne : ses proches le connaissent, et il s'affiche dans l'app.

| Table | Ce qu'elle porte | Rattachée à une personne ? comment | Ce qui la purge aujourd'hui | Ce que `/identity` en efface | En clair |
|---|---|---|---|---|---|
| `push_tokens` | `my_code`, `push_token` (jeton Expo), `updated_at`. Écrite par `/push/register` (`main.py:1020-1031`) à chaque lancement de l'app, si les notifications sont autorisées (`App.js:175` de l'app). | **Directement** par `my_code` (unique, `schema_public.sql:418`). | **Rien** d'automatique. `/admin/reset-social` vide tout (`main.py:2705`), à la main. | Tout, `main.py:2673`. | Le jeton qui permet de sonner le téléphone de quelqu'un. Il reste tant que la personne ne réinitialise pas l'app. |
| `connection_requests` | `from_code`, `to_code`, **`from_alias`, `to_alias`**, `status`, `synced_from`, `synced_to`, dates. | **Directement**, deux personnes par ligne. Les alias sont des **prénoms** : celui que l'autre t'a donné, et ton propre prénom (`ctx.prenom`, envoyé par `/connection/ensure`, `db.js:966` de l'app). | Refusées de plus de 7 j, en attente de plus de 14 j : `main.py:711-718` (quotidien) et `main.py:2695-2696` (manuel). Acceptées : effacées quand **les deux** téléphones ont synchronisé (`main.py:2566`)… puis **recréées** par `/connection/ensure` (voir §3.1). | Toutes les lignes où le code apparaît, d'un côté ou de l'autre : `main.py:2674`. | Qui connaît qui, et sous quel prénom. En pratique, une connexion acceptée ne quitte jamais le serveur tant que l'un des deux téléphones l'utilise. |
| `comparisons` | Deux codes, `from_vector`, `to_vector` (mesures psychométriques), `result` (le texte de l'analyse), statuts, `from_fetched_at`, `to_fetched_at`. | **Directement**, deux personnes par ligne. | Ligne effacée dès que les deux téléphones ont pris le résultat (`main.py:1685`). Vecteurs mis à null à la fin de l'analyse (`:1565`), en cas d'échec (`:1431`) et au refus (`:1634`). Le ménage quotidien efface les refusées, terminées, en échec ou en analyse de plus de 30 jours, et les demandes en attente expirées (`main.py:736-745`). | Toutes les lignes où le code apparaît : `main.py:2675`. | La comparaison entre deux personnes. Au pire, elle vit 30 jours, et les mesures disparaissent dès que l'analyse est finie. |
| `rc_sessions` | `session_key`, compteurs, `version`, `expires_at` (création + 7 j, `main.py:2728`). | **Indirectement**, et seulement par une invitation : **aucune colonne de code**. La clé figure dans le lien que la personne partage avec ses proches. | Quotidien, après `expires_at` : `main.py:720`. À la main par l'app : `main.py:2806` (`RegardCroiseScreen.js:172`). | **Rien** : aucune colonne à cibler. | Le questionnaire Regard croisé qu'on envoie à ses proches. Il vit 7 jours, puis disparaît au ménage suivant. |
| `rc_responses` | `respondent_name`, `words`, `raw_answers`, `vector`, `relation`, `is_anonymous`, `source`. Écrite par `/rc/respond` (**sans secret**, `main.py:2739-2776`) et `/rc/invitation/respond` (`:2913`). | **Deux personnes** : le **tiers** qui répond (souvent sans compte), et, par la `session_key`, la personne sur qui il répond. | Relevée puis effacée une à une par l'app (`main.py:2798`, appelée par `RegardCroiseScreen.js:129`). Sinon, en cascade quand la session expire (`schema_public.sql:657` + `main.py:720`). Voir §5.1. | **Rien.** | Ce que les proches disent de quelqu'un, avec parfois leur propre prénom. Ça reste sur le serveur jusqu'à ce que la personne le relève, 7 jours au plus. |
| `rc_invitations` | `session_key`, `from_code`, `to_code`, `relation`, `status`, `expires_at` (+7 j). | **Directement**, deux personnes par ligne, plus le lien familial (`relation`). | **Pas de purge directe.** `expires_at` n'est lu nulle part. Elle part en cascade avec sa session (`schema_public.sql:649`), donc au plus tard 7 jours après la création de la session. | Toutes les lignes où le code apparaît : `main.py:2676`. | Qui a invité qui à parler de lui, et à quel titre (ami, famille…). L'invitation part avec sa session, 7 jours au plus. |
| `gifts` | `from_code`, `from_alias`, `to_code`, `trait`, **`message`** (texte libre), `status`, dates. | **Directement**, deux personnes par ligne. | **Rien.** Depuis `c7e5f89` (aujourd'hui), plus aucune route ne la touche. | **Plus rien.** `c7e5f89` a retiré la ligne `sb_delete('gifts', …)` de `/identity` en même temps que les routes. | Les « cadeaux » et leur message libre. Ils restent **pour toujours**, et depuis aujourd'hui même la réinitialisation ne les efface plus. |
| `ai_usage_log` | À chaque appel d'un modèle : `client_ref`, `purpose`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd` (`main.py:422-429`). Colonnes réelles à confirmer (§0). | **Indirectement** par `client_ref` : le jeton d'appareil, ou **`my_code` en clair** pour les comparaisons (voir §5.3). | **Rien.** | **Rien.** | Le journal des coûts d'IA. Il garde, pour toujours, quel appareil a utilisé quelle fonction et quand. |
| `v_cost_*` (vues) | Inconnu : aucune définition dans le code (§0). | `v_cost_per_user` expose `client_ref`, d'après ta note. | Sans objet : une vue ne stocke rien. | Sans objet. | Des tableaux de coût calculés à partir du journal. Voir §5.2. |
| `news_articles` | `title`, `description`, `url`, `source`, `image_url`, `category`, `published_at`, `embedding` (`main.py:2192-2205`, `schema_public.sql:183`). | **Non.** Aucune colonne de personne ; l'API n'y écrit que des articles de flux RSS. | Articles de plus de 7 jours, à chaque `/news/embed` (`main.py:2272`). Articles datés dans le futur : quotidien (`main.py:747`) et à chaque `/news/embed` (`:2273`). | Sans objet. | Des articles de presse publics. Rien sur personne : **confirmé**, elle peut sortir de la déclaration. |
| `rss_feeds` | Catalogue de flux : nom, URL, catégorie, région, ville, pays… (`schema_public.sql:301`). | **Non.** L'API ne fait que la lire et marquer un flux mort (`main.py:852`). | Sans objet (catalogue). | Sans objet. | La liste des sources de presse. Rien sur personne : **confirmé**. |
| `device_tokens` (SQLite, serveur Render) | `token` (le `x-device-token` de l'app), `my_code`, `created_at`, `last_seen` (`main.py:326-333`). | **Directement** : c'est **la table qui relie un appareil à un code**. | Aucune purge dans le code. Le disque de Render est éphémère : elle se vide à chaque redéploiement ou redémarrage (`main.py:314-318`). | Toutes les lignes du code : `main.py:2679`. | La correspondance « cet appareil = ce code ». Elle disparaît à chaque redémarrage du serveur, puis se remplit au lancement suivant de l'app. |

### Ce que le croisement fait déjà apparaître

| Constat | Où | En clair |
|---|---|---|
| **`gifts` n'est plus utilisée par l'API**, mais elle contient encore des lignes, messages compris. `/identity` ne l'efface plus depuis ce matin. | `git show c7e5f89`, lignes `-sb_delete('gifts', …)` | La table la plus facile à supprimer est aussi la seule qu'on vient d'oublier dans l'effacement. |
| `connection_requests.from_alias` contient le **prénom réel** de la personne, pas un surnom : `/connection/ensure` l'écrit à partir de `ctx.prenom`. | `main.py:2621-2625`, `db.js:966-973` (app) | La colonne dit « alias », mais elle garde le prénom. |
| `/connection/ensure` **recrée** des lignes acceptées que le serveur venait d'effacer. | `main.py:2573-2630`, `db.js:957-980` (app) | La purge « quand les deux ont synchronisé » est défaite à la synchronisation suivante. |
| `rc_invitations.expires_at` est écrit (`main.py:2854`) mais jamais lu ni purgé. | `grep expires_at` | La date d'expiration de l'invitation ne sert à rien ; c'est la session qui l'emporte. |
| `ai_usage_log.client_ref` vaut **`my_code`** pour les comparaisons. | `main.py:1511` | Le journal des coûts contient le code des personnes. |
| `/push/token/{my_code}`, `/rc/respond`, `/rc/invitations/sent/{from_code}`, `/rc/session/{key}/count`, `/connection/request`, `/device/register` n'exigent pas le secret de l'app. | `main.py:1033`, `:2739`, `:2873`, `:2956`, `:2440`, `:1039` | Hors du sujet des purges, mais `/push/token` rend le jeton de notification de n'importe quel code. |
| **`../monJumeau/data_export.sql` est versionné** dans le dépôt de l'app (commit `943bffa`, 17/08, remote GitHub). Il contient 1 ligne de `comparisons`, 1 de `push_tokens` et 13 de `gifts`, messages compris. | `git ls-files` dans `../monJumeau` | Des données réelles de personnes sont sur GitHub, dans l'historique git. Les effacer de la base ne les efface pas de là. |
| `../BDD/backup_supabase.sh` contient le **mot de passe de la base en clair**. Le fichier n'est dans aucun des deux dépôts. | `../BDD/backup_supabase.sh:4` | À déplacer dans une variable d'environnement, et à changer si le fichier a circulé. |

---

## 2. L'effacement du compte

### Ce que l'app promet

| Texte | Où (dépôt de l'app) | En clair |
|---|---|---|
| « Effacer en un geste. — Tu peux supprimer ton portrait à tout moment, intégralement, **sans trace**. » | `screens/onboarding/Moment2Contrat.js:60-61` | La promesse la plus forte : « sans trace ». |
| « Réinitialiser complètement l'app — Supprime **toutes vos données** — irréversible » | `screens/home_v2/SettingsScreen.js:449-450` | |
| « Cette action supprime **toutes vos données** et est irréversible. » → bouton « Tout supprimer » | `SettingsScreen.js:480-483` | |

Le geste appelle `resetAll()` (`database/db.js:425`). Il envoie `DELETE /identity/{my_code}` (`db.js:437`), puis vide les tables locales. **Si l'appel au serveur échoue, la réinitialisation continue sans rien dire** (`db.js:439-441`) : les lignes du serveur restent.

### Ce que `/identity` efface réellement (`main.py:2633-2688`)

| Table | Effacé ? | Ce qui reste | En clair |
|---|---|---|---|
| `push_tokens` | Oui, `:2673` | — | |
| `connection_requests` | Oui, les deux sens, `:2674` | Rien sur le moment. Mais le téléphone de chaque proche recrée la ligne à sa synchronisation suivante (§3.1), avec l'ancien code et le prénom qu'il t'avait donné. | Effacé, puis réécrit par les proches. |
| `comparisons` | Oui, les deux sens, `:2675` | — (et chez l'autre personne, le résultat disparaît aussi du serveur, §3.2) | |
| `rc_invitations` | Oui, les deux sens, `:2676` | — | |
| `rc_sessions` | **Non** : aucune colonne de code | Les sessions ouvertes, jusqu'à 7 jours | Tes questionnaires en cours restent en ligne, et le lien fonctionne encore. |
| `rc_responses` | **Non** | Les réponses de tes proches non encore relevées, jusqu'à 7 jours (cascade) | Ce que tes proches ont dit de toi reste jusqu'à 7 jours. |
| `gifts` | **Non**, depuis `c7e5f89` | Tout, sans limite | Les cadeaux envoyés et reçus, messages compris, pour toujours. |
| `ai_usage_log` | **Non** | Toutes les lignes, sans limite : le jeton d'appareil, et `my_code` pour les comparaisons | Le détail de ton usage de l'IA, pour toujours. |
| `device_tokens` (SQLite) | Oui, `:2679` | — | |
| PostHog | **Non** (hors serveur) | Tous les événements. Ceux d'avant le lot A3 portent `distinct_id = my_code`. L'identifiant aléatoire (`zeopy_usage_id`) n'est pas retiré par `resetAll` (`db.js` ne touche qu'à `zeopy_onboarding_done`, `:463`). | La mesure d'usage continue sous le même identifiant après la réinitialisation. |
| Journaux Render | **Non** | Les `print` contiennent des codes : `Identité purgée: {code}` (`:2683`), `Device enregistré: {my_code}` (`:1054`), `Connexion auto-réparée: {a} → {b}` (`:2627`)… | La durée de conservation des journaux dépend de l'offre Render : à vérifier. |
| Sauvegardes Supabase | **Non** | Selon l'offre (les sauvegardes quotidiennes sont gardées quelques jours) | À vérifier sur le compte, et à dire dans la politique. |
| `data_export.sql` sur GitHub | **Non** | Les 15 lignes du 17/08 | Voir §1. |

**Le jeton d'appareil survit aussi à la réinitialisation.** Il est dans le Trousseau (`utils/deviceToken.js`, clé `mj_device_token`), que `resetAll` ne touche pas. Sur iOS, le Trousseau survit même à la désinstallation. Après une réinitialisation, `/device/register` associe donc le **même** jeton au **nouveau** code : dans `ai_usage_log`, les lignes d'avant et d'après se suivent sous le même `client_ref`.

**En clair :** « sans trace » n'est pas tenu aujourd'hui. Il reste au moins `gifts`, `ai_usage_log`, les sessions et réponses Regard croisé (7 jours), PostHog, et les connexions que les proches recréent.

---

## 3. Ce qui ne peut pas être effacé unilatéralement

Aujourd'hui, `/identity` tranche toujours dans le même sens : **l'un efface, l'autre perd aussi.** C'est un choix, et il n'est écrit nulle part pour la personne qui subit l'effacement.

### 3.1 Connexions (`connection_requests`)

**Le problème.** Une connexion est une relation entre deux personnes. Chaque téléphone en garde une copie locale (`connections`), avec le prénom qu'il donne à l'autre. Quand A efface, `/identity` supprime les lignes des deux sens. Mais le téléphone de B voit que la connexion manque et la **recrée** par `/connection/ensure` (`db.js:965-975`) : une ligne B → ancien code de A, avec le prénom de B et celui qu'il donnait à A. Cette ligne pointe vers un code que plus personne n'utilise, et elle n'est plus jamais purgée : elle est `accepted`, et A ne synchronisera jamais. Le commentaire de `/identity` (`main.py:2644-2649`) dit que la relation est rompue au prochain sync de B. C'est l'inverse qui se passe.

| Option | Ce que ça règle | Ce que ça coûte | En clair |
|---|---|---|---|
| A. Garder l'effacement des deux sens, et empêcher `/connection/ensure` de recréer une ligne vers un code effacé (liste de codes effacés, hachés, avec une durée) | L'effacement tient | Une petite table de plus, à purger elle aussi | A part vraiment. B voit la connexion disparaître sans explication. |
| B. Idem, et B voit « Cette personne a quitté ZEOPY » au lieu d'une disparition muette | L'effacement tient, et B comprend ce qui arrive | Un statut de plus, et B apprend que A a effacé (c'est déjà une information sur A) | A part, B le sait. |
| C. Supprimer `/connection/ensure` | Plus de résurrection | Perd la réparation après une perte de données Supabase, sa raison d'être | Le filet disparaît pour tout le monde. |
| D. Ne plus garder les connexions acceptées côté serveur du tout : le serveur ne sert qu'à la poignée de main, puis efface | Le serveur n'a plus de graphe social | Plus de réparation, plus de liste `/connection/accepted` côté serveur | Le serveur oublie qui connaît qui. |

### 3.2 Comparaisons (`comparisons`)

**Le problème.** Une comparaison porte les mesures de deux personnes et un texte qui parle des deux. Quand A efface, `/identity` supprime la ligne (`main.py:2675`). Si B n'avait pas encore pris le résultat, il ne l'aura jamais. `/compare/status` répond 404 et l'app de B ne dit pas pourquoi. Si B l'avait déjà pris, le texte reste sur **son** téléphone, et le serveur n'y peut rien : c'est une copie qui appartient à B.

| Option | Ce que ça règle | Ce que ça coûte | En clair |
|---|---|---|---|
| A. Statu quo : effacer la ligne | Rien de A ne reste sur le serveur | B perd un résultat qu'il attendait | Simple, mais B est puni. |
| B. Effacer les mesures de A et garder le texte pour B jusqu'à son accusé de réception (filet 30 j) | B reçoit ce qu'il a accepté | Le texte parle de A : c'est une donnée sur A qui survit à son effacement | B garde son résultat ; A ne part pas tout à fait. |
| C. Effacer, et dire à B « L'autre personne a retiré sa participation » | B comprend | Même fuite d'information que 3.1-B | |
| Dans tous les cas | Dire à A, avant l'effacement, que les résultats déjà reçus par ses proches restent sur leurs téléphones | — | Un effacement ne peut pas atteindre le téléphone d'un autre. La promesse « sans trace » doit le dire. |

### 3.3 Regard croisé (`rc_sessions`, `rc_responses`, `rc_invitations`)

Deux cas, dans les deux sens :

**A efface, et A avait une session ouverte.** Rien n'est effacé côté session : pas de colonne de code (`main.py:2723-2729`). Les réponses des proches restent jusqu'à 7 jours, et le lien marche encore pour eux : ils peuvent répondre sur quelqu'un qui n'a plus l'app. `/identity` pourrait retrouver les sessions par `rc_invitations.session_key`, mais pas celles partagées par lien seulement (chemin web).

**B (répondant) efface.** Sa réponse dans `rc_responses` n'a aucun lien avec son code, même quand il a répondu depuis l'app (`main.py:2913-2922` n'écrit pas `to_code`). Seule son invitation part (`:2676`). Une fois relevée, la réponse vit sur le téléphone de A, avec le prénom de B s'il l'a donné.

| Option | Ce que ça règle | Ce que ça coûte | En clair |
|---|---|---|---|
| A. Ajouter le code du propriétaire à `rc_sessions` (haché ou non), pour que `/identity` efface sessions et réponses en cascade | L'effacement de A vide aussi ses questionnaires | Une colonne de plus qui relie la session à une personne | A part avec ses questionnaires. |
| B. `/identity` efface les sessions trouvées via `rc_invitations` avant de les effacer | Couvre le chemin « app » sans nouvelle colonne | Rate les sessions partagées seulement par lien | Solution partielle, sans toucher au schéma. |
| C. Réduire l'expiration de 7 jours | Diminue la fenêtre dans tous les cas | Moins de temps pour que les proches répondent | Moins longtemps, pour tout le monde. |
| Pour B | Aucune option serveur ne peut retirer une réponse déjà relevée par A. À dire au répondant, dans la page web (`rc_webapp.py`), avant qu'il n'écrive son prénom | — | Le répondant doit savoir que sa réponse finit chez l'autre, pour de bon. |

### 3.4 Cadeaux (`gifts`)

Plus aucune route, donc plus rien de partagé à protéger. La question n'est plus « qui efface », mais « quand vider la table ». Voir §4.

---

## 4. Les durées

Proposition, table par table. **Ce sont des propositions : c'est toi qui décides**, et les phrases de la dernière colonne sont écrites pour pouvoir aller telles quelles dans la politique, une fois la durée retenue.

| Table | Aujourd'hui | Durée proposée | Ce qu'elle permet | Ce qu'elle coûte si on raccourcit | Phrase pour la politique |
|---|---|---|---|---|---|
| `gifts` | Pour toujours | **Vider la table maintenant, puis la supprimer** | Rien : la fonctionnalité n'existe plus | Rien | « La fonction Cadeaux a été retirée le 18 septembre 2026 ; les cadeaux et leurs messages ont été supprimés de nos serveurs. » |
| `push_tokens` | Jusqu'à la réinitialisation | **90 jours sans lancement de l'app** (`updated_at` est rafraîchi à chaque lancement, `App.js:175`) | Notifier une personne qui revient après une pause | En dessous de 30 j, les personnes qui ouvrent l'app une fois par mois ne reçoivent plus les demandes de connexion ou de comparaison avant leur prochain lancement | « Le jeton qui permet de vous envoyer des notifications est supprimé 90 jours après votre dernière ouverture de l'app, ou dès que vous la réinitialisez. » |
| `connection_requests` — `accepted` | Pour toujours, dans les faits (§3.1) | **Dépend du choix fait au §3.1.** Si le serveur ne garde que la poignée de main (option D) : effacée dès la synchronisation des deux côtés, sans résurrection. Sinon : **180 jours sans synchronisation d'aucun des deux côtés** | La réparation après une perte de données | Sans filet de réparation, une perte Supabase casse des connexions qui ne reviennent que si les deux personnes se reconnectent | « Une connexion entre deux personnes est conservée sur nos serveurs tant que l'une des deux utilise l'app, et au plus 180 jours après la dernière utilisation. » |
| `connection_requests` — `pending` / `rejected` | 14 j / 7 j (`main.py:254`, `:237`) | **Inchangé** | La personne a deux semaines pour répondre | — | « Une demande de connexion sans réponse est supprimée après 14 jours ; une demande refusée, après 7 jours. » |
| `comparisons` | Jusqu'aux deux accusés, filet 30 j | **Inchangé** | Le temps que les deux téléphones reviennent | Moins de 30 j : quelqu'un en vacances perd son résultat | « Les mesures envoyées pour une comparaison sont effacées dès la fin de l'analyse. Le texte de l'analyse est effacé dès que les deux personnes l'ont reçu, et au plus tard 30 jours après la demande. » |
| `rc_sessions` + `rc_responses` + `rc_invitations` | 7 j, en cascade (si la contrainte existe encore, §0) | **7 jours** (inchangé), **et** vérifier la cascade en production | Une semaine pour que les proches répondent | Moins : des proches qui n'ont pas le temps de répondre | « Les réponses de vos proches restent sur nos serveurs jusqu'à ce que votre téléphone les récupère, et au plus 7 jours après la création du questionnaire. » |
| `ai_usage_log` | Pour toujours | **90 jours, avec `client_ref` haché** (et plus jamais `my_code`). Au-delà, si le suivi de coût long terme est utile : une table d'agrégats par jour et par `purpose`, **sans `client_ref`**, gardée sans limite | Voir les coûts par fonction, repérer un appareil qui consomme anormalement sur un trimestre | En dessous de 30 j : on ne peut plus comparer un mois au précédent par appareil. Les agrégats sans `client_ref` compensent pour le coût global | « Chaque appel à une IA laisse une ligne de coût (fonction utilisée, modèle, nombre de mots traités, coût), rattachée à un identifiant d'appareil chiffré de façon irréversible. Elle est supprimée après 90 jours. » |
| `device_tokens` (SQLite) | Jusqu'au redémarrage du serveur | **Inchangé** dans les faits. Si le stockage devient persistant un jour : 90 jours sans `last_seen` | — | — | « L'association entre votre appareil et votre code est gardée en mémoire sur le serveur, et effacée à chaque redémarrage. » (à reformuler si le stockage devient persistant) |
| `news_articles` | 7 j | Hors déclaration | — | — | — |
| `rss_feeds` | Catalogue | Hors déclaration | — | — | — |

**Une réserve sur toutes les durées :** la purge tourne dans la boucle `cleanup_old_requests` (`main.py:708-754`). Elle démarre avec le processus puis dort 24 h. S'il n'y a ni planificateur externe ni `pg_cron`, le délai réel est « la durée + au plus 24 h, à condition que le serveur tourne ». Si l'offre Render met l'instance en veille, la purge n'a lieu qu'au réveil suivant. Pour une politique qui cite des durées exactes, il vaut mieux un `pg_cron` côté Supabase, ou écrire « au plus tard N jours + 1 ».

---

## 5. Trois points à traiter en priorité

### 5.1 `rc_responses` : des données sur des tiers

**Ce que dit la note de reprise :** les réponses sont supprimées du serveur une fois enregistrées sur le téléphone.

**Vérifié, avec quatre réserves.**

| Étape | Où | Ce qui se passe | En clair |
|---|---|---|---|
| Relève | `RegardCroiseScreen.js:90` → `main.py:2779-2791` | Toutes les réponses de la session | |
| Enregistrement local | `RegardCroiseScreen.js:98-107` (`saveRCResponse`) | `id`, vecteur, mots, relation, prénom, anonymat, réponses brutes | |
| Effacement serveur | `RegardCroiseScreen.js:129` → `main.py:2794-2799` | `DELETE` de la réponse, juste après l'enregistrement local | **La note dit vrai** dans le cas nominal. |
| Réserve 1 : relève **manuelle** | `RegardCroiseScreen.js:412` (bouton), pas de relève automatique | Si la personne n'appuie jamais sur « Synchroniser », rien n'est effacé par ce chemin | Une personne qui n'ouvre jamais l'écran laisse tout sur le serveur. |
| Réserve 2 : un `DELETE` raté n'est **jamais retenté** | `RegardCroiseScreen.js:98` (`if (!localIds.has(r.id))`) ; le résultat du `DELETE` n'est pas lu | Une fois la réponse en local, la synchronisation suivante l'ignore : elle ne relance pas l'effacement | Une coupure réseau au mauvais moment laisse la réponse jusqu'à l'expiration. |
| Réserve 3 : la cascade n'est prouvée qu'au 17/08 | `schema_public.sql:657` | Sans elle, `main.py:720` efface la session et **laisse les réponses pour toujours** | À vérifier en priorité (§0). |
| Réserve 4 : le filet dépend de la boucle de purge | `main.py:720` | « 7 jours + jusqu'au prochain passage » | Voir la réserve sur les durées, §4. |

**Si la personne ne relève jamais ses réponses :** elles restent, prénom du répondant compris, jusqu'à l'expiration de la session : 7 jours après sa **création** (`main.py:2728`), puis au prochain passage du ménage, qui les efface en cascade. Tout cela suppose que la contrainte `ON DELETE CASCADE` existe toujours en production. Sinon, elles restent **indéfiniment**.

**Un point d'accès à signaler.** `/rc/responses/{session_key}` exige le secret de l'app, mais ce secret est dans l'app publiée (`utils/api.js:112`), donc récupérable. Et la `session_key` est dans le lien envoyé à tous les proches. Quiconque a le lien peut donc, en principe, lire les réponses des **autres** proches (prénoms, mots, réponses brutes) tant qu'elles n'ont pas été relevées. Ce n'est pas une question de purge, mais ça pèse sur la durée : plus elle est courte, plus la fenêtre est étroite.

### 5.2 Les vues `v_cost_*`

| Question | Réponse | En clair |
|---|---|---|
| Sont-elles utilisées par l'API ? | **Non.** Aucune occurrence de `v_cost` dans `main.py`, `model_client.py`, l'app ni `monJumeau-Web`. | Elles ne servent qu'à la lecture manuelle, dans le tableau de bord Supabase. |
| Que font-elles ? | **Inconnu** : aucune définition dans les dépôts. `pg_views` (§0) le dira. | Je ne devine pas. |
| Si `client_ref` est haché ? | Une vue relit la table à chaque requête. `v_cost_per_user` continuera donc de fonctionner, et regroupera par **haché** au lieu de jeton ou de code. Deux cas la cassent : (a) une jointure sur `client_ref` avec une autre table (il n'en existe pas dans le schéma connu, mais la définition le dira) ; (b) un hachage avec un sel qui **tourne** (par mois, par exemple) : le même appareil apparaît alors sous plusieurs lignes, et « par utilisateur » devient « par appareil et par période ». | Avec un hachage stable, la vue reste valable et ne montre plus d'identifiant réutilisable. Avec un sel qui tourne, elle ment sur le nombre d'utilisateurs. |
| Et les lignes déjà écrites ? | Le hachage prévu ne s'appliquera qu'aux nouvelles lignes. Les anciennes gardent jetons et `my_code` en clair, jusqu'à une mise à jour (`update … set client_ref = <hash>(client_ref)`) ou jusqu'à la purge à 90 jours. | Hacher sans reprendre l'existant laisse l'historique en clair. |
| Et `my_code` dans les comparaisons ? | Haché, `my_code` reste un identifiant stable de la personne, et le même haché peut se recalculer à partir d'un code connu (les proches le connaissent). La note S-10 le recommande déjà : remplacer par le jeton d'appareil, ou par `None`. | Hacher un code que d'autres connaissent ne le rend pas anonyme. |

### 5.3 `ai_usage_log`

**Ce qui est écrit, à chaque appel d'un modèle de langage** (`model_client.py:314-317` → `main.py:409-431`) :

| Colonne | Valeur | En clair |
|---|---|---|
| `client_ref` | Le `x-device-token` de la requête, pour 13 usages (`main.py:1015`, `:1969`, `:2016`, `:2154`, `:3052`, `:3135`, `:3236`, `:3372`, `:3469`, `:3654`, `:3731`, `:3780`, `:3865`). **`my_code` de l'initiateur** pour `compare_generate` (`:1511`) | Un identifiant d'appareil, ou le code de la personne. |
| `purpose` | Nom de la fonction : `recommend`, `portrait_narrative`, `capture_extract`, `compare_generate`… | Ce que la personne faisait. |
| `model` | Le modèle appelé | |
| `input_tokens`, `output_tokens` | Compteurs rendus par le prestataire | La longueur, pas le contenu. |
| `estimated_cost_usd` | Calculé (`model_client.estimate_cost_usd`) | |
| (horodatage) | Probablement une colonne `created_at` par défaut : **à confirmer** (§0) | Quand. |

**Aucun contenu** : ni message, ni prompt, ni réponse. Les calculs de vecteurs (`embed_texts`, Mistral) ne passent **pas** par `call_model` et ne sont pas journalisés. `client_ref` n'est **pas** transmis au prestataire : la charge envoyée à Anthropic ne contient que `model`, `max_tokens`, `messages` et `system` (`model_client.py:222`). La vérification demandée par la note de reprise (ligne 123) est donc faite : il n'y a pas de métadonnée.

**La chaîne qui remonte de `client_ref` à une personne :**

| Maillon | Où | En clair |
|---|---|---|
| 1. `client_ref` = jeton d'appareil | `ai_usage_log` | |
| 2. Jeton d'appareil → `my_code` | `device_tokens` (SQLite, `main.py:326-333`), rempli à chaque lancement (`App.js:177`) | Tant que le serveur n'a pas redémarré. |
| 2 bis. **Ou directement** `client_ref` = `my_code` | `main.py:1511` | Pas besoin du maillon 2 pour les comparaisons. |
| 3. `my_code` → prénom | `connection_requests.from_alias` / `to_alias` (§1), `gifts.from_alias` | Le prénom réel, écrit par la personne ou par ses proches. |
| 4. `my_code` → une personne réelle | Les proches connaissent le code : c'est lui qu'on échange pour se connecter | Pour qui connaît le code, le journal dit qui a fait quoi, et quand. |
| Et à travers les réinitialisations | Le jeton d'appareil est dans le Trousseau et survit à `resetAll` (§2) | Une réinitialisation ne coupe pas la chaîne dans `ai_usage_log`. |

---

## PostHog

| Question | Réponse | Source | En clair |
|---|---|---|---|
| Ce qui part | `event` (`$pageview` et quelques événements nommés), `distinct_id` = identifiant aléatoire `zeopy_usage_id`, `properties` (nom d'écran, `app: 'monJumeau'`, `$lib: 'fetch'`), `timestamp`. Rien sans accord. | `utils/analytics.js:86-104` (app) | Quels écrans, quand, sous un identifiant tiré au hasard. |
| Ce que PostHog ajoute de lui-même | **L'adresse IP** de la requête, et par défaut la **géolocalisation** qu'il en tire (ville, pays). L'app ne l'empêche pas : aucune propriété `$ip` ni `$geoip_disable` dans la charge. | `analytics.js:96-100` ; fonctionnement standard de l'API de capture, **à vérifier sur le compte** | Même avec un identifiant au hasard, PostHog sait d'où vient chaque événement. |
| Réglable côté compte ? | Oui, dans les réglages du projet : « Discard client IP data » (ne garde pas l'IP) et la désactivation de la géolocalisation. Autre option côté app : envoyer `$geoip_disable: true` et `$process_person_profile: false` | Documentation PostHog, **à vérifier dans l'interface** | Deux interrupteurs à basculer avant la soumission. |
| Durée de conservation | PostHog Cloud garde les événements **1 an** sur l'offre gratuite ; les offres payantes vont plus loin. Il n'y a pas, à ma connaissance, de durée plus courte réglable soi-même : il faut supprimer les personnes ou les événements (interface ou API) | Tarifs PostHog, **à confirmer sur la page de facturation du compte**, je ne l'ai pas vérifié en ligne | Un an, sauf si on efface soi-même. |
| Données déjà là | Les événements d'avant le lot A3 (17/09) portent `distinct_id = my_code` | `analytics.js:7-11` (commentaire d'en-tête) | L'ancien historique PostHog est rattaché au code des personnes. À supprimer par l'interface « Persons » (supprimer les personnes et leurs événements), ou à dire dans la politique. |
| Effacement | Ni `resetAll` ni `/identity` ne touchent PostHog, et `zeopy_usage_id` n'est pas retiré à la réinitialisation | `db.js:425-465` | Après une réinitialisation, la mesure continue sous le même identifiant. |
| Hébergement | `eu.i.posthog.com` | `analytics.js:28` | En Europe. |

---

## Ce qu'il reste à obtenir avant de trancher

1. La sortie des quatre requêtes du §0 : tables, colonnes, contraintes (**la cascade `rc_*`**), définitions des vues.
2. Sur le compte Supabase : l'offre, et donc la durée des sauvegardes.
3. Sur le compte Render : l'offre, la durée des journaux, et la mise en veille éventuelle de l'instance.
4. Sur le compte PostHog : la durée de conservation affichée, et l'état des réglages IP et géolocalisation.
