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
