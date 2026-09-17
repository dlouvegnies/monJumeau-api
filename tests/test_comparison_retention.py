"""
Conservation des comparaisons (décision L).

Une ligne de `comparisons` porte les vecteurs psychométriques de DEUX
personnes. Avant ce lot, ils y vivaient sans limite : le nettoyage quotidien
ne touchait pas cette table, et `expires_at` ne sert qu'à refuser une
acceptation tardive — il n'efface rien.

Après : les vecteurs ne vivent que le temps de l'analyse, et la ligne
disparaît dès que les deux téléphones ont pris le résultat.

Supabase est simulé par une table en mémoire : on vérifie ce que le code
DEMANDE d'écrire et d'effacer, sans réseau.

---

Comparison retention (decision L). Supabase is simulated in memory.
"""
import json

import pytest

import main


class FausseBase:
    """Une table `comparisons` en mémoire, qui répond comme PostgREST.

    ---

    An in-memory `comparisons` table, answering like PostgREST.
    """

    def __init__(self, lignes=None):
        self.lignes = list(lignes or [])
        self.supprimes = []

    @staticmethod
    def _valeur(filtre):
        return filtre.split(".", 1)[1] if "." in filtre else filtre

    def _correspond(self, ligne, params):
        for cle, filtre in params.items():
            if cle == "select":
                continue
            attendu = self._valeur(filtre)
            if filtre.startswith("eq."):
                if str(ligne.get(cle)) != attendu:
                    return False
            elif filtre.startswith("lt."):
                valeur = ligne.get(cle)
                if valeur is None or str(valeur) >= attendu:
                    return False
            else:
                return False
        return True

    async def get_one(self, table, params):
        for ligne in self.lignes:
            if self._correspond(ligne, params):
                return dict(ligne)
        return None

    async def patch(self, table, params, body):
        for ligne in self.lignes:
            if self._correspond(ligne, params):
                ligne.update(body)
        return True

    async def delete(self, table, params):
        avant = len(self.lignes)
        gardees = [l for l in self.lignes if not (table == "comparisons" and self._correspond(l, params))]
        self.supprimes.append((table, params, avant - len(gardees)))
        self.lignes = gardees
        return True


@pytest.fixture
def base(monkeypatch):
    b = FausseBase()
    monkeypatch.setattr(main, "sb_get_one", b.get_one)
    monkeypatch.setattr(main, "sb_patch", b.patch)
    monkeypatch.setattr(main, "sb_delete", b.delete)
    return b


def comparaison(**extra):
    ligne = {
        "id": "c1", "from_code": "AAA", "to_code": "BBB",
        "status": "analyzing", "from_accepted": 1, "to_accepted": 1,
        "from_vector": json.dumps({"vector": {"values.family": 0.8}}),
        "to_vector": json.dumps({"vector": {"values.family": 0.3}}),
        "from_fetched_at": None, "to_fetched_at": None,
        "created_at": "2026-09-17T08:00:00+00:00",
        "expires_at": "2026-09-18T08:00:00+00:00",
    }
    ligne.update(extra)
    return ligne


# ── Après l'analyse : les vecteurs ne survivent pas ──────────────────────
@pytest.mark.asyncio
async def test_analyse_reussie_efface_les_deux_vecteurs(base, monkeypatch):
    base.lignes = [comparaison()]
    propre = json.dumps({"score_global": 80,
                         "message_poetique": "{A} et {B}, deux rivières."}, ensure_ascii=False)

    async def faux_modele(**kwargs):
        class R:
            status_code = 200
            def json(self): return {"content": [{"text": propre}]}
        return R()

    monkeypatch.setattr(main, "call_model", faux_modele)
    monkeypatch.setattr(main, "send_push_notification", lambda **k: None)
    await main.analyze_comparison("c1")
    ligne = base.lignes[0]
    assert ligne["status"] == "completed"
    assert ligne["result"] is not None
    assert ligne["from_vector"] is None and ligne["to_vector"] is None


@pytest.mark.asyncio
async def test_analyse_ratee_efface_aussi_les_vecteurs(base, monkeypatch):
    """Une analyse qui ne rend rien d'exploitable n'est pas une raison de
    garder les données de deux personnes."""
    base.lignes = [comparaison()]

    async def faux_modele(**kwargs):
        class R:
            status_code = 200
            def json(self): return {"content": [{"text": "pas de JSON ici"}]}
        return R()

    monkeypatch.setattr(main, "call_model", faux_modele)
    await main.analyze_comparison("c1")
    ligne = base.lignes[0]
    assert ligne["status"] == "failed"
    assert ligne["from_vector"] is None and ligne["to_vector"] is None


# ── /compare/ack : la ligne part quand les deux ont pris ─────────────────
def test_un_seul_ack_laisse_la_ligne(client, auth_headers, base):
    base.lignes = [comparaison(status="completed", result="{}")]
    r = client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "AAA"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["deleted"] is False
    assert len(base.lignes) == 1
    assert base.lignes[0]["from_fetched_at"] is not None
    assert base.lignes[0]["to_fetched_at"] is None


def test_les_deux_ack_suppriment_la_ligne(client, auth_headers, base):
    base.lignes = [comparaison(status="completed", result="{}")]
    client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "AAA"}, headers=auth_headers)
    r = client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "BBB"}, headers=auth_headers)
    assert r.json()["deleted"] is True
    assert base.lignes == []


def test_ack_est_idempotente(client, auth_headers, base):
    """Deux fois du même côté ne change rien ; et sur une ligne déjà partie,
    la réponse est un succès — un téléphone ne doit pas rester coincé."""
    base.lignes = [comparaison(status="completed", result="{}")]
    client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "AAA"}, headers=auth_headers)
    r = client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "AAA"}, headers=auth_headers)
    assert r.json()["deleted"] is False and len(base.lignes) == 1
    base.lignes = []
    r = client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "AAA"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["deleted"] is True


def test_ack_d_un_tiers_est_refusee(client, auth_headers, base):
    base.lignes = [comparaison(status="completed", result="{}")]
    r = client.post("/compare/ack", json={"comparison_id": "c1", "my_code": "ZZZ"}, headers=auth_headers)
    assert r.status_code == 403
    assert len(base.lignes) == 1


# ── Le nettoyage quotidien ───────────────────────────────────────────────
@pytest.mark.asyncio
async def test_le_nettoyage_balaie_les_comparaisons(base, monkeypatch):
    """Refusée, en attente expirée, et vieille de plus de 30 jours."""
    vieux = main.iso_days_ago(31)
    base.lignes = [
        comparaison(id="refusee", status="rejected"),
        comparaison(id="expiree", status="pending", expires_at="2020-01-01T00:00:00+00:00"),
        comparaison(id="vieille", status="completed", created_at=vieux),
        comparaison(id="recente", status="completed"),
    ]
    appels = {"n": 0}

    async def une_seule_tournee(_):
        appels["n"] += 1
        raise RuntimeError("stop")

    monkeypatch.setattr(main.asyncio, "sleep", une_seule_tournee)
    with pytest.raises(RuntimeError):
        await main.cleanup_old_requests()
    restants = {l["id"] for l in base.lignes}
    assert restants == {"recente"}, restants


@pytest.mark.asyncio
async def test_une_comparaison_recente_survit_au_nettoyage(base, monkeypatch):
    base.lignes = [comparaison(id="recente", status="completed")]

    async def une_seule_tournee(_):
        raise RuntimeError("stop")

    monkeypatch.setattr(main.asyncio, "sleep", une_seule_tournee)
    with pytest.raises(RuntimeError):
        await main.cleanup_old_requests()
    assert [l["id"] for l in base.lignes] == ["recente"]


# ── Le filet : rien ne meurt en silence (défaut de production du 17/09) ──

@pytest.mark.asyncio
async def test_un_delai_depasse_referme_la_comparaison(base, monkeypatch):
    """Le défaut exact : httpx.ReadTimeout dans l'adaptateur. La ligne
    restait en `analyzing`, vecteurs intacts, et deux téléphones sondaient
    un statut qui ne changerait jamais."""
    import httpx
    base.lignes = [comparaison()]
    base.lignes[0]["status"] = "analyzing"
    pushs = []

    async def modele_qui_expire(**kwargs):
        raise httpx.ReadTimeout("délai dépassé")

    async def faux_push(**kwargs):
        pushs.append(kwargs)

    async def faux_token(table, params):
        if table == "push_tokens":
            return {"push_token": "jeton-" + params["my_code"].split(".")[-1]}
        return await base.get_one(table, params)

    monkeypatch.setattr(main, "call_model", modele_qui_expire)
    monkeypatch.setattr(main, "send_push_notification", faux_push)
    monkeypatch.setattr(main, "sb_get_one", faux_token)

    await main.analyze_comparison("c1")

    ligne = base.lignes[0]
    assert ligne["status"] == "failed"
    assert ligne["from_vector"] is None and ligne["to_vector"] is None
    assert len(pushs) == 2, pushs
    assert all("relancer" in p["body"].lower() for p in pushs)
    assert all("vous" in p["body"].lower() for p in pushs)


@pytest.mark.asyncio
async def test_une_base_indisponible_ne_fait_pas_mourir_la_tache(base, monkeypatch):
    """Même une erreur de base au milieu se referme : le filet attrape tout."""
    base.lignes = [comparaison()]

    async def modele_qui_casse(**kwargs):
        raise RuntimeError("supabase injoignable")

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele_qui_casse)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    await main.analyze_comparison("c1")
    assert base.lignes[0]["status"] == "failed"
    assert base.lignes[0]["from_vector"] is None


@pytest.mark.asyncio
async def test_la_relance_ne_double_pas_l_attente_sans_limite(base, monkeypatch):
    """Quand le budget est épuisé, on renonce à la relance plutôt que de
    faire patienter deux téléphones une seconde fois."""
    base.lignes = [comparaison()]
    appels = []

    async def modele_tronque(**kwargs):
        appels.append(kwargs.get("timeout"))
        return _reponse('{"score_global": 80, "mess', stop_reason="max_tokens")

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele_tronque)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    monkeypatch.setattr(main, "COMPARE_BUDGET_SECONDS", 0.0)
    await main.analyze_comparison("c1")
    assert len(appels) == 1, f"la relance aurait dû être abandonnée : {appels}"


@pytest.mark.asyncio
async def test_une_faute_attributive_ne_declenche_plus_de_relance(base, monkeypatch):
    """Relancer sur une faute de rédaction a échoué 4 fois sur 4 le 17/09 :
    le modèle refait la même tournure, et l'utilisateur attend deux fois plus
    longtemps pour rien. On garde le premier essai et on compte."""
    base.lignes = [comparaison()]
    main.COMPTEUR_COMPARAISONS["total"] = 0
    main.COMPTEUR_COMPARAISONS["conservees_avec_fautes"] = 0
    appels = []
    fautif = json.dumps({"score_global": 70,
                         "message_poetique": "L'un avance, l'autre regarde."}, ensure_ascii=False)

    async def modele_fautif(**kwargs):
        appels.append(kwargs.get("timeout"))
        return _reponse(fautif)

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele_fautif)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    await main.analyze_comparison("c1")
    assert len(appels) == 1, f"un seul essai attendu, obtenu {len(appels)}"
    assert base.lignes[0]["status"] == "completed"
    assert main.COMPTEUR_COMPARAISONS == {"total": 1, "conservees_avec_fautes": 1}


@pytest.mark.asyncio
async def test_la_relance_a_lieu_quand_la_reponse_est_vraiment_inutilisable(base, monkeypatch):
    """Elle ne sert plus qu'à ce qu'elle répare vraiment : un JSON illisible
    ou une réponse tronquée."""
    base.lignes = [comparaison()]
    appels = []
    propre = json.dumps({"score_global": 80, "message_poetique": "{A} et {B}."}, ensure_ascii=False)

    async def modele(**kwargs):
        appels.append(kwargs.get("timeout"))
        if len(appels) == 1:
            return _reponse('{"score_global": 80, "mess', stop_reason="max_tokens")
        return _reponse(propre)

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    await main.analyze_comparison("c1")
    assert len(appels) == 2
    assert all(t is not None and t > 0 for t in appels), appels
    assert base.lignes[0]["status"] == "completed"


def test_la_tache_de_fond_recupere_son_exception():
    """Sans ce rappel, Python avertit « Task exception was never retrieved »
    et la cause n'arrive jamais dans le journal."""
    import asyncio as aio

    class FausseTache:
        def exception(self):
            return RuntimeError("boum")

    main._recuperer_exception(FausseTache())  # ne doit pas lever

    source = (__import__("pathlib").Path(main.__file__)).read_text(encoding="utf8")
    i_creation = source.index("asyncio.create_task(analyze_comparison(")
    i_rappel = source.index("add_done_callback(_recuperer_exception)")
    assert i_rappel > i_creation and i_rappel - i_creation < 200


# ── Jamais un résultat illisible en base (défaut 0F90CED0, 17/09) ────────

def _reponse(texte, stop_reason="end_turn"):
    class R:
        status_code = 200
        def json(self):
            return {"content": [{"text": texte}], "stop_reason": stop_reason}
    return R()


@pytest.mark.asyncio
async def test_une_reponse_tronquee_ne_devient_jamais_completed(base, monkeypatch):
    """Le défaut exact : `max_tokens` atteint, JSON coupé au milieu d'une
    chaîne, stocké tel quel — et /compare/status répondait 500 à chaque
    sondage."""
    base.lignes = [comparaison()]
    coupe = '{"score_global": 75, "message_poetique": "{A} allume et {B}'
    pushs = []

    async def modele_tronque(**kwargs):
        return _reponse(coupe, stop_reason="max_tokens")

    async def faux_push(**kwargs):
        pushs.append(kwargs)

    async def faux_token(table, params):
        if table == "push_tokens":
            return {"push_token": "jeton"}
        return await base.get_one(table, params)

    monkeypatch.setattr(main, "call_model", modele_tronque)
    monkeypatch.setattr(main, "send_push_notification", faux_push)
    monkeypatch.setattr(main, "sb_get_one", faux_token)
    await main.analyze_comparison("c1")

    ligne = base.lignes[0]
    assert ligne["status"] == "failed"
    assert ligne.get("result") in (None, "")
    assert ligne["from_vector"] is None and ligne["to_vector"] is None
    assert len(pushs) == 2


@pytest.mark.asyncio
async def test_un_json_illisible_sans_stop_reason_est_refuse_aussi(base, monkeypatch):
    """Même sans l'indice `max_tokens`, un JSON qu'on ne peut pas relire ne
    doit jamais être écrit : « aucune faute de marqueur » ne veut pas dire
    « exploitable »."""
    base.lignes = [comparaison()]

    async def modele_casse(**kwargs):
        return _reponse('{"score_global": 75, "message_poetique": "{A} et')

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele_casse)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    await main.analyze_comparison("c1")
    assert base.lignes[0]["status"] == "failed"
    assert base.lignes[0].get("result") in (None, "")


@pytest.mark.asyncio
async def test_une_troncature_au_premier_essai_laisse_sa_chance_au_second(base, monkeypatch):
    """La relance sert d'abord à ça : le second essai peut réussir."""
    base.lignes = [comparaison()]
    propre = json.dumps({"score_global": 80, "message_poetique": "{A} et {B}."}, ensure_ascii=False)
    essais = {"n": 0}

    async def modele(**kwargs):
        essais["n"] += 1
        if essais["n"] == 1:
            return _reponse('{"score_global": 80, "message', stop_reason="max_tokens")
        return _reponse(propre)

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    await main.analyze_comparison("c1")
    assert essais["n"] == 2
    assert base.lignes[0]["status"] == "completed"
    assert base.lignes[0]["from_vector"] is None


# ── /compare/status ne plante jamais ─────────────────────────────────────

def test_status_sur_un_resultat_illisible_repond_failed(client, auth_headers, base):
    """Avant : 500 à chaque sondage, sans fin. Après : la comparaison se
    referme et le téléphone l'apprend."""
    base.lignes = [comparaison(status="completed",
                               result='{"score_global": 75, "message_poetique": "{A} et')]
    r = client.get("/compare/status/c1", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert r.json()["result"] is None
    ligne = base.lignes[0]
    assert ligne["status"] == "failed"
    assert ligne["result"] is None
    assert ligne["from_vector"] is None and ligne["to_vector"] is None


def test_status_sur_un_resultat_lisible_reste_inchange(client, auth_headers, base):
    base.lignes = [comparaison(status="completed", result='{"score_global": 75}')]
    r = client.get("/compare/status/c1", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["result"] == {"score_global": 75}


@pytest.mark.asyncio
async def test_une_reponse_coupee_mais_au_JSON_valide_est_refusee_aussi(base, monkeypatch):
    """Une troncature ne produit pas toujours un JSON cassé : le modèle peut
    s'arrêter juste après une accolade fermante, et rendre un objet valide
    mais AMPUTÉ (sans divergences, sans questions). `stop_reason` est le seul
    indice fiable — il faut donc le regarder pour lui-même."""
    base.lignes = [comparaison()]
    ampute = json.dumps({"score_global": 75, "message_poetique": "{A} et {B}."}, ensure_ascii=False)

    async def modele_coupe(**kwargs):
        return _reponse(ampute, stop_reason="max_tokens")

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "call_model", modele_coupe)
    monkeypatch.setattr(main, "send_push_notification", sans_push)
    await main.analyze_comparison("c1")
    assert base.lignes[0]["status"] == "failed", "une réponse coupée ne doit jamais devenir completed"
    assert base.lignes[0].get("result") in (None, "")


@pytest.mark.asyncio
async def test_le_compteur_suit_les_analyses_conservees_avec_fautes(base, monkeypatch):
    """Décision du 17/09 : on laisse passer un texte fautif après deux essais.
    Le compteur dit si ce choix reste raisonnable — au-delà d'environ 10 %,
    c'est le prompt qu'il faut revoir."""
    main.COMPTEUR_COMPARAISONS["total"] = 0
    main.COMPTEUR_COMPARAISONS["conservees_avec_fautes"] = 0
    fautif = json.dumps({"score_global": 70,
                         "message_poetique": "L'un avance, l'autre regarde."}, ensure_ascii=False)
    propre = json.dumps({"score_global": 80, "message_poetique": "{A} et {B}."}, ensure_ascii=False)

    async def sans_push(**kwargs):
        return None

    monkeypatch.setattr(main, "send_push_notification", sans_push)

    async def modele_fautif(**kwargs):
        return _reponse(fautif)

    monkeypatch.setattr(main, "call_model", modele_fautif)
    base.lignes = [comparaison()]
    await main.analyze_comparison("c1")
    assert main.COMPTEUR_COMPARAISONS == {"total": 1, "conservees_avec_fautes": 1}

    async def modele_propre(**kwargs):
        return _reponse(propre)

    monkeypatch.setattr(main, "call_model", modele_propre)
    base.lignes = [comparaison()]
    await main.analyze_comparison("c1")
    assert main.COMPTEUR_COMPARAISONS == {"total": 2, "conservees_avec_fautes": 1}
