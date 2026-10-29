// Acasă (#acasa): intro-ul aplicației. Se deschide la clic pe marca din antet. Un hero, cifrele vii (GET /worklist,
// /autopilot/status prin live.js) și câte un card pentru fiecare tab din bara de navigare (.nav-btn[data-view]).
// Cardurile se construiesc din bara de navigare: un tab nou apare singur, cu descrierea de rezervă.
// Folosește funcțiile din app.js / live.js / demo-dosare.js (h, http, fmtNum, plural, showView, openInDemo, nowDoing) doar la apel.

const HOME_ICON = {
  cases: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M8 13h8M8 16h5"/>',
  agents: '<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M12 8V4M9 4h6"/><circle cx="9" cy="14" r="1.5"/><circle cx="15" cy="14" r="1.5"/>',
  impact: '<path d="M3 20h18"/><path d="M6 16v-4M11 16V8M16 16v-6M21 16V5"/>',
  results: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
  demo: '<circle cx="12" cy="12" r="10"/><path d="M10 8l6 4-6 4z"/>',
  fallback: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12h8M12 8v8"/>',
};
const homeIcon = (name) => {
  const el = document.createElement('span');
  el.className = 'home-ico';
  el.setAttribute('aria-hidden', 'true');
  el.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${HOME_ICON[name] || HOME_ICON.fallback}</svg>`;
  return el;
};

// descrierea și mini-cifra fiecărui tab cunoscut; d = cifrele citite la randare
const HOME_TABS = {
  cases: { text: 'Lista de lucru a băncii: fiecare dosar, etapa lui, ce urmează, termenul și deciziile care te așteaptă.',
    stat: (d) => d.work && (d.decisions ? `${fmtNum(d.decisions)} ${plural(d.decisions, 'decizie te așteaptă', 'decizii te așteaptă', 'de decizii te așteaptă')}`
      : `${fmtNum(d.cases)} ${plural(d.cases, 'dosar', 'dosare', 'de dosare')}, nicio decizie în așteptare`) },
  agents: { text: 'Agenții AI (extractor, investigator, corespondent, comunicator, auditor): ce fac acum, ce au scris, cât au costat.',
    stat: (d) => d.agentNow },
  impact: { text: 'Sinteza pentru juriu: timpul și costul unui dosar cu agentul față de lucrul manual, cu ipotezele afișate.',
    stat: (d) => d.docs > 0 && `${fmtNum(d.docs)} ${plural(d.docs, 'document citit', 'documente citite', 'de documente citite')}` },
  results: { text: 'Rezultatele măsurate: citirea documentelor, cost și timp, stabilitate, siguranță, învățare; fiecare cifră cu sursa ei.',
    stat: (d) => d.reading != null && `${fmtNum(d.reading, 1)}% câmpuri citite corect` },
};

async function renderHome() {
  const box = $('#view-home');
  if (!box) return;
  let work = ui.work && !ui.filter && !ui.q ? ui.work : null;   // lista din antet, dacă e nefiltrată; altfel o citim
  try { work = await http('/worklist'); } catch (e) { if (!work) toast(e.message, true); }
  if (ui.view !== 'home') return;   // între timp omul a plecat
  const rows = (work?.rows || []).filter((r) => r.kind !== 'unmatched');
  const doing = typeof nowDoing === 'function' ? nowDoing() : { kind: 'down' };
  const agentsN = typeof AGENTS !== 'undefined' ? AGENTS.length : 0;
  const agentNow = { idle: 'La dispoziție', paused: 'Pas cu pas: AI la comanda ta', extracting: 'Extractorul citește acum',
    agent: `${(typeof AGENT_LABEL !== 'undefined' && AGENT_LABEL[doing.agent]) || 'Un agent'} scrie acum`,
    stopped: 'Autopilot oprit', off: 'Autopilot nepornit', down: 'Stare indisponibilă' }[doing.kind] || '';
  const sets = window.RESULTS_DATA?.citire?.seturi || [];
  const d = { work, cases: rows.length, decisions: work?.decisions_waiting || 0, agentNow,
    working: ['extracting', 'agent'].includes(doing.kind) ? 1 : 0,
    docs: live?.status ? (live.status.autopilot?.processed || []).length : null,
    reading: sets[0]?.campuri?.valoare ?? null };

  const stat = (n, label, extra = '') => h('div', { class: 'home-stat' + extra }, h('b', {}, n), h('span', {}, label));
  const hero = h('section', { class: 'home-hero' },
    h('p', { class: 'home-kicker' }, 'Raiffeisen Bank · Succesiuni'),
    h('h1', {}, 'Agentul de Succesiune'),
    h('p', { class: 'home-lead' }, 'Preia dosarele de deces ale clienților: citește documentele, aplică regulile băncii, scrie corespondența; ',
      h('b', {}, 'omul aprobă doar plata și excepțiile.')),
    h('div', { class: 'home-stats', 'aria-label': 'Cifrele de acum' },
      stat(work ? fmtNum(d.cases) : '—', plural(d.cases, 'dosar', 'dosare', 'de dosare')),
      stat(work ? fmtNum(d.decisions) : '—', plural(d.decisions, 'decizie te așteaptă', 'decizii te așteaptă', 'de decizii te așteaptă'), d.decisions ? ' warn' : ''),
      stat(fmtNum(agentsN), `agenți AI · ${agentNow.toLowerCase()}`, d.working ? ' live' : '')));

  const card = (view, title, text, mini, icon, go, extra = '') => h('button', { type: 'button', class: 'home-card' + extra, 'data-go': view, onclick: go },
    homeIcon(icon), h('span', { class: 'home-card-body' }, h('b', { class: 'home-card-title' }, title), h('span', { class: 'home-card-text' }, text),
      mini ? h('span', { class: 'home-card-mini' }, mini) : null), h('span', { class: 'home-card-go', 'aria-hidden': 'true' }, '→'));
  // un card pentru fiecare tab din bara de navigare (nu o listă fixă)
  const tabs = [...document.querySelectorAll('.nav-btn[data-view]')].map((b) => {
    const v = b.dataset.view, meta = HOME_TABS[v] || {};
    return card(v, b.textContent.trim(), meta.text || `Deschide ecranul „${b.textContent.trim()}”.`, meta.stat?.(d) || null,
      HOME_ICON[v] ? v : 'fallback', () => b.click());
  });
  const demoCard = typeof openInDemo === 'function' && typeof DEMO_CASE !== 'undefined'
    ? card('demo', 'Începe demo-ul', 'Dosarul Mariei Ionescu, pas cu pas: de la semnalul DGEP la plata către moștenitori, cu agenții la lucru.',
      'Fluxul Mariei Ionescu', 'demo', () => openInDemo(DEMO_CASE), ' demo') : null;
  box.replaceChildren(hero, h('section', { class: 'home-grid', 'aria-label': 'Ecranele aplicației' }, demoCard, tabs));
}
