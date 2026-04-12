from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import sqlite3
from datetime import datetime, timedelta
import uuid
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

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



# ── ENDPOINTS CLAUDE ──
@app.post("/recommend")
async def recommend(req: MessageRequest):
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
async def send_gift(req: SendGiftRequest):
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
async def get_received(my_code: str):
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
async def get_sent(my_code: str):
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
async def respond_gift(req: RespondGiftRequest):
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
async def register_push(req: RegisterPushRequest):
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
async def request_comparison(req: CompareRequestModel):
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
    expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
    
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
async def respond_comparison(req: CompareRespondModel):
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
async def get_comparison_status(comparison_id: str):
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
async def get_pending_comparisons(my_code: str):
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