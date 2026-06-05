RC_WEBAPP_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Regard Croisé — monJumeau</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #F8F7FF;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .container {
    width: 100%;
    max-width: 480px;
    padding: 24px 20px 48px;
  }
  /* Header */
  .header {
    text-align: center;
    margin-bottom: 32px;
  }
  .logo {
    font-size: 28px;
    font-weight: 800;
    color: #1A1523;
    letter-spacing: -1px;
    margin-bottom: 4px;
  }
  .logo span { color: #534AB7; font-style: italic; font-weight: 400; }
  .subtitle {
    font-size: 14px;
    color: #71717A;
    margin-bottom: 24px;
  }
  /* Progress */
  .progress-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 28px;
  }
  .progress-bar {
    flex: 1;
    height: 4px;
    background: #E4E4E7;
    border-radius: 2px;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: #534AB7;
    border-radius: 2px;
    transition: width 0.3s ease;
  }
  .progress-text {
    font-size: 13px;
    color: #71717A;
    white-space: nowrap;
  }
  /* Question card */
  .question-card {
    background: white;
    border-radius: 16px;
    padding: 24px;
    border: 0.5px solid #E4E4E7;
    margin-bottom: 16px;
  }
  .question-number {
    font-size: 11px;
    font-weight: 600;
    color: #534AB7;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 12px;
  }
  .question-text {
    font-size: 18px;
    font-weight: 600;
    color: #1A1523;
    line-height: 1.4;
    margin-bottom: 20px;
  }
  /* Answers */
  .answers {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .answer-btn {
    width: 100%;
    padding: 14px 16px;
    border-radius: 10px;
    border: 1.5px solid #E4E4E7;
    background: white;
    text-align: left;
    font-size: 15px;
    color: #3F3F46;
    cursor: pointer;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .answer-btn:hover {
    border-color: #AFA9EC;
    background: #EEEDFE;
    color: #534AB7;
  }
  .answer-btn.selected {
    border-color: #534AB7;
    background: #EEEDFE;
    color: #534AB7;
    font-weight: 600;
  }
  .answer-letter {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: #F4F4F5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: #71717A;
    flex-shrink: 0;
    transition: all 0.15s;
  }
  .answer-btn.selected .answer-letter {
    background: #534AB7;
    color: white;
  }
  /* Open question */
  .open-input {
    width: 100%;
    padding: 14px 16px;
    border-radius: 10px;
    border: 1.5px solid #E4E4E7;
    font-size: 15px;
    color: #1A1523;
    outline: none;
    font-family: inherit;
    resize: none;
    transition: border-color 0.15s;
  }
  .open-input:focus { border-color: #534AB7; }
  .open-hint {
    font-size: 12px;
    color: #A1A1AA;
    margin-top: 8px;
  }
  /* Navigation */
  .nav {
    display: flex;
    gap: 10px;
    margin-top: 8px;
  }
  .btn-prev {
    padding: 14px 20px;
    border-radius: 10px;
    border: 1.5px solid #E4E4E7;
    background: white;
    font-size: 15px;
    color: #71717A;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .btn-prev:hover { border-color: #D4D4D8; }
  .btn-next {
    flex: 1;
    padding: 14px;
    border-radius: 10px;
    border: none;
    background: #534AB7;
    color: white;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
  }
  .btn-next:hover   { background: #3C3489; }
  .btn-next:disabled { background: #D4D4D8; cursor: not-allowed; }
  /* Relation selector */
  .relation-card {
    background: white;
    border-radius: 16px;
    padding: 24px;
    border: 0.5px solid #E4E4E7;
    margin-bottom: 16px;
  }
  .relation-title {
    font-size: 16px;
    font-weight: 600;
    color: #1A1523;
    margin-bottom: 16px;
  }
  .relation-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 16px;
  }
  .relation-btn {
    padding: 12px;
    border-radius: 10px;
    border: 1.5px solid #E4E4E7;
    background: white;
    font-size: 14px;
    color: #3F3F46;
    cursor: pointer;
    text-align: center;
    font-family: inherit;
    transition: all 0.15s;
  }
  .relation-btn.selected {
    border-color: #534AB7;
    background: #EEEDFE;
    color: #534AB7;
    font-weight: 600;
  }
  .name-input {
    width: 100%;
    padding: 12px 16px;
    border-radius: 10px;
    border: 1.5px solid #E4E4E7;
    font-size: 15px;
    color: #1A1523;
    outline: none;
    font-family: inherit;
    transition: border-color 0.15s;
    margin-bottom: 10px;
  }
  .name-input:focus { border-color: #534AB7; }
  .anon-row {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
  }
  .anon-checkbox {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 1.5px solid #D4D4D8;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  .anon-checkbox.checked {
    background: #534AB7;
    border-color: #534AB7;
  }
  .anon-label {
    font-size: 14px;
    color: #71717A;
  }
  /* Success */
  .success-card {
    background: white;
    border-radius: 16px;
    padding: 40px 24px;
    text-align: center;
    border: 0.5px solid #E4E4E7;
  }
  .success-icon {
    width: 72px;
    height: 72px;
    border-radius: 36px;
    background: #EEEDFE;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    font-size: 32px;
  }
  .success-title {
    font-size: 22px;
    font-weight: 700;
    color: #1A1523;
    margin-bottom: 10px;
  }
  .success-text {
    font-size: 15px;
    color: #71717A;
    line-height: 1.6;
    margin-bottom: 24px;
  }
  .app-cta {
    display: inline-block;
    padding: 14px 28px;
    border-radius: 10px;
    background: #534AB7;
    color: white;
    font-size: 15px;
    font-weight: 600;
    text-decoration: none;
  }
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="logo">mon<span>Jumeau</span></div>
    <div class="subtitle">Regard Croisé</div>
  </div>

  <!-- Étape 0 : Intro + relation -->
  <div id="step-intro">
    <div class="relation-card">
      <div class="relation-title">Avant de commencer</div>
      <p style="font-size:14px;color:#71717A;margin-bottom:16px;line-height:1.5">
        Un proche t'invite à répondre à 15 questions sur lui. Tes réponses resteront anonymes et l'aideront à mieux se connaître.
      </p>
      <div class="relation-title" style="margin-top:16px">Tu es... ?</div>
      <div class="relation-grid">
        <button class="relation-btn" onclick="selectRelation('ami')">Ami(e)</button>
        <button class="relation-btn" onclick="selectRelation('famille')">Famille</button>
        <button class="relation-btn" onclick="selectRelation('collegue')">Collègue</button>
        <button class="relation-btn" onclick="selectRelation('partenaire')">Partenaire</button>
      </div>
      <div class="relation-title" style="margin-top:8px">Ton prénom (optionnel)</div>
      <input class="name-input" id="respondent-name" placeholder="Ex: Paulo" />
      <div class="anon-row" onclick="toggleAnon()">
        <div class="anon-checkbox checked" id="anon-checkbox">✓</div>
        <div class="anon-label" id="anon-label">Rester anonyme</div>
      </div>
    </div>
    <button class="btn-next" id="btn-start" onclick="startQuiz()" disabled>
      Commencer →
    </button>
  </div>

  <!-- Étape 1-14 : Questions -->
  <div id="step-quiz" style="display:none">
    <div class="progress-wrap">
      <div class="progress-bar">
        <div class="progress-fill" id="progress-fill" style="width:0%"></div>
      </div>
      <div class="progress-text" id="progress-text">1 / 15</div>
    </div>
    <div class="question-card">
      <div class="question-number" id="q-number">QUESTION 1</div>
      <div class="question-text" id="q-text"></div>
      <div class="answers" id="q-answers"></div>
    </div>
    <div class="nav">
      <button class="btn-prev" id="btn-prev" onclick="prevQuestion()" style="display:none">←</button>
      <button class="btn-next" id="btn-next" onclick="nextQuestion()" disabled>Suivant →</button>
    </div>
  </div>

  <!-- Succès -->
  <div id="step-success" style="display:none">
    <div class="success-card">
      <div class="success-icon">🪞</div>
      <div class="success-title">Merci !</div>
      <div class="success-text">
        Ton regard a bien été enregistré.<br>
        Il aidera ton proche à mieux se connaître.
      </div>
      <a href="https://apps.apple.com/app/monjumeau" class="app-cta">
        Découvrir monJumeau
      </a>
    </div>
  </div>

</div>

<script>
const SESSION_KEY = '__SESSION_KEY__';
const API_URL     = '__API_URL__';

// ── Questions ──
const QUESTIONS = [
  {
    id: 1,
    text: "Dans un groupe, cette personne est plutôt :",
    answers: [
      { label: "Celle qui anime et lance les idées",      dims: { leadership: 2, sociabilite: 2 } },
      { label: "Celle qui organise et structure",         dims: { organisation: 2, leadership: 1 } },
      { label: "Celle qui met l'ambiance",                dims: { sociabilite: 2, empathie: 1 } },
      { label: "Celle qui écoute et observe",             dims: { empathie: 2, stabilite: 1 } },
    ]
  },
  {
    id: 2,
    text: "Face à un conflit, elle a tendance à :",
    answers: [
      { label: "Confronter directement",                  dims: { audace: 2, leadership: 1 } },
      { label: "Chercher un compromis",                   dims: { cooperation: 2, empathie: 1 } },
      { label: "Prendre du recul et réfléchir",           dims: { stabilite: 2, organisation: 1 } },
      { label: "Éviter et laisser passer",                dims: { stabilite: 1, cooperation: 1 } },
    ]
  },
  {
    id: 3,
    text: "Quand elle rencontre quelqu'un de nouveau :",
    answers: [
      { label: "Elle engage la conversation facilement",  dims: { sociabilite: 2, audace: 1 } },
      { label: "Elle est chaleureuse mais réservée",      dims: { empathie: 2, stabilite: 1 } },
      { label: "Elle observe avant de se lancer",         dims: { stabilite: 2, curiosite: 1 } },
      { label: "Elle met du temps à s'ouvrir",            dims: { stabilite: 2, organisation: 1 } },
    ]
  },
  {
    id: 4,
    text: "Sa plus grande qualité selon toi :",
    answers: [
      { label: "Son énergie et sa détermination",         dims: { audace: 2, leadership: 2 } },
      { label: "Sa fiabilité et sa constance",            dims: { organisation: 2, stabilite: 2 } },
      { label: "Sa créativité et sa curiosité",           dims: { curiosite: 2, audace: 1 } },
      { label: "Son empathie et sa générosité",           dims: { empathie: 2, cooperation: 2 } },
    ]
  },
  {
    id: 5,
    text: "Son principal défaut selon toi :",
    answers: [
      { label: "Impatient(e) et impulsif(ve)",            dims: { audace: 1, stabilite: -1 } },
      { label: "Trop exigeant(e) envers lui/elle-même",  dims: { organisation: 1, stabilite: -1 } },
      { label: "Dispersé(e) et instable",                 dims: { curiosite: 1, organisation: -1 } },
      { label: "Trop accommodant(e)",                     dims: { cooperation: 1, leadership: -1 } },
    ]
  },
  {
    id: 6,
    text: "Face à une décision importante, elle :",
    answers: [
      { label: "Décide vite et assume",                   dims: { audace: 2, leadership: 2 } },
      { label: "Analyse longuement avant d'agir",         dims: { organisation: 2, stabilite: 1 } },
      { label: "Suit son instinct",                       dims: { audace: 2, curiosite: 1 } },
      { label: "Demande l'avis de ses proches",           dims: { cooperation: 2, empathie: 1 } },
    ]
  },
  {
    id: 7,
    text: "Son week-end idéal ressemble à :",
    answers: [
      { label: "Sorties, rencontres, plein de monde",     dims: { sociabilite: 2, audace: 1 } },
      { label: "Un programme bien préparé",               dims: { organisation: 2, stabilite: 1 } },
      { label: "Une aventure improvisée",                 dims: { audace: 2, curiosite: 2 } },
      { label: "Du calme et de la tranquillité",          dims: { stabilite: 2, empathie: 1 } },
    ]
  },
  {
    id: 8,
    text: "Dans un projet, elle est plutôt :",
    answers: [
      { label: "Le moteur — elle lance et impulse",       dims: { leadership: 2, audace: 2 } },
      { label: "Le pilier — elle structure et fiabilise", dims: { organisation: 2, stabilite: 2 } },
      { label: "L'innovatrice — elle apporte des idées",  dims: { curiosite: 2, audace: 1 } },
      { label: "Le liant — elle fédère et harmonise",     dims: { cooperation: 2, empathie: 2 } },
    ]
  },
  {
    id: 9,
    text: "Quand les choses ne se passent pas comme prévu :",
    answers: [
      { label: "Elle s'adapte et rebondit facilement",    dims: { audace: 2, stabilite: 1 } },
      { label: "Elle cherche rapidement un plan B",       dims: { organisation: 2, leadership: 1 } },
      { label: "Elle prend le temps d'analyser",          dims: { stabilite: 2, organisation: 1 } },
      { label: "Elle peut être déstabilisée un moment",   dims: { stabilite: -1, empathie: 1 } },
    ]
  },
  {
    id: 10,
    text: "Dans une amitié, elle est :",
    answers: [
      { label: "Présente et disponible",                  dims: { empathie: 2, cooperation: 2 } },
      { label: "Loyale et fiable",                        dims: { organisation: 1, stabilite: 2 } },
      { label: "Stimulante et inspirante",                dims: { curiosite: 2, leadership: 1 } },
      { label: "Discrète mais profonde",                  dims: { stabilite: 2, empathie: 1 } },
    ]
  },
  {
    id: 11,
    text: "Quand un proche a un problème, elle :",
    answers: [
      { label: "Écoute et soutient émotionnellement",     dims: { empathie: 2, cooperation: 2 } },
      { label: "Cherche des solutions concrètes",         dims: { organisation: 2, leadership: 1 } },
      { label: "Donne son avis directement",              dims: { audace: 2, leadership: 1 } },
      { label: "Accompagne sans imposer",                 dims: { empathie: 2, stabilite: 1 } },
    ]
  },
  {
    id: 12,
    text: "Si tu devais la décrire en un mot, ce serait :",
    answers: [
      { label: "Énergique",                               dims: { audace: 2, sociabilite: 1 } },
      { label: "Fiable",                                  dims: { organisation: 2, stabilite: 2 } },
      { label: "Curieux(se)",                             dims: { curiosite: 2, audace: 1 } },
      { label: "Bienveillant(e)",                         dims: { empathie: 2, cooperation: 2 } },
    ]
  },
  {
    id: 13,
    text: "C'est quelqu'un qui :",
    answers: [
      { label: "Aime relever des défis",                  dims: { audace: 2, leadership: 1 } },
      { label: "Préfère la stabilité et la sécurité",     dims: { stabilite: 2, organisation: 1 } },
      { label: "S'intéresse à tout",                      dims: { curiosite: 2, sociabilite: 1 } },
      { label: "Met les autres avant elle",               dims: { empathie: 2, cooperation: 2 } },
    ]
  },
  {
    id: 14,
    text: "Ce qui la rend unique selon toi :",
    answers: [
      { label: "Sa façon de voir les choses différemment",dims: { curiosite: 2, audace: 1 } },
      { label: "Sa capacité à rassembler les gens",       dims: { sociabilite: 2, leadership: 2 } },
      { label: "Son côté profondément humain",            dims: { empathie: 2, cooperation: 1 } },
      { label: "Sa rigueur et son sérieux",               dims: { organisation: 2, stabilite: 1 } },
    ]
  },
  {
    id: 15,
    type: "open",
    text: "En 3 mots, comment tu la décrirais à quelqu'un qui ne la connaît pas ?",
    placeholder: "Ex: curieux, généreux, fiable",
  },
];

const DIMS = ['sociabilite','organisation','curiosite','audace','empathie','leadership','stabilite','cooperation'];

// ── État ──
let currentIndex  = 0;
let answers       = {};
let relation      = null;
let isAnonymous   = true;
let alreadyAnswered = false;

// ── Anti-doublon ──
const STORAGE_KEY = 'rc_answered_' + SESSION_KEY;
if (localStorage.getItem(STORAGE_KEY)) {
  alreadyAnswered = true;
  document.getElementById('step-intro').style.display = 'none';
  document.getElementById('step-success').style.display = 'block';
}

// ── Relation ──
function selectRelation(rel) {
  relation = rel;
  document.querySelectorAll('.relation-btn').forEach(b => b.classList.remove('selected'));
  event.target.classList.add('selected');
  document.getElementById('btn-start').disabled = false;
}

function toggleAnon() {
  isAnonymous = !isAnonymous;
  const cb = document.getElementById('anon-checkbox');
  cb.classList.toggle('checked', isAnonymous);
  cb.textContent = isAnonymous ? '✓' : '';
  document.getElementById('anon-label').textContent = isAnonymous ? 'Rester anonyme' : 'Indiquer mon prénom';
}

function startQuiz() {
  document.getElementById('step-intro').style.display = 'none';
  document.getElementById('step-quiz').style.display  = 'block';
  renderQuestion();
}

// ── Quiz ──
function renderQuestion() {
  const q      = QUESTIONS[currentIndex];
  const total  = QUESTIONS.length;
  const pct    = Math.round((currentIndex / total) * 100);

  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-text').textContent  = (currentIndex + 1) + ' / ' + total;
  document.getElementById('q-number').textContent       = 'QUESTION ' + (currentIndex + 1);
  document.getElementById('q-text').textContent         = q.text;
  document.getElementById('btn-prev').style.display     = currentIndex > 0 ? 'block' : 'none';

  const answersDiv = document.getElementById('q-answers');
  answersDiv.innerHTML = '';

  if (q.type === 'open') {
    const ta = document.createElement('textarea');
    ta.className   = 'open-input';
    ta.rows        = 2;
    ta.placeholder = q.placeholder;
    ta.value       = answers[q.id] || '';
    ta.oninput = () => {
      answers[q.id] = ta.value;
      document.getElementById('btn-next').disabled = ta.value.trim().length < 2;
    };
    answersDiv.appendChild(ta);
    const hint = document.createElement('div');
    hint.className   = 'open-hint';
    hint.textContent = 'Sépare les mots par des virgules';
    answersDiv.appendChild(hint);
    document.getElementById('btn-next').disabled = !(answers[q.id] && answers[q.id].trim().length >= 2);
    document.getElementById('btn-next').textContent = 'Envoyer mes réponses →';
  } else {
    const letters = ['A','B','C','D'];
    q.answers.forEach((ans, i) => {
      const btn = document.createElement('button');
      btn.className = 'answer-btn' + (answers[q.id] === i ? ' selected' : '');
      btn.innerHTML = `<span class="answer-letter">${letters[i]}</span>${ans.label}`;
      btn.onclick   = () => selectAnswer(i);
      answersDiv.appendChild(btn);
    });
    document.getElementById('btn-next').disabled    = answers[q.id] === undefined;
    document.getElementById('btn-next').textContent = currentIndex < total - 1 ? 'Suivant →' : 'Envoyer mes réponses →';
  }
}

function selectAnswer(index) {
  answers[QUESTIONS[currentIndex].id] = index;
  document.querySelectorAll('.answer-btn').forEach((b, i) => {
    b.classList.toggle('selected', i === index);
  });
  document.getElementById('btn-next').disabled = false;
}

function prevQuestion() {
  if (currentIndex > 0) { currentIndex--; renderQuestion(); }
}

async function nextQuestion() {
  if (currentIndex < QUESTIONS.length - 1) {
    currentIndex++;
    renderQuestion();
  } else {
    await submitAnswers();
  }
}

// ── Calcul vecteur ──
function buildVector() {
  const scores  = Object.fromEntries(DIMS.map(d => [d, 0]));
  const maxScores = Object.fromEntries(DIMS.map(d => [d, 0]));

  QUESTIONS.forEach(q => {
    if (q.type === 'open') return;
    const answerIndex = answers[q.id];
    if (answerIndex === undefined) return;
    const answer = q.answers[answerIndex];
    Object.entries(answer.dims).forEach(([dim, value]) => {
      scores[dim]    += value;
      maxScores[dim] += Math.abs(value);
    });
  });

  const normalized = {};
  DIMS.forEach(dim => {
    const max = maxScores[dim] || 1;
    normalized[dim] = Math.max(0, Math.min(100,
      Math.round(((scores[dim] + max) / (max * 2)) * 100)
    ));
  });
  return normalized;
}

function extractWords() {
  const openAnswer = answers[15] || '';
  return openAnswer.split(',').map(w => w.trim()).filter(w => w.length > 1);
}

// ── Envoi ──
async function submitAnswers() {
  const btn = document.getElementById('btn-next');
  btn.disabled     = true;
  btn.textContent  = 'Envoi en cours...';

  const vector           = buildVector();
  const words            = extractWords();
  const respondentName   = isAnonymous ? null : (document.getElementById('respondent-name').value.trim() || null);

  try {
    const res = await fetch(API_URL + '/rc/respond', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_key:      SESSION_KEY,
        vector,
        words,
        relation:         relation || 'ami',
        respondent_name:  respondentName,
        is_anonymous:     isAnonymous,
        source:           'web',
      }),
    });
    const data = await res.json();
    if (data.success) {
      localStorage.setItem(STORAGE_KEY, '1');
      document.getElementById('step-quiz').style.display   = 'none';
      document.getElementById('step-success').style.display = 'block';
    } else {
      btn.disabled    = false;
      btn.textContent = 'Réessayer →';
      alert('Erreur : ' + (data.error || 'Réessaie plus tard'));
    }
  } catch(e) {
    btn.disabled    = false;
    btn.textContent = 'Réessayer →';
    alert('Erreur réseau. Vérifie ta connexion.');
  }
}
</script>
</body>
</html>"""