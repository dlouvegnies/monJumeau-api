from fastapi import FastAPI, HTTPException, Header, Request,Response
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
import html
from urllib.parse import urlparse
from fastapi.responses import HTMLResponse
from rc_webapp import RC_WEBAPP_HTML

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── VARIABLES D'ENVIRONNEMENT ──
CLAUDE_API_KEY          = os.environ.get("CLAUDE_API_KEY")
APP_SECRET              = os.environ.get("APP_SECRET")
ADZUNA_APP_ID           = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY          = os.environ.get("ADZUNA_APP_KEY")
FRANCE_TRAVAIL_CLIENT_ID     = os.environ.get("FRANCE_TRAVAIL_CLIENT_ID")
FRANCE_TRAVAIL_CLIENT_SECRET = os.environ.get("FRANCE_TRAVAIL_CLIENT_SECRET")
FT_AUTH_URL  = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
FT_API_URL   = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
TMDB_API_KEY    = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL   = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL  = "https://image.tmdb.org/t/p/w500"
SPOTIFY_CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL  = "https://api.spotify.com/v1"
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
GOOGLE_PLACES_URL     = "https://maps.googleapis.com/maps/api/place"
THEMEALDB_URL         = "https://www.themealdb.com/api/json/v1/1"
SPOONACULAR_API_KEY   = os.environ.get("SPOONACULAR_API_KEY")
SPOONACULAR_URL       = "https://api.spoonacular.com"
NEWS_API_KEY  = os.environ.get("NEWS_API_KEY")
NEWS_API_URL  = "https://newsapi.org/v2"
SUPABASE_URL  = os.environ.get("SUPABASE_URL")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY")
MISTRAL_API_KEY    = os.environ.get("MISTRAL_API_KEY")
MISTRAL_EMBED_URL   = "https://api.mistral.ai/v1/embeddings"
MISTRAL_EMBED_MODEL = "mistral-embed"

# ── CONSTANTES ──
CAT_MAP = {
    'general':       'presse',
    'technology':    'technologie',
    'science':       'environnement',
    'business':      'économie',
    'entertainment': 'culture',
    'sports':        'sport',
    'health':        'environnement',
    'politics':      'politique',
}
CATEGORY_KEYWORDS = {
    'general':       'actualité france',
    'technology':    'technologie intelligence artificielle numérique',
    'science':       'science découverte recherche',
    'business':      'économie entreprise finance',
    'entertainment': 'cinéma culture musique',
    'sports':        'sport football tennis',
    'health':        'santé médecine bien-être',
    'politics':      'politique france gouvernement assemblée',
}
EXCLUDED_DOMAINS = ['20min.ch','rts.ch','rtbf.be','lesoir.be','rtl.lu','bsky.app','flipboard.com']
RSS_SOURCES = {
    'general': [
        ('Le Monde',   'https://www.lemonde.fr/rss/une.xml'),
        ('Le Figaro',  'https://www.lefigaro.fr/rss/figaro_actualites.xml'),
        ('France Info','https://www.francetvinfo.fr/titres.rss'),
        ('20 Minutes', 'https://www.20minutes.fr/feeds/rss/news'),
        ('Libération', 'https://www.liberation.fr/arc/outboundfeeds/rss/'),
        ('Les Echos',  'https://services.lesechos.fr/rss/les-echos-politique.xml'),
    ],
    'technology': [
        ('01net',           'https://www.01net.com/actualites/feed/'),
        ('Numerama',        'https://www.numerama.com/feed/'),
        ('Frandroid',       'https://www.frandroid.com/feed'),
        ('Korben',          'https://korben.info/feed'),
        ('Journal du Geek', 'https://www.journaldugeek.com/feed/'),
        ('Les Echos',       'https://services.lesechos.fr/rss/les-echos-tech-medias.xml'),
        ('ZDNet France',    'https://www.zdnet.fr/feeds/rss/actualites/'),
        ('Silicon',         'https://www.silicon.fr/feed'),
    ],
    'science': [
        ('Sciences et Avenir','https://www.sciencesetavenir.fr/rss.xml'),
        ('Futura Sciences',  'https://www.futura-sciences.com/rss/actualites.rss'),
        ('Science Post',     'https://sciencepost.fr/feed/'),
    ],
    'business': [
        ('Les Echos',       'https://services.lesechos.fr/rss/les-echos-economie.xml'),
        ('Le Point Economie','https://www.lepoint.fr/economie/rss.xml'),
        ('BFM Business',    'https://www.bfmtv.com/rss/economie/'),
        ('Le Monde Economie','https://www.lemonde.fr/economie-francaise/rss_full.xml'),
        ('20 minutes',      'https://www.20minutes.fr/feeds/rss-economie.xml'),
    ],
    'entertainment': [
        ('Allociné','https://www.allocine.fr/rss/news.xml'),
        ('Première', 'http://www.premiere.fr/rss/actu-live'),
        ('Télérama', 'https://www.telerama.fr/rss/latest-articles.xml'),
    ],
    'sports': [
        ("L'Equipe",  'https://dwh.lequipe.fr/api/edito/rss?path=/'),
        ('RMC Sport', 'https://rmcsport.bfmtv.com/rss/football/'),
        ('Eurosport', 'https://www.eurosport.fr/rss.xml'),
    ],
    'health': [
        ('Pourquoi Docteur','https://www.pourquoidocteur.fr/rss.xml'),
        ('Top Santé',       'https://www.topsante.com/rss.xml'),
        ('Santé Magazine',  'https://www.santemagazine.fr/feed'),
    ],
}
FLAGSHIP_FEEDS = {
    'general': [
        ('Le Monde',   'https://www.lemonde.fr/rss/une.xml'),
        ('Le Figaro',  'https://news.google.com/rss/search?q=site:lefigaro.fr&hl=fr&gl=FR&ceid=FR:fr'),
        ('Libération', 'https://www.liberation.fr/arc/outboundfeeds/rss/'),
        ('Les Echos',  'https://services.lesechos.fr/rss/les-echos-politique.xml'),
        ('France Info','https://www.francetvinfo.fr/titres.rss'),
        ('Le Parisien','https://feeds.leparisien.fr/leparisien/rss'),
        ('France Inter','https://www.radiofrance.fr/franceinter/rss'),
        ('BFM TV',     'https://www.bfmtv.com/rss/info/flux-rss/toutes-les-actualites/'),
        ("L'Express",  'https://www.lexpress.fr/arc/outboundfeeds/rss/'),
        ('Le Point',   'https://www.lepoint.fr/rss.xml'),
        ('20 Minutes', 'https://www.20minutes.fr/feeds/rss-une.xml'),
        ('Ouest France','https://www.ouest-france.fr/rss/une'),
    ],
    'technology': [
        ('01net',           'https://www.01net.com/actualites/feed/'),
        ('Numerama',        'https://www.numerama.com/feed/'),
        ('Frandroid',       'https://www.frandroid.com/feed'),
        ('Korben',          'https://korben.info/feed'),
        ('Journal du Geek', 'https://www.journaldugeek.com/feed/'),
        ('Les Echos',       'https://services.lesechos.fr/rss/les-echos-tech-medias.xml'),
        ('ZDNet France',    'https://www.zdnet.fr/feeds/rss/actualites/'),
        ('Silicon',         'https://www.silicon.fr/feed'),
    ],
    'science': [
        ('Sciences et Avenir','https://www.sciencesetavenir.fr/rss.xml'),
        ('Futura Sciences',  'https://www.futura-sciences.com/rss/actualites.rss'),
        ('Science Post',     'https://sciencepost.fr/feed/'),
    ],
    'business': [
        ('Les Echos',        'https://services.lesechos.fr/rss/les-echos-economie.xml'),
        ('Le Point Economie','https://www.lepoint.fr/economie/rss.xml'),
        ('BFM Business',     'https://www.bfmtv.com/rss/economie/'),
        ('Challenges',       'https://www.challenges.fr/rss.xml'),
        ('La Tribune',       'https://www.latribune.fr/rss/une.xml'),
    ],
    'entertainment': [
        ('Allociné','https://www.allocine.fr/rss/news.xml'),
        ('Première', 'http://www.premiere.fr/rss/actu-live'),
        ('Télérama', 'https://www.telerama.fr/rss/latest-articles.xml'),
    ],
    'sports': [
        ("L'Equipe",  'https://dwh.lequipe.fr/api/edito/rss?path=/'),
        ('RMC Sport', 'https://rmcsport.bfmtv.com/rss/football/'),
        ('Eurosport', 'https://www.eurosport.fr/rss.xml'),
    ],
    'health': [
        ('Pourquoi Docteur','https://www.pourquoidocteur.fr/rss.xml'),
        ('Top Santé',       'https://www.topsante.com/rss.xml'),
        ('Santé Magazine',  'https://www.santemagazine.fr/feed'),
    ],
    'politics': [
        ('Le Monde Politique',   'https://www.lemonde.fr/politique/rss_full.xml'),
        ('France Info Politique','https://www.francetvinfo.fr/politique.rss'),
        ('Le Point Politique',   'https://www.lepoint.fr/politique/rss.xml'),
        ("L'Express Politique",  'https://www.lexpress.fr/arc/outboundfeeds/rss/rubriques/politique.xml'),
        ('Libération Politique', 'https://www.liberation.fr/arc/outboundfeeds/rss/category/politique/'),
        ('Le NouvelObs Politique','https://www.nouvelobs.com/politique/rss.xml'),
        ('BFM Politique',        'https://www.bfmtv.com/rss/politique/'),
        ('20 Minutes Politique', 'https://www.20minutes.fr/feeds/rss-politique.xml'),
        ('Les Echos Politique',  'https://services.lesechos.fr/rss/les-echos-politique.xml'),
    ],
}
CATEGORIES_WITHOUT_SUPABASE = ['health', 'science']
REJECTED_EXPIRY_DAYS = 7
PENDING_EXPIRY_DAYS  = 14
pays_autorises       = ['fra', 'cor', 'bre']
spotify_token        = None
spotify_token_expiry = 0
ft_token             = None
ft_token_expiry      = 0
last_embed_time      = {}

# ── AUTH ──
def verify_secret(x_app_secret: str = None):
    if APP_SECRET and x_app_secret != APP_SECRET:
        raise HTTPException(status_code=401, detail="Non autorisé")

# ── SQLITE — device_tokens uniquement ──
def get_db():
    db = sqlite3.connect('gifts.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS device_tokens (
            token    TEXT PRIMARY KEY,
            my_code  TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_seen  TEXT DEFAULT (datetime('now'))
        )
    ''')
    db.commit()
    db.close()

init_db()

# ── HELPERS SUPABASE ──
def SB_HEADERS():
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }

async def sb_get(table: str, params: dict) -> list:
    for attempt in range(2):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/{table}",
                    headers=SB_HEADERS(), params=params, timeout=15.0,
                )
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            print(f"⚠️ sb_get erreur: {str(e)[:80]}")
            return []

async def sb_post(table: str, body: dict, prefer: str = "") -> list:
    headers = SB_HEADERS()
    if prefer:
        headers["Prefer"] = prefer
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=headers, json=body, timeout=15.0,
        )
    # ← Supabase retourne 201 avec corps vide si pas de "return=representation"
    if not r.content:
        return []
    try:
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []

async def sb_patch(table: str, params: dict, body: dict) -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.patch(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=SB_HEADERS(), params=params, json=body, timeout=15.0,
        )
    return r.status_code in [200, 204]


async def sb_delete(table: str, params: dict) -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=SB_HEADERS(), params=params, timeout=15.0,
        )
    return r.status_code in [200, 204]

async def sb_get_one(table: str, params: dict):
    rows = await sb_get(table, {**params, "limit": "1"})
    return rows[0] if rows else None

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
    media_type: str = "movie"

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
    page_size: int = 30

class PersonalizedNewsRequest(BaseModel):
    profile_traits: list = []
    personality: dict = {}
    context: dict = {}
    category: str = 'general'
    page_size: int = 30
    feedback: dict = {}
    interests: list = []
    locations: list = []
    langues: list = []

class EmbedNewsRequest(BaseModel):
    categories: list = ['general','technology','business','entertainment','sports','health','science','politics']
    hours_back: int = 2

class SemanticNewsRequest(BaseModel):
    profile_traits: list = []
    personality: dict = {}
    context: dict = {}
    interests: list = []
    locations: list = []
    liked_titles: list = []
    disliked_titles: list = []
    liked_urls: list = []
    liked_with_dates: list = []
    taste_vector: list = []
    category: str = 'general'
    limit: int = 30
    hours_back: int = 48

class NewsLikeRequest(BaseModel):
    user_code: str
    article_url: str
    category: str
    rating: int

class ArticleVectorRequest(BaseModel):
    url: str


# ── MODÈLES REGARD CROISÉ ──
class RCCreateSessionRequest(BaseModel):
    my_code: str
    version: str = 'universel'  # ← ajoute

class RCRespondRequest(BaseModel):
    session_key: str
    vector:      dict
    words:       list = []
    relation:    str  = 'ami'
    respondent_name: Optional[str] = None
    is_anonymous: bool = True
    source:       str  = 'web'
    raw_answers:     Optional[dict] = None   # ← ajoute

class RCInviteRequest(BaseModel):
    session_key: str
    from_code:   str
    to_code:     str
    relation:    str = 'ami'

class RCRespondInviteRequest(BaseModel):
    invitation_id: str
    vector:        dict
    words:         list = []
    respondent_name: Optional[str] = None
    is_anonymous:  bool = True
    raw_answers:   Optional[dict] = None   # ← est-ce présent ?

# ── ENDPOINTS REGARD CROISÉ ──








# ── NETTOYAGE AUTOMATIQUE ──
async def cleanup_old_requests():
    while True:
        try:
            print("🗑️ Nettoyage automatique Supabase...")
            await sb_delete('connection_requests', {
                "status":     "eq.rejected",
                "updated_at": f"lt.NOW() - INTERVAL '{REJECTED_EXPIRY_DAYS} days'",
            })
            await sb_delete('connection_requests', {
                "status":     "eq.pending",
                "created_at": f"lt.NOW() - INTERVAL '{PENDING_EXPIRY_DAYS} days'",
            })
            print("   ✅ Nettoyage terminé")
        except Exception as e:
            print(f"⚠️ Erreur cleanup: {str(e)[:50]}")
        await asyncio.sleep(24 * 60 * 60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_requests())
    print("🚀 Tâche de nettoyage automatique démarrée")

# ── HELPERS RSS ──
def is_excluded_url(url):
    return any(domain in url for domain in EXCLUDED_DOMAINS)

def clean_html(text):
    if not text: return ''
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300] if len(text) > 300 else text

def extract_image_from_entry(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url', '')
            if url and ('image' in media.get('type','') or media.get('medium')=='image' or url.endswith(('.jpg','.jpeg','.png','.webp'))):
                return url
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get('url', '')
        if url: return url
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href') or enc.get('url')
    content = ''
    if hasattr(entry, 'content') and entry.content:
        content = entry.content[0].get('value', '')
    elif hasattr(entry, 'summary'):
        content = entry.summary or ''
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+\.(jpg|jpeg|png|webp|gif))["\']', content, re.IGNORECASE)
    if img_match:
        url = img_match.group(1)
        if url.startswith('http'): return url
    if hasattr(entry, 'image') and entry.image:
        url = entry.image.get('href') or entry.image.get('url', '')
        if url: return url
    if hasattr(entry, 'links'):
        for link in entry.links:
            if 'image' in link.get('type', ''): return link.get('href')
    return None

def parse_date(entry):
    try:
        if hasattr(entry, 'published'):
            return parsedate_to_datetime(entry.published).isoformat()
    except: pass
    try:
        if hasattr(entry, 'updated'):
            return parsedate_to_datetime(entry.updated).isoformat()
    except: pass
    return datetime.now().isoformat()

def sort_by_date(articles):
    def sort_key(a):
        try:
            date_str = a.get('published_at', '')
            if not date_str: return datetime.min.replace(tzinfo=timezone.utc)
            date_str = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except: return datetime.min.replace(tzinfo=timezone.utc)
    return sorted(articles, key=sort_key, reverse=True)

async def mark_feed_inactive(url: str):
    if not SUPABASE_URL or not SUPABASE_KEY: return
    try:
        await sb_patch('rss_feeds', {"feed_url": f"eq.{url}"}, {"is_active": False})
    except Exception as e:
        print(f"⚠️ Erreur mark_feed_inactive: {str(e)[:50]}")

async def fetch_rss_source(source_name: str, url: str, max_items: int = 5):
    try:
        loop = asyncio.get_event_loop()
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url), timeout=15.0
        )
        if feed.bozo and not feed.entries:
            bozo_exception = str(feed.get('bozo_exception', ''))
            fatal_errors = ['Name or service not known','nodename nor servname provided','No address associated','Connection refused','No route to host','urlopen error']
            if any(err in bozo_exception for err in fatal_errors):
                print(f"💀 Flux mort: {source_name}")
                await mark_feed_inactive(url)
            return []
        if not feed.entries: return []
        articles = []
        for entry in feed.entries[:max_items]:
            title = clean_html(entry.get('title', ''))
            if not title or title == '[Removed]': continue
            articles.append({
                "title":        title,
                "description":  clean_html(entry.get('summary', '')),
                "url":          entry.get('link', ''),
                "image_url":    extract_image_from_entry(entry),
                "source":       source_name,
                "published_at": parse_date(entry),
                "author":       entry.get('author', ''),
                "source_type":  "rss",
            })
        print(f"   {'✅' if articles else '⚠️ '} {source_name} → {len(articles)} articles")
        return articles
    except asyncio.TimeoutError:
        print(f"⏱ Timeout: {source_name}")
        return []
    except Exception as e:
        print(f"⚠️ Erreur RSS {source_name}: {str(e)[:100]}")
        return []

async def get_feeds_from_supabase(category: str, limit: int = 15, interests: list = [], locations: list = [], langues: list = []):
    supabase_headers = SB_HEADERS()
    try:
        all_feeds = []
        flagship = FLAGSHIP_FEEDS.get(category, FLAGSHIP_FEEDS['general'])
        all_feeds.extend(flagship)
        print(f"🏆 Flagship: {len(flagship)} flux")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_random_feeds",
                headers=supabase_headers,
                json={"p_categorie": CAT_MAP.get(category, 'presse'), "p_pays_codes": pays_autorises, "p_limit": 10},
                timeout=10.0,
            )
        feeds = r.json()
        if isinstance(feeds, list):
            feeds = [f for f in feeds if not is_excluded_url(f.get('feed_url', ''))]
            all_feeds.extend([(f['source_name'], f['feed_url']) for f in feeds])
            print(f"📂 Supabase: {len(feeds)} flux")
        for interest in interests[:3]:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/rss_feeds",
                    headers=supabase_headers,
                    params={"select": "source_name,feed_url", "is_active": "eq.true", "is_youtube": "eq.false",
                            "pays_code": f"in.({','.join(pays_autorises)})",
                            "or": f"(sous_categorie.ilike.%{interest}%,groupe.ilike.%{interest}%,source_name.ilike.%{interest}%)",
                            "limit": "10"},
                    timeout=10.0,
                )
            interest_feeds = r.json()
            if isinstance(interest_feeds, list):
                interest_feeds = [f for f in interest_feeds if not is_excluded_url(f.get('feed_url', ''))]
                all_feeds.extend([(f['source_name'], f['feed_url']) for f in interest_feeds])
                print(f"🎯 Intérêt '{interest}': {len(interest_feeds)} flux")
        for location in locations[:3]:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/rss_feeds",
                    headers=supabase_headers,
                    params={"select": "source_name,feed_url", "is_active": "eq.true", "is_youtube": "eq.false",
                            "pays_code": f"in.({','.join(pays_autorises)})",
                            "or": f"(region.ilike.%{location}%,ville.ilike.%{location}%,departement.ilike.%{location}%)",
                            "limit": "5"},
                    timeout=10.0,
                )
            location_feeds = r.json()
            if isinstance(location_feeds, list):
                location_feeds = [f for f in location_feeds if not is_excluded_url(f.get('feed_url', ''))]
                all_feeds.extend([(f['source_name'], f['feed_url']) for f in location_feeds])
                print(f"📍 Lieu '{location}': {len(location_feeds)} flux")
        seen_urls = set()
        unique_feeds = []
        for name, url in all_feeds:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_feeds.append((name, url))
        domain_count = {}
        diverse_feeds = []
        for name, url in unique_feeds:
            domain = urlparse(url).netloc
            count = domain_count.get(domain, 0)
            if count < 2:
                diverse_feeds.append((name, url))
                domain_count[domain] = count + 1
        print(f"📡 Total: {len(diverse_feeds)} flux après diversification")
        return diverse_feeds or RSS_SOURCES.get(category, RSS_SOURCES['general'])
    except Exception as e:
        print(f"⚠️ Erreur Supabase feeds: {str(e)}")
        return RSS_SOURCES.get(category, RSS_SOURCES['general'])

def deduplicate_feeds(sources):
    seen = set()
    unique = []
    for name, url in sources:
        if url not in seen:
            seen.add(url)
            unique.append((name, url))
    return unique

def deduplicate_articles(articles):
    seen = set()
    unique = []
    for a in articles:
        key = a.get('title', '')[:50].lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(a)
    return unique

# ── PUSH NOTIFICATIONS ──
async def send_push_notification(push_token: str, title: str, body: str, data: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://exp.host/--/api/v2/push/send',
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                json={'to': push_token, 'title': title, 'body': body, 'data': data, 'sound': 'default', 'badge': 1},
            )
            print(f'Push envoyé: {response.status_code}')
            return response.json()
    except Exception as e:
        print(f'ERREUR push: {e}')
        return None

# ── ENDPOINTS SANTÉ ──
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.head("/health")
async def health_head():
    return Response(status_code=200)

# ── ENDPOINTS CLAUDE ──
@app.post("/recommend")
async def recommend(req: MessageRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    if not CLAUDE_API_KEY:
        raise HTTPException(status_code=500, detail="Clé API manquante")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": req.max_tokens, "system": req.system, "messages": req.messages},
            timeout=30.0,
        )
    return response.json()

# ── ENDPOINTS GIFTS — Supabase ──
@app.post("/gift/send")
async def send_gift(req: SendGiftRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    gift_id    = str(uuid.uuid4())[:8].upper()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    await sb_post('gifts', {
        "id": gift_id, "from_code": req.from_code, "to_code": req.to_code,
        "trait": req.trait, "message": req.message, "expires_at": expires_at,
    })
    token_row = await sb_get_one('push_tokens', {"my_code": f"eq.{req.to_code}"})
    if token_row:
        await send_push_notification(
            push_token=token_row['push_token'],
            title='🎁 Nouveau trait reçu !',
            body="Quelqu'un pense que tu as une qualité particulière...",
            data={'screen': 'ReceivedGifts', 'gift_id': gift_id}
        )
    return {"success": True, "gift_id": gift_id}

@app.get("/gift/received/{my_code}")
async def get_received(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    gifts = await sb_get('gifts', {
        "to_code": f"eq.{my_code}", "status": "eq.pending",
        "select": "*", "order": "created_at.desc",
    })
    return {"gifts": gifts}

@app.get("/gift/sent/{my_code}")
async def get_sent(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    gifts = await sb_get('gifts', {
        "from_code": f"eq.{my_code}", "select": "*",
        "order": "created_at.desc", "limit": "50",
    })
    return {"gifts": gifts}

@app.post("/gift/respond")
async def respond_gift(req: RespondGiftRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    status = 'accepted' if req.accepted else 'rejected'
    await sb_patch('gifts',
        params={"id": f"eq.{req.gift_id}"},
        body={"status": status, "responded_at": datetime.now(timezone.utc).isoformat()}
    )
    gift = await sb_get_one('gifts', {"id": f"eq.{req.gift_id}"})
    return {"success": True, "gift": gift}

@app.get("/gift/check-code/{code}")
async def check_code(code: str):
    gifts = await sb_get('gifts', {"or": f"(from_code.eq.{code},to_code.eq.{code})", "select": "id", "limit": "1"})
    return {"exists": len(gifts) > 0}

# ── ENDPOINTS PUSH TOKENS — Supabase ──
@app.post("/push/register")
async def register_push(req: RegisterPushRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    headers = {**SB_HEADERS(), "Prefer": "resolution=merge-duplicates"}
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/push_tokens",
            headers=headers,
            json={"my_code": req.my_code, "push_token": req.push_token, "updated_at": datetime.now(timezone.utc).isoformat()},
            timeout=10.0,
        )
    return {"success": True}

@app.get("/push/token/{my_code}")
async def get_push_token(my_code: str):
    row = await sb_get_one('push_tokens', {"my_code": f"eq.{my_code}"})
    return {"push_token": row['push_token'] if row else None}

# ── ENDPOINTS DEVICE TOKENS — SQLite (éphémère, ok) ──
@app.post("/device/register")
async def register_device(request: Request):
    try:
        body    = await request.json()
        token   = request.headers.get('x-device-token', '')
        my_code = body.get('my_code', '').strip().upper()
        if not token or not my_code:
            return {"success": False, "error": "Token ou code manquant"}
        db = get_db()
        db.execute(
            'INSERT OR REPLACE INTO device_tokens (token, my_code, last_seen) VALUES (?, ?, datetime("now"))',
            (token, my_code)
        )
        db.commit()
        db.close()
        print(f"✅ Device enregistré: {my_code} / {token[:8]}...")
        return {"success": True}
    except Exception as e:
        print(f"❌ register_device erreur: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/device/token/{my_code}")
async def get_device_token_endpoint(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db  = get_db()
    row = db.execute('SELECT token, last_seen FROM device_tokens WHERE my_code = ?', (my_code.strip().upper(),)).fetchone()
    db.close()
    return {"token": row['token'][:8] + '...' if row else None, "last_seen": row['last_seen'] if row else None}

# ── ENDPOINTS COMPARAISONS — Supabase ──
@app.post("/compare/request")
async def request_comparison(req: CompareRequestModel, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    existing = await sb_get('comparisons', {
        "or":    f"(and(from_code.eq.{req.from_code},to_code.eq.{req.to_code}),and(from_code.eq.{req.to_code},to_code.eq.{req.from_code}))",
        "status": "eq.pending", "select": "id",
    })
    if existing:
        return {"success": False, "error": "Une demande est déjà en cours"}
    comparison_id = str(uuid.uuid4())[:8].upper()
    expires_at    = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    await sb_post('comparisons', {
        "id": comparison_id, "from_code": req.from_code,
        "to_code": req.to_code, "expires_at": expires_at,
    })
    token_row = await sb_get_one('push_tokens', {"my_code": f"eq.{req.to_code}"})
    if token_row:
        await send_push_notification(
            push_token=token_row['push_token'],
            title='🔍 Demande de comparaison',
            body="Quelqu'un veut comparer vos profils de jumeaux !",
            data={'screen': 'Social', 'comparison_id': comparison_id}
        )
    return {"success": True, "comparison_id": comparison_id}

@app.post("/compare/respond")
async def respond_comparison(req: CompareRespondModel, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    comparison = await sb_get_one('comparisons', {"id": f"eq.{req.comparison_id}", "select": "*"})
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparaison non trouvée")
    now_iso = datetime.now(timezone.utc).isoformat()
    expires = str(comparison.get('expires_at', ''))
    if expires and expires < now_iso:
        return {"success": False, "error": "La demande a expiré"}
    if not req.accepted:
        await sb_patch('comparisons', {"id": f"eq.{req.comparison_id}"}, {"status": "rejected"})
        return {"success": True, "status": "rejected"}
    is_from = comparison['from_code'] == req.my_code
    if is_from:
        await sb_patch('comparisons', {"id": f"eq.{req.comparison_id}"},
            {"from_accepted": 1, "from_vector": json.dumps(req.my_vector)})
    else:
        await sb_patch('comparisons', {"id": f"eq.{req.comparison_id}"},
            {"to_accepted": 1, "to_vector": json.dumps(req.my_vector)})
    updated = await sb_get_one('comparisons', {"id": f"eq.{req.comparison_id}"})
    if updated and updated.get('from_accepted') and updated.get('to_accepted'):
        await sb_patch('comparisons', {"id": f"eq.{req.comparison_id}"}, {"status": "analyzing"})
        asyncio.create_task(analyze_comparison(req.comparison_id))
        return {"success": True, "status": "analyzing"}
    return {"success": True, "status": "waiting"}

@app.get("/compare/status/{comparison_id}")
async def get_comparison_status(comparison_id: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    comparison = await sb_get_one('comparisons', {"id": f"eq.{comparison_id}", "select": "*"})
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparaison non trouvée")
    return {
        "status":     comparison['status'],
        "result":     json.loads(comparison['result']) if comparison.get('result') else None,
        "expires_at": comparison.get('expires_at'),
    }

@app.get("/compare/pending/{my_code}")
async def get_pending_comparisons(my_code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    comparisons = await sb_get('comparisons', {
        "to_code": f"eq.{my_code}", "status": "eq.pending",
        "to_accepted": "eq.0", "select": "*", "order": "created_at.desc",
    })
    return {"comparisons": comparisons}

async def analyze_comparison(comparison_id: str):
    comparison = await sb_get_one('comparisons', {"id": f"eq.{comparison_id}", "select": "*"})
    if not comparison: return
    from_vector = json.loads(comparison['from_vector'])
    to_vector   = json.loads(comparison['to_vector'])
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
            headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
            timeout=30.0,
        )
    data = response.json()
    result_text = data['content'][0]['text']
    json_match = re.search(r'\{[\s\S]*\}', result_text)
    if json_match:
        result = json_match.group(0)
        await sb_patch('comparisons', {"id": f"eq.{comparison_id}"}, {"status": "completed", "result": result})
        for code_field in ['from_code', 'to_code']:
            token_row = await sb_get_one('push_tokens', {"my_code": f"eq.{comparison[code_field]}"})
            if token_row:
                await send_push_notification(
                    push_token=token_row['push_token'],
                    title='✨ Comparaison prête !',
                    body='Découvrez vos points communs et différences !',
                    data={'screen': 'CompareResult', 'comparison_id': comparison_id}
                )

# ── ENDPOINTS JOBS ──
@app.post("/jobs/adzuna")
async def search_adzuna(req: JobSearchRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        url = f"https://api.adzuna.com/v1/api/jobs/fr/search/{req.page}"
        params = {"app_id": ADZUNA_APP_ID, "app_key": ADZUNA_APP_KEY, "results_per_page": req.results_per_page, "content-type": "application/json"}
        if req.keywords: params["what"] = req.keywords
        if req.location: params["where"] = req.location
        if req.permanent == '1': params["permanent"] = '1'
        if req.contract == '1': params["contract"] = '1'
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            data = response.json()
        if "results" not in data: return {"results": []}
        jobs = [{
            "id": job.get("id"), "title": job.get("title"),
            "company": job.get("company", {}).get("display_name", "Entreprise non précisée"),
            "location": job.get("location", {}).get("display_name", "Lieu non précisé"),
            "salary_min": job.get("salary_min"), "salary_max": job.get("salary_max"),
            "description": job.get("description"), "contract_type": job.get("contract_type"),
            "created": job.get("created"), "redirect_url": job.get("redirect_url"),
            "category": job.get("category", {}).get("label"),
        } for job in data["results"]]
        return {"results": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_france_travail_token():
    global ft_token, ft_token_expiry
    import time
    if ft_token and time.time() < ft_token_expiry: return ft_token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FT_AUTH_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials", "client_id": FRANCE_TRAVAIL_CLIENT_ID,
                  "client_secret": FRANCE_TRAVAIL_CLIENT_SECRET, "scope": "api_offresdemploiv2 o2dsoffre"},
            timeout=10.0,
        )
        data = response.json()
        ft_token = data.get("access_token")
        ft_token_expiry = time.time() + data.get("expires_in", 1400) - 60
        return ft_token

CITY_DEPT_MAP = {
    'paris': '75', 'marseille': '13', 'lyon': '69', 'toulouse': '31', 'nice': '06',
    'nantes': '44', 'strasbourg': '67', 'montpellier': '34', 'bordeaux': '33', 'lille': '59',
    'rennes': '35', 'reims': '51', 'saint-etienne': '42', 'toulon': '83', 'grenoble': '38',
    'dijon': '21', 'angers': '49', 'nimes': '30', 'clermont-ferrand': '63', 'aix-en-provence': '13',
    'brest': '29', 'amiens': '80', 'limoges': '87', 'tours': '37', 'metz': '57', 'arras': '62',
    'lens': '62', 'douai': '59', 'valenciennes': '59', 'dunkerque': '59', 'calais': '62',
    'le havre': '76', 'rouen': '76', 'caen': '14', 'nancy': '54', 'mulhouse': '68',
    'perpignan': '66', 'besancon': '25', 'orleans': '45', 'poitiers': '86', 'pau': '64',
}

def get_dept_code(city: str) -> str:
    if not city: return None
    city_lower = city.lower().strip()
    for key, code in CITY_DEPT_MAP.items():
        if city_lower in key or key in city_lower: return code
    if city.strip().isdigit() and len(city.strip()) <= 3: return city.strip()
    return None

@app.post("/jobs/france-travail")
async def search_france_travail(req: FranceTravailRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        token = await get_france_travail_token()
        if not token: raise HTTPException(status_code=500, detail="Token France Travail non disponible")
        params = f"range=0-{req.results_per_page - 1}"
        if req.keywords: params += f"&motsCles={req.keywords}"
        if req.location:
            dept = get_dept_code(req.location)
            if dept: params += f"&departement={dept}"
        if req.contract_type: params += f"&typeContrat={req.contract_type}"
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{FT_API_URL}?{params}", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=15.0)
        if response.status_code == 204: return {"results": []}
        if response.status_code not in [200, 206]: return {"results": []}
        data = response.json()
        if "resultats" not in data: return {"results": []}
        jobs = [{
            "id": job.get("id"), "title": job.get("intitule"),
            "company": job.get("entreprise", {}).get("nom", "Entreprise non précisée"),
            "location": job.get("lieuTravail", {}).get("libelle", "Lieu non précisé"),
            "salary_min": job.get("salaire", {}).get("commentaire"), "salary_max": None,
            "description": job.get("description"), "contract_type": job.get("typeContratLibelle"),
            "created": job.get("dateCreation"),
            "redirect_url": f"https://candidat.francetravail.fr/offres/recherche/detail/{job.get('id')}",
            "category": job.get("appellationlibelle"), "source": "france_travail",
        } for job in data["resultats"]]
        return {"results": jobs}
    except Exception as e:
        print(f"ERREUR France Travail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ── ENDPOINTS MEDIA ──
@app.post("/media/details")
async def get_media_details(req: TMDBRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                f"{TMDB_BASE_URL}/search/{req.media_type}",
                params={"api_key": TMDB_API_KEY, "query": req.title, "language": "fr-FR"},
                timeout=10.0,
            )
            search_data = search_response.json()
        if not search_data.get("results"): return {"result": None}
        item = search_data["results"][0]
        item_id = item["id"]
        async with httpx.AsyncClient() as client:
            detail_response = await client.get(
                f"{TMDB_BASE_URL}/{req.media_type}/{item_id}",
                params={"api_key": TMDB_API_KEY, "language": "fr-FR", "append_to_response": "videos,credits,watch/providers"},
                timeout=10.0,
            )
            detail = detail_response.json()
        trailer = None
        for video in detail.get("videos", {}).get("results", []):
            if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                trailer = f"https://www.youtube.com/watch?v={video['key']}"
                break
        cast = [p.get("name") for p in detail.get("credits", {}).get("cast", [])[:5]]
        providers = []
        watch_providers = detail.get("watch/providers", {}).get("results", {}).get("FR", {})
        for p in watch_providers.get("flatrate", [])[:4]:
            providers.append(p.get("provider_name"))
        poster_path = detail.get("poster_path")
        runtime = detail.get("runtime")
        if not runtime:
            episode_runtime = detail.get("episode_run_time", [])
            runtime = episode_runtime[0] if episode_runtime else None
        return {"result": {
            "poster_url": f"{TMDB_IMAGE_URL}{poster_path}" if poster_path else None,
            "overview": detail.get("overview"), "vote_average": round(detail.get("vote_average", 0), 1),
            "vote_count": detail.get("vote_count"),
            "release_date": detail.get("release_date") or detail.get("first_air_date"),
            "runtime": runtime, "genres": [g["name"] for g in detail.get("genres", [])[:3]],
            "cast": cast, "trailer_url": trailer, "providers": providers,
            "tmdb_url": f"https://www.themoviedb.org/{req.media_type}/{item_id}",
            "amazon_url": f"https://www.amazon.fr/s?k={req.title}",
        }}
    except Exception as e:
        print(f"ERREUR TMDB: {str(e)}")
        return {"result": None}

async def get_spotify_token():
    global spotify_token, spotify_token_expiry
    import time, base64
    if spotify_token and time.time() < spotify_token_expiry: return spotify_token
    credentials = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPOTIFY_AUTH_URL,
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"}, timeout=10.0,
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
        if not token: return {"result": None}
        headers = {"Authorization": f"Bearer {token}"}
        query = req.artist
        if req.album: query += f" {req.album}"
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                f"{SPOTIFY_API_URL}/search", headers=headers,
                params={"q": query, "type": "artist,album", "market": "FR", "limit": 1}, timeout=10.0,
            )
            search_data = search_response.json()
        artists = search_data.get("artists", {}).get("items", [])
        albums  = search_data.get("albums",  {}).get("items", [])
        artist = artists[0] if artists else None
        album  = albums[0]  if albums  else None
        if not artist and not album: return {"result": None}
        image_url = None
        if album and album.get("images"):  image_url = album["images"][0]["url"]
        elif artist and artist.get("images"): image_url = artist["images"][0]["url"]
        top_tracks = []
        if artist:
            async with httpx.AsyncClient() as client:
                tracks_response = await client.get(
                    f"{SPOTIFY_API_URL}/artists/{artist['id']}/top-tracks",
                    headers=headers, params={"market": "FR"}, timeout=10.0,
                )
                for track in tracks_response.json().get("tracks", [])[:5]:
                    top_tracks.append({
                        "name": track["name"], "preview_url": track.get("preview_url"),
                        "duration_ms": track.get("duration_ms"),
                        "spotify_url": track["external_urls"].get("spotify"),
                    })
        return {"result": {
            "image_url": image_url, "genres": artist.get("genres", [])[:4] if artist else [],
            "popularity": artist.get("popularity") if artist else None,
            "followers": artist.get("followers", {}).get("total") if artist else None,
            "top_tracks": top_tracks,
            "spotify_artist_url": artist["external_urls"].get("spotify") if artist else None,
            "spotify_album_url": album["external_urls"].get("spotify") if album else None,
            "album_name": album.get("name") if album else None,
            "album_release_date": album.get("release_date") if album else None,
            "amazon_url": f"https://www.amazon.fr/s?k={req.artist}+musique",
        }}
    except Exception as e:
        print(f"ERREUR Spotify: {str(e)}")
        return {"result": None}

@app.post("/restaurant/details")
async def get_restaurant_details(req: RestaurantRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        query = req.name + (f" {req.location}" if req.location else "")
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                f"{GOOGLE_PLACES_URL}/textsearch/json",
                params={"query": query + " restaurant", "key": GOOGLE_PLACES_API_KEY, "language": "fr", "region": "fr"},
                timeout=10.0,
            )
            search_data = search_response.json()
            if not search_data.get("results"): return {"result": None}
            place    = search_data["results"][0]
            place_id = place.get("place_id")
            detail_response = await client.get(
                f"{GOOGLE_PLACES_URL}/details/json",
                params={"place_id": place_id, "key": GOOGLE_PLACES_API_KEY, "language": "fr",
                        "fields": "name,rating,user_ratings_total,formatted_address,opening_hours,price_level,photos,website,url,formatted_phone_number,types"},
                timeout=10.0,
            )
            detail = detail_response.json().get("result", {})
        photo_url = None
        photos = detail.get("photos") or place.get("photos", [])
        if photos:
            photo_ref = photos[0].get("photo_reference")
            if photo_ref:
                photo_url = f"{GOOGLE_PLACES_URL}/photo?maxwidth=600&photo_reference={photo_ref}&key={GOOGLE_PLACES_API_KEY}"
        price_level = detail.get("price_level") or place.get("price_level")
        price_str   = ('💰' * (price_level + 1) if price_level > 0 else 'Gratuit') if price_level is not None else None
        opening_hours = detail.get("opening_hours", {})
        types = detail.get("types", place.get("types", []))
        cuisine_types = [t.replace('_', ' ').title() for t in types if t not in ['restaurant','food','point_of_interest','establishment','store']][:3]
        return {"result": {
            "photo_url": photo_url, "name": detail.get("name") or place.get("name"),
            "rating": detail.get("rating") or place.get("rating"),
            "user_ratings_total": detail.get("user_ratings_total") or place.get("user_ratings_total"),
            "address": detail.get("formatted_address") or place.get("formatted_address"),
            "price_level": price_str, "is_open": opening_hours.get("open_now"),
            "weekday_text": opening_hours.get("weekday_text", [])[:3],
            "phone": detail.get("formatted_phone_number"), "website": detail.get("website"),
            "google_maps_url": detail.get("url") or f"https://www.google.com/maps/place/?q=place_id:{place_id}",
            "cuisine_types": cuisine_types,
        }}
    except Exception as e:
        print(f"ERREUR Google Places: {str(e)}")
        return {"result": None}

@app.post("/recipe/details")
async def get_recipe_details(req: RecipeRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        print(f"🔍 Recherche recette Spoonacular: {req.title}")
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                f"{SPOONACULAR_URL}/recipes/complexSearch",
                params={"apiKey": SPOONACULAR_API_KEY, "query": req.title, "language": "fr",
                        "number": 1, "addRecipeInformation": True, "fillIngredients": True},
                timeout=15.0,
            )
            search_data = search_response.json()
            if not search_data.get("results"):
                simplify_response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json={"model": "claude-sonnet-4-20250514", "max_tokens": 20,
                          "messages": [{"role": "user", "content": f'Give the simplified English name (1-4 words) of this recipe for a search. Reply ONLY with the name: "{req.title}"'}]},
                    timeout=10.0,
                )
                simplified = simplify_response.json()['content'][0]['text'].strip()
                search_response = await client.get(
                    f"{SPOONACULAR_URL}/recipes/complexSearch",
                    params={"apiKey": SPOONACULAR_API_KEY, "query": simplified, "number": 1,
                            "addRecipeInformation": True, "fillIngredients": True},
                    timeout=15.0,
                )
                search_data = search_response.json()
        if not search_data.get("results"): return {"result": None}
        recipe    = search_data["results"][0]
        recipe_id = recipe["id"]
        async with httpx.AsyncClient() as client:
            detail_response = await client.get(
                f"{SPOONACULAR_URL}/recipes/{recipe_id}/information",
                params={"apiKey": SPOONACULAR_API_KEY, "includeNutrition": False},
                timeout=15.0,
            )
            detail = detail_response.json()
        ingredients = [{"ingredient": ing.get("name", ""), "measure": f"{ing.get('amount', '')} {ing.get('unit', '')}".strip()}
                      for ing in detail.get("extendedIngredients", [])]
        steps_raw = [step.get("step", "") for instruction in detail.get("analyzedInstructions", []) for step in instruction.get("steps", [])]
        cuisines  = detail.get("cuisines", [])
        diets     = detail.get("diets", [])
        ready_in  = detail.get("readyInMinutes")
        servings  = detail.get("servings")
        translation_prompt = f"""Traduis en français ces informations de recette de cuisine.
NOM ORIGINAL : {recipe.get('title')}
CUISINES : {', '.join(cuisines) if cuisines else 'International'}
RÉGIMES : {', '.join(diets) if diets else ''}
TEMPS : {ready_in} minutes
PORTIONS : {servings}
INGRÉDIENTS :
{chr(10).join([f"- {i['measure']} {i['ingredient']}" for i in ingredients])}
ÉTAPES :
{chr(10).join([f"{idx+1}. {s}" for idx, s in enumerate(steps_raw[:12])])}
Retourne UNIQUEMENT ce JSON valide sans texte avant ni après :
{{
  "name_fr": "nom de la recette en français",
  "cuisine_fr": "type de cuisine en français",
  "diets_fr": ["régime 1", "régime 2"],
  "ingredients_fr": [{{"ingredient": "ingrédient traduit", "measure": "mesure traduite"}}],
  "steps_fr": ["étape 1 traduite", "étape 2 traduite"]
}}"""
        async with httpx.AsyncClient() as client:
            claude_response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 2000,
                      "messages": [{"role": "user", "content": translation_prompt}]},
                timeout=30.0,
            )
            translation_text = claude_response.json()['content'][0]['text']
        json_match = re.search(r'\{[\s\S]*\}', translation_text)
        translation = {}
        if json_match:
            try: translation = json.loads(json_match.group(0))
            except: pass
        return {"result": {
            "name": translation.get("name_fr") or recipe.get("title"),
            "category": translation.get("cuisine_fr") or (cuisines[0] if cuisines else "International"),
            "area": translation.get("cuisine_fr") or "",
            "diets": translation.get("diets_fr") or diets,
            "image_url": recipe.get("image") or detail.get("image"),
            "ready_in_minutes": ready_in, "servings": servings,
            "ingredients": translation.get("ingredients_fr") or ingredients,
            "steps": translation.get("steps_fr") or steps_raw[:12],
            "source_url": detail.get("sourceUrl"),
            "spoonacular_url": f"https://spoonacular.com/recipes/{detail.get('title','').replace(' ','-').lower()}-{recipe_id}",
            "tags": diets[:3] if diets else [],
        }}
    except Exception as e:
        print(f"❌ ERREUR Spoonacular: {str(e)}")
        return {"result": None}

# ── ENDPOINTS NEWS ──
@app.post("/news/articles")
async def get_news(req: NewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        print(f"🔍 News request: category={req.category}")
        now  = datetime.now(timezone.utc)
        last = last_embed_time.get(req.category)
        if not last or (now - last).total_seconds() > 3600:
            asyncio.create_task(_embed_news_logic([req.category], hours_back=2))
            last_embed_time[req.category] = now
        all_articles = []
        rss_sources  = await get_feeds_from_supabase(category=req.category, limit=15)
        unique_feeds = deduplicate_feeds(rss_sources)
        print(f"📡 {len(unique_feeds)} flux uniques à fetcher")
        rss_results = await asyncio.gather(*[fetch_rss_source(name, url, max_items=4) for name, url in unique_feeds], return_exceptions=True)
        for result in rss_results:
            if isinstance(result, list): all_articles.extend(result)
        try:
            keywords = req.keywords or CATEGORY_KEYWORDS.get(req.category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{NEWS_API_URL}/everything",
                    params={"apiKey": NEWS_API_KEY, "q": keywords, "language": "fr", "sortBy": "publishedAt", "pageSize": 10},
                    timeout=15.0)
            for article in response.json().get("articles", []):
                if article.get("title") and article.get("title") != "[Removed]":
                    all_articles.append({"title": article.get("title"), "description": article.get("description"),
                        "url": article.get("url"), "image_url": article.get("urlToImage"),
                        "source": article.get("source", {}).get("name"), "published_at": article.get("publishedAt"), "source_type": "newsapi"})
        except Exception as e:
            print(f"⚠️ NewsAPI error: {str(e)}")
        unique = deduplicate_articles(all_articles)
        final  = [a for a in sort_by_date(unique) if a.get('title') and a.get('url')][:req.page_size]
        print(f"✅ Total articles final: {len(final)}")
        return {"articles": final}
    except Exception as e:
        print(f"❌ ERREUR get_news: {str(e)}")
        return {"articles": []}

@app.post("/news/personalized")
async def get_personalized_news(req: PersonalizedNewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        all_articles = []
        rss_sources  = await get_feeds_from_supabase(category=req.category, limit=20, interests=req.interests, locations=req.locations, langues=req.langues)
        unique_feeds = deduplicate_feeds(rss_sources)
        rss_results  = await asyncio.gather(*[fetch_rss_source(name, url, max_items=4) for name, url in unique_feeds], return_exceptions=True)
        for result in rss_results:
            if isinstance(result, list): all_articles.extend(result)
        try:
            keywords = CATEGORY_KEYWORDS.get(req.category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{NEWS_API_URL}/everything",
                    params={"apiKey": NEWS_API_KEY, "q": keywords, "language": "fr", "sortBy": "publishedAt", "pageSize": 10},
                    timeout=15.0)
            for article in response.json().get("articles", []):
                if article.get("title") and article.get("title") != "[Removed]":
                    all_articles.append({"title": article.get("title"), "description": article.get("description"),
                        "url": article.get("url"), "image_url": article.get("urlToImage"),
                        "source": article.get("source", {}).get("name"), "published_at": article.get("publishedAt")})
        except Exception as e:
            print(f"⚠️ NewsAPI error: {str(e)}")
        unique = deduplicate_articles(all_articles)
        if not unique: return {"articles": []}
        articles_summary = "\n".join([f"{i+1}. [{a.get('source','?')}] {a.get('title','')} — {(a.get('description','') or '')[:100]}" for i, a in enumerate(unique[:55])])
        traits_str    = ', '.join(req.profile_traits) if req.profile_traits else 'curieux, ouvert'
        context_lines = []
        if req.context.get('metier'):   context_lines.append(f"Métier: {req.context['metier']}")
        if req.context.get('ville'):    context_lines.append(f"Ville: {req.context['ville']}")
        if req.context.get('passions'): context_lines.append(f"Passions: {', '.join(req.context.get('passions', []))}")
        context_str = '\n'.join(context_lines)
        liked    = req.feedback.get('liked', [])
        disliked = req.feedback.get('disliked', [])
        feedback_str = f"\nHISTORIQUE :\n- Appréciés : {', '.join(liked[:5]) if liked else 'aucun'}\n- Non appréciés : {', '.join(disliked[:5]) if disliked else 'aucun'}\n" if liked or disliked else ''
        prompt = f"""Tu es un assistant de curation d'actualités personnalisées.
PROFIL : {traits_str}
{context_str}{feedback_str}
ARTICLES :
{articles_summary}
Sélectionne les 10 articles les plus pertinents. Retourne UNIQUEMENT ce JSON :
{{"selected": [{{"index": 1, "why": "Explication courte"}}]}}"""
        async with httpx.AsyncClient() as client:
            claude_response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 600, "messages": [{"role": "user", "content": prompt}]},
                timeout=20.0,
            )
            claude_text = claude_response.json()['content'][0]['text']
        json_match   = re.search(r'\{[\s\S]*\}', claude_text)
        personalized = []
        if json_match:
            selection = json.loads(json_match.group(0))
            for item in selection.get('selected', []):
                idx = item.get('index', 1) - 1
                if 0 <= idx < len(unique):
                    article = unique[idx].copy()
                    article['why'] = item.get('why', '')
                    personalized.append(article)
        return {"articles": personalized}
    except Exception as e:
        print(f"❌ ERREUR personalized news: {str(e)}")
        return {"articles": []}

@app.post("/news/flagship")
async def get_flagship_news(req: NewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        flagship    = FLAGSHIP_FEEDS.get('general', [])
        rss_results = await asyncio.gather(*[fetch_rss_source(name, url, max_items=5) for name, url in flagship], return_exceptions=True)
        all_articles = []
        for result in rss_results:
            if isinstance(result, list): all_articles.extend(result)
        unique       = deduplicate_articles(all_articles)
        with_image   = sort_by_date([a for a in unique if a.get('image_url')])
        without_image = sort_by_date([a for a in unique if not a.get('image_url')])
        final = with_image + without_image
        print(f"✅ Flagship: {len(with_image)} avec image, {len(without_image)} sans image")
        return {"articles": final}
    except Exception as e:
        print(f"❌ ERREUR flagship news: {str(e)}")
        return {"articles": []}

# ── VECTORISATION ──
async def embed_texts(texts: list) -> list:
    if not texts: return []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MISTRAL_EMBED_URL,
                headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
                json={"model": MISTRAL_EMBED_MODEL, "input": texts, "encoding_format": "float"},
                timeout=30.0,
            )
            data = response.json()
            if "data" not in data:
                print(f"⚠️ Mistral Embed erreur: {data}")
                return []
            return [item["embedding"] for item in data["data"]]
    except Exception as e:
        print(f"❌ Erreur embed_texts: {str(e)}")
        return []

async def upsert_article(article: dict, embedding: list, category: str):
    if not embedding or not article.get("url"): return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/news_articles",
                headers={**SB_HEADERS(), "Prefer": "resolution=merge-duplicates"},
                json={"title": article.get("title","")[:500], "description": article.get("description","")[:1000],
                      "url": article.get("url",""), "source": article.get("source",""),
                      "image_url": article.get("image_url"), "category": category,
                      "published_at": article.get("published_at"), "embedding": embedding},
                timeout=10.0,
            )
    except Exception as e:
        print(f"⚠️ Erreur upsert_article: {str(e)[:100]}")

async def _embed_news_logic(categories: list, hours_back: int = 2):
    total_embedded = 0
    total_skipped  = 0
    for category in categories:
        print(f"🔄 Auto-embed: {category}")
        all_articles = []
        flagship         = FLAGSHIP_FEEDS.get(category, FLAGSHIP_FEEDS.get('general', []))
        flagship_sources = deduplicate_feeds(flagship)
        flagship_results = await asyncio.gather(*[fetch_rss_source(name, url, max_items=20) for name, url in flagship_sources], return_exceptions=True)
        for result in flagship_results:
            if isinstance(result, list): all_articles.extend(result)
        if category not in CATEGORIES_WITHOUT_SUPABASE:
            try:
                supabase_feeds   = await get_feeds_from_supabase(category=category, limit=10)
                supabase_sources = deduplicate_feeds(supabase_feeds)
                supabase_results = await asyncio.gather(*[fetch_rss_source(name, url, max_items=5) for name, url in supabase_sources[:20]], return_exceptions=True)
                for result in supabase_results:
                    if isinstance(result, list): all_articles.extend(result)
            except Exception as e:
                print(f"⚠️ Supabase feeds erreur: {str(e)[:50]}")
        try:
            keywords = CATEGORY_KEYWORDS.get(category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{NEWS_API_URL}/everything",
                    params={"apiKey": NEWS_API_KEY, "q": keywords, "language": "fr", "sortBy": "publishedAt", "pageSize": 10},
                    timeout=15.0)
            for article in response.json().get("articles", []):
                if article.get("title") and article.get("title") != "[Removed]":
                    all_articles.append({"title": article.get("title"), "description": article.get("description"),
                        "url": article.get("url"), "image_url": article.get("urlToImage"),
                        "source": article.get("source", {}).get("name"), "published_at": article.get("publishedAt")})
        except Exception as e:
            print(f"⚠️ NewsAPI erreur: {str(e)[:50]}")
        unique_articles = deduplicate_articles(all_articles)
        if not unique_articles: continue
        urls = [a.get("url") for a in unique_articles if a.get("url")]
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{SUPABASE_URL}/rest/v1/news_articles",
                    headers=SB_HEADERS(),
                    params={"select": "url", "url": f"in.({','.join([chr(34)+u+chr(34) for u in urls[:50]])})"},
                    timeout=10.0)
            existing_urls = {row["url"] for row in r.json()} if isinstance(r.json(), list) else set()
        except:
            existing_urls = set()
        new_articles = [a for a in unique_articles if a.get("url") not in existing_urls]
        total_skipped += len(unique_articles) - len(new_articles)
        if not new_articles: continue
        texts = [f"[{a.get('source','')}] [{category}] {a.get('title','')}. {a.get('description','') or ''}".strip()[:1000] for a in new_articles]
        all_embeddings = []
        for i in range(0, len(texts), 32):
            batch      = texts[i:i+32]
            embeddings = await embed_texts(batch)
            all_embeddings.extend(embeddings)
            await asyncio.sleep(0.3)
        stored = 0
        for article, embedding in zip(new_articles, all_embeddings):
            if embedding:
                await upsert_article(article, embedding, category)
                stored += 1
        total_embedded += stored
        print(f"   ✅ {category}: {stored} articles vectorisés")
        last_embed_time[category] = datetime.now(timezone.utc)
    try:
        await sb_delete('news_articles', {"published_at": "lt.NOW() - INTERVAL '7 days'"})
        print("🗑️ Vieux articles nettoyés")
    except Exception as e:
        print(f"⚠️ Nettoyage erreur: {str(e)[:50]}")
    return total_embedded, total_skipped

@app.post("/news/embed")
async def embed_news(req: EmbedNewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        total_embedded, total_skipped = await _embed_news_logic(req.categories, req.hours_back)
        return {"success": True, "embedded": total_embedded, "skipped": total_skipped}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/news/semantic")
async def semantic_news(req: SemanticNewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        import time
        t0         = time.time()
        all_scores = {}
        ema_vector = [float(v) for v in req.taste_vector] if req.taste_vector else []
        if ema_vector:
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{SUPABASE_URL}/rest/v1/rpc/search_news_articles",
                    headers=SB_HEADERS(),
                    json={"query_embedding": ema_vector, "p_category": req.category if req.category != 'general' else None, "p_limit": 50, "p_hours": req.hours_back},
                    timeout=10.0)
            results = r.json()
            if isinstance(results, list):
                for article in results:
                    url = article.get("url")
                    if url:
                        if url not in all_scores: all_scores[url] = {"article": article, "score": 0}
                        all_scores[url]["score"] += article.get("similarity", 0) * 0.50
        centroid_vector = []
        if req.liked_urls:
            centroid_vector = await get_taste_vector(req.liked_urls)
            if centroid_vector:
                weight = 0.30 if ema_vector else 0.50
                async with httpx.AsyncClient() as client:
                    r = await client.post(f"{SUPABASE_URL}/rest/v1/rpc/search_news_articles",
                        headers=SB_HEADERS(),
                        json={"query_embedding": centroid_vector, "p_category": req.category if req.category != 'general' else None, "p_limit": 50, "p_hours": req.hours_back},
                        timeout=10.0)
                results = r.json()
                if isinstance(results, list):
                    for article in results:
                        url = article.get("url")
                        if url:
                            if url not in all_scores: all_scores[url] = {"article": article, "score": 0}
                            all_scores[url]["score"] += article.get("similarity", 0) * weight
        texts = {}
        if req.interests: texts["interests"] = ", ".join(req.interests)
        profile_parts = []
        if req.profile_traits: profile_parts.append(f"Traits : {', '.join(req.profile_traits)}")
        if req.context.get('metier'):   profile_parts.append(f"Métier : {req.context['metier']}")
        if req.context.get('passions'): profile_parts.append(f"Passions : {', '.join(req.context.get('passions', []))}")
        if profile_parts: texts["profile"] = " | ".join(profile_parts)
        if not texts and not ema_vector and not centroid_vector:
            texts["category"] = CATEGORY_KEYWORDS.get(req.category, 'actualité france')
        WEIGHTS = {
            "interests": 0.25 if (ema_vector or centroid_vector) else 0.40,
            "profile":   0.15 if (ema_vector or centroid_vector) else 0.25,
            "category":  0.05 if (ema_vector or centroid_vector) else 0.10,
        }
        if texts:
            text_list  = list(texts.values())
            keys_list  = list(texts.keys())
            embeddings = await embed_texts(text_list)
            for key, embedding in zip(keys_list, embeddings):
                weight = WEIGHTS.get(key, 0.1)
                async with httpx.AsyncClient() as client:
                    r = await client.post(f"{SUPABASE_URL}/rest/v1/rpc/search_news_articles",
                        headers=SB_HEADERS(),
                        json={"query_embedding": embedding, "p_category": req.category if req.category != 'general' else None, "p_limit": 50, "p_hours": req.hours_back},
                        timeout=10.0)
                results = r.json()
                if not isinstance(results, list): continue
                for article in results:
                    url = article.get("url")
                    if not url: continue
                    if url not in all_scores: all_scores[url] = {"article": article, "score": 0}
                    all_scores[url]["score"] += article.get("similarity", 0) * weight
        if not all_scores: return {"articles": []}
        disliked_lower = [t.lower() for t in req.disliked_titles]
        filtered = {url: data for url, data in all_scores.items() if not any(d in data["article"].get("title","").lower() for d in disliked_lower)}
        max_score   = max((d["score"] for d in filtered.values()), default=1)
        min_score   = min((d["score"] for d in filtered.values()), default=0)
        score_range = max_score - min_score or 1
        now = datetime.now(timezone.utc)
        for url, data in filtered.items():
            normalized_score = (data["score"] - min_score) / score_range
            try:
                pub_str  = str(data["article"].get("published_at", ""))
                pub_date = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
                age_hours  = (now - pub_date).total_seconds() / 3600
                time_score = max(0, 1 - (age_hours / 48))
            except:
                time_score = 0
            data["final_score"] = normalized_score * 0.60 + time_score * 0.40
        sorted_articles = sorted(filtered.values(), key=lambda x: x["final_score"], reverse=True)[:req.limit]
        final = []
        for item in sorted_articles:
            a = item["article"]
            final.append({"title": a.get("title"), "description": a.get("description"), "url": a.get("url"),
                "source": a.get("source"), "image_url": a.get("image_url"),
                "published_at": str(a.get("published_at","")), "category": a.get("category"),
                "score": round(item["final_score"], 4)})
        print(f"✅ Semantic: {len(final)} articles — {time.time()-t0:.2f}s")
        return {"articles": final}
    except Exception as e:
        print(f"❌ ERREUR semantic_news: {str(e)}")
        import traceback; traceback.print_exc()
        return {"articles": []}

async def get_taste_vector(liked_urls: list) -> list:
    if not liked_urls: return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{SUPABASE_URL}/rest/v1/news_articles",
                headers=SB_HEADERS(),
                params={"select": "embedding", "url": f"in.({','.join([chr(34)+u+chr(34) for u in liked_urls[:20]])})"},
                timeout=10.0)
        rows = r.json()
        if not isinstance(rows, list) or not rows: return []
        embeddings = []
        for row in rows:
            emb = row.get("embedding")
            if not emb: continue
            if isinstance(emb, str): emb = json.loads(emb)
            embeddings.append([float(v) for v in emb])
        if not embeddings: return []
        n   = len(embeddings)
        dim = len(embeddings[0])
        centroid = [sum(embeddings[i][j] for i in range(n)) / n for j in range(dim)]
        return centroid
    except Exception as e:
        print(f"⚠️ Erreur get_taste_vector: {str(e)[:50]}")
        return []

@app.post("/news/article_vector")
async def get_article_vector(req: ArticleVectorRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{SUPABASE_URL}/rest/v1/news_articles",
                headers=SB_HEADERS(),
                params={"select": "embedding", "url": f"eq.{req.url}", "limit": "1"},
                timeout=5.0)
        rows = r.json()
        if isinstance(rows, list) and rows and rows[0].get("embedding"):
            embedding = rows[0]["embedding"]
            if isinstance(embedding, str): embedding = json.loads(embedding)
            return {"embedding": [float(v) for v in embedding]}
        return {"embedding": None}
    except Exception as e:
        print(f"⚠️ Erreur article_vector: {str(e)[:50]}")
        return {"embedding": None}

# ── ENDPOINTS CONNEXIONS — Supabase ──
@app.post("/connection/request")
async def connection_request(request: Request):
    body       = await request.json()
    from_code  = body.get("from_code", "").strip().upper()
    to_code    = body.get("to_code",   "").strip().upper()
    from_alias = body.get("from_alias", "Inconnu")
    to_alias   = body.get("to_alias",   "Inconnu")
    if not from_code or not to_code:
        return {"success": False, "error": "Codes manquants"}
    if from_code == to_code:
        return {"success": False, "error": "Tu ne peux pas te connecter à toi-même"}
    try:
        existing_pending = await sb_get('connection_requests', {"from_code": f"eq.{from_code}", "to_code": f"eq.{to_code}", "status": "eq.pending", "select": "id"})
        if existing_pending: return {"success": False, "error": "Demande déjà en attente"}
        existing_accepted = await sb_get('connection_requests', {"from_code": f"eq.{from_code}", "to_code": f"eq.{to_code}", "status": "eq.accepted", "select": "id"})
        if existing_accepted: return {"success": False, "error": "Connexion déjà établie"}
        data = await sb_post('connection_requests', {
            "from_code": from_code, "to_code": to_code,
            "from_alias": from_alias, "to_alias": to_alias, "status": "pending",
        }, prefer="return=representation")
        request_id = data[0]["id"] if data else None
        token_row  = await sb_get_one('push_tokens', {"my_code": f"eq.{to_code}"})
        if token_row:
            await send_push_notification(
                push_token=token_row['push_token'],
                title='🔗 Nouvelle demande de connexion',
                body=f'{from_alias} veut se connecter avec toi !',
                data={'screen': 'Social'}
            )
        return {"success": True, "request_id": request_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/connection/pending/{code}")
async def connection_pending(code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    code = code.strip().upper()
    requests = await sb_get('connection_requests', {"to_code": f"eq.{code}", "status": "eq.pending", "select": "*", "order": "created_at.desc"})
    return {"requests": requests}

@app.post("/connection/respond")
async def connection_respond(request: Request, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    body       = await request.json()
    request_id = body.get("request_id")
    accepted   = body.get("accepted", False)
    my_code    = body.get("my_code", "").strip().upper()
    my_alias   = body.get("my_alias", "Inconnu")
    if not request_id:
        return {"success": False, "error": "request_id manquant"}
    try:
        data = await sb_get('connection_requests', {"id": f"eq.{request_id}", "to_code": f"eq.{my_code}", "status": "eq.pending", "select": "*"})
        if not data: return {"success": False, "error": "Demande introuvable"}
        req_data   = data[0]
        new_status = "accepted" if accepted else "rejected"
        await sb_patch('connection_requests', {"id": f"eq.{request_id}"}, {"status": new_status, "updated_at": "now()"})
        if accepted:
            mirror = await sb_get('connection_requests', {"from_code": f"eq.{my_code}", "to_code": f"eq.{req_data['from_code']}", "status": "eq.accepted", "select": "id"})
            if not mirror:
                await sb_post('connection_requests', {
                    "from_code": my_code, "to_code": req_data["from_code"],
                    "from_alias": my_alias, "to_alias": req_data["from_alias"], "status": "accepted",
                }, prefer="return=representation")
            token_row = await sb_get_one('push_tokens', {"my_code": f"eq.{req_data['from_code']}"})
            if token_row:
                await send_push_notification(
                    push_token=token_row['push_token'],
                    title='🔗 Connexion acceptée !',
                    body=f'{my_alias} a accepté ta demande de connexion.',
                    data={'screen': 'Social'}
                )
        return {"success": True, "status": new_status, "from_code": req_data["from_code"], "from_alias": req_data["from_alias"], "to_alias": req_data["to_alias"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/connection/accepted/{code}")
async def connection_accepted(code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    code = code.strip().upper()
    try:
        r_sent     = await sb_get('connection_requests', {"from_code": f"eq.{code}", "status": "eq.accepted", "select": "to_code,to_alias"})
        r_received = await sb_get('connection_requests', {"to_code": f"eq.{code}",   "status": "eq.accepted", "select": "from_code,from_alias"})
        connections_map = {}
        for c in r_received:
            their_code = c["from_code"]
            connections_map[their_code] = {"their_code": their_code, "their_alias": c["from_alias"] or their_code}
        for c in r_sent:
            their_code = c["to_code"]
            connections_map[their_code] = {"their_code": their_code, "their_alias": c["to_alias"] or their_code}
        return {"connections": list(connections_map.values())}
    except Exception as e:
        return {"connections": [], "error": str(e)}

@app.get("/connection/sent/{code}")
async def connection_sent(code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    code     = code.strip().upper()
    requests = await sb_get('connection_requests', {"from_code": f"eq.{code}", "select": "*", "order": "created_at.desc"})
    return {"requests": requests}

@app.patch("/connection/alias")
async def update_connection_alias(request: Request, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    body      = await request.json()
    from_code = body.get("from_code", "").strip().upper()
    to_code   = body.get("to_code",   "").strip().upper()
    new_alias = body.get("new_alias", "").strip()
    if not from_code or not to_code or not new_alias:
        return {"success": False, "error": "Données manquantes"}
    await sb_patch('connection_requests', {"from_code": f"eq.{from_code}", "to_code": f"eq.{to_code}", "status": "eq.accepted"}, {"to_alias": new_alias})
    return {"success": True}

@app.delete("/connection/request/{request_id}")
async def delete_connection_request(request_id: int, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    await sb_delete('connection_requests', {"id": f"eq.{request_id}"})
    return {"success": True}

@app.post("/connection/synced")
async def connection_synced(request: Request, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    body    = await request.json()
    my_code = body.get("my_code", "").strip().upper()
    try:
        await sb_patch('connection_requests', {"from_code": f"eq.{my_code}", "status": "eq.accepted"}, {"synced_from": True})
        await sb_patch('connection_requests', {"to_code":   f"eq.{my_code}", "status": "eq.accepted"}, {"synced_to":   True})
        await sb_delete('connection_requests', {"status": "eq.accepted", "synced_from": "eq.true", "synced_to": "eq.true"})
        await sb_delete('connection_requests', {"from_code": f"eq.{my_code}", "status": "eq.rejected"})
        await sb_delete('connection_requests', {"to_code":   f"eq.{my_code}", "status": "eq.rejected"})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ── ENDPOINTS ADMIN ──
@app.post("/admin/cleanup")
async def manual_cleanup(x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        await sb_delete('connection_requests', {"status": "eq.rejected", "updated_at": f"lt.NOW() - INTERVAL '{REJECTED_EXPIRY_DAYS} days'"})
        await sb_delete('connection_requests', {"status": "eq.pending",  "created_at": f"lt.NOW() - INTERVAL '{PENDING_EXPIRY_DAYS} days'"})
        return {"success": True, "message": "Nettoyage effectué"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.delete("/admin/reset-social")
async def reset_social(x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    await sb_delete('gifts',       {"id": "neq.IMPOSSIBLE"})
    await sb_delete('comparisons', {"id": "neq.IMPOSSIBLE"})
    await sb_delete('push_tokens', {"id": "gt.0"})
    return {"success": True, "message": "Reset social OK"}



# REGARD CROISEE

@app.post("/rc/session")
async def rc_create_session(req: RCCreateSessionRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        import random
        chars    = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        segments = [''.join(random.choices(chars, k=4)) for _ in range(6)]
        session_key = 'RC-' + '-'.join(segments)

        version = req.version if req.version in ['universel', 'jeunes', 'pro'] else 'universel'

        await sb_post('rc_sessions', {
            "session_key":    session_key,
            "response_count": 0,
            "max_responses":  10,
            "version":        version,   # ← ajoute
            "expires_at":     (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        })

        print(f"✅ Session RC créée: {session_key} (version: {version})")
        return {"success": True, "session_key": session_key, "version": version}
    except Exception as e:
        return {"success": False, "error": str(e)}




@app.post("/rc/respond")
async def rc_respond(req: RCRespondRequest):
    """Paulo répond au questionnaire (web ou app)"""
    try:
        # Vérifie que la session existe
        session = await sb_get_one('rc_sessions', {
            "session_key": f"eq.{req.session_key}",
            "select":      "*",
        })
        if not session:
            return {"success": False, "error": "Session introuvable ou expirée"}

        # Vérifie que la session n'est pas pleine
        if session['response_count'] >= session['max_responses']:
            return {"success": False, "error": "Nombre maximum de réponses atteint"}

        # Enregistre la réponse
        await sb_post('rc_responses', {
            "session_key":    req.session_key,
            "vector":         req.vector,
            "words":          req.words,
            "relation":       req.relation,
            "respondent_name": req.respondent_name,
            "is_anonymous":   req.is_anonymous,
            "source":         req.source,
            "raw_answers":    req.raw_answers,   # ← ajoute
        })

        # Incrémente le compteur
        await sb_patch('rc_sessions',
            params={"session_key": f"eq.{req.session_key}"},
            body={"response_count": session['response_count'] + 1}
        )

        print(f"✅ Réponse RC reçue: {req.session_key} ({req.relation})")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/rc/responses/{session_key}")
async def rc_get_responses(session_key: str, x_app_secret: str = Header(None)):
    """Denis récupère ses réponses"""
    verify_secret(x_app_secret)
    try:
        responses = await sb_get('rc_responses', {
            "session_key": f"eq.{session_key}",
            "select":      "*",
            "order":       "created_at.asc",
        })
        return {"success": True, "responses": responses}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/rc/response/{response_id}")
async def rc_delete_response(response_id: str, x_app_secret: str = Header(None)):
    """Denis supprime une réponse après l'avoir récupérée"""
    verify_secret(x_app_secret)
    await sb_delete('rc_responses', {"id": f"eq.{response_id}"})
    return {"success": True}


@app.delete("/rc/session/{session_key}")
async def rc_delete_session(session_key: str, x_app_secret: str = Header(None)):
    """Denis supprime toute la session (CASCADE supprime les réponses)"""
    verify_secret(x_app_secret)
    await sb_delete('rc_sessions', {"session_key": f"eq.{session_key}"})
    return {"success": True}


@@app.post("/rc/invite")
async def rc_invite(req: RCInviteRequest, x_app_secret: str = Header(None)):
    """Denis invite une connexion monJumeau (chemin B)"""
    verify_secret(x_app_secret)
    try:
        # Vérifie que la session existe
        session = await sb_get_one('rc_sessions', {
            "session_key": f"eq.{req.session_key}",
            "select":      "session_key",
        })
        if not session:
            return {"success": False, "error": "Session introuvable"}

        # ── Vérifie qu'aucune invitation pending n'existe déjà ──
        existing = await sb_get('rc_invitations', {
            "session_key": f"eq.{req.session_key}",
            "to_code":     f"eq.{req.to_code}",
            "status":      "eq.pending",
            "select":      "id",
        })
        if existing:
            return {"success": False, "error": "already_invited"}

        # Crée l'invitation
        data = await sb_post('rc_invitations', {
            "session_key": req.session_key,
            "from_code":   req.from_code,
            "to_code":     req.to_code,
            "relation":    req.relation,
            "status":      "pending",
            "expires_at":  (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }, prefer="return=representation")
        invitation_id = data[0]["id"] if data else None

        # Push notification à Paulo
        token_row = await sb_get_one('push_tokens', {"my_code": f"eq.{req.to_code}"})
        if token_row:
            await send_push_notification(
                push_token=token_row['push_token'],
                title='🪞 Regard Croisé',
                body='Un proche t\'invite à partager ton regard sur lui !',
                data={'screen': 'RegardCroise', 'invitation_id': str(invitation_id)}
            )
        return {"success": True, "invitation_id": invitation_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
    

@app.get("/rc/invitations/sent/{from_code}")
async def rc_invitations_sent(from_code: str):
    try:
        invitations = await sb_get('rc_invitations', {
            'from_code': f'eq.{from_code}',
            'status':    'eq.pending',
        })
        return { "success": True, "invitations": invitations }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rc/invitations/{my_code}")
async def rc_get_invitations(my_code: str, x_app_secret: str = Header(None)):
    """Paulo récupère ses invitations en attente"""
    verify_secret(x_app_secret)
    invitations = await sb_get('rc_invitations', {
        "to_code": f"eq.{my_code}",
        "status":  "eq.pending",
        "select":  "*",
        "order":   "created_at.desc",
    })
    return {"success": True, "invitations": invitations}


@app.post("/rc/invitation/respond")
async def rc_respond_invitation(req: RCRespondInviteRequest, x_app_secret: str = Header(None)):
    """Paulo répond via l'app (chemin B)"""
    verify_secret(x_app_secret)
    try:
        # Récupère l'invitation
        invitation = await sb_get_one('rc_invitations', {
            "id":     f"eq.{req.invitation_id}",
            "status": "eq.pending",
            "select": "*",
        })
        if not invitation:
            return {"success": False, "error": "Invitation introuvable"}

        # Enregistre la réponse
        await sb_post('rc_responses', {
            "session_key":    invitation['session_key'],
            "vector":         req.vector,
            "words":          req.words,
            "relation":       invitation['relation'],
            "respondent_name": req.respondent_name,
            "is_anonymous":   req.is_anonymous,
            "source":         "app",
            "raw_answers":    req.raw_answers,   # ← est-ce présent ?
        })

        # Marque l'invitation comme répondue
        await sb_patch('rc_invitations',
            params={"id": f"eq.{req.invitation_id}"},
            body={"status": "responded"}
        )

        # Incrémente le compteur de la session
        session = await sb_get_one('rc_sessions', {
            "session_key": f"eq.{invitation['session_key']}",
            "select": "response_count",
        })
        if session:
            await sb_patch('rc_sessions',
                params={"session_key": f"eq.{invitation['session_key']}"},
                body={"response_count": session['response_count'] + 1}
            )

        # Push notif à Denis
        token_row = await sb_get_one('push_tokens', {"my_code": f"eq.{invitation['from_code']}"})
        if token_row:
            await send_push_notification(
                push_token=token_row['push_token'],
                title='🪞 Nouvelle réponse Regard Croisé',
                body='Un proche vient de répondre sur toi !',
                data={'screen': 'RegardCroise'}
            )

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/rc/session/{session_key}/count")
async def rc_get_count(session_key: str):
    """Vérifie le nombre de réponses — accessible sans auth (pour la WebApp)"""
    session = await sb_get_one('rc_sessions', {
        "session_key": f"eq.{session_key}",
        "select":      "response_count,max_responses,expires_at",
    })
    if not session:
        return {"valid": False}
    return {
        "valid":          True,
        "response_count": session['response_count'],
        "max_responses":  session['max_responses'],
        "expires_at":     session['expires_at'],
    }




async def cleanup_old_requests():
    while True:
        try:
            print("🗑️ Nettoyage automatique Supabase...")
            # ... code existant ...

            # ← Ajoute le nettoyage RC
            await sb_delete('rc_sessions', {"expires_at": "lt.NOW()"})
            print("   ✅ Sessions RC expirées supprimées")

        except Exception as e:
            print(f"⚠️ Erreur cleanup: {str(e)[:50]}")
        await asyncio.sleep(24 * 60 * 60)


# WEBAPP

@app.get("/rc/{session_key}", response_class=HTMLResponse)
async def rc_webapp(session_key: str, v: str = "universel"):
    """Sert la WebApp — v = universel | jeunes | pro"""
    session = await sb_get_one('rc_sessions', {
        "session_key": f"eq.{session_key}",
        "select":      "session_key,response_count,max_responses,expires_at,version",
    })
    if not session:
        return HTMLResponse(content="""
        <html><body style="font-family:sans-serif;text-align:center;padding:40px">
          <h2>Lien invalide ou expiré</h2>
          <p>Ce questionnaire n'est plus disponible.</p>
        </body></html>
        """, status_code=404)

    # Récupère la version depuis la session ou le paramètre URL
    version = session.get('version') or v
    if version not in ['universel', 'jeunes', 'pro']:
        version = 'universel'

    html = (RC_WEBAPP_HTML
        .replace("__SESSION_KEY__", session_key)
        .replace("__API_URL__", str(os.environ.get("API_URL", "https://monjumeau-api.onrender.com")))
        .replace("__VERSION__", version)
    )
    return HTMLResponse(content=html)