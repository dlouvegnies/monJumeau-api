from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import sqlite3
from datetime import datetime, timedelta
import uuid

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