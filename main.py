from fastapi import FastAPI, HTTPException, Header, Request
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
import random

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

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_EMBED_URL = "https://api.mistral.ai/v1/embeddings"
MISTRAL_EMBED_MODEL = "mistral-embed"

CAT_MAP = {
    'general':       'presse',
    'technology':    'technologie',
    'science':       'environnement',  # ← science → environnement (le plus proche)
    'business':      'économie',
    'entertainment': 'culture',
    'sports':        'sport',
    'health':        'environnement',  # ← health → environnement (bien-être, nature)
    'politics':      'politique',
}


CATEGORY_KEYWORDS = {
    'general': 'actualité france',
    'technology': 'technologie intelligence artificielle numérique',
    'science': 'science découverte recherche',
    'business': 'économie entreprise finance',
    'entertainment': 'cinéma culture musique',
    'sports': 'sport football tennis',
    'health': 'santé médecine bien-être',
    'politics':      'politique france gouvernement assemblée',  # ← ajoute ça

}

EXCLUDED_DOMAINS = [
    '20min.ch',
    'rts.ch',
    'rtbf.be',
    'lesoir.be',
    'rtl.lu',
    'bsky.app',
    'flipboard.com',
]

RSS_SOURCES = {
    'general': [
        ('Le Monde', 'https://www.lemonde.fr/rss/une.xml'),
        ('Le Figaro', 'https://www.lefigaro.fr/rss/figaro_actualites.xml'),
        ('France Info', 'https://www.francetvinfo.fr/titres.rss'),
        ('20 Minutes', 'https://www.20minutes.fr/feeds/rss/news'),
        ('Libération', 'https://www.liberation.fr/arc/outboundfeeds/rss/'),
        ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-politique.xml'),
    ],
    'technology': [
        ('01net', 'https://www.01net.com/actualites/feed/'),
        ('Numerama', 'https://www.numerama.com/feed/'),
        ('Frandroid', 'https://www.frandroid.com/feed'),
        ('Korben', 'https://korben.info/feed'),
        ('Journal du Geek', 'https://www.journaldugeek.com/feed/'),
        ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-tech-medias.xml'),
        ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-start-up.xml'),
        ('ZDNet France', 'https://www.zdnet.fr/feeds/rss/actualites/'),
        ('Silicon', 'https://www.silicon.fr/feed'),
    ],
    'science': [
        ('Sciences et Avenir', 'https://www.sciencesetavenir.fr/rss.xml'),
        ('Futura Sciences', 'https://www.futura-sciences.com/rss/actualites.rss'),
        ('Science Post', 'https://sciencepost.fr/feed/'),
    ],
    'business': [
        ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-economie.xml'),
        ('Le Point Economie', 'https://www.lepoint.fr/economie/rss.xml'),
        ('BFM Business', 'https://www.bfmtv.com/rss/economie/'),
        ('Le Monde Economie', 'https://www.lemonde.fr/economie-francaise/rss_full.xml'),
        ('20 minutes', 'https://www.20minutes.fr/feeds/rss-economie.xml'),
    ],
    'entertainment': [
        ('Allociné', 'https://www.allocine.fr/rss/news.xml'),
        ('Première', 'http://www.premiere.fr/rss/actu-live'),
        ('Télérama', 'https://www.telerama.fr/rss/latest-articles.xml'),
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


# Flux "une" garantis des grands médias français
FLAGSHIP_FEEDS = {
        'general': [
            ('Le Monde', 'https://www.lemonde.fr/rss/une.xml'),
            #('Le Figaro', 'https://www.lefigaro.fr/rss/figaro_actualites.xml'),
            ('Le Figaro', 'https://news.google.com/rss/search?q=site:lefigaro.fr&hl=fr&gl=FR&ceid=FR:fr'),
            ('Libération', 'https://www.liberation.fr/arc/outboundfeeds/rss/'),
            ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-politique.xml'),
            # Bonus — toujours bienvenus

            ('France Info', 'https://www.francetvinfo.fr/titres.rss'),
            ('Le Parisien', 'https://feeds.leparisien.fr/leparisien/rss'),
            ('France Inter', 'https://www.radiofrance.fr/franceinter/rss'),
            ('BFM TV', 'https://www.bfmtv.com/rss/info/flux-rss/toutes-les-actualites/'),
            ('L\'Express', 'https://www.lexpress.fr/arc/outboundfeeds/rss/'),
            ('Le Point', 'https://www.lepoint.fr/rss.xml'),
            ('20 Minutes', 'https://www.20minutes.fr/feeds/rss-une.xml'),
            ('Ouest France', 'https://www.ouest-france.fr/rss/une'),
        ],
        'technology': [
            ('01net', 'https://www.01net.com/actualites/feed/'),
            ('Numerama', 'https://www.numerama.com/feed/'),
            ('Frandroid', 'https://www.frandroid.com/feed'),
            ('Korben', 'https://korben.info/feed'),
            ('Journal du Geek', 'https://www.journaldugeek.com/feed/'),
            ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-tech-medias.xml'),
            ('Les Echos', 'https://news.google.com/rss/search?q=les+echos+tech&hl=fr&gl=FR&ceid=FR:fr'),
            ('ZDNet France', 'https://www.zdnet.fr/feeds/rss/actualites/'),
            ('Silicon', 'https://www.silicon.fr/feed'),
        ],
        'science': [
            ('Sciences et Avenir', 'https://www.sciencesetavenir.fr/rss.xml'),
            ('Futura Sciences', 'https://www.futura-sciences.com/rss/actualites.rss'),
            ('Science Post', 'https://sciencepost.fr/feed/'),
        ],
        'business': [
            ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-economie.xml'),
            ('Le Point Economie', 'https://www.lepoint.fr/economie/rss.xml'),
            ('BFM Business', 'https://www.bfmtv.com/rss/economie/'),
            ('Challenges', 'https://www.challenges.fr/rss.xml'),
            ('La Tribune', 'https://www.latribune.fr/rss/une.xml'),
        ],
        'entertainment': [
            ('Allociné', 'https://www.allocine.fr/rss/news.xml'),
            ('Première', 'http://www.premiere.fr/rss/actu-live'),
            ('Télérama', 'https://www.telerama.fr/rss/latest-articles.xml'),
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
        'politics': [  # ← ajoute ça
            ('Le Monde Politique', 'https://www.lemonde.fr/politique/rss_full.xml'),
            ('France Info Politique', 'https://www.francetvinfo.fr/politique.rss'),
            ('Le Point Politique', 'https://www.lepoint.fr/politique/rss.xml'),
            ('L\'Express Politique', 'https://www.lexpress.fr/arc/outboundfeeds/rss/rubriques/politique.xml'),
            ('Libération Politique', 'https://www.liberation.fr/arc/outboundfeeds/rss/category/politique/'),
            ('France Inter Politique', 'https://www.radiofrance.fr/franceinter/podcasts/le-telephone-sonne/rss'),
            ('Le NouvelObs Politique', 'https://www.nouvelobs.com/politique/rss.xml'),
            ('BFM Politique', 'https://www.bfmtv.com/rss/politique/'),
            ('20 Minutes Politique', 'https://www.20minutes.fr/feeds/rss-politique.xml'),
            ('Mediapart', 'https://www.mediapart.fr/articles/feed'),
            ('Les Echos', 'https://services.lesechos.fr/rss/les-echos-politique.xml'),
         ],
    }

# Catégories sans correspondance dans Supabase → flagship uniquement
CATEGORIES_WITHOUT_SUPABASE = ['health', 'science']

pays_autorises = ['fra', 'cor', 'bre']

spotify_token = None
spotify_token_expiry = 0
ft_token = None
ft_token_expiry = 0

# ── Auto-embed tracking ──
last_embed_time = {}  # category → datetime

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
    categories: list = ['general', 'technology', 'business',
                        'entertainment', 'sports', 'health',
                        'science', 'politics']
    hours_back: int = 2  # Ne re-vectorise que les X dernières heures


class SemanticNewsRequest(BaseModel):
    profile_traits: list = []
    personality: dict = {}
    context: dict = {}
    interests: list = []
    locations: list = []
    liked_titles: list = []
    disliked_titles: list = []
    liked_urls: list = []           # ← ajoute
    liked_with_dates: list = []     # ← ajoute
    taste_vector: list = []  # ← EMA local
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

# ── HELPERS RSS ──
def is_excluded_url(url):
    return any(domain in url for domain in EXCLUDED_DOMAINS)

def clean_html(text):
    if not text:
        return ''
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300] if len(text) > 300 else text

def extract_image_from_entry(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            url = media.get('url', '')
            if url and ('image' in media.get('type', '') or
                        media.get('medium') == 'image' or
                        url.endswith(('.jpg', '.jpeg', '.png', '.webp'))):
                return url
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get('url', '')
        if url:
            return url
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if 'image' in enc.get('type', ''):
                return enc.get('href') or enc.get('url')
    content = ''
    if hasattr(entry, 'content') and entry.content:
        content = entry.content[0].get('value', '')
    elif hasattr(entry, 'summary'):
        content = entry.summary or ''
    elif hasattr(entry, 'description'):
        content = entry.description or ''
    img_match = re.search(
        r'<img[^>]+src=["\']([^"\']+\.(jpg|jpeg|png|webp|gif))["\']',
        content, re.IGNORECASE
    )
    if img_match:
        url = img_match.group(1)
        if url.startswith('http'):
            return url
    if hasattr(entry, 'image') and entry.image:
        url = entry.image.get('href') or entry.image.get('url', '')
        if url:
            return url
    if hasattr(entry, 'links'):
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    return None

def parse_date(entry):
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

def sort_by_date(articles):
    def sort_key(a):
        try:
            date_str = a.get('published_at', '')
            if not date_str:
                return datetime.min.replace(tzinfo=timezone.utc)
            date_str = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    return sorted(articles, key=sort_key, reverse=True)

async def mark_feed_inactive(url: str):
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

async def fetch_rss_source(source_name: str, url: str, max_items: int = 5):
    try:
        loop = asyncio.get_event_loop()
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url),
            timeout=15.0
        )
        if feed.bozo and not feed.entries:
            bozo_exception = str(feed.get('bozo_exception', ''))
            fatal_errors = [
                'Name or service not known',
                'nodename nor servname provided',
                'No address associated',
                'Connection refused',
                'No route to host',
                'urlopen error',
            ]
            if any(err in bozo_exception for err in fatal_errors):
                print(f"💀 Flux mort: {source_name}")
                await mark_feed_inactive(url)
            return []
        if not feed.entries:
            return []
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
        print(f"   {'✅' if articles else '⚠️ '} {source_name} → {len(articles)} articles")
        return articles
    except asyncio.TimeoutError:
        print(f"⏱ Timeout: {source_name}")
        return []
    except Exception as e:
        print(f"⚠️ Erreur RSS {source_name}: {str(e)[:100]}")
        return []

# ── SUPABASE RSS ──
async def get_feeds_from_supabase_origine(
    category: str, limit: int = 15,
    interests: list = [],
    locations: list = [],
    langues: list = [],
):
    
    

    LANGUE_TO_PAYS = {
        'anglais':  'ang',
        'italien':  'ita',
        'espagnol': 'esp',
        'suisse':   'sui',
    }

    pays_autorises = ['fra', 'cor', 'bre']
    for langue in langues:
        pays = LANGUE_TO_PAYS.get(langue.lower())
        if pays and pays not in pays_autorises:
            pays_autorises.append(pays)
            print(f"🌍 Langue '{langue}' → pays '{pays}' ajouté")

    print(f"🌍 Pays autorisés: {pays_autorises}")

    supabase_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        all_feeds = []

        # ── 0. Flagship feeds — toujours en premier ──
        flagship = FLAGSHIP_FEEDS.get(category, FLAGSHIP_FEEDS['general'])
        all_feeds.extend(flagship)
        print(f"🏆 Flagship feeds: {len(flagship)} flux")


        # ── 1. Flux par catégorie — via fonction SQL get_random_feeds ──
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_random_feeds",
                headers=supabase_headers,
                json={
                    "p_categorie": CAT_MAP.get(category, 'presse'),
                    "p_pays_codes": pays_autorises,
                    "p_limit": limit,
                },
                timeout=10.0,
            )

        print(f"🔍 Status Supabase RPC: {r.status_code}")
        print(f"🔍 Réponse brute: {r.text[:300]}")

        feeds = r.json()
        if isinstance(feeds, list):
            feeds = [f for f in feeds if not is_excluded_url(f.get('feed_url', ''))]
            all_feeds.extend([(f['source_name'], f['feed_url']) for f in feeds])
            print(f"📂 Catégorie '{category}': {len(feeds)} flux (aléatoires)")
        else:
            print(f"⚠️ get_random_feeds réponse inattendue: {feeds}")

        # ── 2. Flux par centres d'intérêt ──
        for interest in interests[:3]:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/rss_feeds",
                    headers=supabase_headers,
                    params={
                        "select": "source_name,feed_url",
                        "is_active": "eq.true",
                        "is_youtube": "eq.false",
                        "pays_code": f"in.({','.join(pays_autorises)})",
                        "or": f"(sous_categorie.ilike.%{interest}%,groupe.ilike.%{interest}%,sous_groupe.ilike.%{interest}%,base_subject.ilike.%{interest}%,source_name.ilike.%{interest}%)",
                        "limit": "10",
                    },
                    timeout=10.0,
                )
            interest_feeds = r.json()
            if isinstance(interest_feeds, list):
                interest_feeds = [f for f in interest_feeds if not is_excluded_url(f.get('feed_url', ''))]
                all_feeds.extend([(f['source_name'], f['feed_url']) for f in interest_feeds])
                print(f"🎯 Intérêt '{interest}': {len(interest_feeds)} flux")
            else:
                print(f"⚠️ Intérêt '{interest}': réponse inattendue")

        # ── 3. Flux par lieux ──
        for location in locations[:3]:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/rss_feeds",
                    headers=supabase_headers,
                    params={
                        "select": "source_name,feed_url",
                        "is_active": "eq.true",
                        "is_youtube": "eq.false",
                        "pays_code": f"in.({','.join(pays_autorises)})",
                        "or": f"(region.ilike.%{location}%,ville.ilike.%{location}%,departement.ilike.%{location}%)",
                        "limit": "5",
                    },
                    timeout=10.0,
                )
            location_feeds = r.json()
            if isinstance(location_feeds, list):
                location_feeds = [f for f in location_feeds if not is_excluded_url(f.get('feed_url', ''))]
                all_feeds.extend([(f['source_name'], f['feed_url']) for f in location_feeds])
                print(f"📍 Lieu '{location}': {len(location_feeds)} flux")

        # ── 4. Dédupliquer par URL ──
        seen_urls = set()
        unique_feeds = []
        for name, url in all_feeds:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_feeds.append((name, url))

        # ── 5. Diversifier — max 2 flux par domaine ──
        domain_count = {}
        diverse_feeds = []
        for name, url in unique_feeds:
            domain = urlparse(url).netloc
            count = domain_count.get(domain, 0)
            if count < 2:
                diverse_feeds.append((name, url))
                domain_count[domain] = count + 1

        print(f"📡 Total: {len(all_feeds)} → {len(unique_feeds)} uniques → {len(diverse_feeds)} après diversification")
        return diverse_feeds or RSS_SOURCES.get(category, RSS_SOURCES['general'])

    except Exception as e:
        print(f"⚠️ Erreur Supabase: {str(e)}")
        import traceback
        traceback.print_exc()
        return RSS_SOURCES.get(category, RSS_SOURCES['general'])


async def get_feeds_from_supabase(
    category: str, limit: int = 15,
    interests: list = [],
    locations: list = [],
    langues: list = [],
):
    # ... code pays_autorises inchangé ...
    supabase_headers = {  # ← vérifier que c'est bien là
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        all_feeds = []

        # ── 0. Flagship — 10 flux garantis ──
        flagship = FLAGSHIP_FEEDS.get(category, FLAGSHIP_FEEDS['general'])
        all_feeds.extend(flagship)
        print(f"🏆 Flagship: {len(flagship)} flux")

        # ── 1. Supabase — 10 flux aléatoires ──
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/get_random_feeds",
                headers=supabase_headers,
                json={
                    "p_categorie": CAT_MAP.get(category, 'presse'),
                    "p_pays_codes": pays_autorises,
                    "p_limit": 10,  # ← 10 flux aléatoires
                },
                timeout=10.0,
            )
        feeds = r.json()
        if isinstance(feeds, list):
            feeds = [f for f in feeds if not is_excluded_url(f.get('feed_url', ''))]
            all_feeds.extend([(f['source_name'], f['feed_url']) for f in feeds])
            print(f"📂 Supabase: {len(feeds)} flux")

        # ── 2. Intérêts — jusqu'à 10 flux ──
        for interest in interests[:3]:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/rss_feeds",
                    headers=supabase_headers,
                    params={
                        "select": "source_name,feed_url",
                        "is_active": "eq.true",
                        "is_youtube": "eq.false",
                        "pays_code": f"in.({','.join(pays_autorises)})",
                        "or": f"(sous_categorie.ilike.%{interest}%,groupe.ilike.%{interest}%,sous_groupe.ilike.%{interest}%,base_subject.ilike.%{interest}%,source_name.ilike.%{interest}%)",
                        "limit": "10",  # ← 10 flux par intérêt (max 30 total)
                    },
                    timeout=10.0,
                )
            interest_feeds = r.json()
            if isinstance(interest_feeds, list):
                interest_feeds = [f for f in interest_feeds if not is_excluded_url(f.get('feed_url', ''))]
                all_feeds.extend([(f['source_name'], f['feed_url']) for f in interest_feeds])
                print(f"🎯 Intérêt '{interest}': {len(interest_feeds)} flux")

        # ── 3. Lieux — jusqu'à 5 flux ──
        for location in locations[:3]:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/rss_feeds",
                    headers=supabase_headers,
                    params={
                        "select": "source_name,feed_url",
                        "is_active": "eq.true",
                        "is_youtube": "eq.false",
                        "pays_code": f"in.({','.join(pays_autorises)})",
                        "or": f"(region.ilike.%{location}%,ville.ilike.%{location}%,departement.ilike.%{location}%)",
                        "limit": "5",  # ← 5 flux par lieu (max 15 total)
                    },
                    timeout=10.0,
                )
            location_feeds = r.json()
            if isinstance(location_feeds, list):
                location_feeds = [f for f in location_feeds if not is_excluded_url(f.get('feed_url', ''))]
                all_feeds.extend([(f['source_name'], f['feed_url']) for f in location_feeds])
                print(f"📍 Lieu '{location}': {len(location_feeds)} flux")

        # ── 4. Dédupliquer ──
        seen_urls = set()
        unique_feeds = []
        for name, url in all_feeds:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_feeds.append((name, url))

        # ── 5. Diversifier — max 2 flux par domaine ──
        domain_count = {}
        diverse_feeds = []
        for name, url in unique_feeds:
            domain = urlparse(url).netloc
            count = domain_count.get(domain, 0)
            if count < 2:
                diverse_feeds.append((name, url))
                domain_count[domain] = count + 1

        # ── 6. Log répartition ──
        flagship_count = len([f for f in diverse_feeds if f in flagship])
        print(f"📊 Répartition finale:")
        print(f"   🏆 Flagship : {flagship_count} flux")
        print(f"   📡 Total    : {len(diverse_feeds)} flux")

        return diverse_feeds or RSS_SOURCES.get(category, RSS_SOURCES['general'])

    except Exception as e:
        print(f"⚠️ Erreur Supabase: {str(e)}")
        import traceback
        traceback.print_exc()
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
    gift_id = str(uuid.uuid4())[:8].upper()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db.execute('''
        INSERT INTO gifts (id, from_code, to_code, trait, message, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (gift_id, req.from_code, req.to_code, req.trait, req.message, expires_at))
    db.commit()
    db.close()
    return {"success": True, "gift_id": gift_id}

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
    token_row = db.execute(
        'SELECT push_token FROM push_tokens WHERE my_code = ?',
        (req.to_code,)
    ).fetchone()
    db.close()
    if token_row:
        await send_push_notification(
            push_token=token_row['push_token'],
            title='🎁 Nouveau trait reçu !',
            body='Quelqu\'un pense que tu as une qualité particulière...',
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
    return {"gifts": [dict(g) for g in gifts]}

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
    return {"gifts": [dict(g) for g in gifts]}

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
    gift = db.execute('SELECT * FROM gifts WHERE id = ?', (req.gift_id,)).fetchone()
    db.close()
    return {"success": True, "gift": dict(gift)}

@app.post("/gift/register-alias")
async def register_alias(req: RegisterAliasRequest):
    db = get_db()
    db.execute('''
        INSERT OR REPLACE INTO gifts (id, from_code, to_code, trait, status)
        VALUES (?, ?, ?, 'CONNECTION', 'connection')
    ''', (f"CONN_{req.my_code}_{req.their_code}", req.my_code, req.their_code, 'CONNECTION'))
    db.commit()
    db.close()
    return {"success": True}

@app.get("/gift/check-code/{code}")
async def check_code(code: str):
    db = get_db()
    exists = db.execute(
        'SELECT COUNT(*) as count FROM gifts WHERE from_code = ? OR to_code = ?',
        (code, code)
    ).fetchone()
    db.close()
    return {"exists": exists['count'] > 0}

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
    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
    db.execute('''
        INSERT INTO comparisons (id, from_code, to_code, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (comparison_id, req.from_code, req.to_code, expires_at))
    db.commit()
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
        'SELECT * FROM comparisons WHERE id = ?', (req.comparison_id,)
    ).fetchone()
    if not comparison:
        db.close()
        raise HTTPException(status_code=404, detail="Comparaison non trouvée")
    if comparison['expires_at'] < datetime.now().isoformat():
        db.close()
        return {"success": False, "error": "La demande a expiré"}
    if not req.accepted:
        db.execute('UPDATE comparisons SET status = ? WHERE id = ?', ('rejected', req.comparison_id))
        db.commit()
        db.close()
        return {"success": True, "status": "rejected"}
    is_from = comparison['from_code'] == req.my_code
    if is_from:
        db.execute('''
            UPDATE comparisons SET from_accepted = 1, from_vector = ? WHERE id = ?
        ''', (json.dumps(req.my_vector), req.comparison_id))
    else:
        db.execute('''
            UPDATE comparisons SET to_accepted = 1, to_vector = ? WHERE id = ?
        ''', (json.dumps(req.my_vector), req.comparison_id))
    db.commit()
    updated = db.execute('SELECT * FROM comparisons WHERE id = ?', (req.comparison_id,)).fetchone()
    if updated['from_accepted'] and updated['to_accepted']:
        db.execute('UPDATE comparisons SET status = ? WHERE id = ?', ('analyzing', req.comparison_id))
        db.commit()
        db.close()
        asyncio.create_task(analyze_comparison(req.comparison_id))
        return {"success": True, "status": "analyzing"}
    db.close()
    return {"success": True, "status": "waiting"}

@app.get("/compare/status/{comparison_id}")
async def get_comparison_status(comparison_id: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    comparison = db.execute('SELECT * FROM comparisons WHERE id = ?', (comparison_id,)).fetchone()
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
        WHERE to_code = ? AND status = 'pending'
        AND to_accepted = 0 AND expires_at > datetime('now')
        ORDER BY created_at DESC
    ''', (my_code,)).fetchall()
    db.close()
    return {"comparisons": [dict(c) for c in comparisons]}

async def analyze_comparison(comparison_id: str):
    db = get_db()
    comparison = db.execute('SELECT * FROM comparisons WHERE id = ?', (comparison_id,)).fetchone()
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
    json_match = re.search(r'\{[\s\S]*\}', result_text)
    if json_match:
        result = json_match.group(0)
        db.execute(
            'UPDATE comparisons SET status = ?, result = ? WHERE id = ?',
            ('completed', result, comparison_id)
        )
        db.commit()
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
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                json={
                    'to': push_token, 'title': title, 'body': body,
                    'data': data, 'sound': 'default', 'badge': 1,
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
        if not token:
            raise HTTPException(status_code=500, detail="Token France Travail non disponible")
        params = f"range=0-{req.results_per_page - 1}"
        if req.keywords: params += f"&motsCles={req.keywords}"
        if req.location:
            dept = get_dept_code(req.location)
            if dept: params += f"&departement={dept}"
        if req.contract_type: params += f"&typeContrat={req.contract_type}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FT_API_URL}?{params}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                timeout=15.0,
            )
        if response.status_code == 204: return {"results": []}
        if response.status_code not in [200, 206]: return {"results": []}
        data = response.json()
        if "resultats" not in data: return {"results": []}
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/media/details")
async def get_media_details(req: TMDBRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        search_url = f"{TMDB_BASE_URL}/search/{req.media_type}"
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                search_url,
                params={"api_key": TMDB_API_KEY, "query": req.title, "language": "fr-FR"},
                timeout=10.0,
            )
            search_data = search_response.json()
        if not search_data.get("results"):
            return {"result": None}
        item = search_data["results"][0]
        item_id = item["id"]
        async with httpx.AsyncClient() as client:
            detail_response = await client.get(
                f"{TMDB_BASE_URL}/{req.media_type}/{item_id}",
                params={
                    "api_key": TMDB_API_KEY,
                    "language": "fr-FR",
                    "append_to_response": "videos,credits,watch/providers",
                },
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
        }}
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
        query = req.artist
        if req.album: query += f" {req.album}"
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                f"{SPOTIFY_API_URL}/search",
                headers=headers,
                params={"q": query, "type": "artist,album", "market": "FR", "limit": 1},
                timeout=10.0,
            )
            search_data = search_response.json()
        artists = search_data.get("artists", {}).get("items", [])
        albums = search_data.get("albums", {}).get("items", [])
        artist = artists[0] if artists else None
        album = albums[0] if albums else None
        if not artist and not album:
            return {"result": None}
        image_url = None
        if album and album.get("images"): image_url = album["images"][0]["url"]
        elif artist and artist.get("images"): image_url = artist["images"][0]["url"]
        top_tracks = []
        if artist:
            async with httpx.AsyncClient() as client:
                tracks_response = await client.get(
                    f"{SPOTIFY_API_URL}/artists/{artist['id']}/top-tracks",
                    headers=headers,
                    params={"market": "FR"},
                    timeout=10.0,
                )
                for track in tracks_response.json().get("tracks", [])[:5]:
                    top_tracks.append({
                        "name": track["name"],
                        "preview_url": track.get("preview_url"),
                        "duration_ms": track.get("duration_ms"),
                        "spotify_url": track["external_urls"].get("spotify"),
                    })
        return {"result": {
            "image_url": image_url,
            "genres": artist.get("genres", [])[:4] if artist else [],
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
            if not search_data.get("results"):
                return {"result": None}
            place = search_data["results"][0]
            place_id = place.get("place_id")
            detail_response = await client.get(
                f"{GOOGLE_PLACES_URL}/details/json",
                params={
                    "place_id": place_id, "key": GOOGLE_PLACES_API_KEY, "language": "fr",
                    "fields": "name,rating,user_ratings_total,formatted_address,opening_hours,price_level,photos,website,url,formatted_phone_number,types",
                },
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
        price_str = ('💰' * (price_level + 1) if price_level > 0 else 'Gratuit') if price_level is not None else None
        opening_hours = detail.get("opening_hours", {})
        types = detail.get("types", place.get("types", []))
        cuisine_types = [t.replace('_', ' ').title() for t in types
                        if t not in ['restaurant', 'food', 'point_of_interest', 'establishment', 'store']][:3]
        return {"result": {
            "photo_url": photo_url,
            "name": detail.get("name") or place.get("name"),
            "rating": detail.get("rating") or place.get("rating"),
            "user_ratings_total": detail.get("user_ratings_total") or place.get("user_ratings_total"),
            "address": detail.get("formatted_address") or place.get("formatted_address"),
            "price_level": price_str,
            "is_open": opening_hours.get("open_now"),
            "weekday_text": opening_hours.get("weekday_text", [])[:3],
            "phone": detail.get("formatted_phone_number"),
            "website": detail.get("website"),
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
                params={
                    "apiKey": SPOONACULAR_API_KEY, "query": req.title,
                    "language": "fr", "number": 1,
                    "addRecipeInformation": True, "fillIngredients": True,
                },
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
        if not search_data.get("results"):
            return {"result": None}
        recipe = search_data["results"][0]
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
        steps_raw = [step.get("step", "") for instruction in detail.get("analyzedInstructions", [])
                    for step in instruction.get("steps", [])]
        cuisines = detail.get("cuisines", [])
        diets = detail.get("diets", [])
        ready_in = detail.get("readyInMinutes")
        servings = detail.get("servings")
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
            try:
                translation = json.loads(json_match.group(0))
            except:
                pass
        return {"result": {
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
            "tags": diets[:3] if diets else [],
        }}
    except Exception as e:
        print(f"❌ ERREUR Spoonacular: {str(e)}")
        return {"result": None}

@app.post("/news/articles")
async def get_news(req: NewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        print(f"🔍 News request: category={req.category}, keywords={req.keywords}")

        # ── Auto-embed si > 1h depuis le dernier embed ──
        now = datetime.now(timezone.utc)
        last = last_embed_time.get(req.category)
        if not last or (now - last).total_seconds() > 3600:
            print(f"🔄 Auto-embed déclenché pour '{req.category}'")
            asyncio.create_task(_embed_news_logic([req.category], hours_back=2))
            last_embed_time[req.category] = now  # évite les doublons


        all_articles = []

        # ── 1. RSS depuis Supabase ──
        rss_sources = await get_feeds_from_supabase(category=req.category, limit=15)
        unique_feeds = deduplicate_feeds(rss_sources)
        print(f"📡 {len(unique_feeds)} flux uniques à fetcher")

        rss_results = await asyncio.gather(*[
            fetch_rss_source(name, url, max_items=4)
            for name, url in unique_feeds
        ], return_exceptions=True)
        for result in rss_results:
            if isinstance(result, list):
                all_articles.extend(result)
        print(f"📰 RSS articles: {len(all_articles)}")

        # ── 2. NewsAPI ──
        try:
            keywords = req.keywords or CATEGORY_KEYWORDS.get(req.category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NEWS_API_URL}/everything",
                    params={"apiKey": NEWS_API_KEY, "q": keywords, "language": "fr",
                            "sortBy": "publishedAt", "pageSize": 10},
                    timeout=15.0,
                )
            for article in response.json().get("articles", []):
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
            print(f"📰 NewsAPI articles: {len(all_articles)}")
        except Exception as e:
            print(f"⚠️ NewsAPI error: {str(e)}")

        # ── 3. Dédupliquer + trier + retourner ──
        unique = deduplicate_articles(all_articles)
        final = [a for a in sort_by_date(unique) if a.get('title') and a.get('url')][:req.page_size]
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
        all_articles = []

        # ── 1. RSS depuis Supabase ──
        rss_sources = await get_feeds_from_supabase(
            category=req.category, limit=20,
            interests=req.interests, locations=req.locations, langues=req.langues,
        )
        unique_feeds = deduplicate_feeds(rss_sources)
        print(f"📡 {len(unique_feeds)} flux uniques à fetcher")

        rss_results = await asyncio.gather(*[
            fetch_rss_source(name, url, max_items=4)
            for name, url in unique_feeds
        ], return_exceptions=True)
        for result in rss_results:
            if isinstance(result, list):
                all_articles.extend(result)

        # ── 2. NewsAPI ──
        try:
            keywords = CATEGORY_KEYWORDS.get(req.category, 'actualité')
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NEWS_API_URL}/everything",
                    params={"apiKey": NEWS_API_KEY, "q": keywords, "language": "fr",
                            "sortBy": "publishedAt", "pageSize": 10},
                    timeout=15.0,
                )
            for article in response.json().get("articles", []):
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

        # ── 3. Dédupliquer ──
        unique = deduplicate_articles(all_articles)
        if not unique:
            return {"articles": []}

        # ── 4. Préparer résumé pour Claude ──
        articles_summary = "\n".join([
            f"{i+1}. [{a.get('source', '?')}] {a.get('title', '')} — {(a.get('description', '') or '')[:100]}"
            for i, a in enumerate(unique[:55])
        ])

        # ── 5. Construire profil ──
        traits_str = ', '.join(req.profile_traits) if req.profile_traits else 'curieux, ouvert'
        context_lines = []
        if req.context.get('metier'): context_lines.append(f"Métier: {req.context['metier']}")
        if req.context.get('ville'): context_lines.append(f"Ville: {req.context['ville']}")
        if req.context.get('passions'): context_lines.append(f"Passions: {', '.join(req.context.get('passions', []))}")
        if req.context.get('valeurs'): context_lines.append(f"Valeurs: {', '.join(req.context.get('valeurs', []))}")
        context_str = '\n'.join(context_lines)

        # ── 6. Feedback ──
        liked = req.feedback.get('liked', [])
        disliked = req.feedback.get('disliked', [])
        feedback_str = f"""
HISTORIQUE DES PRÉFÉRENCES :
- Appréciés (4-5⭐) : {', '.join(liked[:5]) if liked else 'aucun'}
- Non appréciés (1-2⭐) : {', '.join(disliked[:5]) if disliked else 'aucun'}
""" if liked or disliked else ''

        # ── 7. Claude sélectionne ──
        prompt = f"""Tu es un assistant de curation d'actualités personnalisées.
PROFIL :
- Traits : {traits_str}
- Personnalité : extraversion {req.personality.get('extraversion', 0.5)}, ouverture {req.personality.get('openness', 0.5)}, curiosité {req.personality.get('curiosity', 0.5)}
{context_str}
{feedback_str}
ARTICLES DISPONIBLES :
{articles_summary}
Sélectionne les 10 articles les plus pertinents et explique pourquoi en 1 phrase.
Retourne UNIQUEMENT ce JSON valide :
{{
  "selected": [
    {{"index": 1, "why": "Explication courte"}}
  ]
}}"""

        async with httpx.AsyncClient() as client:
            claude_response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 600,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=20.0,
            )
            claude_text = claude_response.json()['content'][0]['text']

        # ── 8. Parser ──
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
    

@app.post("/news/flagship")
async def get_flagship_news(req: NewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        print(f"🏆 Flagship news request")

        # Fetcher tous les flagship feeds en parallèle
        flagship = FLAGSHIP_FEEDS.get('general', [])
        rss_tasks = [
            fetch_rss_source(name, url, max_items=5)
            for name, url in flagship
        ]
        rss_results = await asyncio.gather(*rss_tasks, return_exceptions=True)

        all_articles = []
        for result in rss_results:
            if isinstance(result, list):
                all_articles.extend(result)

        # Dédupliquer par titre
        unique = deduplicate_articles(all_articles)

        # Trier : avec image en premier, sans image à la fin
        with_image = [a for a in unique if a.get('image_url')]
        without_image = [a for a in unique if not a.get('image_url')]

        # Trier chaque groupe par date
        with_image = sort_by_date(with_image)
        without_image = sort_by_date(without_image)

        final = with_image + without_image

        print(f"✅ Flagship: {len(with_image)} avec image, {len(without_image)} sans image")
        return {"articles": final}

    except Exception as e:
        print(f"❌ ERREUR flagship news: {str(e)}")
        return {"articles": []}
    


#VECTORISARTION

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Vectorise une liste de textes avec Mistral Embed"""
    if not texts:
        return []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MISTRAL_EMBED_URL,
                headers={
                    "Authorization": f"Bearer {MISTRAL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MISTRAL_EMBED_MODEL,
                    "input": texts,
                    "encoding_format": "float",
                },
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

async def embed_single(text: str) -> list[float]:
    """Vectorise un seul texte"""
    results = await embed_texts([text])
    return results[0] if results else []

async def upsert_article(article: dict, embedding: list[float], category: str):
    """Insère ou met à jour un article dans Supabase avec son vecteur"""
    if not embedding or not article.get("url"):
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SUPABASE_URL}/rest/v1/news_articles",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
                json={
                    "title": article.get("title", "")[:500],
                    "description": article.get("description", "")[:1000],
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "image_url": article.get("image_url"),
                    "category": category,
                    "published_at": article.get("published_at"),
                    "embedding": embedding,
                },
                timeout=10.0,
            )
    except Exception as e:
        print(f"⚠️ Erreur upsert_article: {str(e)[:100]}")




async def _embed_news_logic(categories: list, hours_back: int = 2):
    """Logique d'embedding — appelable sans vérification du secret"""
    total_embedded = 0
    total_skipped = 0

    for category in categories:
        print(f"🔄 Auto-embed: {category}")
        all_articles = []

        # ── Flagship feeds — tous les articles du jour ──
        flagship = FLAGSHIP_FEEDS.get(category, FLAGSHIP_FEEDS.get('general', []))
        flagship_sources = deduplicate_feeds(flagship)

        print(f"📡 Flagship feeds pour '{category}' ({len(flagship_sources)}):")
        for name, url in flagship_sources:
            print(f"   🏆 → {name}")

        flagship_results = await asyncio.gather(*[
            fetch_rss_source(name, url, max_items=20)
            for name, url in flagship_sources
        ], return_exceptions=True)
        for result in flagship_results:
            if isinstance(result, list):
                all_articles.extend(result)

        print(f"   🏆 Flagship: {len(all_articles)} articles")

        # ── Supabase feeds — uniquement si catégorie couverte ──
        if category not in CATEGORIES_WITHOUT_SUPABASE:
            try:
                supabase_feeds = await get_feeds_from_supabase(
                    category=category, limit=10, langues=[]
                )
                supabase_sources = deduplicate_feeds(supabase_feeds)

                print(f"📡 Supabase feeds pour '{category}' ({len(supabase_sources)}):")
                for name, url in supabase_sources[:20]:
                    print(f"   📂 → {name}")

                supabase_results = await asyncio.gather(*[
                    fetch_rss_source(name, url, max_items=5)
                    for name, url in supabase_sources[:20]
                ], return_exceptions=True)
                for result in supabase_results:
                    if isinstance(result, list):
                        all_articles.extend(result)
            except Exception as e:
                print(f"⚠️ Supabase feeds erreur: {str(e)[:50]}")
        else:
            print(f"   ⏭️ Supabase ignoré pour '{category}' — pas de catégorie correspondante")

        # ── NewsAPI ──
        try:
            keywords = CATEGORY_KEYWORDS.get(category, 'actualité')
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
            newsapi_articles = response.json().get("articles", [])
            for article in newsapi_articles:
                if article.get("title") and article.get("title") != "[Removed]":
                    all_articles.append({
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "url": article.get("url"),
                        "image_url": article.get("urlToImage"),
                        "source": article.get("source", {}).get("name"),
                        "published_at": article.get("publishedAt"),
                    })
            print(f"   📰 NewsAPI: {len(newsapi_articles)} articles")
        except Exception as e:
            print(f"⚠️ NewsAPI erreur: {str(e)[:50]}")

        # ── Dédupliquer ──
        unique_articles = deduplicate_articles(all_articles)
        print(f"   📊 Total unique: {len(unique_articles)} articles")

        if not unique_articles:
            continue

        # ── Vérifier articles existants dans Supabase ──
        urls = [a.get("url") for a in unique_articles if a.get("url")]
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/news_articles",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                    },
                    params={
                        "select": "url",
                        "url": f"in.({','.join([chr(34) + u + chr(34) for u in urls[:50]])})",
                    },
                    timeout=10.0,
                )
            existing_urls = {row["url"] for row in r.json()} if isinstance(r.json(), list) else set()
        except:
            existing_urls = set()

        new_articles = [a for a in unique_articles if a.get("url") not in existing_urls]
        total_skipped += len(unique_articles) - len(new_articles)
        print(f"   ✨ {len(new_articles)} nouveaux, {len(unique_articles) - len(new_articles)} déjà en base")

        if not new_articles:
            continue

        # ── Vectoriser — titre + description + source + catégorie ──
        texts = [
            f"[{a.get('source', '')}] [{category}] "
            f"{a.get('title', '')}. "
            f"{a.get('description', '') or ''}".strip()[:1000]
            for a in new_articles
        ]

        all_embeddings = []
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            embeddings = await embed_texts(batch)
            all_embeddings.extend(embeddings)
            print(f"   🔢 Batch {i//32 + 1}: {len(embeddings)} vecteurs")
            await asyncio.sleep(0.3)

        # ── Stocker dans Supabase ──
        stored = 0
        for article, embedding in zip(new_articles, all_embeddings):
            if embedding:
                await upsert_article(article, embedding, category)
                stored += 1

        total_embedded += stored
        print(f"   ✅ {category}: {stored} articles vectorisés et stockés")
        last_embed_time[category] = datetime.now(timezone.utc)

    # ── Nettoyer les vieux articles (> 7 jours) ──
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{SUPABASE_URL}/rest/v1/news_articles",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                params={"published_at": "lt.NOW() - INTERVAL '7 days'"},
                timeout=10.0,
            )
        print(f"🗑️ Vieux articles nettoyés (> 7 jours)")
    except Exception as e:
        print(f"⚠️ Nettoyage erreur: {str(e)[:50]}")

    return total_embedded, total_skipped





@app.post("/news/embed")
async def embed_news(req: EmbedNewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        print(f"🚀 Embed manuel: {len(req.categories)} catégories, hours_back={req.hours_back}")
        total_embedded, total_skipped = await _embed_news_logic(
            req.categories, req.hours_back
        )
        print(f"✅ Embedding terminé : {total_embedded} nouveaux, {total_skipped} ignorés")
        return {
            "success": True,
            "embedded": total_embedded,
            "skipped": total_skipped,
        }
    except Exception as e:
        print(f"❌ ERREUR embed_news: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}



@app.post("/news/semantic")
async def semantic_news(req: SemanticNewsRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        import time
        t0 = time.time()
        print(f"🔍 Semantic news: category={req.category}")

        all_scores = {}

        # ── 1. Vecteur EMA persistant (signal le plus fort) ──
        t_ema = time.time()
        # ── 1. Vecteur EMA local (priorité maximale) ──
        ema_vector = [float(v) for v in req.taste_vector] if req.taste_vector else []
        if ema_vector:
                print(f"   🧠 EMA local reçu ({len(ema_vector)} dims)")
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/search_news_articles",
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "query_embedding": ema_vector,
                            "p_category": req.category if req.category != 'general' else None,
                            "p_limit": 50,
                            "p_hours": req.hours_back,
                        },
                        timeout=10.0,
                    )
                results = r.json()
                print(f"   🎯 EMA (×0.50): {len(results) if isinstance(results, list) else 'ERR'} résultats")
                if isinstance(results, list):
                    for article in results:
                        url = article.get("url")
                        if url:
                            if url not in all_scores:
                                all_scores[url] = {"article": article, "score": 0}
                            all_scores[url]["score"] += article.get("similarity", 0) * 0.50

        # ── 2. Centroïde des articles aimés ──
        t_centroid = time.time()
        centroid_vector = []
        if req.liked_urls:
            centroid_vector = await get_taste_vector(req.liked_urls)
            if centroid_vector:
                print(f"   🎯 Centroïde calculé ({time.time()-t_centroid:.2f}s)")
                weight = 0.30 if ema_vector else 0.50
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/search_news_articles",
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "query_embedding": centroid_vector,
                            "p_category": req.category if req.category != 'general' else None,
                            "p_limit": 50,
                            "p_hours": req.hours_back,
                        },
                        timeout=10.0,
                    )
                results = r.json()
                print(f"   🎯 Centroïde (×{weight}): {len(results) if isinstance(results, list) else 'ERR'} résultats")
                if isinstance(results, list):
                    for article in results:
                        url = article.get("url")
                        if url:
                            if url not in all_scores:
                                all_scores[url] = {"article": article, "score": 0}
                            all_scores[url]["score"] += article.get("similarity", 0) * weight

        # ── 3. Construire textes pour dimensions restantes ──
        texts = {}
        if req.interests:
            texts["interests"] = ", ".join(req.interests)
        profile_parts = []
        if req.profile_traits:
            profile_parts.append(f"Traits : {', '.join(req.profile_traits)}")
        if req.context.get('metier'):
            profile_parts.append(f"Métier : {req.context['metier']}")
        if req.context.get('passions'):
            profile_parts.append(f"Passions : {', '.join(req.context.get('passions', []))}")
        if req.context.get('valeurs'):
            profile_parts.append(f"Valeurs : {', '.join(req.context.get('valeurs', []))}")
        if profile_parts:
            texts["profile"] = " | ".join(profile_parts)
        if not texts and not ema_vector and not centroid_vector:
            texts["category"] = CATEGORY_KEYWORDS.get(req.category, 'actualité france')

        # Poids adaptés selon disponibilité EMA/centroïde
        WEIGHTS = {
            "interests": 0.25 if (ema_vector or centroid_vector) else 0.40,
            "profile":   0.15 if (ema_vector or centroid_vector) else 0.25,
            "category":  0.05 if (ema_vector or centroid_vector) else 0.10,
        }

        print(f"   📝 Dimensions texte: {list(texts.keys())} — {time.time()-t0:.2f}s")

        # ── 4. Vectoriser + rechercher les dimensions texte ──
        if texts:
            text_list = list(texts.values())
            keys_list = list(texts.keys())

            t_embed = time.time()
            embeddings = await embed_texts(text_list)
            print(f"   🔢 Embedding Mistral: {time.time()-t_embed:.2f}s ({len(text_list)} textes)")

            t_search = time.time()
            for key, embedding in zip(keys_list, embeddings):
                weight = WEIGHTS.get(key, 0.1)
                t_key = time.time()
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/search_news_articles",
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "query_embedding": embedding,
                            "p_category": req.category if req.category != 'general' else None,
                            "p_limit": 50,
                            "p_hours": req.hours_back,
                        },
                        timeout=10.0,
                    )
                results = r.json()
                print(f"   🎯 {key} (×{weight}): {len(results) if isinstance(results, list) else 'ERR'} résultats — {time.time()-t_key:.2f}s")
                if not isinstance(results, list):
                    continue
                for article in results:
                    url = article.get("url")
                    if not url:
                        continue
                    if url not in all_scores:
                        all_scores[url] = {"article": article, "score": 0}
                    all_scores[url]["score"] += article.get("similarity", 0) * weight

            print(f"   🔍 Total recherches pgvector: {time.time()-t_search:.2f}s")

        if not all_scores:
            return {"articles": []}

        # ── 5. Filtrer les articles non aimés ──
        disliked_lower = [t.lower() for t in req.disliked_titles]
        filtered = {
            url: data for url, data in all_scores.items()
            if not any(d in data["article"].get("title", "").lower()
                      for d in disliked_lower)
        }

        # ── 6. Trier par score final + fraîcheur ──
        max_score = max((d["score"] for d in filtered.values()), default=1)
        min_score = min((d["score"] for d in filtered.values()), default=0)
        score_range = max_score - min_score or 1
        now = datetime.now(timezone.utc)

        for url, data in filtered.items():
            normalized_score = (data["score"] - min_score) / score_range
            try:
                pub_str = str(data["article"].get("published_at", ""))
                pub_date = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                age_hours = (now - pub_date).total_seconds() / 3600
                time_score = max(0, 1 - (age_hours / 48))
            except:
                time_score = 0
            data["final_score"] = normalized_score * 0.60 + time_score * 0.40

        sorted_articles = sorted(
            filtered.values(),
            key=lambda x: x["final_score"],
            reverse=True
        )[:req.limit]

        # ── 7. Formater le résultat ──
        final = []
        for item in sorted_articles:
            a = item["article"]
            final.append({
                "title": a.get("title"),
                "description": a.get("description"),
                "url": a.get("url"),
                "source": a.get("source"),
                "image_url": a.get("image_url"),
                "published_at": str(a.get("published_at", "")),
                "category": a.get("category"),
                "score": round(item["final_score"], 4),
            })

        print(f"✅ Semantic: {len(final)} articles — TOTAL: {time.time()-t0:.2f}s")
        return {"articles": final}

    except Exception as e:
        print(f"❌ ERREUR semantic_news: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"articles": []}



async def get_taste_vector(liked_urls: list) -> list:
    if not liked_urls:
        return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/news_articles",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                params={
                    "select": "embedding",
                    "url": f"in.({','.join([chr(34) + u + chr(34) for u in liked_urls[:20]])})",
                },
                timeout=10.0,
            )
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            return []

        embeddings = []
        for row in rows:
            emb = row.get("embedding")
            if not emb:
                continue
            # ← Convertir string en liste si nécessaire
            if isinstance(emb, str):
                import json
                emb = json.loads(emb)
            embeddings.append([float(v) for v in emb])

        if not embeddings:
            return []

        n = len(embeddings)
        dim = len(embeddings[0])
        centroid = [
            sum(embeddings[i][j] for i in range(n)) / n
            for j in range(dim)
        ]
        print(f"   🎯 Centroïde calculé sur {n} articles aimés")
        return centroid

    except Exception as e:
        print(f"⚠️ Erreur get_taste_vector: {str(e)[:50]}")
        return []

   
@app.post("/news/article_vector")
async def get_article_vector(req: ArticleVectorRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/news_articles",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                params={
                    "select": "embedding",
                    "url": f"eq.{req.url}",
                    "limit": "1",
                },
                timeout=5.0,
            )
        rows = r.json()
        if isinstance(rows, list) and rows and rows[0].get("embedding"):
            embedding = rows[0]["embedding"]
            # Convertir en liste de floats si c'est une string
            if isinstance(embedding, str):
                import json
                embedding = json.loads(embedding)
            embedding = [float(v) for v in embedding]
            return {"embedding": embedding}
        return {"embedding": None}
    except Exception as e:
        print(f"⚠️ Erreur article_vector: {str(e)[:50]}")
        return {"embedding": None}
    


# ── CONNEXIONS ──────────────────────────────────────────────
@app.post("/connection/request")
async def connection_request(request: Request):
    body = await request.json()
    from_code  = body.get("from_code", "").strip().upper()
    to_code    = body.get("to_code", "").strip().upper()
    from_alias = body.get("from_alias", "Inconnu")  # prénom de A
    to_alias   = body.get("to_alias", "Inconnu")    # surnom que A donne à B

    if not from_code or not to_code:
        return {"success": False, "error": "Codes manquants"}
    if from_code == to_code:
        return {"success": False, "error": "Tu ne peux pas te connecter à toi-même"}

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            # Vérifier si demande pending existe déjà
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={
                    "from_code": f"eq.{from_code}",
                    "to_code":   f"eq.{to_code}",
                    "status":    "eq.pending",
                    "select":    "id",
                },
                timeout=10.0,
            )
            if r.json():
                return {"success": False, "error": "Demande déjà en attente"}

            # Vérifier si déjà acceptée
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={
                    "from_code": f"eq.{from_code}",
                    "to_code":   f"eq.{to_code}",
                    "status":    "eq.accepted",
                    "select":    "id",
                },
                timeout=10.0,
            )
            if r.json():
                return {"success": False, "error": "Connexion déjà établie"}

            # Créer la demande
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers={**headers, "Prefer": "return=representation"},
                json={
                    "from_code":  from_code,
                    "to_code":    to_code,
                    "from_alias": from_alias,  # prénom de A → "Denis"
                    "to_alias":   to_alias,    # surnom de A pour B → "Paulo"
                    "status":     "pending",
                },
                timeout=10.0,
            )
            data = r.json()
            request_id = data[0]["id"] if data else None
            return {"success": True, "request_id": request_id}

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/connection/pending/{code}")
async def connection_pending(code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    code = code.strip().upper()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={
                    "to_code": f"eq.{code}",
                    "status":  "eq.pending",
                    "select":  "*",
                    "order":   "created_at.desc",
                },
                timeout=10.0,
            )
        return {"requests": r.json() or []}
    except Exception as e:
        return {"requests": [], "error": str(e)}


@app.post("/connection/respond")
async def connection_respond(request: Request, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    body       = await request.json()
    request_id = body.get("request_id")
    accepted   = body.get("accepted", False)
    my_code    = body.get("my_code", "").strip().upper()
    my_alias   = body.get("my_alias", "Inconnu")  # prénom de B

    if not request_id:
        return {"success": False, "error": "request_id manquant"}

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={
                    "id":      f"eq.{request_id}",
                    "to_code": f"eq.{my_code}",
                    "status":  "eq.pending",
                    "select":  "*",
                },
                timeout=10.0,
            )
            data = r.json()
            if not data:
                return {"success": False, "error": "Demande introuvable"}

            req_data   = data[0]
            new_status = "accepted" if accepted else "rejected"

            await client.patch(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={"id": f"eq.{request_id}"},
                json={"status": new_status, "updated_at": "now()"},
                timeout=10.0,
            )

            if accepted:
                # Miroir B → A
                # from_alias = prénom de B "Paul"
                # to_alias   = surnom que B donne à A = on utilise from_alias de la demande "Denis"
                r_mirror = await client.get(
                    f"{SUPABASE_URL}/rest/v1/connection_requests",
                    headers=headers,
                    params={
                        "from_code": f"eq.{my_code}",
                        "to_code":   f"eq.{req_data['from_code']}",
                        "status":    "eq.accepted",
                        "select":    "id",
                    },
                    timeout=10.0,
                )
                if not r_mirror.json():
                    await client.post(
                        f"{SUPABASE_URL}/rest/v1/connection_requests",
                        headers={**headers, "Prefer": "return=representation"},
                        json={
                            "from_code":  my_code,
                            "to_code":    req_data["from_code"],
                            "from_alias": my_alias,              # prénom de B → "Paul"
                            "to_alias":   req_data["from_alias"], # prénom de A → "Denis"
                            "status":     "accepted",
                        },
                        timeout=10.0,
                    )
                    print(f"🔗 Miroir créé: {my_code} → {req_data['from_code']}")

                # Push notif à A
                db = get_db()
                token_row = db.execute(
                    'SELECT push_token FROM push_tokens WHERE my_code = ?',
                    (req_data["from_code"],)
                ).fetchone()
                db.close()
                if token_row:
                    await send_push_notification(
                        push_token=token_row['push_token'],
                        title='🔗 Connexion acceptée !',
                        body=f'{my_alias} a accepté ta demande de connexion.',
                        data={'screen': 'Social'}
                    )

        return {
            "success":    True,
            "status":     new_status,
            "from_code":  req_data["from_code"],
            "from_alias": req_data["from_alias"],  # prénom de A → pour que B l'affiche
            "to_alias":   req_data["to_alias"],    # surnom de A pour B → pas utilisé ici
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/connection/accepted/{code}")
async def connection_accepted(code: str, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    code = code.strip().upper()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        async with httpx.AsyncClient() as client:
            # Lignes où je suis from_code → to_alias = surnom que j'ai donné
            r_sent = await client.get(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={
                    "from_code": f"eq.{code}",
                    "status":    "eq.accepted",
                    "select":    "to_code,to_alias",
                },
                timeout=10.0,
            )
            # Lignes où je suis to_code → from_alias = prénom de l'autre
            r_received = await client.get(
                f"{SUPABASE_URL}/rest/v1/connection_requests",
                headers=headers,
                params={
                    "to_code": f"eq.{code}",
                    "status":  "eq.accepted",
                    "select":  "from_code,from_alias",
                },
                timeout=10.0,
            )

        # Construire un dict pour dédupliquer par their_code
        # Priorité aux lignes sent (to_alias = surnom personnalisé)
        connections_map = {}

        # D'abord les received (priorité basse)
        for c in (r_received.json() or []):
            their_code = c["from_code"]
            connections_map[their_code] = {
                "their_code":  their_code,
                "their_alias": c["from_alias"] or their_code,
            }

        # Ensuite les sent (priorité haute — écrase received)
        # car to_alias = surnom personnalisé choisi par l'utilisateur
        for c in (r_sent.json() or []):
            their_code = c["to_code"]
            connections_map[their_code] = {
                "their_code":  their_code,
                "their_alias": c["to_alias"] or their_code,
            }

        return {"connections": list(connections_map.values())}

    except Exception as e:
        return {"connections": [], "error": str(e)}



 # ──TEMPORAIRE POUR VIDER LA BASE
 #  ──curl -X DELETE https://monjumeau-api.onrender.com/admin/reset-social \ -H "x-app-secret: TON_APP_SECRET"
@app.delete("/admin/reset-social")
async def reset_social(x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)
    db = get_db()
    db.execute("DELETE FROM gifts;")
    db.execute("DELETE FROM comparisons;")
    db.execute("DELETE FROM push_tokens;")
    db.commit()
    db.close()
    return {"success": True, "message": "Reset social OK"}