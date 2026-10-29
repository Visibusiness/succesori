// Agenți, trimiterea documentelor din dosar și indicatorul din antet: ce fac extractorul, sistemul și agenții, în timp real.
// Surse (toate reale): GET /autopilot/status (ce citește / ce agent scrie acum, documente citite, apeluri de agenți),
// GET /inbox (fișiere în așteptare; portalul 056), GET /cases/{id}/artifacts (ce au scris agenții), GET /cases/{id} (câmpurile extrase).
// Încarcat înaintea lui app.js; folosește funcțiile lui (h, http, api, badge, select, showView …) doar la apel.

// Agenții LLM ai proiectului (.claude/agents) + ce fac, pe înțelesul operatorului.
const AGENTS = [
  ['extractor', 'Extractorul', 'Citește documentul (PDF sau text), îl clasifică și scoate câmpurile, fiecare cu scor de încredere. Nu decide nimic.'],
  ['case-investigator', 'Investigatorul', 'Când un document sau un dosar nu poate continua singur (ilizibil, CNP necunoscut, cote greșite, minor, poliță nepotrivită), pregătește pentru operator o propunere de rezolvare cu dovezi. Nu execută nimic.'],
  ['correspondent', 'Corespondentul', 'Scrie scrisorile dosarului (răspuns către notar, cerere de supliment, avizare de daună) din datele calculate de sistem, niciodată din memorie.'],
  ['heir-communicator', 'Comunicatorul cu moștenitorii', 'Scrie mesajele către moștenitori (ce mai lipsește, cât durează), pe canalul lor, cu respectarea secretului bancar.'],
  ['auditor', 'Auditorul', 'După fiecare lot verifică regulile: fiecare acțiune are regula citată, nicio plată fără aprobare umană, cote care însumează 1, minori blocați.'],
];
const AGENT_LABEL = Object.fromEntries(AGENTS.map(([id, label]) => [id, label]));
// Ce raportează sistemul (agent/pipeline.py, cod determinist) pentru un document.
const ACTION_LABEL = {
  frozen: 'Produsele clientului au fost blocate (reversibil)', fees_reversed: 'Comisioanele de după deces au fost stornate',
  freeze_definitive: 'Blocare definitivă (certificat de deces)', notary_answer_drafted: 'Răspunsul către notar a fost redactat (de semnat)',
  insurance_claim_opened: 'Dosar de daună deschis la asigurător', insurance_refused: 'Asigurătorul a refuzat (escaladat)',
  loan_settled_by_insurance: 'Creditul a fost stins de asigurător', indemnity_mismatch: 'Indemnizație în afara intervalului din condiții (escaladat)',
  heirs_recorded: 'Moștenitorii și cotele au fost înregistrate', supplement_requested: 'Certificat suplimentar cerut notarului',
  coverage_complete: 'Toate produsele sunt acoperite; planul de plată e pregătit pentru aprobare',
};

const live = { serverNow: Date.now(), status: null, inbox: null, portal: null, timer: null, seen: -1, busy: false, direct: [], cases: {}, outputs: {}, open: new Set(), sig: {}, ok: null };
const hms = (iso) => (iso ? String(iso).slice(11, 19) : '—');
const apState = () => live.status?.autopilot || null;
const stripMeta = (t) => String(t || '').replace(/^<!--.*?-->\s*/s, '');
const usd = (n) => `${fmtNum(n || 0, 2)} $`;

// ---------- sondare ----------
function startLive() {
  if (live.timer) return;
  live.timer = setInterval(pollLive, 2000);
  pollLive();
}

async function pollLive() {
  if (document.hidden && live.seen >= 0) return;
  try {
    const r = await fetch(API_BASE + '/autopilot/status');
    if (!r.ok) throw new Error(String(r.status));
    live.status = await r.json();
    live.serverNow = Date.parse(r.headers.get('date')) || Date.now();   // ora serverului (antetul Date): vârsta bătăii nu depinde de ceasul browserului
  } catch { live.status = null; }
  const ok = live.status !== null;
  if (ok !== live.ok) { live.ok = ok; ui.ok = ok; renderConn(); }
  try { live.inbox = await http('/inbox'); live.portal = true; } catch (e) { live.inbox = null; if (e.status === 404) live.portal = false; }
  const n = (apState()?.processed || []).length;
  if (n !== live.seen) {                     // un document nou a fost procesat: dosarele s-au schimbat
    const first = live.seen < 0;
    live.seen = n; live.cases = {}; live.outputs = {};
    if (!first) { if (ui.view === 'cases' && ui.selected?.startsWith('SC')) select(ui.selected); else refresh(); }
  }
  renderPill();
  if (ui.view === 'agents') renderAgents();
}

// Ce lucrează autopilotul chiar acum: {kind: 'off'|'idle'|'extracting'|'agent', ...}
function nowDoing() {
  const st = live.status, ap = apState();
  if (!st) return { kind: 'down' };
  if (st.paused) {   // Demo ghidat pas cu pas: lucrează doar apelurile AI pornite de operator (agent/ai_jobs.py)
    const j = (st.ai_jobs || []).find((x) => x.status === 'running') || (st.ai_jobs || [])[0];
    if (!j) return { kind: 'paused' };
    return j.agent === 'extractor' ? { kind: 'extracting', file: j.file || '', silent: 0 } : { kind: 'agent', agent: j.agent, key: j.label, silent: 0 };
  }
  if (!ap) return { kind: 'off' };
  // Bătaia (last_poll) se actualizează doar la începutul unui pas, iar un apel LLM durează 35–90 s (timeout 180 s): serverul declară „oprit” după 60 s
  // de liniște (st.running), deci cât lucrează un agent ar părea oprit. Cât lucrează, îl considerăm viu până la 5 min fără semnal.
  const quiet = Math.max(0, (live.serverNow - Date.parse(ap.last_poll)) / 1000) || 0;   // secunde de la ultima bătaie a autopilotului
  const working = ap.state === 'extracting' || ap.state === 'agent';
  const dead = ap.state === 'stopped' || (working ? quiet > 300 : !st.running);
  if (dead) return { kind: 'stopped', since: ap.last_poll };
  const silent = working && quiet > 60 ? Math.round(quiet) : 0;
  if (ap.state === 'extracting') return { kind: 'extracting', file: ap.current || '', silent };
  if (ap.state === 'agent') { const [agent, ...key] = String(ap.current || '').split(':'); return { kind: 'agent', agent, key: key.join(':'), silent }; }
  return { kind: 'idle', since: ap.last_poll };
}

// Un apel LLM lung nu dă semn de viață până termină; după 1 min spunem asta, ca să nu pară blocat sau oprit.
const quietNote = (d) => (d.silent ? [' ', badge(`apel în curs de ${d.silent} s`, 'info')] : '');

function nowBadge(d) {
  const waiting = live.inbox?.waiting?.length || 0;
  const more = waiting ? ` (+${waiting} în așteptare)` : '';
  switch (d.kind) {
    case 'down': return [badge('serverul nu răspunde', 'bad')];
    case 'off': return [badge('autopilot nepornit', 'bad'), ' Nu a rulat niciodată pe acest server, deci documentele nu sunt preluate și niciun agent nu lucrează. Pornește-l: ',
      h('code', {}, `.venv/bin/python scripts/autopilot.py --watch --api ${API_BASE}`)];
    case 'stopped': return [badge('autopilot oprit', 'warn'), ` procesul nu mai dă semne de viață (ultima activitate ${hms(d.since)} UTC). Repornește-l: `,
      h('code', {}, `.venv/bin/python scripts/autopilot.py --watch --api ${API_BASE}`)];
    case 'extracting': return [h('span', { class: 'spin' }), badge('Extractorul citește', 'warn'), ' ', h('strong', {}, d.file), more, quietNote(d)];
    case 'agent': return [h('span', { class: 'spin' }), badge(AGENT_LABEL[d.agent] || d.agent, 'warn'), ' scrie ', h('strong', {}, d.key), more, quietNote(d)];
    case 'paused': return [badge('pas cu pas', 'info'), ' Demo ghidat rulează pas cu pas: autopilotul e în pauză și niciun apel AI nu pornește fără butonul ▶.'];
    default: return [badge('aștept documente', 'ok'), `${more} · ultima verificare ${hms(d.since)} UTC`];
  }
}

function renderPill() {
  const d = nowDoing(), el = $('#agent-pill');
  if (!el) return;
  const tone = { down: 'bad', off: 'bad', stopped: 'warn', extracting: 'warn', agent: 'warn', idle: 'ok', paused: 'info' }[d.kind];
  const text = { down: 'Server indisponibil', off: 'Autopilot nepornit', stopped: 'Autopilot oprit', idle: 'Agenți: la dispoziție',
    paused: 'Pas cu pas: AI doar la comanda ta' }[d.kind]
    || (d.kind === 'extracting' ? `Extractorul citește ${d.file}` : `${AGENT_LABEL[d.agent] || d.agent} scrie…`);
  el.className = 'pill ' + tone;
  el.replaceChildren(...(['extracting', 'agent'].includes(d.kind) ? [h('span', { class: 'spin' })] : [h('span', { class: 'dot' })]), text);
  el.title = `${text} · deschide „Agenți”`;
}

// ---------- trimitere documente ----------
async function sendFiles(files) {
  if (!files.length) { toast('Alege cel puțin un fișier.', true); return; }
  if (live.busy) return;
  live.busy = true;
  try {
    if (live.portal) {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      const r = await http('/inbox', { method: 'POST', body: fd });
      toast(`${r.saved.length} ${plural(r.saved.length, 'fișier trimis', 'fișiere trimise', 'de fișiere trimise')} agentului`
        + (r.rejected.length ? `; respinse: ${r.rejected.map((x) => `${x.name} (${x.reason})`).join('; ')}` : '.'), r.rejected.length > 0 && !r.saved.length);
    } else {
      for (const f of files) { // server fără portal: direct la extractor + sistem (fără scrisori / investigații / audit)
        toast(`Se extrage ${f.name}… (poate dura un minut)`);
        const at = new Date().toISOString();
        try { live.direct.unshift({ at, file: f.name, result: await api.uploadDocument('x', f, 'neclasificat') }); }
        catch (e) { live.direct.unshift({ at, file: f.name, error: e.message }); }
      }
      await refresh();
    }
  } catch (e) { toast(e.message, true); } finally { live.busy = false; pollLive(); }
}

// ---------- ieșirile agenților (fila Agenți) ----------
function outputBox(call, caseId) {
  const key = call.file + '|' + call.at;
  const pre = h('pre', { class: 'agent-out' }, '');
  const load = async () => {
    const cached = call.file === 'audit.md' ? null : live.outputs[call.file];
    if (cached != null) { pre.textContent = cached; return; }
    pre.textContent = 'Se încarcă…';
    const cid = (/SC-\d{4}-\d{4}|SC-NEIDENTIFICAT/.exec(call.file) || [caseId])[0] || caseId || 'x';
    try {
      const r = await http(`/cases/${encodeURIComponent(cid)}/artifacts`);
      (r.artifacts || []).forEach((a) => { live.outputs[a.file] = stripMeta(a.content); });
      const text = call.file === 'audit.md' ? stripMeta(r.audit) : live.outputs[call.file];
      pre.textContent = text || '(fișierul nu a fost găsit)';
    } catch (e) { pre.textContent = e.message; }
  };
  const det = h('details', { class: 'call', open: live.open.has(key) },
    h('summary', {}, h('strong', {}, AGENT_LABEL[call.agent] || call.agent), ' a scris ', h('code', {}, call.file || '—'),
      h('span', { class: 'muted small' }, ` · ${hms(call.at)} · ${call.seconds != null ? fmtNum(call.seconds, 1) + ' s' : ''}${call.cost_usd != null ? ' · ' + usd(call.cost_usd) : ''}`),
      call.ok === false ? badge('eșuat', 'bad') : ''), pre);
  det.addEventListener('toggle', () => { if (det.open) { live.open.add(key); load(); } else live.open.delete(key); });
  if (det.open) load();
  return det;
}

// ---------- Agenți ----------
function renderAgents() {
  const root = $('#view-agents');
  const doing = nowDoing(), ap = apState();
  const processed = ap?.processed || [], calls = ap?.agent_calls || [];
  const sig = JSON.stringify([doing, processed.length, calls.length, [...live.open], ui.lastCases.length]);
  if (live.sig.agents === sig && root.childElementCount) return;
  live.sig.agents = sig;
  const totalCost = calls.reduce((a, c) => a + (c.cost_usd || 0), 0), totalSec = calls.reduce((a, c) => a + (c.seconds || 0), 0);
  const escOpen = ui.lastCases.filter(openEsc).length + ui.lastUnmatched.filter((u) => u.status !== 'închis').length;
  const lowConf = processed.filter((p) => p.confidence != null && p.confidence < ui.threshold).length;
  const status = (isNow, text) => (isNow ? h('div', { class: 'now' }, h('span', { class: 'spin' }), badge('lucrează', 'warn'), ' ', text) : h('div', { class: 'now' }, badge('liber', 'ok')));
  const card = (id, label, text, stats, now, body) => h('div', { class: 'card agent-card' + (now ? ' working' : '') },
    h('div', { class: 'agent-head' }, h('h3', {}, label), badge(id === 'sistem' ? 'cod' : 'LLM', id === 'sistem' ? 'info' : 'warn')),
    h('p', { class: 'small' }, text), id === 'sistem' ? null : status(now, now ? (doing.kind === 'extracting' ? doing.file : doing.key) : ''),
    stats ? h('p', { class: 'muted small' }, stats) : null, ...body);
  const agentCards = AGENTS.map(([id, label, text]) => {
    if (id === 'extractor') {
      const avg = processed.length ? processed.reduce((a, p) => a + (p.confidence || 0), 0) / processed.length : null;
      return card(id, label, text, `${processed.length} ${plural(processed.length, 'document citit', 'documente citite', 'de documente citite')}`
        + (avg != null ? ` · încredere medie ${avg.toFixed(2)}` : '') + (lowConf ? ` · ${lowConf} sub pragul ${ui.threshold}` : ''), doing.kind === 'extracting',
        [...processed].reverse().slice(0, 8).map((p) => h('div', { class: 'small' }, hms(p.at), ' · ', h('strong', {}, p.file), ' → ', DOC_TYPES[p.document_type] || p.document_type || '—', ' · ', conf(p.confidence))));
    }
    const mine = calls.filter((c) => c.agent === id);
    const sec = mine.reduce((a, c) => a + (c.seconds || 0), 0), cost = mine.reduce((a, c) => a + (c.cost_usd || 0), 0);
    return card(id, label, text, `${mine.length} ${plural(mine.length, 'apel', 'apeluri', 'de apeluri')}${mine.length ? ` · ${fmtNum(sec, 0)} s · ${usd(cost)}` : ''}`,
      doing.kind === 'agent' && doing.agent === id,
      mine.length ? [...mine].reverse().slice(0, 8).map((c) => outputBox(c, null)) : [h('p', { class: 'muted small' }, 'Nu a fost chemat încă.')]);
  });
  root.replaceChildren(
    h('div', { class: 'card' }, h('h3', {}, 'Cine face ce'),
      h('p', { class: 'small' }, 'Doi pași sunt cod determinist, testat (validările, calculele, starea dosarului, planul de plată); cinci sunt agenți LLM care citesc sau scriu text. ',
        'Niciun agent nu calculează o sumă și niciunul nu aprobă o plată: aprobarea e a omului.'),
      h('div', { class: 'now' }, nowBadge(doing)),
      h('p', { class: 'muted small' }, `Ultimele ${calls.length} apeluri de agenți: ${fmtNum(totalSec, 0)} s, ${usd(totalCost)}.`)),
    h('div', { class: 'agent-grid' },
      card('sistem', 'Sistemul', 'Validează documentele (poarta de încredere 0,80, CNP, cote), ține starea dosarului, calculează soldurile la data decesului, comisioanele de stornat, cotele și planul de plată, și blochează produsele. Același rezultat la fiecare rulare.',
        `${ui.lastCases.length} ${plural(ui.lastCases.length, 'dosar', 'dosare', 'de dosare')} · ${escOpen} ${plural(escOpen, 'escaladare deschisă', 'escaladări deschise', 'de escaladări deschise')}`, false,
        [h('p', { class: 'small' }, 'În „Dosare” vezi, document cu document, regula citată la fiecare acțiune.')]),
      ...agentCards));
}
