from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import sqlite3
from datetime import datetime, timedelta, timezone
import uuid
import json
import re

import feedparser
from email.utils import parsedate_to_datetime
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
APP_SECRET = os.environ.get("APP_SECRET")

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")

FRANCE_TRAVAIL_CLIENT_ID = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID")
FRANCE_TRAVAIL_CLIENT_SECRET = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET")

FT_AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
FT_API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place"

THEMEALDB_URL = "https://www.themealdb.com/api/json/v1/1"

SPOONACULAR_API_KEY = os.environ.get("SPOONACULAR_API_KEY")
SPOONACULAR_URL = "https://api.spoonacular.com"

NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")


spotify_token = None
spotify_token_expiry = 0

ft_token = None
ft_token_expiry = 0


def verify_secret(x_app_secret: str = None):
    if APP_SECRET and x_app_secret != APP_SECRET:
        raise HTTPException(status_code=401, detail="Non autorisé")


# ── BASE DE DONNÉES SERVEUR ──
def get_db():
    db = sqlite3.connect('gifts.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS gifts (
            id TEXT PRIMARY KEY,
            from_code TEXT NOT NULL,
            from_alias TEXT,
            to_code TEXT NOT NULL,
            trait TEXT NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            responded_at TEXT
        )
    ''')

    db.execute('''
    CREATE TABLE IF NOT EXISTS push_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        my_code TEXT UNIQUE NOT NULL,
        push_token TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    ''')

    db.execute('''
        CREATE TABLE IF NOT EXISTS comparisons (
            id TEXT PRIMARY KEY,
            from_code TEXT NOT NULL,
            to_code TEXT NOT NULL,
            from_vector TEXT,
            to_vector TEXT,
            from_accepted INTEGER DEFAULT 0,
            to_accepted INTEGER DEFAULT 0,
            result TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT
        )
    ''')


    db.commit()
    db.close()

init_db()


# ── RSS Sources par catégorie ──
RSS_SOURCES = {
    'general': [
        ('Le Monde', 'https://www.lemonde.fr/rss/une.xml'),
        ('Le Figaro', 'https://www.lefigaro.fr/rss/figaro_actualites.xml'),
        ('France Info', 'https://www.francetvinfo.fr/titres.rss'),
        ('20 Minutes', 'https://www.20minutes.fr/feeds/rss/news'),
        ('Libération', 'https://www.liberation.fr/arc/outboundfeeds/rss/'),
    ],
    'technology': [
        ('01net', 'https://www.01net.com/actualites/feed/'),
        ('Numerama', 'https://www.numerama.com/feed/'),
        ('Frandroid', 'https://www.frandroid.com/feed'),
        ('Korben', 'https://korben.info/feed'),
        ('Journal du Geek', 'https://www.journaldugeek.com/feed/'),
    ],
    'science': [
        ('Sciences et Avenir', 'https://www.sciencesetavenir.fr/rss.xml'),
        ('Futura Sciences', 'https://www.futura-sciences.com/rss/actualites.rss'),
        ('Science Post', 'https://sciencepost.fr/feed/'),
    ],
    'business': [
        ('Les Echos', 'https://www.lesechos.fr/rss/rss_une.xml'),
        ('Le Point Economie', 'https://www.lepoint.fr/economie/rss.xml'),
        ('BFM Business', 'https://www.bfmtv.com/rss/economie/'),
        ('Le Monde', 'https://www.lemonde.fr/economie-francaise/rss_full.xml'),
        ('Le Monde', 'https://www.lemonde.fr/economie-mondiale/rss_full.xml'),
        ('20 minutes', 'https://www.20minutes.fr/feeds/rss-economie.xml'),
         
    ],
    'entertainment': [
        ('Allociné', 'https://www.allocine.fr/rss/news.xml'),
        ('Première', 'http://www.premiere.fr/rss/actu-live'),
        ('Télérama', 'https://www.telerama.fr/rss/latest-articles.xml'),
        ('Télérama', 'https://www.telerama.fr/rss/une.xml'),
    ],
    'sports': [
        ("L'Equipe", 'https://dwh.lequipe.fr/api/edito/rss?path=/'),
        ('RMC Sport', 'https://rmcsport.bfmtv.com/rss/football/'),
        ('Eurosport', 'https://www.eurosport.fr/rss.xml'),
    ],
    'health': [
        ('Pourquoi Docteur', 'https://www.pourquoidocteur.fr/rss.xml'),
        ('Top Santé', 'https://www.topsante.com/rss.xml'),
        ('Santé Magazine', 'https://www.santemagazine.fr/feed'),
    ],
}

CATEGORY_KEYWORDS = {
    'general': 'actualité france',
    'technology': 'technologie intelligence artificielle numérique',
    'science': 'science découverte recherche',
    'business': 'économie entreprise finance',
    'entertainment': 'cinéma culture musique',
    'sports': 'sport football tennis',
    'health': 'santé médecine bien-être',
}



# ── MODÈLES ──
class MessageRequest(BaseModel):
    system: str
    messages: list
    max_tokens: int = 1000

class SendGiftRequest(BaseModel):
    from_code: str
    to_code: str
    trait: str
    message: Optional[str] = None

class RespondGiftRequest(BaseModel):
    gift_id: str
    accepted: bool

class RegisterAliasRequest(BaseModel):
    my_code: str
    their_code: str
    alias: str

class RegisterPushRequest(BaseModel):
    my_code: str
    push_token: str


class CompareRequestModel(BaseModel):
    from_code: str
    to_code: str

class CompareAcceptModel(BaseModel):
    comparison_id: str
    my_code: str
    my_vector: dict

class CompareRespondModel(BaseModel):
    comparison_id: str
    accepted: bool
    my_code: str
    my_vector: Optional[dict] = None

class JobSearchRequest(BaseModel):
    keywords: str = ''
    location: str = ''
    contract_type: str = ''
    results_per_page: int = 20
    page: int = 1
    permanent: str = ''
    contract: str = ''

class FranceTravailRequest(BaseModel):
    keywords: str = ''
    location: str = ''
    contract_type: str = ''
    results_per_page: int = 20

class TMDBRequest(BaseModel):
    title: str
    media_type: str = "movie"  # "movie" ou "tv"

class SpotifyRequest(BaseModel):
    artist: str
    album: str = ''

class RestaurantRequest(BaseModel):
    name: str
    location: str = ''

class RecipeRequest(BaseModel):
    title: str

class NewsRequest(BaseModel):
    category: str = 'general'
    keywords: str = ''
    language: str = 'fr'
    page_size: int = 15

class PersonalizedNewsRequest(BaseModel):
    profile_traits: list = []
    personality: dict = {}
    context: dict = {}
    category: str = 'general'
    page_size: int = 15
    feedback: dict = {}  # ← ajoute ça






# ── ENDPOINTS CLAUDE ──
@app.post("/recommend")
async def recommend(req: MessageRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    if not CLAUDE_API_KEY:
        raise HTTPException(status_code=500, detail="Clé API manquante")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": req.max_tokens,
                "system": req.system,
                "messages": req.messages,
            },
            timeout=30.0,
        )
    return response.json()

# ── ENDPOINTS GIFTS ──
@app.post("/gift/send_old")
async def send_gift_old(req: SendGiftRequest):
    db = get_db()

    # Vérifier que le code destinataire existe
    existing = db.execute(
        'SELECT id FROM gifts WHERE to_code = ? LIMIT 1', 
        (req.to_code,)
    ).fetchone()

    # Créer le gift
    gift_id = str(uuid.uuid4())[:8].upper()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()

    db.execute('''
        INSERT INTO gifts (id, from_code, to_code, trait, message, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (gift_id, req.from_code, req.to_code, req.trait, req.message, expires_at))
    db.commit()
    db.close()

    return { "success": True, "gift_id": gift_id }

@app.post("/gift/send")
async def send_gift(req: SendGiftRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()

    gift_id = str(uuid.uuid4())[:8].upper()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()

    db.execute('''
        INSERT INTO gifts (id, from_code, to_code, trait, message, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (gift_id, req.from_code, req.to_code, req.trait, req.message, expires_at))
    db.commit()

    # Récupérer le token push du destinataire
    token_row = db.execute(
        'SELECT push_token FROM push_tokens WHERE my_code = ?',
        (req.to_code,)
    ).fetchone()
    db.close()

    # Envoyer la notification push si token disponible
    if token_row:
        await send_push_notification(
            push_token=token_row['push_token'],
            title='🎁 Nouveau trait reçu !',
            body=f'Quelqu\'un pense que tu as une qualité particulière...',
            data={'screen': 'ReceivedGifts', 'gift_id': gift_id}
        )

    return {"success": True, "gift_id": gift_id}




@app.get("/gift/received/{my_code}")
async def get_received(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    gifts = db.execute('''
        SELECT * FROM gifts 
        WHERE to_code = ? 
        AND status = 'pending'
        AND expires_at > datetime('now')
        ORDER BY created_at DESC
    ''', (my_code,)).fetchall()
    db.close()
    return { "gifts": [dict(g) for g in gifts] }

@app.get("/gift/sent/{my_code}")
async def get_sent(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    gifts = db.execute('''
        SELECT * FROM gifts 
        WHERE from_code = ?
        ORDER BY created_at DESC
        LIMIT 50
    ''', (my_code,)).fetchall()
    db.close()
    return { "gifts": [dict(g) for g in gifts] }

@app.post("/gift/respond")
async def respond_gift(req: RespondGiftRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    db = get_db()
    status = 'accepted' if req.accepted else 'rejected'
    db.execute('''
        UPDATE gifts 
        SET status = ?, responded_at = datetime('now')
        WHERE id = ?
    ''', (status, req.gift_id))
    db.commit()

    # Récupérer le gift pour retourner les infos
    gift = db.execute(
        'SELECT * FROM gifts WHERE id = ?', 
        (req.gift_id,)
    ).fetchone()
    db.close()

    return { "success": True, "gift": dict(gift) }

@app.post("/gift/register-alias")
async def register_alias(req: RegisterAliasRequest):
    db = get_db()
    # Enregistrer l'alias dans un gift fictif pour mémoriser la relation
    db.execute('''
        INSERT OR REPLACE INTO gifts (id, from_code, to_code, trait, status)
        VALUES (?, ?, ?, 'CONNECTION', 'connection')
    ''', (f"CONN_{req.my_code}_{req.their_code}", req.my_code, req.their_code, 'CONNECTION'))
    db.commit()
    db.close()
    return { "success": True }

@app.get("/gift/check-code/{code}")
async def check_code(code: str):
    # Vérifier si un code existe déjà dans le système
    db = get_db()
    exists = db.execute(
        'SELECT COUNT(*) as count FROM gifts WHERE from_code = ? OR to_code = ?',
        (code, code)
    ).fetchone()
    db.close()
    return { "exists": exists['count'] > 0 }

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/push/register")
async def register_push(req: RegisterPushRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    db.execute('''
        INSERT INTO push_tokens (my_code, push_token)
        VALUES (?, ?)
        ON CONFLICT(my_code) DO UPDATE SET 
        push_token = excluded.push_token,
        updated_at = datetime('now')
    ''', (req.my_code, req.push_token))
    db.commit()
    db.close()
    return {"success": True}

@app.get("/push/token/{my_code}")
async def get_push_token(my_code: str):
    db = get_db()
    row = db.execute(
        'SELECT push_token FROM push_tokens WHERE my_code = ?',
        (my_code,)
    ).fetchone()
    db.close()
    return {"push_token": row['push_token'] if row else None}

@app.post("/compare/request")
async def request_comparison(req: CompareRequestModel, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    
    # Vérifier qu'il n'y a pas déjà une demande en cours
    existing = db.execute('''
        SELECT id FROM comparisons 
        WHERE ((from_code = ? AND to_code = ?) OR (from_code = ? AND to_code = ?))
        AND status = 'pending'
        AND expires_at > datetime('now')
    ''', (req.from_code, req.to_code, req.to_code, req.from_code)).fetchone()
    
    if existing:
        db.close()
        return {"success": False, "error": "Une demande est déjà en cours"}
    
    comparison_id = str(uuid.uuid4())[:8].upper()
    # 10 minutes
    # expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()

    # APRÈS — 24 heures
    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
    
    db.execute('''
        INSERT INTO comparisons (id, from_code, to_code, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (comparison_id, req.from_code, req.to_code, expires_at))
    db.commit()
    
    # Envoyer notification push au destinataire
    token_row = db.execute(
        'SELECT push_token FROM push_tokens WHERE my_code = ?',
        (req.to_code,)
    ).fetchone()
    db.close()
    
    if token_row:
        await send_push_notification(
            push_token=token_row['push_token'],
            title='🔍 Demande de comparaison',
            body='Quelqu\'un veut comparer vos profils de jumeaux !',
            data={'screen': 'CompareRequest', 'comparison_id': comparison_id}
        )
    
    return {"success": True, "comparison_id": comparison_id}

@app.post("/compare/respond")
async def respond_comparison(req: CompareRespondModel, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    
    comparison = db.execute(
        'SELECT * FROM comparisons WHERE id = ?',
        (req.comparison_id,)
    ).fetchone()
    
    if not comparison:
        db.close()
        raise HTTPException(status_code=404, detail="Comparaison non trouvée")
    
    if comparison['expires_at'] < datetime.now().isoformat():
        db.close()
        return {"success": False, "error": "La demande a expiré"}
    
    if not req.accepted:
        db.execute(
            'UPDATE comparisons SET status = ? WHERE id = ?',
            ('rejected', req.comparison_id)
        )
        db.commit()
        db.close()
        return {"success": True, "status": "rejected"}
    
    # Mettre à jour le vecteur selon qui répond
    is_from = comparison['from_code'] == req.my_code
    
    if is_from:
        db.execute('''
            UPDATE comparisons 
            SET from_accepted = 1, from_vector = ?
            WHERE id = ?
        ''', (json.dumps(req.my_vector), req.comparison_id))
    else:
        db.execute('''
            UPDATE comparisons 
            SET to_accepted = 1, to_vector = ?
            WHERE id = ?
        ''', (json.dumps(req.my_vector), req.comparison_id))
    
    db.commit()
    
    # Vérifier si les deux ont accepté
    updated = db.execute(
        'SELECT * FROM comparisons WHERE id = ?',
        (req.comparison_id,)
    ).fetchone()
    
    if updated['from_accepted'] and updated['to_accepted']:
        # Les deux ont accepté → générer la comparaison
        db.execute(
            'UPDATE comparisons SET status = ? WHERE id = ?',
            ('analyzing', req.comparison_id)
        )
        db.commit()
        db.close()
        
        # Lancer l'analyse en arrière-plan
        import asyncio
        asyncio.create_task(analyze_comparison(req.comparison_id))
        
        return {"success": True, "status": "analyzing"}
    
    db.close()
    return {"success": True, "status": "waiting"}

@app.get("/compare/status/{comparison_id}")
async def get_comparison_status(comparison_id: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    comparison = db.execute(
        'SELECT * FROM comparisons WHERE id = ?',
        (comparison_id,)
    ).fetchone()
    db.close()
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparaison non trouvée")
    
    return {
        "status": comparison['status'],
        "result": json.loads(comparison['result']) if comparison['result'] else None,
        "expires_at": comparison['expires_at'],
    }

@app.get("/compare/pending/{my_code}")
async def get_pending_comparisons(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    comparisons = db.execute('''
        SELECT * FROM comparisons 
        WHERE to_code = ? 
        AND status = 'pending'
        AND to_accepted = 0
        AND expires_at > datetime('now')
        ORDER BY created_at DESC
    ''', (my_code,)).fetchall()
    db.close()
    return {"comparisons": [dict(c) for c in comparisons]}

async def analyze_comparison(comparison_id: str):
    db = get_db()
    comparison = db.execute(
        'SELECT * FROM comparisons WHERE id = ?',
        (comparison_id,)
    ).fetchone()
    
    from_vector = json.loads(comparison['from_vector'])
    to_vector = json.loads(comparison['to_vector'])
    
    prompt = f"""Tu es un expert en psychologie et compatibilité interpersonnelle.
Compare ces deux profils psychométriques anonymes et génère une analyse de convergences et divergences.

PROFIL A : {json.dumps(from_vector)}
PROFIL B : {json.dumps(to_vector)}

Retourne UNIQUEMENT un JSON valide :
{{
  "score_global": 75,
  "archetype_a": "L'Explorateur",
  "archetype_b": "Le Gardien", 
  "archetype_commun": "L'Aventure Ancrée",
  "convergences": [
    {{"dimension": "Empathie", "score_a": 0.8, "score_b": 0.85, "description": "Très similaires dans leur sensibilité aux autres"}},
    {{"dimension": "Curiosité", "score_a": 0.7, "score_b": 0.75, "description": "Partagent un goût pour l'apprentissage"}}
  ],
  "divergences": [
    {{"dimension": "Rythme de vie", "score_a": 0.8, "score_b": 0.3, "description": "L'un est très actif, l'autre contemplatif"}},
    {{"dimension": "Goûts culturels", "score_a": 0.9, "score_b": 0.4, "description": "Des univers culturels très différents"}}
  ],
  "superpower": "Empathie profonde",
  "tension": "Rythme de vie",
  "questions_conversation": [
    "Vous aimez tous les deux la nature — plutôt randonnée intense ou balade contemplative ?",
    "Votre curiosité commune vous pousse-t-elle vers les mêmes sujets ou des directions opposées ?",
    "Comment vos rythmes de vie différents se complètent-ils au quotidien ?"
  ],
  "message_poetique": "Deux rivières qui coulent à des vitesses différentes, mais qui nourrissent le même territoire."
}}"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30.0,
        )
    
    data = response.json()
    result_text = data['content'][0]['text']
    
    # Parser le JSON
    import re
    json_match = re.search(r'\{[\s\S]*\}', result_text)
    if json_match:
        result = json_match.group(0)
        db.execute(
            'UPDATE comparisons SET status = ?, result = ? WHERE id = ?',
            ('completed', result, comparison_id)
        )
        db.commit()
        
        # Notifier les deux jumeaux
        for code_field in ['from_code', 'to_code']:
            token_row = db.execute(
                'SELECT push_token FROM push_tokens WHERE my_code = ?',
                (comparison[code_field],)
            ).fetchone()
            if token_row:
                await send_push_notification(
                    push_token=token_row['push_token'],
                    title='✨ Comparaison prête !',
                    body='Découvrez vos points communs et différences !',
                    data={'screen': 'CompareResult', 'comparison_id': comparison_id}
                )
    
    db.close()








async def send_push_notification(push_token: str, title: str, body: str, data: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://exp.host/--/api/v2/push/send',
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                json={
                    'to': push_token,
                    'title': title,
                    'body': body,
                    'data': data,
                    'sound': 'default',
                    'badge': 1,
                }
            )
            print(f'Push envoyé: {response.status_code}')
            return response.json()
    except Exception as e:
        print(f'ERREUR push: {e}')
        return None
    

@app.post("/jobs/adzuna")
async def search_adzuna(req: JobSearchRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    
    try:
        url = f"https://api.adzuna.com/v1/api/jobs/fr/search/{req.page}"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": req.results_per_page,
            "content-type": "application/json",
        }
        if req.keywords: params["what"] = req.keywords
        if req.location: params["where"] = req.location
        if req.permanent == '1': params["permanent"] = '1'
        if req.contract == '1': params["contract"] = '1'

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            data = response.json()

        if "results" not in data:
            return {"results": []}

        jobs = [{
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company", {}).get("display_name", "Entreprise non précisée"),
            "location": job.get("location", {}).get("display_name", "Lieu non précisé"),
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "description": job.get("description"),
            "contract_type": job.get("contract_type"),
            "created": job.get("created"),
            "redirect_url": job.get("redirect_url"),
            "category": job.get("category", {}).get("label"),
        } for job in data["results"]]

        return {"results": jobs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

async def get_france_travail_token():
    global ft_token, ft_token_expiry
    import time
    
    if ft_token and time.time() < ft_token_expiry:
        return ft_token
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FT_AUTH_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": FRANCE_TRAVAIL_CLIENT_ID,
                "client_secret": FRANCE_TRAVAIL_CLIENT_SECRET,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            timeout=10.0,
        )
        data = response.json()
        ft_token = data.get("access_token")
        ft_token_expiry = time.time() + data.get("expires_in", 1400) - 60
        return ft_token

CITY_DEPT_MAP = {
    'paris': '75', 'marseille': '13', 'lyon': '69',
    'toulouse': '31', 'nice': '06', 'nantes': '44',
    'strasbourg': '67', 'montpellier': '34', 'bordeaux': '33',
    'lille': '59', 'rennes': '35', 'reims': '51',
    'saint-etienne': '42', 'toulon': '83', 'grenoble': '38',
    'dijon': '21', 'angers': '49', 'nimes': '30',
    'clermont-ferrand': '63', 'aix-en-provence': '13',
    'brest': '29', 'amiens': '80', 'limoges': '87',
    'tours': '37', 'metz': '57', 'arras': '62',
    'lens': '62', 'douai': '59', 'valenciennes': '59',
    'dunkerque': '59', 'calais': '62', 'le havre': '76',
    'rouen': '76', 'caen': '14', 'nancy': '54',
    'mulhouse': '68', 'perpignan': '66', 'besancon': '25',
    'orleans': '45', 'poitiers': '86', 'pau': '64',
}

def get_dept_code(city: str) -> str:
    if not city:
        return None
    city_lower = city.lower().strip()
    for key, code in CITY_DEPT_MAP.items():
        if city_lower in key or key in city_lower:
            return code
    if city.strip().isdigit() and len(city.strip()) <= 3:
        return city.strip()
    return None


@app.post("/jobs/france-travail")
async def search_france_travail(req: FranceTravailRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    
    try:
        token = await get_france_travail_token()
        print(f"Token FT: {token[:20] if token else 'None'}...")
        
        if not token:
            raise HTTPException(status_code=500, detail="Token France Travail non disponible")

        params = f"range=0-{req.results_per_page - 1}"
        if req.keywords:
            params += f"&motsCles={req.keywords}"
        if req.location:
            dept = get_dept_code(req.location)
            print(f"Ville: {req.location} → Dept: {dept}")
            if dept:
                params += f"&departement={dept}"
        if req.contract_type:
            params += f"&typeContrat={req.contract_type}"

        print(f"URL FT: {FT_API_URL}?{params}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FT_API_URL}?{params}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=15.0,
            )

        print(f"Status FT: {response.status_code}")

        if response.status_code == 204:
            return {"results": []}

        if response.status_code == 403:
            print("Erreur 403 — scope insuffisant ou token invalide")
            return {"results": []}

        if response.status_code not in [200, 206]:
            print(f"Erreur HTTP {response.status_code}")
            return {"results": []}

        data = response.json()
        if "resultats" not in data:
            return {"results": []}

        jobs = [{
            "id": job.get("id"),
            "title": job.get("intitule"),
            "company": job.get("entreprise", {}).get("nom", "Entreprise non précisée"),
            "location": job.get("lieuTravail", {}).get("libelle", "Lieu non précisé"),
            "salary_min": job.get("salaire", {}).get("commentaire"),
            "salary_max": None,
            "description": job.get("description"),
            "contract_type": job.get("typeContratLibelle"),
            "created": job.get("dateCreation"),
            "redirect_url": f"https://candidat.francetravail.fr/offres/recherche/detail/{job.get('id')}",
            "category": job.get("appellationlibelle"),
            "source": "france_travail",
        } for job in data["resultats"]]

        return {"results": jobs}

    except Exception as e:
        print(f"ERREUR France Travail: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/media/details")
async def get_media_details(req: TMDBRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    try:
        # Recherche du film/série
        search_url = f"{TMDB_BASE_URL}/search/{req.media_type}"
        params = {
            "api_key": TMDB_API_KEY,
            "query": req.title,
            "language": "fr-FR",
        }

        async with httpx.AsyncClient() as client:
            search_response = await client.get(search_url, params=params, timeout=10.0)
            search_data = search_response.json()

        if not search_data.get("results"):
            return {"result": None}

        item = search_data["results"][0]
        item_id = item["id"]

        # Détails complets
        detail_url = f"{TMDB_BASE_URL}/{req.media_type}/{item_id}"
        detail_params = {
            "api_key": TMDB_API_KEY,
            "language": "fr-FR",
            "append_to_response": "videos,credits,watch/providers",
        }

        async with httpx.AsyncClient() as client:
            detail_response = await client.get(detail_url, params=detail_params, timeout=10.0)
            detail = detail_response.json()

        # Trailer YouTube
        trailer = None
        for video in detail.get("videos", {}).get("results", []):
            if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                trailer = f"https://www.youtube.com/watch?v={video['key']}"
                break

        # Casting principal
        cast = []
        for person in detail.get("credits", {}).get("cast", [])[:5]:
            cast.append(person.get("name"))

        # Plateformes de streaming (France)
        providers = []
        watch_providers = detail.get("watch/providers", {}).get("results", {}).get("FR", {})
        for p in watch_providers.get("flatrate", [])[:4]:
            providers.append(p.get("provider_name"))

        # Poster
        poster_path = detail.get("poster_path")
        poster_url = f"{TMDB_IMAGE_URL}{poster_path}" if poster_path else None

        # Durée
        runtime = detail.get("runtime")  # films
        if not runtime:
            episode_runtime = detail.get("episode_run_time", [])
            runtime = episode_runtime[0] if episode_runtime else None

        result = {
            "poster_url": poster_url,
            "overview": detail.get("overview"),
            "vote_average": round(detail.get("vote_average", 0), 1),
            "vote_count": detail.get("vote_count"),
            "release_date": detail.get("release_date") or detail.get("first_air_date"),
            "runtime": runtime,
            "genres": [g["name"] for g in detail.get("genres", [])[:3]],
            "cast": cast,
            "trailer_url": trailer,
            "providers": providers,
            "tmdb_url": f"https://www.themoviedb.org/{req.media_type}/{item_id}",
            "amazon_url": f"https://www.amazon.fr/s?k={req.title}",
        }

        return {"result": result}

    except Exception as e:
        print(f"ERREUR TMDB: {str(e)}")
        return {"result": None}
    

async def get_spotify_token():
    global spotify_token, spotify_token_expiry
    import time, base64

    if spotify_token and time.time() < spotify_token_expiry:
        return spotify_token

    credentials = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_AUTH_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=10.0,
        )
        data = response.json()
        spotify_token = data.get("access_token")
        spotify_token_expiry = time.time() + data.get("expires_in", 3500) - 60
        return spotify_token
    

@app.post("/music/details")
async def get_music_details(req: SpotifyRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    try:
        token = await get_spotify_token()
        if not token:
            return {"result": None}

        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:

            # Recherche artiste
            query = req.artist
            if req.album:
                query += f" {req.album}"

            search_response = await client.get(
                f"{SPOTIFY_API_URL}/search",
                headers=headers,
                params={
                    "q": query,
                    "type": "artist,album",
                    "market": "FR",
                    "limit": 1,
                },
                timeout=10.0,
            )
            search_data = search_response.json()

        artist = None
        album = None

        # Récupérer l'artiste
        artists = search_data.get("artists", {}).get("items", [])
        if artists:
            artist = artists[0]

        # Récupérer l'album
        albums = search_data.get("albums", {}).get("items", [])
        if albums:
            album = albums[0]

        if not artist and not album:
            return {"result": None}

        # Image artiste ou album
        image_url = None
        if album and album.get("images"):
            image_url = album["images"][0]["url"]
        elif artist and artist.get("images"):
            image_url = artist["images"][0]["url"]

        # Genres
        genres = artist.get("genres", [])[:4] if artist else []

        # Popularité
        popularity = artist.get("popularity") if artist else None

        # Top tracks de l'artiste
        top_tracks = []
        if artist:
            async with httpx.AsyncClient() as client:
                tracks_response = await client.get(
                    f"{SPOTIFY_API_URL}/artists/{artist['id']}/top-tracks",
                    headers=headers,
                    params={"market": "FR"},
                    timeout=10.0,
                )
                tracks_data = tracks_response.json()
                for track in tracks_data.get("tracks", [])[:5]:
                    top_tracks.append({
                        "name": track["name"],
                        "preview_url": track.get("preview_url"),
                        "duration_ms": track.get("duration_ms"),
                        "spotify_url": track["external_urls"].get("spotify"),
                    })

        result = {
            "image_url": image_url,
            "genres": genres,
            "popularity": popularity,
            "followers": artist.get("followers", {}).get("total") if artist else None,
            "top_tracks": top_tracks,
            "spotify_artist_url": artist["external_urls"].get("spotify") if artist else None,
            "spotify_album_url": album["external_urls"].get("spotify") if album else None,
            "album_name": album.get("name") if album else None,
            "album_release_date": album.get("release_date") if album else None,
            "amazon_url": f"https://www.amazon.fr/s?k={req.artist}+musique",
        }

        return {"result": result}

    except Exception as e:
        print(f"ERREUR Spotify: {str(e)}")
        return {"result": None}
    

@app.post("/restaurant/details")
async def get_restaurant_details(req: RestaurantRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    try:
        async with httpx.AsyncClient() as client:

            # Étape 1 — Recherche du restaurant
            query = req.name
            if req.location:
                query += f" {req.location}"

            search_response = await client.get(
                f"{GOOGLE_PLACES_URL}/textsearch/json",
                params={
                    "query": query + " restaurant",
                    "key": GOOGLE_PLACES_API_KEY,
                    "language": "fr",
                    "region": "fr",
                },
                timeout=10.0,
            )
            search_data = search_response.json()

            if not search_data.get("results"):
                return {"result": None}

            place = search_data["results"][0]
            place_id = place.get("place_id")

            # Étape 2 — Détails complets
            detail_response = await client.get(
                f"{GOOGLE_PLACES_URL}/details/json",
                params={
                    "place_id": place_id,
                    "key": GOOGLE_PLACES_API_KEY,
                    "language": "fr",
                    "fields": "name,rating,user_ratings_total,formatted_address,opening_hours,price_level,photos,website,url,formatted_phone_number,types",
                },
                timeout=10.0,
            )
            detail_data = detail_response.json()
            detail = detail_data.get("result", {})

            # Photo principale
            photo_url = None
            photos = detail.get("photos") or place.get("photos", [])
            if photos:
                photo_ref = photos[0].get("photo_reference")
                if photo_ref:
                    photo_url = (
                        f"{GOOGLE_PLACES_URL}/photo"
                        f"?maxwidth=600"
                        f"&photo_reference={photo_ref}"
                        f"&key={GOOGLE_PLACES_API_KEY}"
                    )

            # Prix
            price_level = detail.get("price_level") or place.get("price_level")
            price_str = None
            if price_level is not None:
                price_str = '💰' * (price_level + 1) if price_level > 0 else 'Gratuit'

            # Horaires
            opening_hours = detail.get("opening_hours", {})
            is_open = opening_hours.get("open_now")
            weekday_text = opening_hours.get("weekday_text", [])

            # Types de cuisine
            types = detail.get("types", place.get("types", []))
            cuisine_types = [
                t.replace('_', ' ').title()
                for t in types
                if t not in ['restaurant', 'food', 'point_of_interest',
                             'establishment', 'store']
            ][:3]

            result = {
                "photo_url": photo_url,
                "name": detail.get("name") or place.get("name"),
                "rating": detail.get("rating") or place.get("rating"),
                "user_ratings_total": detail.get("user_ratings_total") or place.get("user_ratings_total"),
                "address": detail.get("formatted_address") or place.get("formatted_address"),
                "price_level": price_str,
                "is_open": is_open,
                "weekday_text": weekday_text[:3],
                "phone": detail.get("formatted_phone_number"),
                "website": detail.get("website"),
                "google_maps_url": detail.get("url") or f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                "cuisine_types": cuisine_types,
            }

            return {"result": result}

    except Exception as e:
        print(f"ERREUR Google Places: {str(e)}")
        return {"result": None}
    

@app.post("/recipe/details")
async def get_recipe_details(req: RecipeRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    try:
        print(f"🔍 Recherche recette Spoonacular: {req.title}")

        async with httpx.AsyncClient() as client:

            # Étape 1 — Recherche par titre
            search_response = await client.get(
                f"{SPOONACULAR_URL}/recipes/complexSearch",
                params={
                    "apiKey": SPOONACULAR_API_KEY,
                    "query": req.title,
                    "language": "fr",
                    "number": 1,
                    "addRecipeInformation": True,
                    "fillIngredients": True,
                },
                timeout=15.0,
            )
            search_data = search_response.json()
            print(f"Status Spoonacular: {search_response.status_code}")

            # Si pas de résultat en français, chercher en anglais
            if not search_data.get("results"):
                print("🔍 Tentative en anglais...")

                # Simplifier le titre via Claude
                simplify_response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": CLAUDE_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 20,
                        "messages": [{
                            "role": "user",
                            "content": f'Give the simplified English name (1-4 words) of this recipe for a search. Reply ONLY with the name: "{req.title}"'
                        }],
                    },
                    timeout=10.0,
                )
                simplified = simplify_response.json()['content'][0]['text'].strip()
                print(f"🔍 Titre simplifié: {simplified}")

                search_response = await client.get(
                    f"{SPOONACULAR_URL}/recipes/complexSearch",
                    params={
                        "apiKey": SPOONACULAR_API_KEY,
                        "query": simplified,
                        "number": 1,
                        "addRecipeInformation": True,
                        "fillIngredients": True,
                    },
                    timeout=15.0,
                )
                search_data = search_response.json()

        if not search_data.get("results"):
            print(f"❌ Aucune recette trouvée pour: {req.title}")
            return {"result": None}

        recipe = search_data["results"][0]
        recipe_id = recipe["id"]
        print(f"✅ Recette trouvée: {recipe.get('title')}")

        # Étape 2 — Détails complets avec instructions
        async with httpx.AsyncClient() as client:
            detail_response = await client.get(
                f"{SPOONACULAR_URL}/recipes/{recipe_id}/information",
                params={
                    "apiKey": SPOONACULAR_API_KEY,
                    "includeNutrition": False,
                },
                timeout=15.0,
            )
            detail = detail_response.json()

        # Extraire les ingrédients
        ingredients = []
        for ing in detail.get("extendedIngredients", []):
            ingredients.append({
                "ingredient": ing.get("name", ""),
                "measure": f"{ing.get('amount', '')} {ing.get('unit', '')}".strip(),
            })

        # Extraire les étapes
        steps_raw = []
        for instruction in detail.get("analyzedInstructions", []):
            for step in instruction.get("steps", []):
                steps_raw.append(step.get("step", ""))

        # Temps de préparation
        ready_in = detail.get("readyInMinutes")
        servings = detail.get("servings")

        # Cuisines et régimes
        cuisines = detail.get("cuisines", [])
        diets = detail.get("diets", [])

        # Traduction via Claude
        ingredients_str = "\n".join([
            f"- {i['measure']} {i['ingredient']}"
            for i in ingredients
        ])
        steps_str = "\n".join([
            f"{idx+1}. {s}"
            for idx, s in enumerate(steps_raw[:12])
        ])

        translation_prompt = f"""Traduis en français ces informations de recette de cuisine.

NOM ORIGINAL : {recipe.get('title')}
CUISINES : {', '.join(cuisines) if cuisines else 'International'}
RÉGIMES : {', '.join(diets) if diets else ''}
TEMPS : {ready_in} minutes
PORTIONS : {servings}

INGRÉDIENTS :
{ingredients_str}

ÉTAPES :
{steps_str}

Retourne UNIQUEMENT ce JSON valide sans texte avant ni après :
{{
  "name_fr": "nom de la recette en français",
  "cuisine_fr": "type de cuisine en français",
  "diets_fr": ["régime 1", "régime 2"],
  "ingredients_fr": [
    {{"ingredient": "ingrédient traduit", "measure": "mesure traduite"}}
  ],
  "steps_fr": [
    "étape 1 traduite et reformulée clairement",
    "étape 2 traduite"
  ]
}}"""

        async with httpx.AsyncClient() as client:
            claude_response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": translation_prompt}],
                },
                timeout=30.0,
            )
            translation_text = claude_response.json()['content'][0]['text']

        # Parser la traduction
        json_match = re.search(r'\{[\s\S]*\}', translation_text)
        translation = {}
        if json_match:
            try:
                translation = json.loads(json_match.group(0))
                print(f"✅ Traduction OK: {translation.get('name_fr')}")
            except Exception as e:
                print(f"⚠️ Erreur parsing: {e}")

        result = {
            "name": translation.get("name_fr") or recipe.get("title"),
            "category": translation.get("cuisine_fr") or (cuisines[0] if cuisines else "International"),
            "area": translation.get("cuisine_fr") or "",
            "diets": translation.get("diets_fr") or diets,
            "image_url": recipe.get("image") or detail.get("image"),
            "ready_in_minutes": ready_in,
            "servings": servings,
            "ingredients": translation.get("ingredients_fr") or ingredients,
            "steps": translation.get("steps_fr") or steps_raw[:12],
            "source_url": detail.get("sourceUrl"),
            "spoonacular_url": f"https://spoonacular.com/recipes/{detail.get('title', '').replace(' ', '-').lower()}-{recipe_id}",
            "youtube_url": None,
            "tags": diets[:3] if diets else [],
        }

        return {"result": result}

    except Exception as e:
        print(f"❌ ERREUR Spoonacular: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"result": None}
    

@app.post("/news/articles_old")
async def get_news_old(req: NewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    try:
        # Mapping catégories → mots-clés français
        CATEGORY_KEYWORDS = {
            'general': 'actualité france',
            'technology': 'technologie intelligence artificielle',
            'science': 'science découverte recherche',
            'business': 'économie entreprise bourse',
            'entertainment': 'cinéma culture musique',
            'sports': 'sport football tennis',
            'health': 'santé médecine bien-être',
        }

        keywords = req.keywords or CATEGORY_KEYWORDS.get(req.category, 'actualité')

        async with httpx.AsyncClient() as client:
            params = {
                "apiKey": NEWS_API_KEY,
                "q": keywords,
                "language": "fr",
                "sortBy": "publishedAt",
                "pageSize": req.page_size,
            }
            print(f"🔍 Everything search: {params}")
            response = await client.get(
                f"{NEWS_API_URL}/everything",
                params=params,
                timeout=15.0,
            )

        data = response.json()
        print(f"📰 Total: {data.get('totalResults', 0)}")

        if data.get("status") != "ok":
            return {"articles": []}

        articles = []
        for article in data.get("articles", []):
            if not article.get("title") or article.get("title") == "[Removed]":
                continue
            articles.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "url": article.get("url"),
                "image_url": article.get("urlToImage"),
                "source": article.get("source", {}).get("name"),
                "published_at": article.get("publishedAt"),
                "author": article.get("author"),
            })

        return {"articles": articles}

    except Exception as e:
        print(f"ERREUR NewsAPI: {str(e)}")
        return {"articles": []}
    



def extract_image_from_entry(entry):
    """Extrait l'image d'un article RSS"""
    # Media content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('medium') == 'image' or 'image' in media.get('type', ''):
                return media.get('url')

    # Media thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url')

    # Enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href')

    # Image dans le contenu HTML
    content = ''
    if hasattr(entry, 'content') and entry.content:
        content = entry.content[0].get('value', '')
    elif hasattr(entry, 'summary'):
        content = entry.summary or ''

    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    if img_match:
        url = img_match.group(1)
        if url.startswith('http'):
            return url

    return None

def parse_date(entry):
    """Parse la date d'un article RSS"""
    try:
        if hasattr(entry, 'published'):
            return parsedate_to_datetime(entry.published).isoformat()
    except:
        pass
    try:
        if hasattr(entry, 'updated'):
            return parsedate_to_datetime(entry.updated).isoformat()
    except:
        pass
    return datetime.now().isoformat()

def clean_html(text):
    """Supprime les balises HTML d'un texte"""
    if not text:
        return ''
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:300] if len(clean) > 300 else clean

async def fetch_rss_source(source_name: str, url: str, max_items: int = 5):
    """Fetch un flux RSS et retourne les articles.
    Marque automatiquement le flux inactif dans Supabase s'il est vraiment mort.
    """
    try:
        loop = asyncio.get_event_loop()

        # Fetch avec timeout via executor
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url),
            timeout=15.0
        )

        # Flux vraiment mort — domaine inexistant ou erreur réseau fatale
        if feed.bozo and not feed.entries:
            bozo_exception = str(feed.get('bozo_exception', ''))
            # Erreurs fatales → marquer inactif
            fatal_errors = [
                'Name or service not known',
                'nodename nor servname provided',
                'No address associated',
                'Connection refused',
                'No route to host',
                'urlopen error',
            ]
            is_fatal = any(err in bozo_exception for err in fatal_errors)
            if is_fatal:
                print(f"💀 Flux mort, marquage inactif : {source_name}")
                await mark_feed_inactive(url)
            return []

        # Flux vivant mais vide → pas de marquage
        if not feed.entries:
            return []

        # Parser les articles
        articles = []
        for entry in feed.entries[:max_items]:
            title = clean_html(entry.get('title', ''))
            if not title or title == '[Removed]':
                continue

            articles.append({
                "title": title,
                "description": clean_html(entry.get('summary', '')),
                "url": entry.get('link', ''),
                "image_url": extract_image_from_entry(entry),
                "source": source_name,
                "published_at": parse_date(entry),
                "author": entry.get('author', ''),
                "source_type": "rss",
            })
            print(f"   {'✅' if articles else '⚠️ '} {source_name} → {len(articles)} articles | {url[:60]}")
        return articles

    except asyncio.TimeoutError:
        # Timeout → lent mais pas forcément mort
        print(f"⏱ Timeout RSS {source_name} — ignoré")
        return []
    except Exception as e:
        print(f"⚠️ Erreur RSS {source_name}: {str(e)[:100]}")
        return []


async def mark_feed_inactive(url: str):
    """Marque un flux comme inactif dans Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/rss_feeds",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                },
                params={"feed_url": f"eq.{url}"},
                json={"is_active": False},
                timeout=5.0,
            )
    except Exception as e:
        print(f"⚠️ Erreur mark_feed_inactive: {str(e)[:50]}")


@app.post("/news/articles")
async def get_news(req: NewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    try:
        print(f"🔍 News request: category={req.category}, keywords={req.keywords}")

        all_articles = []

        # ── 1. Fetch RSS depuis Supabase ──
        rss_sources = await get_feeds_from_supabase(
            category=req.category,
            limit=15,
        )

        rss_tasks = [
            fetch_rss_source(name, url, max_items=4)
            for name, url in rss_sources
        ]
        rss_results = await asyncio.gather(*rss_tasks, return_exceptions=True)
        for result in rss_results:
            if isinstance(result, list):
                all_articles.extend(result)

        print(f"📰 RSS articles: {len(all_articles)}")

        # ── 2. NewsAPI en complément ──
        try:
            keywords = req.keywords or CATEGORY_KEYWORDS.get(req.category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NEWS_API_URL}/everything",
                    params={
                        "apiKey": NEWS_API_KEY,
                        "q": keywords,
                        "language": "fr",
                        "sortBy": "publishedAt",
                        "pageSize": 10,
                    },
                    timeout=15.0,
                )
            data = response.json()
            for article in data.get("articles", []):
                if article.get("title") and article.get("title") != "[Removed]":
                    all_articles.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "image_url": article.get("urlToImage"),
                        "source": article.get("source", {}).get("name"),
                        "published_at": article.get("publishedAt"),
                        "source_type": "newsapi",
                    })
            print(f"📰 NewsAPI articles: {len(data.get('articles', []))}")
        except Exception as e:
            print(f"⚠️ NewsAPI error: {str(e)}")

        # ── 3. Dédupliquer ──
        seen = set()
        unique = []
        for a in all_articles:
            key = a.get('title', '')[:50].lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(a)

        # ── 4. Trier par date ──
        def sort_key(a):
            try:
                date_str = a.get('published_at', '')
                if not date_str:
                    return datetime.min.replace(tzinfo=timezone.utc)
                
                # Normaliser la date
                date_str = date_str.replace('Z', '+00:00')
                dt = datetime.fromisoformat(date_str)
                
                # Forcer timezone UTC si absent
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except:
                return datetime.min.replace(tzinfo=timezone.utc)

        unique.sort(key=sort_key, reverse=True)

        # ── 5. Filtrer et retourner ──
        final = [a for a in unique if a.get('title') and a.get('url')][:req.page_size]

        print(f"✅ Total articles final: {len(final)}")
        return {"articles": final}

    except Exception as e:
        print(f"❌ ERREUR get_news: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"articles": []}



@app.post("/news/personalized")
async def get_personalized_news(req: PersonalizedNewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        print(f"🔍 Personalized news: category={req.category}")

        # 1. Récupérer les articles RSS
        all_articles = []
        #AVANT rss_sources = RSS_SOURCES.get(req.category, RSS_SOURCES['general'])
        rss_sources = await get_feeds_from_supabase(category=req.category, limit=20)
        rss_tasks = [
            fetch_rss_source(name, url, max_items=5)
            for name, url in rss_sources
        ]
        rss_results = await asyncio.gather(*rss_tasks, return_exceptions=True)
        for result in rss_results:
            if isinstance(result, list):
                all_articles.extend(result)

        # 2. NewsAPI en complément
        try:
            keywords = CATEGORY_KEYWORDS.get(req.category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NEWS_API_URL}/everything",
                    params={
                        "apiKey": NEWS_API_KEY,
                        "q": keywords,
                        "language": "fr",
                        "sortBy": "publishedAt",
                        "pageSize": 10,
                    },
                    timeout=15.0,
                )
            data = response.json()
            for article in data.get("articles", []):
                if article.get("title") and article.get("title") != "[Removed]":
                    all_articles.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "image_url": article.get("urlToImage"),
                        "source": article.get("source", {}).get("name"),
                        "published_at": article.get("publishedAt"),
                    })
        except Exception as e:
            print(f"⚠️ NewsAPI error: {str(e)}")

        # 3. Dédupliquer
        seen = set()
        unique = []
        for a in all_articles:
            key = a.get('title', '')[:50].lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(a)

        if not unique:
            return {"articles": []}

        # 4. Préparer le résumé des articles pour Claude
        articles_summary = "\n".join([
            f"{i+1}. [{a.get('source', '?')}] {a.get('title', '')} — {a.get('description', '')[:100] if a.get('description') else ''}"
            for i, a in enumerate(unique[:25])
        ])

        # 5. Construire le profil
        traits_str = ', '.join(req.profile_traits) if req.profile_traits else 'curieux, ouvert'
        context_lines = []
        if req.context.get('metier'): context_lines.append(f"Métier: {req.context['metier']}")
        if req.context.get('ville'): context_lines.append(f"Ville: {req.context['ville']}")
        if req.context.get('passions'): context_lines.append(f"Passions: {', '.join(req.context.get('passions', []))}")
        if req.context.get('valeurs'): context_lines.append(f"Valeurs: {', '.join(req.context.get('valeurs', []))}")
        context_str = '\n'.join(context_lines) if context_lines else ''

        # 6. Feedback utilisateur
        liked = req.feedback.get('liked', [])
        disliked = req.feedback.get('disliked', [])
        liked_str = ', '.join(liked[:5]) if liked else 'aucun'
        disliked_str = ', '.join(disliked[:5]) if disliked else 'aucun'
        feedback_str = f"""
HISTORIQUE DES PRÉFÉRENCES :
- Articles appréciés (4-5⭐) : {liked_str}
- Articles non appréciés (1-2⭐) : {disliked_str}
Tiens compte de ces préférences pour sélectionner les articles.
""" if liked or disliked else ''

        # 7. Claude sélectionne et commente
        prompt = f"""Tu es un assistant de curation d'actualités personnalisées.

PROFIL DE L'UTILISATEUR :
- Traits : {traits_str}
- Personnalité : extraversion {req.personality.get('extraversion', 0.5)}, ouverture {req.personality.get('openness', 0.5)}, curiosité {req.personality.get('curiosity', 0.5)}
{context_str}
{feedback_str}
ARTICLES DISPONIBLES :
{articles_summary}

Sélectionne les 5 articles les plus pertinents pour ce profil et explique brièvement pourquoi chacun correspond.
Retourne UNIQUEMENT ce JSON valide sans texte avant ni après :
{{
  "selected": [
    {{
      "index": 1,
      "why": "Explication courte (1 phrase) pourquoi cet article correspond au profil"
    }}
  ]
}}"""
        
        async with httpx.AsyncClient() as client:
            claude_response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20.0,
            )
            claude_data = claude_response.json()
            claude_text = claude_data['content'][0]['text']
            print(f"Claude PROMPT: {prompt}")
            print(f"Claude réponse: {claude_text[:200]}")

        # 8. Parser la réponse Claude
        json_match = re.search(r'\{[\s\S]*\}', claude_text)
        personalized = []

        if json_match:
            selection = json.loads(json_match.group(0))
            for item in selection.get('selected', []):
                idx = item.get('index', 1) - 1
                if 0 <= idx < len(unique):
                    article = unique[idx].copy()
                    article['why'] = item.get('why', '')
                    personalized.append(article)

        print(f"✅ Articles personnalisés: {len(personalized)}")
        return {"articles": personalized}

    except Exception as e:
        print(f"❌ ERREUR personalized news: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"articles": []}
    

async def get_feeds_from_supabase(category: str, limit: int = 15, region: str = None, is_youtube: bool = False):
    """Récupère des flux actifs depuis Supabase selon la catégorie"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        # Fallback sur RSS_SOURCES hardcodé
        return RSS_SOURCES.get(category, RSS_SOURCES['general'])

    try:
        params = {
            "select": "source_name,feed_url",
            "is_active": "eq.true",
            "is_youtube": f"eq.{str(is_youtube).lower()}",
            "limit": str(limit),
            "order": "id.asc",
        }

        # Filtre catégorie
        cat_map = {
            'general':       'presse',
            'technology':    'technologie',
            'science':       'culture',
            'business':      'économie',
            'entertainment': 'culture',
            'sports':        'sport',
            'health':        'culture',
            'local':         'local',
        }
        supabase_cat = cat_map.get(category, 'presse')
        params["categorie"] = f"eq.{supabase_cat}"

        # Filtre région optionnel
        if region:
            params["region"] = f"ilike.%{region}%"

        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/rss_feeds",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                params=params,
                timeout=10.0,
            )

        feeds = r.json()
        if not feeds or not isinstance(feeds, list):
            return RSS_SOURCES.get(category, RSS_SOURCES['general'])

        print(f"📡 Supabase: {len(feeds)} flux pour catégorie '{supabase_cat}'")
        for f in feeds:
            print(f"   → {f['source_name']} | {f['feed_url']}")

        return [(f['source_name'], f['feed_url']) for f in feeds]

    except Exception as e:
        print(f"⚠️ Erreur Supabase get_feeds: {str(e)}")
        return RSS_SOURCES.get(category, RSS_SOURCES['general'])
    


