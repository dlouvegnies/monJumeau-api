# ============================================================
# ZEOPY — endpoint /research
# À coller dans main.py avec les autres routes
# ============================================================

class ResearchInsightInput(BaseModel):
    label_fr: str
    insight:  str
    source:   str

class ResearchRequest(BaseModel):
    insights: List[ResearchInsightInput]

@app.post("/research")
async def generate_research(req: ResearchRequest, x_app_secret: str = Header(None)):
    verify_secret(x_app_secret)

    if not req.insights:
        raise HTTPException(status_code=400, detail="Aucun insight fourni")

    # ── Construction du bloc insights ──
    insights_block = "\n\n".join([
        f"• {i.label_fr}\n  {i.insight}\n  ({i.source})"
        for i in req.insights
    ])

    prompt = f"""Tu es un coach professionnel qui s'appuie sur la recherche scientifique pour aider les gens à mieux se comprendre.

Voici une sélection d'insights issus de la littérature scientifique, choisis parce qu'ils correspondent aux traits dominants de cette personne :

{insights_block}

Rédige une synthèse personnalisée de 2 paragraphes (100 à 150 mots) qui :
- S'adresse directement à la personne (vous)
- Transforme ces insights en quelque chose de concret et actionnable pour elle
- Ne cite pas les sources de façon académique — intègre-les naturellement
- Commence par "Ce que la recherche dit des personnes qui vous ressemblent…"
- Termine par une phrase qui ouvre une perspective, pas un conseil prescriptif
- Ton : coach professionnel, bienveillant, factuel — jamais condescendant

Ne reproduis pas les insights mot pour mot. Synthétise, relie, donne du sens."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30.0,
        )

    data      = response.json()
    synthesis = data['content'][0]['text'].strip()

    return {
        "success":   True,
        "synthesis": synthesis,
    }
