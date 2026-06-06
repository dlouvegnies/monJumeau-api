RC_WEBAPP_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Regard Croisé — monJumeau</title>
<script src="https://unpkg.com/@phosphor-icons/web@2.1.1"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #F8F7FF; min-height: 100vh;
    display: flex; flex-direction: column; align-items: center;
  }
  .container { width: 100%; max-width: 480px; padding: 24px 20px 48px; }
  .header { text-align: center; margin-bottom: 28px; }
  .logo-icon {
    width: 56px; height: 56px; border-radius: 28px; background: #EEEDFE;
    display: flex; align-items: center; justify-content: center; margin: 0 auto 10px;
  }
  .logo { font-size: 26px; font-weight: 800; color: #1A1523; letter-spacing: -1px; }
  .logo span { color: #534AB7; font-style: italic; font-weight: 400; }
  .subtitle {
    font-size: 13px; color: #71717A; margin-top: 4px;
    display: flex; align-items: center; justify-content: center; gap: 5px;
  }
  .version-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 12px; border-radius: 20px; margin-top: 8px;
    font-size: 12px; font-weight: 600;
  }
  .progress-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 24px; }
  .progress-bar { flex: 1; height: 4px; background: #E4E4E7; border-radius: 2px; overflow: hidden; }
  .progress-fill { height: 100%; background: #534AB7; border-radius: 2px; transition: width 0.3s ease; }
  .progress-text { font-size: 13px; color: #71717A; white-space: nowrap; display: flex; align-items: center; gap: 4px; }
  .card { background: white; border-radius: 16px; padding: 22px; border: 0.5px solid #E4E4E7; margin-bottom: 14px; }
  .info-banner {
    display: flex; align-items: flex-start; gap: 10px;
    background: #EEEDFE; border-radius: 10px; padding: 12px 14px;
    margin-bottom: 18px; border: 0.5px solid #AFA9EC;
  }
  .info-banner-text { font-size: 13px; color: #534AB7; line-height: 1.5; }
  .section-label {
    font-size: 11px; font-weight: 600; color: #71717A;
    letter-spacing: 1px; text-transform: uppercase;
    margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
  }
  .relation-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 18px; }
  .relation-btn {
    padding: 12px 10px; border-radius: 10px; border: 1.5px solid #E4E4E7;
    background: white; font-size: 14px; color: #3F3F46; cursor: pointer;
    text-align: center; font-family: inherit; transition: all 0.15s;
    display: flex; flex-direction: column; align-items: center; gap: 6px;
  }
  .relation-btn i { font-size: 20px; color: #A1A1AA; transition: color 0.15s; }
  .relation-btn.selected { border-color: #534AB7; background: #EEEDFE; color: #534AB7; font-weight: 600; }
  .relation-btn.selected i { color: #534AB7; }
  .input-wrap { position: relative; margin-bottom: 14px; }
  .input-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 16px; color: #A1A1AA; }
  .text-input {
    width: 100%; padding: 12px 16px 12px 38px; border-radius: 10px;
    border: 1.5px solid #E4E4E7; font-size: 15px; color: #1A1523; outline: none;
    font-family: inherit; transition: border-color 0.15s; background: white;
  }
  .text-input:focus { border-color: #534AB7; }
  .anon-row { display: flex; align-items: center; gap: 10px; cursor: pointer; padding: 8px 0; }
  .anon-checkbox {
    width: 22px; height: 22px; border-radius: 6px; border: 1.5px solid #D4D4D8;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s; flex-shrink: 0; background: white;
  }
  .anon-checkbox.checked { background: #534AB7; border-color: #534AB7; }
  .anon-checkbox i { font-size: 14px; color: white; }
  .anon-label { font-size: 14px; color: #52525B; display: flex; align-items: center; gap: 6px; }
  .anon-label i { font-size: 16px; color: #A1A1AA; }
  .question-number {
    font-size: 11px; font-weight: 600; color: #534AB7; letter-spacing: 1px;
    text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;
  }
  .question-text { font-size: 18px; font-weight: 600; color: #1A1523; line-height: 1.4; margin-bottom: 18px; }
  .answers { display: flex; flex-direction: column; gap: 9px; }
  .answer-btn {
    width: 100%; padding: 13px 15px; border-radius: 10px; border: 1.5px solid #E4E4E7;
    background: white; text-align: left; font-size: 15px; color: #3F3F46; cursor: pointer;
    transition: all 0.15s; display: flex; align-items: center; gap: 11px; font-family: inherit;
  }
  .answer-btn:hover { border-color: #AFA9EC; background: #EEEDFE; color: #534AB7; }
  .answer-btn.selected { border-color: #534AB7; background: #EEEDFE; color: #534AB7; font-weight: 600; }
  .answer-letter {
    width: 28px; height: 28px; border-radius: 8px; background: #F4F4F5;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #71717A; flex-shrink: 0; transition: all 0.15s;
  }
  .answer-btn.selected .answer-letter { background: #534AB7; color: white; }
  .open-input {
    width: 100%; padding: 13px 15px; border-radius: 10px; border: 1.5px solid #E4E4E7;
    font-size: 15px; color: #1A1523; outline: none; font-family: inherit;
    resize: none; transition: border-color 0.15s; background: white;
  }
  .open-input:focus { border-color: #534AB7; }
  .open-hint { font-size: 12px; color: #A1A1AA; margin-top: 7px; display: flex; align-items: center; gap: 4px; }
  .nav { display: flex; gap: 10px; margin-top: 8px; }
  .btn-prev {
    padding: 13px 18px; border-radius: 10px; border: 1.5px solid #E4E4E7;
    background: white; font-size: 15px; color: #71717A; cursor: pointer;
    font-family: inherit; transition: all 0.15s; display: flex; align-items: center; gap: 6px;
  }
  .btn-prev:hover { border-color: #D4D4D8; }
  .btn-next {
    flex: 1; padding: 13px; border-radius: 10px; border: none; background: #534AB7; color: white;
    font-size: 15px; font-weight: 600; cursor: pointer; font-family: inherit;
    transition: all 0.15s; display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .btn-next:hover { background: #3C3489; }
  .btn-next:disabled { background: #D4D4D8; cursor: not-allowed; }
  .btn-start {
    width: 100%; padding: 15px; border-radius: 12px; border: none;
    background: #534AB7; color: white; font-size: 16px; font-weight: 600; cursor: pointer;
    font-family: inherit; transition: all 0.15s;
    display: flex; align-items: center; justify-content: center; gap: 10px;
  }
  .btn-start:hover { background: #3C3489; }
  .btn-start:disabled { background: #D4D4D8; cursor: not-allowed; }
  .success-icon-wrap {
    width: 80px; height: 80px; border-radius: 40px; background: #EEEDFE;
    display: flex; align-items: center; justify-content: center; margin: 0 auto 18px;
  }
  .success-title { font-size: 24px; font-weight: 700; color: #1A1523; margin-bottom: 10px; }
  .success-text { font-size: 15px; color: #71717A; line-height: 1.6; margin-bottom: 26px; }
  .app-cta {
    display: inline-flex; align-items: center; gap: 8px; padding: 13px 26px; border-radius: 12px;
    background: #534AB7; color: white; font-size: 15px; font-weight: 600;
    text-decoration: none; transition: background 0.15s;
  }
  .app-cta:hover { background: #3C3489; }
  .divider { height: 0.5px; background: #F4F4F5; margin: 14px 0; }
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <div class="logo-icon">
      <i class="ph ph-shooting-star" style="font-size:28px;color:#534AB7"></i>
    </div>
    <div class="logo">mon<span>Jumeau</span></div>
    <div class="subtitle">
      <i class="ph ph-eye" style="font-size:14px;color:#A1A1AA"></i>
      Regard Croisé
    </div>
    <div id="version-badge" class="version-badge"></div>
  </div>

  <!-- ── INTRO ── -->
  <div id="step-intro">
    <div class="card">
      <div class="info-banner">
        <i class="ph ph-info" style="font-size:18px;color:#534AB7;flex-shrink:0;margin-top:1px"></i>
        <div class="info-banner-text">
          Un proche t'invite à répondre à 15 questions sur lui. Tes réponses l'aideront à mieux se connaître grâce à ton regard extérieur.
        </div>
      </div>
      <div class="section-label">
        <i class="ph ph-users-three"></i>
        Tu es...
      </div>
      <div class="relation-grid">
        <button class="relation-btn" onclick="selectRelation('ami', this)">
          <i class="ph ph-hand-waving"></i>Ami(e)
        </button>
        <button class="relation-btn" onclick="selectRelation('famille', this)">
          <i class="ph ph-house"></i>Famille
        </button>
        <button class="relation-btn" onclick="selectRelation('collegue', this)">
          <i class="ph ph-briefcase"></i>Collègue
        </button>
        <button class="relation-btn" onclick="selectRelation('partenaire', this)">
          <i class="ph ph-heart"></i>Partenaire
        </button>
      </div>
      <div class="divider"></div>


     <!-- Prénom visible par défaut, plus de checkbox ambiguë -->
        <div class="section-label">
            <i class="ph ph-user"></i>
            Ton prénom
        </div>
        <div class="input-wrap">
            <i class="ph ph-user input-icon"></i>
            <input class="text-input" id="respondent-name" placeholder="Ex: Paulo, Marie..." />
        </div>
        <div class="anon-row" onclick="toggleAnon()">
            <div class="anon-checkbox" id="anon-checkbox">
                <i class="ph ph-check" style="display:none"></i>
            </div>
            <div class="anon-label">
                <i class="ph ph-eye-slash" id="anon-icon"></i>
                <span id="anon-label">Rester anonyme</span>
            </div>
        </div>


    <button class="btn-start" id="btn-start" onclick="startQuiz()" disabled>
      <i class="ph ph-play"></i>
      Commencer le questionnaire
      <i class="ph ph-arrow-right"></i>
    </button>
  </div>

  <!-- ── QUIZ ── -->
  <div id="step-quiz" style="display:none">
    <div class="progress-wrap">
      <div class="progress-bar">
        <div class="progress-fill" id="progress-fill" style="width:0%"></div>
      </div>
      <div class="progress-text">
        <i class="ph ph-list-bullets" style="font-size:14px;color:#A1A1AA"></i>
        <span id="progress-text">1 / 15</span>
      </div>
    </div>
    <div class="card">
      <div class="question-number" id="q-number">
        <i class="ph ph-question"></i> QUESTION 1
      </div>
      <div class="question-text" id="q-text"></div>
      <div class="answers" id="q-answers"></div>
    </div>
    <div class="nav">
      <button class="btn-prev" id="btn-prev" onclick="prevQuestion()" style="display:none">
        <i class="ph ph-arrow-left"></i> Précédent
      </button>
      <button class="btn-next" id="btn-next" onclick="nextQuestion()" disabled>
        <span id="btn-next-label">Suivant</span>
        <i class="ph ph-arrow-right" id="btn-next-icon"></i>
      </button>
    </div>
  </div>

  <!-- ── SUCCÈS ── -->
  <div id="step-success" style="display:none">
    <div class="card" style="text-align:center;padding:40px 24px">
      <div class="success-icon-wrap">
        <i class="ph ph-check-circle" style="font-size:40px;color:#534AB7"></i>
      </div>
      <div class="success-title">Merci !</div>
      <div class="success-text">
        Ton regard a bien été enregistré.<br>
        Il aidera ton proche à mieux se connaître grâce à ta vision extérieure.
      </div>
      <a href="https://apps.apple.com/app/monjumeau" class="app-cta">
        <i class="ph ph-device-mobile"></i>
        Découvrir monJumeau
      </a>
    </div>
  </div>
</div>

<script>
const SESSION_KEY = '__SESSION_KEY__';
const API_URL     = '__API_URL__';
const VERSION     = '__VERSION__';
const DIMS        = ['sociabilite','organisation','curiosite','audace','empathie','leadership','stabilite','cooperation'];

// ── Badge version ──
const VERSION_CONFIG = {
  universel: { label:'Famille & Amis',   color:'#534AB7', bg:'#EEEDFE', icon:'ph-users-three' },
  jeunes:    { label:'Amis · 16-25 ans', color:'#993556', bg:'#FBEAF0', icon:'ph-hand-waving' },
  pro:       { label:'Collègues & Pro',  color:'#185FA5', bg:'#E6F1FB', icon:'ph-briefcase'   },
};
const vc    = VERSION_CONFIG[VERSION] || VERSION_CONFIG.universel;
const badge = document.getElementById('version-badge');
badge.style.background = vc.bg;
badge.style.color      = vc.color;
badge.innerHTML        = `<i class="ph ${vc.icon}" style="font-size:14px"></i>${vc.label}`;

// ── Questions communes Q1-Q7 ──
const Q_COMMUNES_1_7 = [
  { id:1, text:"Dans un groupe, cette personne est plutôt :", answers:[
    { label:"Celle qui anime et lance les idées",        dims:{ leadership:2, sociabilite:2 } },
    { label:"Celle qui organise et structure",           dims:{ organisation:2, leadership:1 } },
    { label:"Celle qui met l'ambiance",                  dims:{ sociabilite:2, empathie:1 } },
    { label:"Celle qui écoute et observe",               dims:{ empathie:2, stabilite:1 } },
  ]},
  { id:2, text:"Face à un conflit, elle a tendance à :", answers:[
    { label:"Confronter directement",                    dims:{ audace:2, leadership:1 } },
    { label:"Chercher un compromis",                     dims:{ cooperation:2, empathie:1 } },
    { label:"Prendre du recul et réfléchir",             dims:{ stabilite:2, organisation:1 } },
    { label:"Éviter et laisser passer",                  dims:{ stabilite:1, cooperation:-1 } },
  ]},
  { id:3, text:"Quand elle rencontre quelqu'un de nouveau :", answers:[
    { label:"Elle engage la conversation facilement",    dims:{ sociabilite:2, audace:1 } },
    { label:"Elle est chaleureuse mais réservée",        dims:{ empathie:2, stabilite:1 } },
    { label:"Elle observe avant de se lancer",           dims:{ stabilite:2, curiosite:1 } },
    { label:"Elle met du temps à s'ouvrir",              dims:{ stabilite:2, sociabilite:-1 } },
  ]},
  { id:4, text:"Sa plus grande qualité selon toi :", answers:[
    { label:"Son énergie et sa détermination",           dims:{ audace:2, leadership:2 } },
    { label:"Sa fiabilité et sa constance",              dims:{ organisation:2, stabilite:2 } },
    { label:"Sa créativité et sa curiosité",             dims:{ curiosite:2, audace:1 } },
    { label:"Son empathie et sa générosité",             dims:{ empathie:2, cooperation:2 } },
  ]},
  { id:5, text:"Son principal défaut selon toi :", answers:[
    { label:"Impatient(e) et impulsif(ve)",              dims:{ audace:1, stabilite:-1 } },
    { label:"Trop exigeant(e) envers lui/elle-même",    dims:{ organisation:1, stabilite:-1 } },
    { label:"Dispersé(e) et instable",                   dims:{ curiosite:1, organisation:-1 } },
    { label:"Trop accommodant(e)",                       dims:{ cooperation:1, audace:-1 } },
  ]},
  { id:6, text:"Face à une décision importante, elle :", answers:[
    { label:"Décide vite et assume",                     dims:{ audace:2, leadership:2 } },
    { label:"Analyse longuement avant d'agir",           dims:{ organisation:2, stabilite:1 } },
    { label:"Suit son instinct",                         dims:{ audace:2, curiosite:1 } },
    { label:"Demande l'avis de ses proches",             dims:{ cooperation:2, empathie:1 } },
  ]},
  { id:7, text:"Son week-end idéal ressemble à :", answers:[
    { label:"Sorties, rencontres, plein de monde",       dims:{ sociabilite:2, audace:1 } },
    { label:"Un programme bien préparé",                 dims:{ organisation:2, stabilite:1 } },
    { label:"Une aventure improvisée",                   dims:{ audace:2, curiosite:2 } },
    { label:"Du calme et de la tranquillité",            dims:{ stabilite:2, empathie:1 } },
  ]},
];

// ── Questions communes Q12-Q15 ──
const Q_COMMUNES_12_15 = [
  { id:12, text:"Si tu devais la décrire en un mot, ce serait :", answers:[
    { label:"Énergique",       dims:{ audace:2, sociabilite:1 } },
    { label:"Fiable",          dims:{ organisation:2, stabilite:2 } },
    { label:"Curieux(se)",     dims:{ curiosite:2, audace:1 } },
    { label:"Bienveillant(e)", dims:{ empathie:2, cooperation:2 } },
  ]},
  { id:13, text:"C'est quelqu'un qui :", answers:[
    { label:"Aime relever des défis",                    dims:{ audace:2, leadership:1 } },
    { label:"Préfère la stabilité et la sécurité",       dims:{ stabilite:2, organisation:1 } },
    { label:"S'intéresse à tout",                        dims:{ curiosite:2, sociabilite:1 } },
    { label:"Met les autres avant elle",                 dims:{ empathie:2, cooperation:1, leadership:-1 } },
  ]},
  { id:14, text:"Ce qui la rend unique selon toi :", answers:[
    { label:"Sa façon de voir les choses différemment",  dims:{ curiosite:2, audace:1 } },
    { label:"Sa capacité à rassembler les gens",         dims:{ sociabilite:2, leadership:2 } },
    { label:"Son côté profondément humain",              dims:{ empathie:2, cooperation:1 } },
    { label:"Sa rigueur et son sérieux",                 dims:{ organisation:2, stabilite:1 } },
  ]},
  { id:15, type:"open",
    text:"En 3 mots, comment tu la décrirais à quelqu'un qui ne la connaît pas ?",
    placeholder:"Ex: curieux, généreux, fiable",
  },
];

// ── Questions spécifiques ──
const Q_UNIVERSEL = [
  { id:8, text:"Dans un projet, elle est plutôt :", answers:[
    { label:"Le moteur — elle lance et impulse",         dims:{ leadership:2, audace:2 } },
    { label:"Le pilier — elle structure et fiabilise",   dims:{ organisation:2, stabilite:2 } },
    { label:"L'innovatrice — elle apporte des idées",    dims:{ curiosite:2, audace:1 } },
    { label:"Le liant — elle fédère et harmonise",       dims:{ cooperation:2, empathie:2 } },
  ]},
  { id:9, text:"Quand les choses ne se passent pas comme prévu :", answers:[
    { label:"Elle s'adapte et rebondit facilement",      dims:{ audace:2, stabilite:1 } },
    { label:"Elle cherche rapidement un plan B",         dims:{ organisation:2, leadership:1 } },
    { label:"Elle prend le temps d'analyser",            dims:{ stabilite:2, organisation:1 } },
    { label:"Elle peut être déstabilisée un moment",     dims:{ stabilite:-1, cooperation:1 } },
  ]},
  { id:10, text:"Dans une amitié, elle est :", answers:[
    { label:"Présente et disponible",                    dims:{ empathie:2, cooperation:2 } },
    { label:"Loyale et fiable",                          dims:{ stabilite:2, cooperation:1 } },
    { label:"Stimulante et inspirante",                  dims:{ curiosite:2, leadership:1 } },
    { label:"Discrète mais profonde",                    dims:{ stabilite:2, empathie:1 } },
  ]},
  { id:11, text:"Quand un proche a un problème, elle :", answers:[
    { label:"Écoute et soutient émotionnellement",       dims:{ empathie:2, cooperation:2 } },
    { label:"Cherche des solutions concrètes",           dims:{ organisation:2, leadership:1 } },
    { label:"Donne son avis directement",                dims:{ audace:2, leadership:1 } },
    { label:"Accompagne sans imposer",                   dims:{ empathie:2, cooperation:1 } },
  ]},
];

const Q_JEUNES = [
  { id:8, text:"Face à un exam ou une deadline, elle est :", answers:[
    { label:"Organisée — elle s'y prend à l'avance",     dims:{ organisation:2, stabilite:2 } },
    { label:"Last minute — mais elle s'en sort toujours",dims:{ audace:2, curiosite:1 } },
    { label:"Stressée — elle cherche de l'aide",         dims:{ cooperation:2, stabilite:-1 } },
    { label:"Cool — elle relativise facilement",         dims:{ stabilite:2, empathie:1 } },
  ]},
  { id:9, text:"Sur ses réseaux sociaux, elle est plutôt :", answers:[
    { label:"Active — elle poste et commente souvent",   dims:{ sociabilite:2, audace:1 } },
    { label:"Présente mais discrète",                    dims:{ stabilite:2, empathie:1 } },
    { label:"Elle consomme sans trop poster",            dims:{ curiosite:2, stabilite:1 } },
    { label:"Presque absente des réseaux",               dims:{ stabilite:2, organisation:1 } },
  ]},
  { id:10, text:"En soirée ou en sortie, elle est :", answers:[
    { label:"Celle qui organise et s'assure que ça roule",dims:{ organisation:2, leadership:2 } },
    { label:"Celle qui met l'ambiance pour tout le monde",dims:{ sociabilite:2, audace:2 } },
    { label:"Celle qui reste avec ses proches",           dims:{ empathie:2, stabilite:1 } },
    { label:"Celle qui arrive tard et repart tôt",        dims:{ stabilite:2, organisation:1 } },
  ]},
  { id:11, text:"Quand il y a une tension dans le groupe d'amis :", answers:[
    { label:"Elle prend position clairement",            dims:{ audace:2, leadership:2 } },
    { label:"Elle essaie de réconcilier tout le monde",  dims:{ cooperation:2, empathie:2 } },
    { label:"Elle reste neutre et observe",              dims:{ stabilite:2, curiosite:1 } },
    { label:"Elle préfère s'éloigner du conflit",        dims:{ stabilite:2, cooperation:1 } },
  ]},
];

const Q_PRO = [
  { id:8, text:"Dans une équipe de travail, elle est :", answers:[
    { label:"Le moteur — elle impulse et décide",        dims:{ leadership:2, audace:2 } },
    { label:"Le référent — fiable et rigoureux(se)",     dims:{ organisation:2, stabilite:2 } },
    { label:"L'innovateur(trice) — plein(e) d'idées",   dims:{ curiosite:2, audace:1 } },
    { label:"Le médiateur — elle gère les relations",    dims:{ cooperation:2, empathie:2 } },
  ]},
  { id:9, text:"Face à une forte pression au travail, elle :", answers:[
    { label:"Performe mieux sous pression",              dims:{ audace:2, leadership:1 } },
    { label:"S'organise encore mieux",                   dims:{ organisation:2, stabilite:2 } },
    { label:"Cherche du soutien dans l'équipe",          dims:{ cooperation:2, empathie:1 } },
    { label:"Peut être dépassée temporairement",         dims:{ stabilite:-1, empathie:1 } },
  ]},
  { id:10, text:"Dans sa vie professionnelle, elle est motivée par :", answers:[
    { label:"La reconnaissance et les résultats",        dims:{ leadership:2, audace:2 } },
    { label:"La stabilité et la sécurité",               dims:{ stabilite:2, organisation:2 } },
    { label:"Apprendre et progresser en permanence",     dims:{ curiosite:2, audace:1 } },
    { label:"L'impact positif sur les autres",           dims:{ empathie:2, cooperation:2 } },
  ]},
  { id:11, text:"Face à un désaccord professionnel, elle :", answers:[
    { label:"Défend son point de vue fermement",         dims:{ audace:2, leadership:2 } },
    { label:"Cherche un consensus acceptable",           dims:{ cooperation:2, empathie:1 } },
    { label:"Analyse la situation avant de réagir",      dims:{ organisation:2, stabilite:1 } },
    { label:"Préfère éviter l'affrontement",             dims:{ stabilite:2, cooperation:1 } },
  ]},
];

const Q_SPECIFIQUES = VERSION === 'jeunes' ? Q_JEUNES : VERSION === 'pro' ? Q_PRO : Q_UNIVERSEL;
const QUESTIONS     = [...Q_COMMUNES_1_7, ...Q_SPECIFIQUES, ...Q_COMMUNES_12_15];

// ── État — anonyme décoché par défaut ──
let currentIndex = 0;
let answers      = {};
let relation     = null;
let isAnonymous  = false;   // ← décoché par défaut

// ── Anti-doublon ──
const STORAGE_KEY = 'rc_answered_' + SESSION_KEY;
if (localStorage.getItem(STORAGE_KEY)) {
  document.getElementById('step-intro').style.display   = 'none';
  document.getElementById('step-success').style.display = 'block';
}

// ── Relation ──
function selectRelation(rel, btn) {
  relation = rel;
  document.querySelectorAll('.relation-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  document.getElementById('btn-start').disabled = false;
}

// ── Anonymat ──
function toggleAnon() {
  isAnonymous = !isAnonymous;
  const cb    = document.getElementById('anon-checkbox');
  const check = cb.querySelector('i');
  const icon  = document.getElementById('anon-icon');
  const label = document.getElementById('anon-label');
  const input = document.getElementById('respondent-name');

  cb.classList.toggle('checked', isAnonymous);
  check.style.display      = isAnonymous ? 'flex' : 'none';
  icon.className           = isAnonymous ? 'ph ph-eye-slash' : 'ph ph-eye-slash';
  label.textContent        = isAnonymous ? 'Rester anonyme ✓' : 'Rester anonyme';
  input.style.opacity      = isAnonymous ? '0.4' : '1';
  input.style.pointerEvents = isAnonymous ? 'none' : 'auto';
}

// ── Démarrer ──
function startQuiz() {
  document.getElementById('step-intro').style.display = 'none';
  document.getElementById('step-quiz').style.display  = 'block';
  renderQuestion();
}

// ── Render question ──
function renderQuestion() {
  const q     = QUESTIONS[currentIndex];
  const total = QUESTIONS.length;
  const pct   = Math.round((currentIndex / total) * 100);
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-text').textContent = (currentIndex + 1) + ' / ' + total;
  document.getElementById('q-number').innerHTML = '<i class="ph ph-question"></i> QUESTION ' + (currentIndex + 1);
  document.getElementById('q-text').textContent = q.text;
  document.getElementById('btn-prev').style.display = currentIndex > 0 ? 'flex' : 'none';
  const isLast = currentIndex === total - 1;
  document.getElementById('btn-next-label').textContent = isLast ? 'Envoyer' : 'Suivant';
  document.getElementById('btn-next-icon').className    = isLast ? 'ph ph-paper-plane-tilt' : 'ph ph-arrow-right';

  const answersDiv = document.getElementById('q-answers');
  answersDiv.innerHTML = '';

  if (q.type === 'open') {
    const ta       = document.createElement('textarea');
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
    hint.className = 'open-hint';
    hint.innerHTML = '<i class="ph ph-info" style="font-size:13px"></i> Sépare les mots par des virgules';
    answersDiv.appendChild(hint);
    document.getElementById('btn-next').disabled = !(answers[q.id] && answers[q.id].trim().length >= 2);
  } else {
    const letters = ['A','B','C','D'];
    q.answers.forEach((ans, i) => {
      const btn     = document.createElement('button');
      btn.className = 'answer-btn' + (answers[q.id] === i ? ' selected' : '');
      btn.innerHTML = `<span class="answer-letter">${letters[i]}</span>${ans.label}`;
      btn.onclick   = () => selectAnswer(i);
      answersDiv.appendChild(btn);
    });
    document.getElementById('btn-next').disabled = answers[q.id] === undefined;
  }
}

function selectAnswer(index) {
  answers[QUESTIONS[currentIndex].id] = index;
  document.querySelectorAll('.answer-btn').forEach((b, i) => b.classList.toggle('selected', i === index));
  document.getElementById('btn-next').disabled = false;
}

function prevQuestion() {
  if (currentIndex > 0) { currentIndex--; renderQuestion(); }
}

async function nextQuestion() {
  if (currentIndex < QUESTIONS.length - 1) { currentIndex++; renderQuestion(); }
  else await submitAnswers();
}

// ── Calcul vecteur — normalisation 50±40 ──
function buildVector() {
  const scores    = Object.fromEntries(DIMS.map(d => [d, 0]));
  const maxScores = Object.fromEntries(DIMS.map(d => [d, 0]));

  QUESTIONS.forEach(q => {
    if (q.type === 'open') return;
    const idx = answers[q.id];
    if (idx === undefined) return;
    Object.entries(q.answers[idx].dims).forEach(([dim, value]) => {
      scores[dim]    += value;
      maxScores[dim] += Math.abs(value);
    });
  });

  const normalized = {};
  DIMS.forEach(dim => {
    const max = maxScores[dim] || 1;
    const raw = scores[dim] / max;           // -1 à +1
    normalized[dim] = Math.max(5, Math.min(95,
      Math.round(50 + raw * 40)              // amplitude 40 pts — évite 0 et 100
    ));
  });
  return normalized;
}

function extractWords() {
  return (answers[15] || '').split(',').map(w => w.trim().toLowerCase()).filter(w => w.length > 1);
}

// ── Envoi ──
async function submitAnswers() {
  const btn = document.getElementById('btn-next');
  btn.disabled = true;
  btn.innerHTML = '<i class="ph ph-circle-notch"></i> Envoi...';
  try {
    const raw_answers = {};
    QUESTIONS.forEach(q => {
      if (q.type !== 'open' && answers[q.id] !== undefined) {
        raw_answers[q.id] = answers[q.id];
      }
    });

    const respondentName = document.getElementById('respondent-name').value.trim();

    const res = await fetch(API_URL + '/rc/respond', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_key:     SESSION_KEY,
        vector:          buildVector(),
        words:           extractWords(),
        relation:        relation || 'ami',
        respondent_name: isAnonymous ? null : (respondentName || null),
        is_anonymous:    isAnonymous,
        source:          'web',
        raw_answers,
      }),
    });
    const data = await res.json();
    if (data.success) {
      localStorage.setItem(STORAGE_KEY, '1');
      document.getElementById('step-quiz').style.display    = 'none';
      document.getElementById('step-success').style.display = 'block';
    } else {
      btn.disabled = false;
      btn.innerHTML = '<i class="ph ph-arrow-clockwise"></i> Réessayer';
      alert('Erreur : ' + (data.error || 'Réessaie plus tard'));
    }
  } catch(e) {
    btn.disabled = false;
    btn.innerHTML = '<i class="ph ph-arrow-clockwise"></i> Réessayer';
    alert('Erreur réseau. Vérifie ta connexion.');
  }
}
</script>
</body>
</html>"""
