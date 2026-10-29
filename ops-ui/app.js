// Succesiuni — UI de operațiuni (Raiffeisen Bank). Fără build, fără framework. Doar date reale: nu există mock sau demo.
// Fișiere: app.js (dosare, plată, impact), live.js (Agenți, trimiterea documentelor, indicatorul din antet).
// API_BASE: aceeași origine când pagina e servită de backend la /ui/ (8000 stabil, 8001 dev, 8010 instanța proprie), altfel localhost:8000.
const API_BASE = location.pathname.startsWith('/ui') ? location.origin : 'http://localhost:8000';
const APPROVER_ROLE = 'ops_approver'; // trimis ca X-Role până există autentificare reală

// Mașina de stări din kb/tech/api-contract-bank.md, în ordine.
const STATES = [
  ['DEATH_SIGNALLED', 'Deces semnalat'], ['FROZEN', 'Blocat'], ['NOTARY_REQUESTED', 'Cerere notar'],
  ['NOTARY_ANSWERED', 'Răspuns la notar'], ['INSURANCE_CLAIM_OPEN', 'Daună deschisă'], ['INSURANCE_SETTLED', 'Daună închisă'],
  ['HEIR_CERT_RECEIVED', 'Certificat primit'], ['COVERAGE_GAP', 'Lipsă acoperire'], ['SUPPLEMENT_REQUESTED', 'Supliment cerut'],
  ['SUPPLEMENT_RECEIVED', 'Supliment primit'], ['PLAN_DRAFTED', 'Plan întocmit'], ['PAYMENT_PENDING_APPROVAL', 'Plată de aprobat'],
  ['PAID', 'Plătit'], ['CLOSED', 'Închis'], ['ESCALATED', 'Escaladat'],
];
const STATE_LABEL = { NEW: 'Nou', ...Object.fromEntries(STATES) };
const STATE_TONE = { ESCALATED: 'bad', PAYMENT_PENDING_APPROVAL: 'warn', COVERAGE_GAP: 'warn', SUPPLEMENT_REQUESTED: 'warn',
  PLAN_DRAFTED: 'warn', PAID: 'ok', CLOSED: 'ok' };

// Etichete în română pentru câmpurile extrase; cheia brută rămâne în title (pentru depanare).
const FIELD_LABEL = {
  cnp: 'CNP', name: 'Nume', raw_name: 'Nume (cum apare)', birth_date: 'Data nașterii', date_of_death: 'Data decesului',
  case_file: 'Dosar succesoral', reference: 'Număr de înregistrare', document_number: 'Număr document', document_series: 'Serie document',
  hearing_date: 'Termen dezbatere', notary_name: 'Notar', notary_office: 'Birou notarial', heirs: 'Moștenitori și cote',
  products: 'Produse', insurer: 'Asigurător', policy_id: 'Poliță', loan_contract: 'Contract de credit', amount: 'Sumă',
  decision: 'Decizie', reason: 'Motiv', minor: 'Minor', legal_representative: 'Reprezentant legal', spouse: 'Soț/soție',
  share: 'Cotă', ibans: 'IBAN-uri', testament: 'Testament', product_id: 'Produs', status: 'Stare', cif: 'CIF client',
  initial_certificate: 'Certificatul inițial', cnp_raw: 'CNP (cum apare)', claim_number: 'Număr dosar daună',
};
// Valori codificate din extracție, spuse omenește (cheia brută rămâne în title)
const VALUE_LABEL = { approved: 'aprobat', refused: 'refuzat', rejected: 'refuzat', pending: 'în analiză' };
const fieldLabel = (n) => h('span', { title: n }, FIELD_LABEL[n] || String(n).replace(/_/g, ' '));

const DOC_TYPES = {
  dgep_signal: 'Semnal DGEP', notary_request: 'Adresa notarului', insurance_certificate: 'Certificat de asigurare',
  heir_certificate: 'Certificat de moștenitor', insurer_response: 'Răspunsul asigurătorului',
  supplementary_certificate: 'Certificat suplimentar', death_certificate: 'Certificat de deces',
  neclasificat: 'Neclasificat (agentul decide)', unknown: 'Neclasificat', quarantined: 'Document în carantină',
};
const PRODUCT_LABEL = { 'CC-1': 'Cont curent', 'RO..CUR': 'Cont curent', 'DEP-1': 'Depozit la termen', 'CRD-1': 'Credit' };

// Etichete în română pentru codurile pe care le emite pipeline-ul (agent/pipeline.py); un cod necunoscut devine text citibil.
const ESC_LABEL = { unsupported_document: 'Tip de document necunoscut', missing_date_of_death: 'Lipsește data decesului',
  post_death_mandate_withdrawal: 'Retragere de către împuternicit după deces', policy_mismatch: 'Poliță care nu se potrivește',
  insurance_refused: 'Asigurătorul a refuzat', indemnity_mismatch: 'Indemnizație în afara intervalului din condiții',
  shares_invalid: 'Cote care nu însumează 1', minor_heir: 'Moștenitor minor', product_unknown: 'Produs necunoscut clientului',
  product_ambiguous: 'Produs fără IBAN, ambiguu', supplement_without_certificate: 'Supliment sosit înaintea certificatului de moștenitor',
  suspicious_document: 'Document suspect (posibilă manipulare)', unsafe_output: 'Text de agent oprit înainte de trimitere',
  document_deficient_institution: 'Document cu probleme de la o instituție', contact_no_channel: 'Moștenitor fără canal de contact',
  debt_exceeds_estate: 'Datoriile depășesc masa succesorală', document_illegible: 'Document ilizibil' };
// 076: motivele porții de siguranță (agent/guard.py), pe scurt; detaliul complet vine din API.
const GUARD_LABEL = { pdf_hidden_text: 'text ascuns în PDF', pdf_javascript: 'JavaScript în PDF', pdf_openaction: 'acțiune la deschiderea PDF-ului',
  pdf_launch: 'PDF care pornește un program', pdf_embedded_file: 'fișier atașat în PDF', pdf_auto_action: 'acțiuni automate în PDF',
  pdf_xfa: 'formular XFA', pdf_encrypted: 'PDF criptat', pdf_malformed: 'PDF corupt', type_mismatch: 'tipul real ≠ extensia',
  dangerous_type: 'fișier executabil / arhivă', too_large: 'fișier prea mare', too_many_pages: 'prea multe pagini',
  ignore_instructions: '„ignoră instrucțiunile”', role_override: 'schimbă rolul modelului', system_prompt: 'invocă promptul de sistem',
  chat_template: 'jetoane de conversație (<|im_start|>)', instructions_heading: 'titlu „### instrucțiuni”', role_spoof: 'rol falsificat (SYSTEM:)',
  answer_only: '„răspunde doar cu”', set_confidence: 'fixează scorul de încredere', set_field: 'dictează un câmp',
  approve_payment: 'cere aprobarea plății', send_money: 'cere trimiterea banilor', iban_change: 'cere schimbarea IBAN-ului',
  model_addressed: 'se adresează modelului', urgent_pressure: 'presiune de timp pe o plată', invisible_chars: 'caractere invizibile',
  bidi_override: 'inversare bidi', html_comment: 'comentariu HTML ascuns', html_hidden: 'HTML ascuns', html_active: 'HTML activ (script)',
  markdown_hidden: 'Markdown ascuns', base64_block: 'bloc base64', url_call_to_action: 'îndemn la un link', url_dangerous: 'link periculos',
  unexpected_field: 'câmp în afara schemei', forged_guard: 'verdict de siguranță falsificat', injection_suspected: 'extractorul a văzut instrucțiuni',
  json_invalid: 'JSON invalid', output_url: 'link străin', output_iban: 'IBAN care nu e în dosar', output_cnp: 'CNP străin',
  output_transfer: 'instrucțiuni de transfer', output_injection: 'instrucțiune injectată' };
const guardFlags = (flags) => (flags || []).length ? h('ul', { class: 'guard-flags small' }, flags.map((f) => h('li', {},
  h('strong', {}, human(GUARD_LABEL, f.code)), ': ', f.detail || '', f.evidence ? h('span', { class: 'evidence muted' }, ' — „', f.evidence, '”') : null))) : null;
const suspectBadge = (doc) => doc.quarantined ? badge('Suspect · carantină', 'bad')
  : doc.guard?.risk === 'high' ? badge('Suspect', 'bad') : doc.guard?.risk === 'medium' ? badge('Suspect (informativ)', 'warn') : '';
const FLAG_LABEL = { pension: 'pensie necuvenită', fee_to_reverse: 'comision de stornat', post_death_credit: 'încasare după deces',
  pension_return_CNPP: 'pensie de returnat la CNPP', post_death_withdrawal: 'retragere după deces' };
const human = (map, code) => map[code] || String(code).replace(/_/g, ' ');
// textul jurnalului, pentru om: tipurile de document în română, fără căi de fișier și fără rolul tehnic (ops_approver)
const DOC_RE = /\b(dgep_signal|notary_request|insurance_certificate|heir_certificate|insurer_response|supplementary_certificate|death_certificate)\b/g;
// coduri interne care ajung în texte (temeiuri, motive, canale): spuse omenește
const CODE_LABEL = { posta_recomandata: 'poștă recomandată', field_missing: 'câmp lipsă', certificate_incomplete: 'certificat incomplet',
  fees_to_reverse: 'comisioane de stornat', 'rules.fees_to_reverse': 'regula comisioanelor de stornat', document_illegible: 'document ilizibil',
  document_deficient_institution: 'document cu probleme de la o instituție', contact_no_channel: 'fără canal de contact',
  debt_exceeds_estate: 'datoriile depășesc masa succesorală' };
const CODE_RE = new RegExp(`\\b(${Object.keys(CODE_LABEL).map((k) => k.replace('.', '\\.')).join('|')})\\b`, 'g');
const cleanText = (t) => String(t || '').replace(/ \([^()]*\.(?:pdf|json|md|txt|png|jpe?g)\)/gi, '')
  .replace(/„[^”]*\.(?:pdf|json|md|txt|png|jpe?g)”/gi, '')
  .replace(/tip=(\w+)/g, (m, k) => `tip: ${(DOC_TYPES[k] || k).toLowerCase()}`)
  .replace(/încredere=([0-9.]+)/g, (m, x) => `încredere ${Math.round(Number(x) * 100)}%`).replace(/CNP=/g, 'CNP: ')
  .replace(CODE_RE, (k) => CODE_LABEL[k]).replace(DOC_RE, (k) => DOC_TYPES[k] || k)
  .replace(/ ?\(ops_approver\)/g, '').replace(/\bops_approver\b/g, 'aprobator').replace(/ {2,}/g, ' ');
// textele din lista de lucru (GET /worklist) poartă codul escaladării cu spații („document deficient institution”): în română
const decText = (t) => String(t || '').replace(/^Aprobă planul de plată \(0,00 lei\)$/, 'Confirmă: nimic de plătit (datoriile depășesc masa)').replace(/^(Escaladare|Document fără client): (.+)$/, (m, k, code) => {
  const key = code.trim().replace(/ /g, '_');
  return `${k}: ${(ESC_LABEL[key] || CODE_LABEL[key] || code).replace(/^./, (x) => x.toLowerCase())}`;
});
const productLabel = (c, id) => (c?.products || []).find((p) => p.id === id)?.label || PRODUCT_LABEL[id] || id;

// Contorul de timp: fiecare pas de mai jos înlocuiește o interacțiune manuală în back-office (business-case.md:
// 3–6 interacțiuni × 30–60 min / dosar). Ipoteza afișată: 30 min / interacțiune evitată, 5 min de om / decizie.
const MANUAL_MIN = 30;
const HUMAN_DECISION_MIN = 5;
const AVOIDED = [
  ['freeze', 'Blocare conturi, mandate, carduri', /blocare|freeze/i],
  ['fees', 'Stornare comisioane după deces', /stornare|stornate/i],
  ['notary', 'Răspuns către notar', /răspuns către notar|raspuns catre notar/i],
  ['claim', 'Dosar de daună la asigurător', /dosar de daună|dosar de dauna/i],
  ['shares', 'Calcul cote moștenitori', /cote extrase|certificat de moștenitor:|împărțire pe moștenitori/i],
  ['plan', 'Plan de plată', /plan de plată generat|instrucțiune de plată/i],
];

const ui = { ok: false, selected: null, tab: 'timeline', dchip: 'toate', dcase: null, row: null, focus: null, view: 'demo', threshold: 0.8, filter: null, q: '', work: null, lastCases: [], lastUnmatched: [] };

// ---------- utilitare ----------
const $ = (s) => document.querySelector(s);
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'class') el.className = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : String(kid));
  return el;
}
const fmtMoney = (bani) => bani == null ? '—'
  : (bani / 100).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' lei';
const fmtNum = (n, d = 0) => n.toLocaleString('ro-RO', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtDate = (s) => {
  if (!s) return '—';
  const [y, m, d] = String(s).slice(0, 10).split('-');
  return `${d}.${m}.${y}` + (String(s).length > 10 ? ' ' + String(s).slice(11, 16) : '');
};
const fmtDuration = (min) => min >= 60 ? `${fmtNum(Math.floor(min / 60))} h ${String(Math.round(min % 60)).padStart(2, '0')} min` : `${fmtNum(min)} min`;
const badge = (text, tone) => h('span', { class: 'badge ' + (tone || '') }, text);
const stateBadge = (s) => badge(STATE_LABEL[s] || s, STATE_TONE[s] || 'info');
const clone = (x) => JSON.parse(JSON.stringify(x));
const missingOf = (c) => c.missing || c.open_tasks || [];
const openEsc = (c) => c.open_escalations > 0 || (c.escalations || []).some((e) => (e.status || 'deschis') !== 'închis');
const waitingDocs = (c) => missingOf(c).filter((t) => !/^(aprobare|semnare)/i.test(t)); // aprobarea/semnarea sunt sarcini ale omului, nu documente care lipsesc
const plural = (n, one, few, many) => (n === 1 ? one : n === 0 || (n % 100 >= 1 && n % 100 < 20) ? few : many); // 0 apeluri, 5 apeluri, 25 de apeluri
// „în 5 zile” / „întârziat 2 zile” față de azi; null pentru termenele deja îndeplinite.
function relDays(date, status) {
  if (!date || status === 'îndeplinit') return null;
  const d = Math.round((Date.parse(String(date).slice(0, 10)) - Date.parse(new Date().toISOString().slice(0, 10))) / 864e5);
  if (Number.isNaN(d)) return null;
  const z = (n) => `${fmtNum(n)} ${plural(n, 'zi', 'zile', 'de zile')}`;
  return d === 0 ? { text: 'astăzi', late: false } : d > 0 ? { text: `în ${z(d)}`, late: false } : { text: `întârziat ${z(-d)}`, late: true };
}
function lsGet(k) { try { return localStorage.getItem('succesiuni.' + k) || ''; } catch { return ''; } }
function lsSet(k, v) { try { localStorage.setItem('succesiuni.' + k, v); } catch { /* browser fără storage: nu e grav */ } }
function conf(c) {
  if (c == null) return h('span', { class: 'muted' }, '—');
  const cls = c < ui.threshold ? 'low' : c < 0.9 ? 'mid' : '';
  return h('span', { class: 'conf ' + cls, title: `prag de escaladare ${ui.threshold}` },
    h('span', { class: 'bar' }, h('i', { style: `width:${Math.round(c * 100)}%` })), Number(c).toFixed(2));
}
function toast(msg, bad) {
  const t = $('#toast');
  t.textContent = msg; t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
  void t.offsetWidth; t.classList.add('in');
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 4000);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast('Copiat.'); } catch { toast('Copierea nu e permisă în acest browser.', true); }
}

// ---------- sursa de date: API real ----------
async function http(path, opts = {}) {
  const r = await fetch(API_BASE + path, opts);
  if (!r.ok) {
    const err = new Error(`${opts.method || 'GET'} ${path} → ${r.status} ${await r.text().catch(() => '')}`.trim());
    err.status = r.status;
    throw err;
  }
  return r.status === 204 ? null : r.json();
}
const json = (method, body, headers = {}) => ({ method, headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body ?? {}) });

const api = {
  listCases: async () => (await http('/cases')).filter((c) => c.kind !== 'unmatched'),
  getCase: (id) => http(`/cases/${encodeURIComponent(id)}`),
  listUnmatched: () => http('/escalations?unmatched=true'),
  uploadDocument: (id, file, type) => {
    const fd = new FormData();
    fd.append('file', file);
    if (type && type !== 'neclasificat') fd.append('document_type', type);
    return http(`/cases/${encodeURIComponent(id)}/documents`, { method: 'POST', body: fd });
  },
  approve: (pid, approver) => http(`/payments/${encodeURIComponent(pid)}/approve`, json('POST', { approver: approver || APPROVER_ROLE }, { 'X-Role': APPROVER_ROLE })),
  reject: (pid, reason) => http(`/payments/${encodeURIComponent(pid)}/reject`, json('POST', { reason }, { 'X-Role': APPROVER_ROLE })),
  resolveEscalation: (caseId, escId, note) => http(`/escalations/${encodeURIComponent(caseId)}/${encodeURIComponent(escId)}/resolve`, json('POST', { note })),
  signNotaryAnswer: (caseId, signer) => http(`/cases/${encodeURIComponent(caseId)}/letters/notary/sign`, json('POST', { signer })),
  listMessages: (caseId) => http(`/messages?case_id=${encodeURIComponent(caseId)}`),
  sendMessage: (msg) => http('/messages', json('POST', msg)),
  uploadToken: (caseId, to) => http(`/cases/${encodeURIComponent(caseId)}/upload-token`, json('POST', { to })),
  // GET /cases/{id}/artifacts vine din 040 (Ștefan); până atunci arătăm doar mesajele din outbox.
  artifacts: async (caseId) => {
    try {
      const r = await http(`/cases/${encodeURIComponent(caseId)}/artifacts`);
      if (r.letters || r.messages || r.investigations) return { ...r, source: 'api' }; // forma din contractul UI, dacă o dă serverul
      // forma reală a lui agent/api.py: {artifacts: [{kind, file, content, modified_at}], audit}
      const by = (kind) => (r.artifacts || []).filter((a) => a.kind === kind).map((a) => ({
        title: /^# (.+)$/m.exec(a.content || '')?.[1] || a.file.split('/').pop().replace(/\.md$/, ''), at: a.modified_at,
        content: (a.content || '').replace(/^<!--.*?-->\s*/s, '') }));
      return { letters: by('letter'), messages: by('message'), investigations: by('investigation'), audit: r.audit, source: 'api' };
    } catch (e) {
      if (e.status !== 404) throw e;
      return { messages: await api.listMessages(caseId), letters: [], investigations: [], audit: null, source: 'fallback' };
    }
  },
  audit: () => http('/audit'),
  contactPlan: (caseId) => http(`/cases/${encodeURIComponent(caseId)}/contact-plan`),
  advanceClock: (days) => http(`/demo/advance-clock?days=${days}`, { method: 'POST' }),
  worklist: (filtru, q) => http(`/worklist?filtru=${encodeURIComponent(filtru)}&q=${encodeURIComponent(q)}`),
};

// ---------- calcule pe dosar ----------
// Interacțiuni manuale evitate (din evenimentele agentului) și timpul agentului (din trace: processed_at).
function savings(c) {
  const events = (c.events || []).filter((e) => (e.kind || 'action') !== 'decision' || /plan|cote|împărțire/i.test(e.action || e.detail || ''));
  const steps = AVOIDED.map(([key, label, re]) => ({ key, label,
    done: events.some((e) => re.test(`${e.action || ''} ${e.detail || ''}`)) })).filter((s) => s.done);
  // Timp agent: pentru fiecare document, intervalul dintre primul și ultimul eveniment pe care l-a declanșat (+1 s), fără
  // timpul de așteptare dintre documente și fără deciziile umane (care nu au document).
  const byDoc = {};
  (c.events || []).forEach((e) => {
    const t = Date.parse(e.processed_at || e.at);
    if (e.document_id && !Number.isNaN(t)) (byDoc[e.document_id] ||= []).push(t);
  });
  const agentSec = Object.values(byDoc).reduce((s, ts) => s + 1 + (Math.max(...ts) - Math.min(...ts)) / 1000, 0);
  const decisions = (c.payments || []).length + (c.escalations || []).length;
  return { steps, manualMin: steps.length * MANUAL_MIN, agentSec, humanMin: decisions * HUMAN_DECISION_MIN };
}

// ---------- pornire ----------
const VIEWS = ['demo', 'cases', 'agents', 'impact', 'results', 'home'];
const HASH_VIEW = { '#dosare': 'cases', '#agenti': 'agents', '#impact': 'impact', '#rezultate': 'results', '#acasa': 'home' };
async function init() {
  const q = new URLSearchParams(location.search);
  try { await http('/cases'); ui.ok = true; } catch { ui.ok = false; }
  renderConn();
  if (!ui.ok) { showOffline(); return; }
  startLive();            // live.js: sondează autopilotul (extractor + agenți), actualizează indicatorul din antet
  await refresh();
  // Dosare e ecranul principal (și fără hash); #dosare/<id> = dosarul complet; #demo/<id> = fluxul dosarului (demo-dosare.js)
  const fromHash = (/^#dosare\/([\w-]+)/.exec(location.hash) || [])[1];
  if (q.get('case') || fromHash) { showView('cases'); select(q.get('case') || fromHash); }
  else showView(VIEWS.includes(q.get('view')) ? q.get('view') : location.hash.startsWith('#demo') ? 'demo' : HASH_VIEW[location.hash] || 'cases');
}

// insigna apare doar când serverul nu răspunde („Conectat” nu mai e afișat)
function renderConn() {
  $('#mode-badge').replaceWith(ui.ok
    ? h('span', { id: 'mode-badge', hidden: true })
    : h('span', { id: 'mode-badge', class: 'badge bad', title: API_BASE }, 'Server indisponibil'));
}

function showOffline() {
  VIEWS.forEach((v) => { $('#view-' + (v === 'cases' ? 'cases' : v)).hidden = true; });
  $('#view-offline').hidden = false;
  $('#view-offline').replaceChildren(h('div', { class: 'card' }, h('h3', {}, 'Nu mă pot conecta la server'),
    h('p', {}, 'Adresa încercată: ', h('code', {}, API_BASE), '. Aplicația lucrează doar cu serverul real; nu are date de probă.'),
    h('p', { class: 'muted small' }, 'Pornește serverul (de exemplu ', h('code', {}, 'scripts/test-instance.sh start 8010'), ') și reîncarcă.'),
    h('button', { type: 'button', class: 'primary', onclick: () => location.reload() }, 'Reîncearcă')));
}

function showView(view) {
  ui.view = view;
  // fluxul unui dosar se deschide peste „Dosare” (nu are tab propriu): în el, „Dosare” rămâne tabul activ
  document.querySelectorAll('.nav-btn').forEach((b) => b.classList.toggle('active', b.dataset.view === (view === 'demo' ? 'cases' : view)));
  VIEWS.forEach((v) => { $('#view-' + v).hidden = v !== view; });
  const shown = $('#view-' + view);   // intrarea ecranului: animația pornește din nou la fiecare schimbare de tab
  shown.classList.remove('view-enter'); void shown.offsetWidth; shown.classList.add('view-enter');
  clearTimeout(showView.t); showView.t = setTimeout(() => shown.classList.remove('view-enter'), 1000);   // reîmprospătările nu o mai reiau
  if (view === 'impact') renderImpact();
  if (view === 'agents') renderAgents();
  if (view === 'results' && window.renderResults) renderResults();
  if (view === 'demo') renderDemo();
  if (view === 'home' && window.renderHome) renderHome();
  if (typeof demoHash === 'function') demoHash();   // #demo/<dosar> doar pe tabul Demo ghidat
}

// ---------- lista de lucru (084): GET /worklist — fiecare dosar al băncii, ce urmează, termenul, deciziile umane ----------
async function refresh() {
  let cases = [], unmatched = [], work = null;
  try {
    [cases, unmatched, work] = await Promise.all([api.listCases(), api.listUnmatched(),
      api.worklist(ui.filter || 'toate', ui.q || '')]);
  } catch (e) { toast(e.message, true); }
  ui.lastCases = cases; ui.lastUnmatched = unmatched; ui.work = work;
  renderDecisionsPill(work);
  renderTodo(work);
  renderQueue(work);
  renderUnmatched(unmatched);
  if (ui.view === 'impact') renderImpact();
}

// Contorul din antet: câte decizii umane așteaptă în toată banca (plăți, semnături, escaladări, pași ai operatorului).
function renderDecisionsPill(work) {
  const pill = $('#decisions-pill');
  if (!pill || !work) return;
  const n = work.decisions_waiting;
  const text = n ? `${fmtNum(n)} ${plural(n, 'decizie te așteaptă', 'decizii te așteaptă', 'de decizii te așteaptă')}` : 'Nicio decizie nu te așteaptă';
  pill.hidden = false;
  pill.className = 'dec-counter' + (n ? '' : ' zero');   // în stilul antetului (buton rotund), nu pastilele scoase din antet
  pill.title = `${text}: clic pentru listă`;
  pill.setAttribute('aria-label', `${text}. Deschide lista`);
  pill.setAttribute('aria-haspopup', 'menu');
  pill.replaceChildren(svgIcon('hand'), h('span', { class: 'dc-n' }, fmtNum(n)), h('span', { class: 'dc-l small' }, plural(n, 'decizie', 'decizii', 'de decizii')));
}

// Filtrele rapide: câte un buton cu numărul de dosare din categorie; „Toate” le arată pe toate.
function renderTodo(work) {
  if (!work) { $('#todo').replaceChildren(); return; }
  const active = ui.filter || 'toate';
  $('#todo').replaceChildren(h('div', { class: 'wl-chips', role: 'group', 'aria-label': 'Filtre' }, work.filters.map((f) =>
    h('button', { type: 'button', class: 'wl-chip' + (active === f.key ? ' on' : '') + (f.count && f.key !== 'toate' ? ' has' : ''),
      'aria-pressed': String(active === f.key), onclick: () => { ui.filter = f.key === 'toate' ? null : f.key; refresh(); } },
      f.label, h('span', { class: 'n' }, fmtNum(f.count))))));
}

function termCell(t) {
  if (!t) return h('span', { class: 'muted' }, '—');
  const d = t.days, z = (n) => `${fmtNum(n)} ${plural(n, 'zi', 'zile', 'de zile')}`;
  const rel = d === 0 ? 'astăzi' : d > 0 ? `în ${z(d)}` : `întârziat ${z(-d)}`;
  return [h('div', {}, fmtDate(t.date), ' ', h('span', { class: 'rel ' + (d < 0 ? 'late' : d <= 7 ? 'soon' : '') }, rel)),
    h('div', { class: 'muted small' }, t.name)];
}

const DEC_ACTION = { plata: 'Aprobă plata', semnatura: 'Semnează răspunsul', escaladare: 'Rezolvă escaladarea', scara: 'Pasul de contact' };
function renderQueue(work) {
  const box = $('#queue');
  let rows = work?.rows || [];
  // dosarul demo al Mariei, înainte de primul document: un rând fix sus, ca demo-ul ghidat să pornească tot din listă
  const q = (ui.q || '').toLowerCase();
  if (work && !ui.filter && !rows.some((r) => r.case_id === DEMO_CASE) && (!q || 'maria ionescu sc-2026-0001 2xxxxxxxxxxxx'.includes(q))) {
    rows = [{ case_id: DEMO_CASE, kind: 'case', name: 'Maria Ionescu', state: 'NEW', fixed: true, state_label: 'Demo ghidat · de la zero',
      next: { text: 'Primul document: semnalul DGEP (6 pași, pas cu pas)' }, deadline: null, decisions_count: 0, decisions: [] }, ...rows];
  }
  const total = work?.filters?.[0]?.count || 0;
  const shown = rows.filter((r) => !r.fixed).length;
  $('#queue-count').textContent = total ? `${shown === total ? '' : shown + ' din '}${total} ${plural(total, 'dosar', 'dosare', 'de dosare')}` : '';
  if (!rows.length) {
    box.replaceChildren(h('p', { class: 'muted small' }, total ? 'Niciun dosar în această categorie.'
      : 'Banca nu are niciun dosar încă. Un dosar apare la primul document (de exemplu din „Demo ghidat”).'));
    return;
  }
  const open = (r) => {
    if (r.kind !== 'unmatched') return openInDemo(r.case_id);   // dosarul se deschide în Demo ghidat, la etapa unde e oprit
    const u = ui.lastUnmatched.find((x) => x.status !== 'închis') || ui.lastUnmatched[0];   // documentele fără client
    if (u) selectUnmatched(u);
  };
  // un rând curat pe dosar: cine, unde e (etapa), ce urmează, termenul, câte decizii te așteaptă
  box.replaceChildren(h('div', { class: 'wl-head', 'aria-hidden': 'true' }, ['Dosar', 'Etapa', 'Ce urmează', 'Termen', 'Decizii', ''].map((t) => h('span', {}, t))),
    h('ul', { class: 'wl-rows', role: 'list' }, rows.map((r, i) => {
    const tone = r.kind === 'unmatched' ? (r.open_escalations ? 'bad' : 'ok') : STATE_TONE[r.state] || 'info';
    const t = r.deadline;
    return h('li', { class: 'wl-row' + (r.case_id === ui.selected ? ' active' : '') + (r.decisions_count ? ' has-dec' : ''), tabindex: 0, role: 'button',
      style: `--i:${Math.min(i, 20)}`,
      'data-case': r.case_id, 'aria-label': `${r.name}, ${r.state_label}, ${r.next.text}`,
      onclick: () => open(r), onkeydown: (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(r); } } },
      h('div', { class: 'wl-who' }, h('span', { class: 'wl-av', 'aria-hidden': 'true' }, (r.name || '?').split(/\s+/).map((w) => w[0]).slice(0, 2).join('')),
        h('div', {}, h('b', {}, r.name), h('div', { class: 'muted small' }, r.kind === 'unmatched' ? 'documente fără client' : r.case_id,
          r.date_of_death ? ` · deces ${fmtDate(r.date_of_death)}` : ''))),
      h('div', { class: 'wl-stage' }, badge(r.state_label, tone), r.kind !== 'unmatched' && r.open_escalations ? badge('escaladare', 'bad') : null),
      h('div', { class: 'wl-next small' }, h('div', {}, decText(r.next.text)),
        r.next.due ? h('div', { class: 'muted' }, fmtDate(r.next.due), r.next.status ? ` · ${r.next.status}` : '') : null),
      h('div', { class: 'wl-term small' }, t ? [h('span', { class: 'rel ' + (t.days < 0 ? 'late' : t.days <= 7 ? 'soon' : '') }, fmtDate(t.date)),
        h('div', { class: 'muted' }, t.name)] : h('span', { class: 'muted' }, 'fără termen deschis')),
      h('div', { class: 'wl-dec' }, r.decisions_count ? h('span', { class: 'wl-dec-n', title: r.decisions.map((d) => decText(d.text)).join('\n') },
        fmtNum(r.decisions_count), h('span', { class: 'sr' }, ` ${plural(r.decisions_count, 'decizie', 'decizii', 'de decizii')}`)) : h('span', { class: 'wl-dec-0', title: 'nicio decizie' }, '✓')),
      // acțiunea rândului: decizia care așteaptă (dacă are), altfel fluxul dosarului; ambele deschid #demo/<dosar>
      h('div', { class: 'wl-act' }, h('span', { class: 'wl-go' + (r.decisions_count ? ' dec' : ''), 'aria-hidden': 'true' },
        r.kind === 'unmatched' ? 'Verifică →' : r.decisions_count ? `${r.decisions[0].kind === 'plata' && /\(0,00 lei\)/.test(r.decisions[0].text) ? 'Confirmă: nimic de plătit'
          : DEC_ACTION[r.decisions[0].kind] || 'Decide'} →` : 'Deschide fluxul →')));
  })));
}

// Lista de lucru pe toată lățimea; un dosar deschis o înlocuiește, cu „← Lista de lucru” deasupra.
function setCasesMode(mode) {
  const m = $('#view-cases');
  m.classList.toggle('list-mode', mode === 'list');
  m.classList.toggle('case-mode', mode === 'case');
}
function backToList() {
  ui.selected = null;
  ui.unmatched = false;
  setCasesMode('list');
  if (typeof demoHash === 'function' && ui.view === 'cases') demoHash();
  $('#detail').replaceChildren(h('div', { class: 'card empty' }, 'Alege un dosar din listă.'));
  refresh();
}

function renderUnmatched(list) {
  const box = $('#unmatched');
  if (!list.length) { box.replaceChildren(h('p', { class: 'muted small' }, 'Nimic de revizuit.')); return; }
  box.replaceChildren(...list.map((u) => h('button', {
    type: 'button', class: 'qitem' + (ui.selected === u.escalation_id ? ' active' : ''), onclick: () => selectUnmatched(u) },
    h('div', {}, badge(u.status === 'închis' ? 'rezolvată' : 'escaladat', u.status === 'închis' ? 'ok' : 'bad'), ' ',
      h('strong', {}, DOC_TYPES[u.document_type] || u.document_type)),
    h('div', { class: 'muted small' }, u.escalation_id, ' · primit ', fmtDate(u.received_at)),
    h('div', { class: 'small' }, cleanText(u.reason)))));
}

// ---------- detaliul dosarului ----------
async function select(id) {
  if (id === 'SC-NEIDENTIFICAT') {   // documentele fără client: prima escaladare deschisă
    const list = ui.lastUnmatched.length ? ui.lastUnmatched : await api.listUnmatched().catch(() => []);
    const u = list.find((x) => x.status !== 'închis') || list[0];
    if (u) return selectUnmatched(u);
  }
  ui.unmatched = false;
  ui.selected = id;
  setCasesMode('case');
  if (typeof demoHash === 'function' && ui.view === 'cases') demoHash();   // #dosare/<id>: înapoi / reîncărcarea păstrează dosarul
  try {
    const [c, wl] = await Promise.all([api.getCase(id), http(`/worklist?q=${encodeURIComponent(id)}`).catch(() => null)]);
    ui.row = (wl?.rows || []).find((r) => r.case_id === id) || null;
    renderCase(c);
  } catch (e) {
    $('#detail').replaceChildren(h('div', { class: 'card' }, h('h3', {}, 'Eroare'), h('p', {}, e.message)));
  }
  refresh();
}

function caseHeader(c, row) {
  const d = c.deceased || {};
  const t = row?.deadline;
  const docs = (c.documents || []).length, heirs = (c.heirs || []).length, prods = (c.products || []).length;
  const planTotal = (c.payments || [])[0]?.total ?? (c.payment_plan?.lines || []).reduce((x, l) => x + (l.blocked_reason ? 0 : l.amount), 0);
  const figs = [`${fmtNum(docs)} ${plural(docs, 'document', 'documente', 'de documente')}`,
    heirs ? `${fmtNum(heirs)} ${plural(heirs, 'moștenitor', 'moștenitori', 'de moștenitori')}` : null,
    prods ? `${fmtNum(prods)} ${plural(prods, 'produs', 'produse', 'de produse')}` : null,
    c.payment_plan ? `plan de plată ${fmtMoney(planTotal)}` : null].filter(Boolean);
  return h('section', { class: 'card case-top' },
    h('div', { class: 'case-top-main' },
      h('div', { class: 'case-kicker' }, 'Dosar de succesiune · ', c.case_id),
      h('h2', { class: 'case-name' }, d.name || c.cif, ' ', stateBadge(c.state)),
      h('p', { class: 'case-facts' },
        h('span', {}, 'Deces ', h('b', {}, fmtDate(d.date_of_death))),
        d.cnp ? h('span', {}, 'CNP ', d.cnp) : null,
        t ? h('span', { class: t.days < 0 ? 'late' : t.days <= 7 ? 'soon' : '' }, `${t.name}: `, h('b', {}, fmtDate(t.date)),
          ` (${t.days === 0 ? 'astăzi' : t.days > 0 ? `în ${fmtNum(t.days)} ${plural(t.days, 'zi', 'zile', 'de zile')}` : 'depășit'})`) : null),
      h('p', { class: 'case-figs' }, figs.map((f, i) => [i ? h('span', { class: 'dot-sep', 'aria-hidden': 'true' }, '·') : null, h('span', {}, f)]))),
    h('button', { type: 'button', class: 'case-top-demo', title: 'Fluxul dosarului: pașii, agenții, deciziile', 'aria-label': 'Deschide fluxul dosarului', onclick: () => openInDemo(c.case_id) },
      svgIcon('signal', 'ico sm'), 'Deschide fluxul dosarului →'));
}

// parcursul pe etape, cu aspectul roadmap-ului din Demo ghidat (etapele din demo-dosare.js: pfStages); un clic deschide dosarul acolo
const RM_CHIP = { done: ['complet', 'done'], waits: ['Rândul tău', 'partial'], next: ['aici e oprit', 'partial'] };
function caseRoadmap(c, row) {
  if (typeof pfStages !== 'function') return null;
  const { list, stop } = pfStages(c, row);
  const total = list.length;
  const lastDone = list.reduce((a, s) => (s.state === 'done' || s.state === 'skip' ? s.i : a), -1);
  const to = lastDone <= 0 ? 0 : lastDone / (total - 1);
  const done = list.filter((s) => s.state === 'done').length, counted = list.filter((s) => s.state !== 'skip').length;
  return h('section', { class: 'card roadmap case-roadmap' },
    h('div', { class: 'rm-head' },
      h('div', {}, h('h3', {}, 'Parcursul dosarului'),
        h('p', { class: 'small muted' }, `${done} din ${counted} etape făcute`, stop ? ` · oprit la: ${stop.title}` : ' · toate etapele sunt făcute')),
      null),
    h('div', { class: 'rm-track', style: `--n:${total}` },
      h('div', { class: 'rm-line' }, h('div', { class: 'rm-fill', style: `width:${to * 100}%` })),
      h('ol', { class: 'rm-nodes' }, list.map((s) => {
        const icon = s.state === 'done' ? 'check' : s.state === 'locked' || s.state === 'skip' ? 'lock' : s.state === 'waits' ? 'hand' : s.icon;
        const chip = RM_CHIP[s.state];
        return h('li', { class: `rm-node ${s.state === 'skip' ? 'locked' : s.state}${stop && s.i === stop.i ? ' open' : ''}`, style: `--accent:${s.accent}` },
          h('button', { type: 'button', class: 'rm-dot', 'aria-label': `Etapa ${s.i + 1}: ${s.title}${chip ? ` (${chip[0]})` : ''}. Deschide fluxul dosarului`,
            onclick: () => openInDemo(c.case_id) }, svgIcon(icon), h('span', { class: 'rm-num' }, String(s.i + 1))),
          h('span', { class: 'rm-title' }, s.short),
          chip ? h('span', { class: `rm-chip ${chip[1]}` }, chip[0]) : null);
      }))));
}

// Detalii tehnice (restrânse implicit): timpul manual vs. agent și mașina de stări
function techCard(c) {
  const hist = new Set((c.state_history || []).map((x) => x.state));
  const s = savings(c);
  return h('div', { class: 'card' },
    h('div', { class: 'timer', title: `Ipoteză: ${MANUAL_MIN} min / interacțiune manuală evitată; ${HUMAN_DECISION_MIN} min / decizie umană` },
      h('div', { class: 't-head' }, 'Timp manual vs. agent'),
      h('div', {}, h('div', { class: 'muted small' }, `Manual estimat (${s.steps.length} × ${MANUAL_MIN} min)`), h('div', { class: 'big' }, fmtDuration(s.manualMin))),
      h('div', { class: 'row2' }, h('span', {}, 'Agent'), h('strong', {}, s.agentSec < 60 ? `${fmtNum(s.agentSec, 1)} s` : fmtDuration(s.agentSec / 60))),
      h('div', { class: 'row2' }, h('span', {}, 'Om (decizii)'), h('strong', {}, fmtDuration(s.humanMin))),
      h('div', { class: 'row2 small muted' }, s.steps.map((x) => x.label).join(' · ') || 'nicio interacțiune evitată încă')),
    h('p', { class: 'small muted', style: 'margin:12px 0 0' }, 'Mașina de stări a dosarului'),
    h('div', { class: 'steps' }, STATES.filter(([st]) => st !== 'ESCALATED').map(([st, l]) =>
      h('span', { class: st === c.state ? 'now' : hist.has(st) ? 'done' : '' }, l))));
}

// ---- „Ce ai de făcut”: acțiunile care așteaptă omul pe acest dosar, fiecare cu locul ei în pagină
// Sursa: deciziile din lista de lucru (GET /worklist: plată, semnătură, escaladare, scara de contact), cu rezervă din dosar.
function caseTodos(c, row) {
  const out = [];
  const pay = (c.payments || []).find((p) => p.status === 'pending_approval');
  if (pay) {
    const plan = c.payment_plan;
    const held = (plan?.lines || []).filter((l) => !(pay.line_ids || []).includes(l.line_id)).length;
    out.push({ kind: 'plata', icon: 'bank', tone: 'warn', cat: 'pay', zero: !pay.total,
      title: pay.total ? `Aprobă planul de plată: ${fmtMoney(pay.total)}` : 'Confirmă: nimic de plătit (datoriile depășesc masa)',
      detail: !pay.total ? 'Datoriile depășesc masa succesorală: nu pleacă niciun ban. Confirmi planul ca dosarul să meargă mai departe.'
        : `${(pay.line_ids || []).length} ${plural((pay.line_ids || []).length, 'linie', 'linii', 'de linii')} de plătit acum${held ? `; ${held} ${plural(held, 'rămâne blocată', 'rămân blocate', 'rămân blocate')}` : ''}. Banii pleacă doar cu aprobarea ta.`,
      where: 'Plată · planul de plată', sec: 'plan', el: '.approve-bar', pay });
  }
  const decs = row?.decisions || [];
  const signNeeded = decs.length ? decs.some((d) => d.kind === 'semnatura')
    : (c.deadlines || []).some((t) => t.code === 'notary_answer' && t.status !== 'îndeplinit') && (c.state_history || []).some((x) => x.state === 'NOTARY_ANSWERED');
  if (signNeeded) {
    const t = (c.deadlines || []).find((x) => x.code === 'notary_answer');
    const rel = t && relDays(t.date, t.status);
    out.push({ kind: 'semnatura', icon: 'notary', tone: 'warn', cat: 'corr', title: 'Semnează răspunsul către notar',
      detail: `Soldurile la data decesului sunt redactate de sistem; pleacă doar semnate de un om.${t ? ` Termen ${fmtDate(t.date)}${rel ? ` (${rel.text})` : ''}.` : ''}`,
      where: 'Termene · răspunsul către notar', sec: 'terms', el: '[data-sign]' });
  }
  for (const e of (c.escalations || []).filter((x) => (x.status || 'deschis') !== 'închis')) {
    out.push({ kind: 'escaladare', icon: 'fileAlert', tone: 'bad', cat: 'esc', title: `Rezolvă escaladarea: ${human(ESC_LABEL, e.code)}`,
      detail: cleanText(e.reason), where: 'Escaladări', sec: 'esc', el: `[data-esc="${e.id || e.escalation_id}"]` });
  }
  for (const d of decs.filter((x) => x.kind === 'scara')) {
    out.push({ kind: 'scara', icon: 'heirs', tone: 'info', cat: 'corr', title: d.text, detail: 'Pasul din scara de contact care e al operatorului.',
      where: 'Scrisori și mesaje · scara de contact', sec: 'letters', el: '[data-ladder]' });
  }
  return out;
}

// ce face sistemul singur, fără om (lista de lucru: „Ce urmează”; altfel ce lipsește)
function autoNext(c, row) {
  const n = row?.next;
  if (n && n.source && n.source !== 'decizie') return n.text + (n.due ? ` (${fmtDate(n.due)}${n.status ? ', ' + n.status : ''})` : '');
  const miss = waitingDocs(c);
  if (miss.length) return `Așteptăm ${miss[0]}${miss.length > 1 ? ` (și încă ${miss.length - 1})` : ''}; documentul intră singur în dosar când sosește.`;
  if (c.state === 'PAID' || c.state === 'CLOSED') return 'Dosarul e plătit; liniile blocate se eliberează la scadență sau la acord.';
  return 'Agentul așteaptă următorul document.';
}

function todoPanel(c, row) {
  const todos = caseTodos(c, row);
  const auto = autoNext(c, row);
  if (!todos.length) {
    return h('section', { class: 'card todo-panel empty-todo', id: 'todo-panel' },
      h('div', { class: 'tp-head' }, svgIcon('check', 'ico tp-ok'), h('div', {}, h('div', { class: 'tp-kicker' }, 'Ce ai de făcut'),
        h('h3', {}, 'Nimic de făcut acum'))),
      h('p', { class: 'tp-auto' }, h('b', {}, 'Urmează automat: '), auto));
  }
  const goBtn = (t) => h('button', { type: 'button', class: 'tp-go', onclick: () => goTo(t) }, 'Du-mă acolo ', h('span', { 'aria-hidden': 'true' }, '↓'));
  return h('section', { class: 'card todo-panel', id: 'todo-panel' },
    h('div', { class: 'tp-head' }, h('div', {}, h('div', { class: 'tp-kicker' }, 'Ce ai de făcut'),
      h('h3', {}, `${todos.length} ${plural(todos.length, 'acțiune te așteaptă', 'acțiuni te așteaptă', 'de acțiuni te așteaptă')} pe acest dosar`))),
    h('ol', { class: 'tp-list' }, todos.map((t, i) => h('li', { class: 'tp-item ' + t.tone, 'data-kind': t.kind },
      h('span', { class: 'tp-ico' }, svgIcon(t.icon), h('span', { class: 'tp-n' }, String(i + 1))),
      h('div', { class: 'tp-text' }, h('b', {}, t.title), t.detail ? h('div', { class: 'small' }, t.detail) : null,
        h('div', { class: 'tp-where small' }, 'Unde: ', h('span', {}, t.where))),
      h('div', { class: 'tp-acts' },
        t.pay ? h('button', { type: 'button', class: 'primary', onclick: async (ev) => {
          const who = await confirmApprove(c.payment_plan, t.pay);
          if (!who) return;
          ev.target.disabled = true;
          try { await api.approve(t.pay.payment_id, who); toast(`${t.pay.payment_id} aprobată de ${who}`); await select(c.case_id); }
          catch (e) { toast(e.message, true); ev.target.disabled = false; }
        } }, t.zero ? 'Confirmă…' : 'Aprobă…') : null,
        goBtn(t))))),
    h('p', { class: 'tp-auto small' }, h('b', {}, 'Între timp, automat: '), auto));
}

// ---- secțiunile dosarului, restrânse; filtrele (cipurile) aleg ce se vede
const DCHIPS = [['toate', 'Toate'], ['todo', 'De făcut de mine'], ['docs', 'Documente'], ['corr', 'Scrisori și mesaje'],
  ['pay', 'Plăți'], ['esc', 'Escaladări'], ['ai', 'Agenți AI']];
// ce intră în jurnal la fiecare filtru
const EV_CAT = {
  docs: (e) => e.kind === 'document' || /document|certificat|primit/i.test(e.detail || ''),
  corr: (e) => /scrisoare|mesaj|notar|scara de contact|avizare|cerere|reprezentant/i.test(`${e.action || ''} ${e.detail || ''}`),
  pay: (e) => /plat|plan de plată|indemniza|comision|storn|sold|credit/i.test(`${e.action || ''} ${e.detail || ''}`),
  esc: (e) => e.kind === 'escalation' || /escalad/i.test(e.detail || ''),
  ai: (e) => /generat|redactat|mesaj|scrisoare|investiga|încredere|extras/i.test(`${e.action || ''} ${e.detail || ''}`),
};
// tabul vechi (ui.tab, din Demo ghidat) → secțiunea la care se ajunge
const TAB_SEC = { timeline: 'journal', documents: 'docs', plan: 'plan', corr: 'letters', audit: 'esc' };
const SEC_ALIAS = { contact: 'letters', system: 'agents' };

function caseSections(c, todos) {
  const has = (k) => todos.some((t) => t.kind === k);
  const openEsc = (c.escalations || []).filter((e) => (e.status || 'deschis') !== 'închis').length;
  const pay = (c.payments || []).find((p) => p.status === 'pending_approval');
  const docs = c.documents || [];
  const probs = docs.reduce((n, d) => n + openProblems(d.problems), 0) + (c.deficiencies || []).filter((r) => r.status !== 'closed').length;
  const list = [
    { key: 'plan', title: 'Plată', icon: 'bank', cats: ['pay', ...(has('plata') ? ['todo'] : [])], todo: has('plata'),
      badge: pay ? ['de aprobat', 'warn'] : c.payment_plan ? [{ approved: 'aprobată', rejected: 'respinsă' }[c.payment_plan.status] || 'în lucru', c.payment_plan.status === 'rejected' ? 'bad' : 'ok'] : null,
      hint: c.payment_plan ? 'planul pe cote și produsele la data decesului' : 'planul nu există încă',
      build: () => [tabPlan(c), c.payment_plan ? generatedDocsList(c.case_id, { group: 'pay', title: 'Planul ca document' }) : null, productsCard(c)] },
    { key: 'esc', title: 'Escaladări', icon: 'fileAlert', cats: ['esc', ...(openEsc ? ['todo'] : [])], todo: !!openEsc,
      badge: openEsc ? [`${openEsc} ${plural(openEsc, 'deschisă', 'deschise', 'deschise')}`, 'bad'] : (c.escalations || []).length ? ['rezolvate', 'ok'] : null,
      hint: (c.escalations || []).length ? 'excepțiile pe care sistemul nu le decide singur' : 'niciuna', build: () => escalationsCard(c) },
    { key: 'terms', title: 'Termene', icon: 'lock', cats: ['corr', ...(has('semnatura') ? ['todo'] : [])], todo: has('semnatura'),
      badge: has('semnatura') ? ['de semnat', 'warn'] : null, hint: 'termenele legale ale dosarului', build: () => deadlinesCard(c.deadlines || [], c) },
    { key: 'docs', title: 'Documente', icon: 'notary', cats: ['docs'], badge: probs ? [`${probs} cu probleme`, 'bad'] : docs.length ? [`${docs.length} primite`, 'ok'] : null,
      hint: 'ce a citit extractorul din fiecare, cu dovada', build: () => tabDocuments(c) },
    { key: 'letters', title: 'Scrisori și mesaje', icon: 'filePlus', cats: ['corr', ...(has('scara') ? ['todo'] : [])], todo: has('scara'),
      badge: has('scara') ? ['pasul tău', 'warn'] : null, hint: 'scara de contact, scrisorile și mesajele, mesaj nou',
      build: () => [contactCard(c), generatedDocsList(c.case_id, { group: 'corr', title: 'Scrisori și mesaje generate', empty: 'Nicio scrisoare sau mesaj generat încă.' }),
        deficientCard(c), composerCard(c)] },
    { key: 'agents', title: 'Agenți AI', icon: 'signal', cats: ['ai'], hint: 'ce au făcut sistemul și agenții: investigații, auditul',
      build: () => [agentCard(c) || null, generatedDocsList(c.case_id, { group: 'ai', title: 'Investigații și rapoartele auditorului', empty: 'Nicio propunere a investigatorului și niciun raport al auditorului pentru acest dosar.' })] },
    { key: 'gen', title: 'Documente generate de bancă', icon: 'filePlus', cats: ['docs', 'corr', 'ai'],
      hint: 'tot ce au scris banca și agenții: previzualizează sau descarcă (PDF, text)', build: () => generatedDocsList(c.case_id) },
    { key: 'journal', title: 'Jurnal', icon: 'signal', cats: ['docs', 'corr', 'pay', 'esc', 'ai'], journal: true,
      hint: `${(c.events || []).length} intrări, fiecare cu regula aplicată`, build: () => tabTimeline(c, EV_CAT[ui.dchip]) },
    { key: 'tech', title: 'Detalii tehnice', icon: 'lock', cats: [], hint: 'pentru audit: deciziile umane, jurnalul băncii, mașina de stări, timpul',
      build: () => [humanDecisionsCard(c), bankJournalCard(c), techCard(c)] },
  ];
  const first = list.find((x) => x.todo);   // numai prima secțiune relevantă e deschisă
  list.forEach((x) => { x.open = x === first; });
  return list;
}

function sectionEl(s, c, show, forceOpen) {
  const body = h('div', { class: 'dsec-body' });
  let built = false;
  const build = () => {
    if (built) return;
    built = true;
    body.replaceChildren(...[].concat(s.build(c)).filter(Boolean));
    const h3 = body.querySelector(':scope > .card > h3:first-child, :scope > .grid2 > .card > h3:first-child');
    if (h3 && h3.textContent.trim() === s.title) h3.remove();   // „Termene” sub „Termene”: o dată
  };
  const el = h('details', { class: 'dsec', id: 'dsec-' + s.key, 'data-sec': s.key, hidden: !show },
    h('summary', {}, svgIcon(s.icon, 'ico dsec-ico'), h('span', { class: 'dsec-t' }, s.title),
      s.badge ? badge(s.badge[0], s.badge[1]) : null, s.hint ? h('span', { class: 'dsec-hint muted small' }, s.hint) : null),
    body);
  el.addEventListener('toggle', () => { if (el.open) build(); });   // conținutul (și cererile lui) se fac la prima deschidere
  if (show && (forceOpen || s.open)) { el.open = true; build(); }
  return el;
}

function chipBar(c, sections, todos) {
  const n = (k) => k === 'toate' ? (c.events || []).length : k === 'todo' ? todos.length : (c.events || []).filter(EV_CAT[k]).length;
  return h('div', { class: 'dchips wl-chips', role: 'group', 'aria-label': 'Filtre pe activitate' },
    h('span', { class: 'dchips-l small muted' }, 'Arată:'),
    DCHIPS.map(([k, l]) => h('button', { type: 'button', class: 'wl-chip' + (ui.dchip === k ? ' on' : '') + (k === 'todo' && todos.length ? ' has' : ''),
      'aria-pressed': String(ui.dchip === k), 'data-chip': k, title: k === 'toate' ? 'Toate secțiunile' : k === 'todo' ? 'Doar ce așteaptă o decizie a ta'
        : 'Secțiunile și intrările din jurnal de acest tip',
      onclick: () => { ui.dchip = k; renderCase(c); } }, l, h('span', { class: 'n' }, fmtNum(n(k))))));
}

function renderCase(c) {
  if (ui.dcase !== c.case_id) { ui.dcase = c.case_id; ui.dchip = 'toate'; }
  ui.caseNow = c;
  const row = ui.row?.case_id === c.case_id ? ui.row : null;
  const todos = caseTodos(c, row);
  ui.lastTodos = todos;
  const sections = caseSections(c, todos);
  const f = ui.dchip || 'toate';
  const shown = sections.map((s) => sectionEl(s, c, f === 'toate' || s.cats.includes(f), f !== 'toate'));
  const empty = shown.every((el) => el.hidden)
    ? h('p', { class: 'card muted' }, f === 'todo' ? 'Nimic de făcut de tine pe acest dosar acum.' : 'Nimic de acest tip în dosar.') : null;
  $('#detail').replaceChildren(...[caseHeader(c, row), todoPanel(c, row), caseRoadmap(c, row), chipBar(c, sections, todos), empty,
    h('div', { class: 'dsecs' }, shown)].filter(Boolean));
  const focus = ui.focus || (ui.tab && ui.tab !== 'timeline' ? TAB_SEC[ui.tab] : null);
  ui.focus = null; ui.tab = 'timeline';
  if (focus) setTimeout(() => goTo(typeof focus === 'string' ? { sec: focus } : focus), 60);
}

// „Du-mă acolo”: deschide secțiunea, derulează la locul exact și îl evidențiază scurt
function goTo(t) {
  if (t.sec === 'todo') {
    const p = document.getElementById('todo-panel');
    if (p) { p.scrollIntoView({ behavior: 'smooth', block: 'start' }); p.classList.add('flash'); setTimeout(() => p.classList.remove('flash'), 2600); }
    return;
  }
  if (t.kind) {   // o acțiune anume (din antet): ținta ei din „Ce ai de făcut”, dacă dosarul o mai are
    const todo = (ui.lastTodos || []).find((x) => x.kind === t.kind && (!t.match || x.title.toLowerCase().includes(t.match.toLowerCase()))) || (ui.lastTodos || []).find((x) => x.kind === t.kind);
    if (todo) t = todo; else return goTo({ sec: 'todo' });
  }
  const sec = document.getElementById('dsec-' + (SEC_ALIAS[t.sec] || t.sec));
  if (!sec) return;
  if (sec.hidden) {   // filtrul activ o ascunde: înapoi la „Toate”
    ui.dchip = 'toate';
    document.querySelectorAll('#detail .dchips .wl-chip').forEach((b) => { const on = b.dataset.chip === 'toate'; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
    document.querySelectorAll('#detail .dsec').forEach((d) => { d.hidden = false; });
  }
  if (!sec.open) sec.open = true;   // „toggle” construiește conținutul
  sec.dispatchEvent(new Event('toggle'));
  const find = (tries) => {
    const el = (t.el && sec.querySelector(t.el)) || sec;
    if (el === sec && t.el && tries > 0) { setTimeout(() => find(tries - 1), 150); return; }   // conținut încărcat asincron
    el.scrollIntoView({ behavior: 'smooth', block: el === sec ? 'start' : 'center' });
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
    setTimeout(() => el.classList.remove('flash'), 2600);
    el.querySelector?.('input:not([type=file]), button.primary')?.focus({ preventScroll: true });
  };
  find(6);
}

// Ce a făcut sistemul (cod determinist, nu un agent LLM) la ultimul document. API-ul nu pune document_id pe acțiuni, dar le ordonează: tot ce urmează după
// evenimentul „Primit:” al ultimului document îi aparține. Dacă acțiunile au document_id, se folosește el; altfel data documentului.
function lastDocWork(c) {
  const doc = (c.documents || []).at(-1), evs = c.events || [];
  if (!doc) return { doc: null, events: [] };
  const human_ = /operator|aprobat|respins|rezolvat/i; // deciziile omului nu sunt ale agentului
  const start = evs.findLastIndex((e) => e.kind === 'document' && e.document_id === doc.document_id);
  let mine = start >= 0 ? evs.slice((c.documents || []).length === 1 ? 0 : start) : evs.filter((e) => e.document_id === doc.document_id);
  if (!mine.length) mine = evs.filter((e) => String(e.at).slice(0, 10) === doc.received_at);
  return { doc, events: mine.filter((e) => !/^Primit:/.test(e.detail || '') && !(e.kind === 'decision' && human_.test(`${e.action} ${e.detail}`))) };
}

function agentCard(c) {
  const { doc, events } = lastDocWork(c);
  if (!doc) return null;
  const miss = waitingDocs(c);
  return h('div', { class: 'card agent' }, h('h3', {}, 'Ce a făcut sistemul (regulile băncii, cod) la ultimul document'),
    h('p', { class: 'small muted' }, 'La ultimul document: ', h('strong', {}, DOC_TYPES[doc.document_type] || doc.document_type), ', din ', fmtDate(doc.received_at), '.'),
    events.length ? h('ul', { class: 'did' }, events.map((e) => h('li', { class: 'k-' + (e.kind || 'action') },
      h('span', { class: 'tick', 'aria-hidden': 'true' }, e.kind === 'escalation' ? '!' : '✔'),
      h('div', {}, cleanText(e.detail || e.action), e.rule ? h('div', { class: 'small muted' }, 'Regula: ', e.rule) : null))))
      : h('p', { class: 'muted small' }, 'Nicio acțiune nouă a agentului la acest document.'),
    miss.length ? h('p', { class: 'small' }, h('strong', {}, 'Aștept: '), miss.join('; '), '.') : null);
}

// ---- Cronologie
function tabTimeline(c, only) {
  const all = [...(c.events || [])].reverse();
  const list = only ? all.filter(only) : all;
  return h('div', { class: 'card' }, h('h3', {}, 'Cronologie: acțiunile agentului și regula aplicată',
      only ? h('span', { class: 'muted small' }, ` · ${list.length} din ${all.length} (filtrat)`) : null),
    list.length ? h('ul', { class: 'timeline' }, list.map((e) => {
      const cite = `${fmtDate(e.at)} · ${e.action || e.kind}: ${cleanText(e.detail)} — Regula: ${e.rule || '—'}`;
      return h('li', { class: 'k-' + (e.kind || 'action') },
        h('div', {}, h('strong', {}, e.action || e.kind), e.amount != null ? ' · ' + fmtMoney(e.amount) : '',
          h('span', { class: 'muted small' }, ' · ', fmtDate(e.at)),
          e.data?.flag ? [' ', badge(human(FLAG_LABEL, e.data.flag), 'info')] : null),
        e.detail ? h('div', {}, cleanText(e.detail)) : null,
        e.rule ? h('div', { class: 'rule' }, h('strong', {}, 'Regula: '), e.rule, ' ',
          h('button', { type: 'button', class: 'link', title: 'Copiază pentru citare (dată · acțiune · regulă)', onclick: () => copyText(cite) }, 'citează')) : null,
        e.id ? docActionsFor(c.case_id, (d) => d.event_id === e.id) : null);   // documentul pe care l-a produs intrarea
    })) : h('p', { class: 'muted' }, 'Nicio acțiune încă.'));
}

// ---- Documente
function fieldValue(v, name) {
  if (v == null) return h('span', { class: 'muted' }, 'necitit');
  if (typeof v === 'boolean') return v ? 'da' : 'nu';
  if (typeof v === 'string' && VALUE_LABEL[v]) return h('span', { title: v }, VALUE_LABEL[v]);
  if (typeof v === 'number' && /suma|sold|indemniz|amount|_bani/i.test(name)) return fmtMoney(v);
  if (Array.isArray(v)) return v.map((x) => (typeof x === 'object' ? [x.name, x.share, x.minor ? '(minor)' : ''].filter(Boolean).join(' ') : x)).join('; ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

// ---- Markdown → DOM, pentru textele scrise de agenți (scrisori, mesaje, propuneri, audit). Construiește elementele cu h(),
// fără innerHTML: un text venit dintr-un document nu poate injecta HTML. Știe: titluri, paragrafe, **bold**, *italic*, `cod`,
// liste (- * 1.), tabele (| … |), citate (>), linii (---). Linkurile rămân text (nimic din bancă nu se deschide dintr-un draft).
function mdInline(text) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_|\[[^\]]+\]\([^)]+\))/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith('**') || t.startsWith('__')) out.push(h('strong', {}, ...mdInline(t.slice(2, -2))));
    else if (t.startsWith('`')) out.push(h('code', {}, t.slice(1, -1)));
    else if (t.startsWith('[')) { const [, label, href] = t.match(/^\[([^\]]+)\]\(([^)]+)\)$/); out.push(h('span', { class: 'md-link', title: href }, label)); }
    else out.push(h('em', {}, ...mdInline(t.slice(1, -1))));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

// o listă care începe la lines[i]; elementele mai indentate decât ea devin o sub-listă a elementului de deasupra
const LIST_ITEM = /^(\s*)([-*+]|\d+[.)])\s+/;
function mdList(lines, i) {
  const indent = lines[i].match(LIST_ITEM)[1].length;
  const list = h(/^\s*\d/.test(lines[i]) ? 'ol' : 'ul');
  let li = null;
  while (i < lines.length) {
    const m = lines[i].match(LIST_ITEM);
    if (m && m[1].length > indent && li) { const [sub, next] = mdList(lines, i); li.append(sub); i = next; continue; }
    if (m && m[1].length === indent) {
      let item = lines[i++].replace(LIST_ITEM, '');
      while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !LIST_ITEM.test(lines[i])) item += ' ' + lines[i++].trim();
      li = h('li', {}, ...mdInline(item));
      list.append(li);
      continue;
    }
    break;
  }
  return [list, i];
}

function mdRender(src) {
  const lines = stripMeta(src).replace(/\r/g, '').split('\n');
  const root = h('div', { class: 'md' });
  const cells = (l) => l.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)$/))) { root.append(h(`h${Math.min(m[1].length + 1, 5)}`, {}, ...mdInline(m[2]))); i++; continue; }
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { root.append(h('hr')); i++; continue; }
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
      const head = cells(line); i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(cells(lines[i++]));
      root.append(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, head.map((c) => h('th', {}, ...mdInline(c))))),
        h('tbody', {}, rows.map((r) => h('tr', {}, r.map((c) => h('td', { class: /^[−-]?[\d.]+(,\d+)?$/.test(c) ? 'num' : null }, ...mdInline(c)))))))));
      continue;
    }
    if (/^\s*>/.test(line)) {
      const q = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ''));
      root.append(h('blockquote', {}, mdRender(q.join('\n'))));
      continue;
    }
    if (LIST_ITEM.test(line)) {
      const [list, next] = mdList(lines, i);
      root.append(list);
      i = next;
      continue;
    }
    const para = [lines[i++]];   // linia curentă intră mereu (o linie „|…” fără tabel nu blochează bucla)
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*\||\s*>|\s*([-*+]|\d+[.)])\s+|\s*-{3,}\s*$)/.test(lines[i])) para.push(lines[i++]);
    root.append(h('p', {}, para.flatMap((l, k) => (k ? [h('br'), ...mdInline(l.trim())] : mdInline(l.trim())))));
  }
  return root;
}

// ---- previzualizare document (054): fișierul sursă, din GET /cases/{id}/documents/{doc}/preview (doar pe API)
function previewDocument(caseId, doc) {
  return previewFile(DOC_TYPES[doc.document_type] || doc.document_type, doc.source || doc.document_id,
    `${API_BASE}/cases/${encodeURIComponent(caseId)}/documents/${encodeURIComponent(doc.document_id)}/preview`);
}

// fereastra de previzualizare pentru orice fișier servit de API (PDF, imagine, text, JSON)
async function previewFile(title, label, url) {
  let blobUrl = null;
  const body = h('div', { class: 'preview-body' }, h('p', { class: 'muted' }, 'Se încarcă…'));
  const openTab = h('a', { class: 'btn', target: '_blank', rel: 'noopener', hidden: true }, 'Deschide într-o filă nouă');
  const onKey = (ev) => { if (ev.key === 'Escape') close(); };
  const close = () => { document.removeEventListener('keydown', onKey); if (blobUrl) URL.revokeObjectURL(blobUrl); overlay.remove(); };
  const overlay = h('div', { class: 'modal', onclick: (ev) => { if (ev.target === overlay) close(); } },
    h('div', { class: 'card modal-card wide', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Previzualizare document' },
      h('div', { class: 'preview-head' }, h('h3', {}, title), h('span', { class: 'muted small' }, label),
        openTab, h('button', { type: 'button', onclick: close }, 'Închide')),
      body));
  document.addEventListener('keydown', onKey);
  document.body.append(overlay);
  try {
    const r = await fetch(url);
    if (!r.ok) {
      const detail = (await r.json().catch(() => ({}))).detail;
      throw new Error(detail && detail !== 'Not Found' ? detail : 'Serverul nu știe încă să servească acest document: rulează o versiune mai veche și trebuie repornit (scripts/test-instance.sh start).');
    }
    const type = r.headers.get('content-type') || '';
    const isPdf = type.startsWith('application/pdf');
    let blob, view;
    if (isPdf) {
      blob = await r.blob();
      blobUrl = URL.createObjectURL(blob);
      view = h('iframe', { src: blobUrl, title: `${title}: ${label}` });
    } else if (type.startsWith('image/')) {   // scanare / fotografie
      blob = await r.blob();
      blobUrl = URL.createObjectURL(blob);
      view = h('img', { src: blobUrl, alt: `${title}: ${label}`, class: 'preview-img' });
    } else {
      let text = await r.text();
      if ((r.headers.get('content-type') || '').includes('json')) { try { text = JSON.stringify(JSON.parse(text), null, 2); } catch { /* rămâne textul brut */ } }
      blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      blobUrl = URL.createObjectURL(blob);
      view = h('pre', {}, text);
    }
    openTab.href = blobUrl; openTab.hidden = false;
    body.replaceChildren(view);
  } catch (e) {
    body.replaceChildren(h('p', {}, h('strong', {}, 'Nu pot afișa documentul. '), e.message));
  }
}

function docBlock(doc, open, caseId) {
  const low = (doc.fields || []).filter((f) => f.confidence != null && f.confidence < ui.threshold).length;
  return h('details', { class: 'doc', open },
    h('summary', {}, h('strong', {}, DOC_TYPES[doc.document_type] || doc.document_type),
      h('span', { class: 'muted small' }, 'primit ', fmtDate(doc.received_at)),
      doc.variant ? badge('varianta ' + doc.variant, 'info') : '',
      suspectBadge(doc),
      doc.legibility === 'illegible' && !doc.quarantined ? badge('ilizibil', 'bad') : '',
      doc.status ? badge(doc.status, 'warn') : '',
      low ? badge(`${low} câmpuri sub prag`, 'bad') : '',
      openProblems(doc.problems) ? badge(`${openProblems(doc.problems)} ${plural(openProblems(doc.problems), 'problemă', 'probleme', 'de probleme')}`, 'bad') : '',
      (doc.validation?.failed || []).map((f) => h('span', { class: 'badge ' + (f.severity === 'soft' ? 'warn' : 'bad'), title: f.code }, f.message || human({}, f.code))),
      (doc.validation?.flags || []).map((f) => h('span', { class: 'badge info', title: f }, human(FLAG_LABEL, f))),
      doc.validation?.passed?.length ? h('span', { class: 'badge ok', title: doc.validation.passed.join(', ') }, `✓ ${doc.validation.passed.length} verificări`) : '',
      h('span', { style: 'margin-left:auto' }, 'încredere ', conf(doc.confidence))),
    h('div', {}, (doc.guard?.flags || []).length ? h('div', { class: 'guard-box' },
        h('p', { class: 'small' }, h('strong', {}, doc.quarantined ? 'Document în carantină: ' : 'Semne de manipulare: '),
          doc.quarantined ? 'nu a produs nicio acțiune (blocare, scrisori, mesaje, plată). Verificați-l la sursă.'
            : 'documentul a fost procesat; verificați motivele de mai jos.'),
        guardFlags(doc.guard.flags)) : null,
      (doc.problems || []).length ? problemsBox(doc.problems, doc.sender) : null,
      caseId && hasOriginal(doc)
      ? h('div', { class: 'doc-actions' }, h('button', { type: 'button', onclick: () => previewDocument(caseId, doc) }, 'Previzualizează documentul')) : null,
      (doc.fields || []).length
      ? h('div', { class: 'table-wrap' }, h('table', {}, h('tr', {}, h('th', {}, 'Câmp'), h('th', {}, 'Valoare extrasă'), h('th', {}, 'Încredere'), h('th', {}, 'Dovadă din document')),
        doc.fields.filter((f) => !f.name.startsWith('_') && f.value != null && f.value !== '').map((f) => h('tr', {}, h('td', { class: 'muted' }, fieldLabel(f.name)), h('td', {}, fieldValue(f.value, f.name)),
          h('td', {}, conf(f.confidence)), h('td', { class: 'evidence small' }, f.evidence ? `„${f.evidence}”` : '')))))
      : h('p', { class: 'muted small' }, 'Fără câmpuri extrase încă.')));
}

// ---- Documentele dosarului: lista (tip, data, sursa, încrederea, suspect) și vizualizatorul mare (fișierul + ce s-a citit)
const DOC_SENDER = { dgep_signal: 'DGEP · lot electronic', notary_request: 'Notarul public', insurance_certificate: 'Dosarul creditului',
  heir_certificate: 'Notarul public', insurer_response: 'Asigurătorul', supplementary_certificate: 'Notarul public', death_certificate: 'Ghișeu / moștenitori' };
function docSource(d) {
  const src = String(d.source || '');
  const via = /^scan\//.test(src) ? 'scanare' : /upload|link/i.test(src) ? 'link de încărcare' : /^portofoliu\//.test(src) ? 'arhiva dosarului'
    : /\.json$/i.test(src) ? 'electronic' : src ? 'portal' : '';
  return [DOC_SENDER[d.document_type], via].filter(Boolean).join(' · ');
}
// originalul: API-ul nu spune dacă există, deci /preview se încearcă o singură dată pe document și rezultatul se ține minte
// (un 404 nu se mai cere din nou); fără sursă nu există fișier
const previewMissing = new Set();
const previewKey = (d) => `${d.document_id}|${d.source}`;
const hasOriginal = (d) => Boolean(d.source) && !previewMissing.has(previewKey(d));
const confBadge = (x) => x == null ? null : badge(`încredere ${Math.round(x * 100)}%`, x < ui.threshold ? 'bad' : x < 0.9 ? 'warn' : 'ok');

function docList(c) {
  const docs = c.documents || [];
  return h('ul', { class: 'doc-list' }, docs.map((d, i) => h('li', {},
    h('button', { type: 'button', class: 'doc-row', 'data-doc': d.document_id, onclick: () => docViewer(c, i) },
      svgIcon(d.quarantined || d.guard?.risk === 'high' ? 'fileAlert' : 'notary', 'ico doc-ico'),
      h('span', { class: 'doc-main' }, h('b', {}, DOC_TYPES[d.document_type] || d.document_type),
        h('span', { class: 'muted small' }, fmtDate(d.received_at), docSource(d) ? ` · ${docSource(d)}` : '')),
      h('span', { class: 'doc-badges' }, suspectBadge(d) || null, d.legibility === 'illegible' && !d.quarantined ? badge('ilizibil', 'bad') : null,
        openProblems(d.problems) ? badge(`${openProblems(d.problems)} ${plural(openProblems(d.problems), 'problemă', 'probleme', 'de probleme')}`, 'bad') : null,
        confBadge(d.confidence)),
      h('span', { class: 'doc-open', 'aria-hidden': 'true' }, 'Deschide →')))));
}

// Vizualizatorul: fișierul (PDF / scanare / text) în stânga, câmpurile citite în dreapta (valoare, încredere, dovada din text);
// Anterior / Următor (și ← →) trec prin documentele dosarului; Esc închide. Pe mobil ocupă tot ecranul.
function docViewer(c, start) {
  const docs = c.documents || [];
  let i = start, blobUrl = null;
  const file = h('div', { class: 'dv-file' });
  const side = h('div', { class: 'dv-side' });
  const title = h('h3', {});
  const pos = h('span', { class: 'muted small' });
  const openTab = h('a', { class: 'btn small', target: '_blank', rel: 'noopener', hidden: true }, 'Deschide într-o filă nouă');
  const prev = h('button', { type: 'button', onclick: () => go(-1), 'aria-label': 'Documentul anterior' }, '← Anterior');
  const next = h('button', { type: 'button', onclick: () => go(1), 'aria-label': 'Documentul următor' }, 'Următor →');
  const onKey = (ev) => {
    if (ev.key === 'Escape') close();
    else if (ev.key === 'ArrowLeft' && !ev.target.closest('input, textarea')) go(-1);
    else if (ev.key === 'ArrowRight' && !ev.target.closest('input, textarea')) go(1);
  };
  const close = () => { document.removeEventListener('keydown', onKey); if (blobUrl) URL.revokeObjectURL(blobUrl); overlay.remove(); };
  const overlay = h('div', { class: 'modal dv-modal', onclick: (ev) => { if (ev.target === overlay) close(); } },
    h('div', { class: 'card dv-card', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Vizualizator de documente' },
      h('div', { class: 'dv-head' }, h('div', { class: 'dv-title' }, title, pos),
        h('div', { class: 'dv-nav' }, prev, next, openTab, h('button', { type: 'button', class: 'dark', onclick: close }, 'Închide'))),
      h('div', { class: 'dv-body' }, file, side)));
  const go = (d) => { const j = i + d; if (j >= 0 && j < docs.length) { i = j; show(); } };
  async function show() {
    const doc = docs[i];
    title.textContent = DOC_TYPES[doc.document_type] || doc.document_type;
    pos.textContent = ` · ${i + 1} din ${docs.length} · primit ${fmtDate(doc.received_at)}${docSource(doc) ? ' · ' + docSource(doc) : ''}`;
    prev.disabled = i === 0; next.disabled = i === docs.length - 1;
    side.replaceChildren(docFieldsPane(doc));
    file.replaceChildren(h('p', { class: 'muted' }, h('span', { class: 'spinner' }), ' Se încarcă documentul…'));
    if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = null; }
    openTab.hidden = true;
    const want = i;
    try {
      if (!hasOriginal(doc)) throw Object.assign(new Error(), { status: 404 });
      const r = await fetch(`${API_BASE}/cases/${encodeURIComponent(c.case_id)}/documents/${encodeURIComponent(doc.document_id)}/preview`);
      if (want !== i) return;
      if (r.status === 404) previewMissing.add(previewKey(doc));
      if (!r.ok) throw Object.assign(new Error(), { status: r.status });
      const type = r.headers.get('content-type') || '';
      let view;
      if (type.startsWith('application/pdf') || type.startsWith('image/')) {
        blobUrl = URL.createObjectURL(await r.blob());
        view = type.startsWith('image/') ? h('img', { src: blobUrl, alt: title.textContent, class: 'preview-img' }) : h('iframe', { src: blobUrl, title: title.textContent });
      } else {
        let text = await r.text();
        if (type.includes('json')) { try { text = JSON.stringify(JSON.parse(text), null, 2); } catch { /* text brut */ } }
        blobUrl = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
        view = h('pre', {}, text);
      }
      if (want !== i) return;
      openTab.href = blobUrl; openTab.hidden = false;
      file.replaceChildren(view);
    } catch (e) {
      if (want !== i) return;
      file.replaceChildren(h('div', { class: 'dv-nofile' }, svgIcon('notary', 'ico dv-nofile-ico'),
        h('p', {}, h('b', {}, 'Originalul nu e păstrat în această instanță.')),
        h('p', { class: 'muted small' }, e.status === 404 ? 'Documentul a intrat direct (nu prin portal) sau e din arhiva dosarului. Ce a citit extractorul din el e în dreapta, cu dovada din text.'
          : `Nu pot încărca fișierul (${e.message || 'eroare'}).`)));
    }
  }
  document.addEventListener('keydown', onKey);
  document.body.append(overlay);
  show();
  next.focus();
}

// scorul unui câmp, în procente ca insigna documentului; fără scor pe câmp: câmpul structurat (lot electronic) e exact,
// altfel scorul documentului
const STRUCTURED = (doc) => doc.document_type === 'dgep_signal' || /\.json$/i.test(doc.source || '');
function fieldScore(f, doc) {
  if (f.confidence != null) return confBadge(f.confidence);
  if (STRUCTURED(doc)) return badge('câmp structurat, exact', 'ok');
  return doc.confidence != null ? h('span', { class: 'badge ' + (doc.confidence < ui.threshold ? 'bad' : doc.confidence < 0.9 ? 'warn' : 'ok'),
    title: 'Scorul documentului (extractorul nu a dat scor pe câmp)' }, `${Math.round(doc.confidence * 100)}% (document)`) : null;
}
function docFieldsPane(doc) {
  const all = (doc.fields || []).filter((f) => !f.name.startsWith('_') && f.value != null && f.value !== '');
  // „Număr de înregistrare” și „Număr document” cu aceeași valoare: o singură dată
  const ref = all.find((f) => f.name === 'reference');
  const fields = all.filter((f) => !(f.name === 'document_number' && ref && String(ref.value) === String(f.value)));
  const low = fields.filter((f) => f.confidence != null && f.confidence < ui.threshold).length;
  return h('div', {},
    h('div', { class: 'dv-badges' }, confBadge(doc.confidence), suspectBadge(doc) || null,
      doc.legibility === 'illegible' && !doc.quarantined ? badge('ilizibil', 'bad') : null,
      low ? badge(`${low} ${plural(low, 'câmp', 'câmpuri', 'de câmpuri')} sub prag`, 'bad') : null,
      doc.validation?.passed?.length ? h('span', { class: 'badge ok', title: doc.validation.passed.join(', ') }, `✓ ${doc.validation.passed.length} verificări`) : null),
    (doc.guard?.flags || []).length ? h('div', { class: 'guard-box' }, h('p', { class: 'small' }, h('strong', {}, doc.quarantined ? 'În carantină: ' : 'Semne de manipulare: '),
      doc.quarantined ? 'nu a produs nicio acțiune.' : 'documentul a fost procesat; verificați motivele.'), guardFlags(doc.guard.flags)) : null,
    (doc.problems || []).length ? problemsBox(doc.problems, doc.sender) : null,
    h('h4', { class: 'dv-h' }, 'Ce a citit extractorul'),
    fields.length ? h('dl', { class: 'dv-fields' }, fields.flatMap((f) => [
      h('dt', {}, fieldLabel(f.name), ' ', fieldScore(f, doc)),
      h('dd', {}, h('div', { class: 'dv-val' }, fieldValue(f.value, f.name)), f.evidence ? h('div', { class: 'evidence small' }, `„${f.evidence}”`) : null)]))
      : h('p', { class: 'muted small' }, 'Fără câmpuri extrase.'));
}

function tabDocuments(c) {
  const docs = c.documents || [];
  const ids = new Set(docs.map((d) => d.document_id));
  // 078: trimise pentru acest dosar (link de încărcare), dar neatașate: ilizibile, alt CNP, carantină
  const loose = (c.deficiencies || []).filter((r) => !ids.has(r.document_id));
  return [h('div', { class: 'card' }, h('h3', {}, `Documente primite (${docs.length})`),
    docs.length ? [h('p', { class: 'muted small' }, 'Clic pe un document: fișierul în stânga, ce a citit extractorul în dreapta (cu dovada și scorul); ← → trec la celelalte.'), docList(c)]
      : h('p', { class: 'muted' }, 'Niciun document.')),
    loose.length ? h('div', { class: 'card' }, h('h3', {}, `Trimise pentru dosar, neatașate (${loose.length})`),
      h('p', { class: 'muted small' }, 'Documente primite prin linkul de încărcare al dosarului pe care sistemul nu le-a putut atașa.'),
      loose.map((r) => h('details', { class: 'doc', open: true },
        h('summary', {}, h('strong', {}, DOC_TYPES[r.intended_type] || DOC_TYPES[r.document_type] || 'Document'),
          h('span', { class: 'muted small' }, r.document_id, ' · ', fmtDate(r.received_on), ' · ', r.name || ''),
          r.status === 'closed' ? badge('rezolvat', 'ok') : badge(`${openProblems(r.problems)} ${plural(openProblems(r.problems), 'problemă', 'probleme', 'de probleme')}`, 'bad')),
        problemsBox(r.problems, r.sender)))) : null,
    uploadCard(c)];
}

// ---- 078: Probleme găsite la un document + mesajul trimis expeditorului (DOCUMENT_DEFICIENT)
const openProblems = (ps) => (ps || []).filter((p) => p.status !== 'closed').length;
function problemsBox(problems, sender) {
  const who = sender ? (sender.name || sender.institution) + (sender.label ? ` (${sender.label})` : '') : 'necunoscut: escaladare la operator';
  return h('div', { class: 'problems-box' },
    h('p', { class: 'small' }, h('strong', {}, 'Probleme găsite'), h('span', { class: 'muted' }, ' · expeditor: ', who)),
    h('ul', {}, problems.map((p) => h('li', { class: p.status === 'closed' ? 'muted' : null },
      p.text, ' ',
      p.status === 'closed' ? badge('închisă', 'ok') : badge('deschisă', 'warn'),
      h('div', { class: 'small muted' },
        p.notified_at ? `Mesaj trimis la ${fmtDate(p.notified_at)} către ${p.notified_to}${p.channel ? ' (' + p.channel + ')' : ''}.`
          : p.already_notified ? 'Aceeași problemă pe același document a fost deja comunicată; nu se retrimite.'
          : p.handled_by_bank && !(sender && sender.name) ? 'Banca a cerut ea notarului; niciun mesaj.' : 'Mesaj netrimis încă.',
        p.status === 'closed' && p.closed_by ? ` Închisă: ${p.closed_by}${p.closed_at ? ', ' + fmtDate(p.closed_at) : ''}.` : '')))));
}

function uploadCard(c) {
  const file = h('input', { type: 'file', multiple: true, accept: '.pdf,.png,.jpg,.jpeg,.md,.txt,.json' });
  const send = h('button', { type: 'button', class: 'primary', onclick: async () => {
    if (!file.files.length) { toast('Alege un fișier.', true); return; }
    await sendFiles([...file.files]);
  } }, 'Trimite agentului');
  return h('div', { class: 'card' }, h('h3', {}, 'Adaugă un document'),
    h('div', { class: 'upload' }, file, send),
    h('p', { class: 'muted small' }, 'Documentul trece prin extractor, sistem și agenți; ce au scris agenții vezi în „Agenți”. Dosarul îl alege sistemul după CNP.'));
}

// ---- Plan de plată
// Dialog de confirmare: ce plătești, cui, de ce și ce rămâne blocat. Rezolvă cu numele aprobatorului sau null (renunțat).
// textele regulilor în română de ecran: sume „54750.16 lei” → „54.750,16 lei”, date ISO → zz.ll.aaaa; cota „1” → „1/1 (întreg)”
const roText = (t) => String(t ?? '').replace(/\b(\d+)\.(\d{2}) lei\b/g, (_, a, b) => `${Number(a).toLocaleString('ro-RO')},${b} lei`)
  .replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, '$3.$2.$1');
const shareRo = (x) => (String(x) === '1' ? '1/1 (întreg)' : String(x));
function confirmApprove(plan, pay, c = ui.caseNow) {
  return new Promise((resolve) => {
    const ids = new Set(pay.line_ids || []);
    const paid = plan.lines.filter((l) => ids.has(l.line_id));
    const held = plan.lines.filter((l) => !ids.has(l.line_id));
    const who = h('input', { type: 'text', placeholder: 'Numele tău (apare în audit)', value: lsGet('approver'), 'aria-label': 'Numele aprobatorului' });
    const onKey = (ev) => { if (ev.key === 'Escape') close(null); };
    const close = (v) => { document.removeEventListener('keydown', onKey); overlay.remove(); resolve(v); };
    const ok = h('button', { type: 'button', class: 'primary', onclick: () => {
      if (!who.value.trim()) { who.focus(); toast('Scrie numele tău, ca să rămână în audit.', true); return; }
      lsSet('approver', who.value.trim()); close(who.value.trim());
    } }, `Da, aprob ${fmtMoney(pay.total)}`);
    const overlay = h('div', { class: 'modal', onclick: (ev) => { if (ev.target === overlay) close(null); } },
      h('div', { class: 'card modal-card', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Confirmă aprobarea plății' },
        h('h3', {}, `Aprobi plata de ${fmtMoney(pay.total)}?`),
        h('p', {}, `Se plătesc ${paid.length} ${plural(paid.length, 'linie', 'linii', 'de linii')} din planul de plată. Cotele vin din certificatul de moștenitor, nu din lege.`),
        h('div', { class: 'table-wrap' }, h('table', {}, h('tr', {}, h('th', {}, 'Cui'), h('th', {}, 'De ce'), h('th', { class: 'num' }, 'Sumă'), h('th', {}, 'Când')),
          paid.map((l) => h('tr', {}, h('td', {}, l.name), h('td', { class: 'small' }, `cota ${shareRo(l.share)} din ${productLabel(c, l.product_id)}`),
            h('td', { class: 'num' }, fmtMoney(l.amount)), h('td', {}, l.pay_on === 'acum' ? 'acum' : fmtDate(l.pay_on)))))),
        held.length ? h('p', { class: 'small' }, h('strong', {}, 'Nu se plătesc acum: '),
          [...new Map(held.map((l) => [l.name, `${l.name} (${roText((l.blocked_reason || 'rămâne blocat').split(':')[0])})`])).values()].join('; '), '.') : null,
        h('p', { class: 'small muted' }, 'Aprobarea e a ta; agentul doar a pregătit instrucțiunea. După aprobare, plata nu mai poate fi respinsă din această pagină.'),
        h('label', { class: 'small' }, 'Cine aprobă ', who),
        h('div', { class: 'upload', style: 'margin-top:12px' }, ok, h('button', { type: 'button', onclick: () => close(null) }, 'Renunț'))));
    document.addEventListener('keydown', onKey);
    document.body.append(overlay);
    who.focus();
  });
}

function tabPlan(c) {
  const plan = c.payment_plan;
  if (!plan) return h('div', { class: 'card' }, h('h3', {}, 'Plan de plată'),
    h('p', { class: 'muted' }, 'Nu există încă. Se întocmește după certificatul de moștenitor cu acoperire completă și după răspunsul asigurătorului.'));
  const pay = (c.payments || []).find((p) => p.plan_id === plan.plan_id) || (c.payments || [])[0];
  const payLines = new Set(pay?.line_ids || []);
  const rows = plan.lines.map((l) => h('tr', { class: l.blocked ? 'blocked' : '' },
    h('td', {}, l.name, l.minor ? [' ', badge('minoră', 'warn')] : ''),
    h('td', {}, h('code', {}, l.share)),
    h('td', {}, productLabel(c, l.product_id)),
    h('td', { class: 'num' }, fmtMoney(l.amount)),
    h('td', {}, l.pay_on === 'acum' ? 'acum' : fmtDate(l.pay_on)),
    h('td', {}, l.blocked ? [badge('blocat', 'bad'), h('div', { class: 'small' }, l.blocked_reason || '')]
      : payLines.has(l.line_id) ? badge(pay.status === 'approved' ? 'plătit' : 'în plată', pay.status === 'approved' ? 'ok' : 'warn') : badge('liber', 'ok'))));
  const withheld = (plan.withheld || []).map((w) => h('tr', {},
    h('td', { colspan: 3 }, 'Reținut: ', w.label || w.reason), h('td', { class: 'num' }, fmtMoney(w.amount)), h('td', { colspan: 2 }, '')));
  // net_of_debts (scenariu §2.3): ce se împarte din contul curent, după datoriile masei; pensia reținută nu intră
  const na = plan.net_account;
  const net = na ? [h('tr', {},
    h('td', { colspan: 3 }, h('strong', {}, 'Net de împărțit: ' + productLabel(c, na.product_id))),
    h('td', { class: 'num' }, h('strong', {}, fmtMoney(na.net))),
    h('td', { colspan: 2, class: 'small muted' }, `${fmtMoney(na.gross)} − datorii ${fmtMoney(na.debts_deducted)}`))] : [];
  let bar = null;
  if (pay) {
    const tone = { pending_approval: 'warn', approved: 'ok', rejected: 'bad' }[pay.status];
    const label = { pending_approval: 'așteaptă aprobare', approved: 'aprobată', rejected: 'respinsă' }[pay.status] || pay.status;
    const pending = pay.status === 'pending_approval';
    const reason = h('input', { type: 'text', placeholder: 'Motivul respingerii (obligatoriu la respingere)' });
    const act = (fn, okMsg) => async (ev) => {
      ev.target.disabled = true;
      try { await fn(); toast(okMsg); await select(c.case_id); } catch (e) { toast(e.message, true); ev.target.disabled = false; }
    };
    bar = h('div', { class: 'approve-bar' },
      h('span', {}, 'Plata: ', h('strong', {}, fmtMoney(pay.total)), ' ', badge(label, tone)),
      pending ? reason : null,
      pending ? h('button', { type: 'button', class: 'primary', onclick: async (ev) => {
        const who = await confirmApprove(plan, pay);
        if (who) await act(() => api.approve(pay.payment_id, who), `Plata de ${fmtMoney(pay.total)} aprobată de ${who}`)(ev);
      } }, pay.total ? 'Aprobă plata…' : 'Confirmă: nimic de plătit…') : null,
      pending ? h('button', { type: 'button', class: 'danger', onclick: act(() => {
        if (!reason.value.trim()) { reason.focus(); throw new Error('Scrie motivul respingerii.'); }
        return api.reject(pay.payment_id, reason.value.trim());
      }, 'Planul de plată a fost respins') }, 'Respinge') : null,
      h('div', { class: 'muted small', style: 'flex-basis:100%' },
        'Aprobarea e a unui om; agentul doar pregătește instrucțiunea. Liniile blocate nu intră în plată.'));
  }
  return h('div', { class: 'card' },
    h('h3', {}, 'Planul de plată ', badge(plan.variant_label || ('varianta ' + plan.variant), 'info')),
    h('div', { class: 'table-wrap' }, h('table', {}, h('tr', {}, h('th', {}, 'Moștenitor'), h('th', {}, 'Fracție din bun'), h('th', {}, 'Produs'),
      h('th', { class: 'num' }, 'Sumă'), h('th', {}, 'Când'), h('th', {}, 'Stare')), rows, net, withheld)),
    bar);
}

// ---- Corespondență
const TEMPLATES = {
  MISSING_DOCS_FIRST: (c) => `Bună ziua. Ne pare rău pentru pierderea dumneavoastră. Pentru dosarul ${c.case_id} mai avem nevoie de: ${missingOf(c).join('; ') || '—'}. Le puteți încărca aici: {{UPLOAD_URL}}/cases/${c.case_id}/upload?token={{token}}`,
  MISSING_DOCS_REMINDER: (c) => `Reamintire dosar ${c.case_id}: lipsesc ${missingOf(c).join('; ') || '—'}. Încărcare: {{UPLOAD_URL}}/cases/${c.case_id}/upload?token={{token}}`,
  MINOR_REPRESENTATION: (c) => `Pentru partea minorului avem nevoie de acordul scris al reprezentantului legal și de un cont pe numele lui. Încărcare: {{UPLOAD_URL}}/cases/${c.case_id}/upload?token={{token}}`,
  SUPPLEMENT_NEEDED: (c) => `Certificatul de moștenitor nu cuprinde toate produsele. Vă rugăm cereți notarului un certificat suplimentar și încărcați-l aici: {{UPLOAD_URL}}/cases/${c.case_id}/upload?token={{token}}`,
  PLAN_APPROVED: () => 'Plata părții dumneavoastră a fost aprobată. Ce rămâne blocat (depozit până la scadență, partea minorului) vă anunțăm separat.',
  DEADLINE_SOON: () => 'Vă reamintim că termenul de opțiune succesorală (1 an de la deces) se apropie. Pentru întrebări, răspundeți la acest mesaj.',
};

const TEMPLATE_LABEL = { MISSING_DOCS_FIRST: 'Documente lipsă (prima cerere)', MISSING_DOCS_REMINDER: 'Reamintire documente lipsă',
  MINOR_REPRESENTATION: 'Reprezentarea minorului', SUPPLEMENT_NEEDED: 'Certificat suplimentar necesar', PLAN_APPROVED: 'Plată aprobată',
  DEADLINE_SOON: 'Termen care se apropie', DOCUMENT_DEFICIENT: 'Document cu probleme' };
const tplText = (t) => String(t).replace(/\b[A-Z][A-Z_]+[A-Z]\b/g, (k) => TEMPLATE_LABEL[k] || k);

function artifactItem(kind, a) {
  const title = tplText(a.title || a.name || a.file || a.path || a.template_id || a.message_id || kind);
  const body = a.content || a.body || a.text || '';
  return h('details', { class: 'artifact' },
    h('summary', {}, badge(kind, { Scrisoare: 'info', Mesaj: 'warn', Investigație: 'bad' }[kind]), h('strong', {}, title),
      h('span', { class: 'muted small' }, fmtDate(a.at || a.created_at), a.to ? ` · către ${a.to}` : '', a.channel ? ` · ${a.channel}` : '')),
    h('pre', {}, body || '(fără conținut)'));
}


// 078: mesajele DOCUMENT_DEFICIENT din outbox (cui, când, pentru ce document, textul trimis)
function deficientCard(c) {
  const box = h('div', { class: 'card' }, h('h3', {}, 'Documente cu probleme: mesaje către expeditori'));
  api.listMessages(c.case_id).then((msgs) => {
    const mine = (msgs || []).filter((m) => m.template_id === 'DOCUMENT_DEFICIENT');
    const waiting = (c.deficiencies || []).filter((r) => r.problems.some((p) => p.status !== 'closed' && !p.notified_at && !p.handled_by_bank));
    box.append(...(mine.length ? mine.map((m) => [artifactItem('Mesaj', { ...m, title: `Document cu probleme (${m.deficiency?.document_id || '—'}): ${(m.deficiency?.problems || []).join(', ')}`, at: m.case_date || m.at }),
      docActionsFor(c.case_id, (d) => d.message_id === m.message_id)])
      : [h('p', { class: 'muted small' }, 'Niciun mesaj de acest tip.')]),
      waiting.length ? h('p', { class: 'small' }, badge('în așteptare', 'warn'), ' ',
        waiting.map((r) => `${r.document_id}: ${r.sender?.name ? 'mesajul către ' + r.sender.name + ' îl scrie autopilotul' : 'expeditor necunoscut, la operator'}`).join('; ')) : '');
  }).catch((e) => box.append(h('p', { class: 'muted small' }, e.message)));
  return box;
}

// ---- 077: Contact cu moștenitorii: scara de contact (GET /cases/{id}/contact-plan), pașii făcuți, următorul, data
const LADDER_TONE = { done: 'ok', due: 'warn', waiting: 'warn', upcoming: 'info', skipped: '' };
function contactCard(c) {
  const title = () => h('h3', {}, 'Contact cu moștenitorii');
  const box = h('div', { class: 'card' }, title(), h('p', { class: 'muted small' }, 'Se încarcă…'));
  const load = () => api.contactPlan(c.case_id).then((p) => box.replaceChildren(...ladderView(p, load)))
    .catch((e) => box.replaceChildren(title(), h('p', { class: 'muted small' },
      e.status === 404 ? 'Scara de contact nu e disponibilă pe acest server.' : e.message)));
  load();
  return box;
}

function ladderView(p, reload) {
  const advance = (days, label) => {
    const b = h('button', { type: 'button', class: 'dark', onclick: async () => {
      b.disabled = true;
      try {
        await api.advanceClock(days);
        toast(`Ceasul demo a avansat ${label}. Autopilotul aplică pasul scadent la următorul poll.`);
        await reload();
      } catch (e) { toast(e.status === 403 ? 'Ceasul se avansează doar pe un server cu DEMO_MODE=1.' : e.message, true); b.disabled = false; }
    } }, label);
    return b;
  };
  const toNext = p.next ? Math.round((Date.parse(p.next.due) - Date.parse(p.today)) / 864e5) : 0;
  const rows = (p.steps || []).map((s) => h('tr', { class: s.status === 'skipped' ? 'muted' : null },
    h('td', {}, cleanText(s.label), h('div', { class: 'muted small' }, 'Temei: ', cleanText(s.basis))),
    h('td', {}, fmtDate(s.status === 'done' ? s.done_at : s.due)),
    h('td', {}, s.action_label,
      s.recipients.length ? h('div', { class: 'small muted' }, s.recipients.map((r) => [r.name, r.channel && cleanText(r.channel), r.address].filter(Boolean).join(' · ')).join('; ')) : null,
      s.note ? h('div', { class: 'small' }, s.note) : null),
    h('td', {}, badge(s.status_label, LADDER_TONE[s.status]))));
  return [h('h3', { 'data-ladder': '' }, 'Contact cu moștenitorii'),
    h('p', { class: 'small' }, h('strong', {}, p.summary), ' ',
      h('span', { class: 'muted' }, p.since ? `Azi (ceasul dosarului): ${fmtDate(p.today)}; zilele se numără de la ultima mișcare din dosar, ${fmtDate(p.since)}.` : '')),
    ...(p.blocked || []).map((b) => h('p', { class: 'small' }, badge('blocat', 'bad'), ' ', `${b.heir}: ${b.reason}.`)),
    rows.length ? h('div', { class: 'table-wrap' }, h('table', {},
      h('tr', {}, h('th', {}, 'Pas'), h('th', {}, 'Data'), h('th', {}, 'Cum / către cine'), h('th', {}, 'Stare')), rows))
      : h('p', { class: 'muted' }, 'Nicio treaptă de contact.'),
    h('div', { class: 'upload', style: 'margin-top:8px' }, advance(14, '+14 zile'),
      toNext > 0 ? advance(toNext, `Sari la pasul următor (${fmtDate(p.next.due)})`) : null,
      h('span', { class: 'muted small' }, 'Demo: avansează ceasul dosarului ca să vezi scara (doar DEMO_MODE).'))];
}

function composerCard(c) {
  const people = (c.heirs || []).map((x) => x.name).filter(Boolean);
  const to = h('select', {}, people.map((n) => h('option', { value: n }, n)), h('option', { value: '__notifier' }, 'Persoana care a notificat decesul'));
  const channel = h('select', {}, ['email', 'sms', 'whatsapp', 'app'].map((x) => h('option', { value: x }, x)));
  const tpl = h('select', {}, Object.keys(TEMPLATES).map((k) => h('option', { value: k }, TEMPLATE_LABEL[k] || k)));
  const body = h('textarea', { rows: 3, style: 'width:100%' });
  // linkul real îl pune API-ul la trimitere ({{UPLOAD_URL}}…{{token}}); omul vede doar locul lui
  const LINK = '[link securizat de încărcare]';
  const placeholder = `{{UPLOAD_URL}}/cases/${c.case_id}/upload?token={{token}}`;
  const fill = () => { body.value = TEMPLATES[tpl.value](c).split(placeholder).join(LINK); };
  tpl.addEventListener('change', fill);
  fill();
  const send = h('button', { type: 'button', class: 'primary', onclick: async () => {
    send.disabled = true;
    try {
      const notifier = to.value === '__notifier';
      await api.sendMessage({ case_id: c.case_id, to: notifier ? 'notificator' : to.value, to_role: notifier ? 'notifier' : 'heir',
        channel: channel.value, template_id: tpl.value, body: body.value.split(LINK).join(placeholder) });
      toast('Mesaj pus în coada de trimitere (canalele externe nu sunt conectate încă).');
      renderCase(await api.getCase(c.case_id));
    } catch (e) { toast(e.message, true); send.disabled = false; }
  } }, 'Trimite');
  const link = h('button', { type: 'button', class: 'dark', onclick: async () => {
    link.disabled = true;
    try {
      const t = await api.uploadToken(c.case_id, to.value);
      await copyText(`${API_BASE}/upload?token=${encodeURIComponent(t.token)}`);
      toast('Link de încărcare copiat (valabil 7 zile, doar pentru acest dosar).');
    } catch (e) { toast(e.message, true); } finally { link.disabled = false; }
  } }, 'Copiază linkul de încărcare');
  const cc = c.contact_channels || {};
  return h('div', { class: 'card' }, h('h3', {}, 'Mesaj nou către moștenitori'),
    Object.keys(cc).length ? h('p', { class: 'small muted' }, 'Canale: ', Object.values(cc).map((x) =>
      `${x.name}: ${x.preferred}${x.via ? ' prin ' + x.via : ''}${x.verified ? ' ✓' : ''}`).join(' · ')) : null,
    h('div', { class: 'upload' }, to, channel, tpl), body,
    h('div', { class: 'upload', style: 'margin-top:6px' }, send,
      h('span', { class: 'muted small' }, 'Doar mesaje operaționale. SMS/WhatsApp ≤ 300 caractere; linkul de încărcare îl generează API-ul (7 zile).')),
    h('div', { class: 'upload', style: 'margin-top:12px; padding-top:12px; border-top:1px solid var(--line)' },
      link, h('span', { class: 'muted small' }, 'Pentru moștenitor: deschide o pagină de unde încarcă documentele lipsă.')));
}

// ---- Audit
function resolveControls(caseId, escId, after) {
  const note = h('input', { type: 'text', placeholder: 'Notă pentru decizie (obligatorie)' });
  const btn = h('button', { type: 'button', class: 'primary', onclick: async () => {
    if (!note.value.trim()) { note.focus(); toast('Scrie nota deciziei.', true); return; }
    btn.disabled = true;
    try { await api.resolveEscalation(caseId, escId, note.value.trim()); toast(`${escId} rezolvată`); await after(); }
    catch (e) { toast(e.message, true); btn.disabled = false; }
  } }, 'Rezolvă');
  return h('div', { class: 'esc-actions' }, note, btn);
}

function signNotaryAction(caseId) {
  // Răspunsul către notar e redactat de agent, dar pleacă doar cu semnătura unui om: abia atunci termenul e îndeplinit.
  const name = h('input', { type: 'text', placeholder: 'Numele semnatarului', 'aria-label': 'Numele semnatarului' });
  const btn = h('button', { class: 'btn primary small', onclick: async () => {
    if (!name.value.trim()) { toast('Scrie numele celui care semnează răspunsul', true); name.focus(); return; }
    btn.disabled = true;
    try { await api.signNotaryAnswer(caseId, name.value.trim()); toast('Răspunsul către notar a fost semnat'); await select(caseId); refresh(); }
    catch (e) { toast(e.message, true); btn.disabled = false; }
  } }, 'Semnează răspunsul');
  return h('div', { class: 'esc-actions', 'data-sign': '' }, name, btn);
}

function deadlinesCard(list, c) {
  const tone = { deschis: 'warn', 'în așteptare': 'warn', îndeplinit: 'ok', programat: 'info', depășit: 'bad' };
  const caseId = c && (c.case_id || c.id);
  return h('div', { class: 'card' }, h('h3', {}, 'Termene'),
    list.length ? h('div', { class: 'table-wrap' }, h('table', {}, h('tr', {}, h('th', {}, 'Termen'), h('th', {}, 'Data'), h('th', {}, 'Stare')),
      list.map((t) => {
        const rel = relDays(t.date, t.status);
        const canSign = caseId && t.code === 'notary_answer' && t.status !== 'îndeplinit';
        return h('tr', {}, h('td', {}, t.name, t.hypothesis ? badge('ipoteză, de confirmat', 'warn') : null, h('div', { class: 'muted small' }, t.rule || '')),
          h('td', {}, fmtDate(t.date), rel ? h('div', { class: 'small ' + (rel.late ? 'late' : 'muted') }, rel.text) : null),
          h('td', {}, badge(t.status, tone[t.status]), canSign ? signNotaryAction(caseId) : null));
      })))
      : h('p', { class: 'muted' }, 'Niciun termen.'));
}

function productsCard(c) {
  const rows = (c.products || []).map((p) => h('tr', {},
    h('td', {}, p.label || p.type, p.iban ? h('div', { class: 'muted small' }, p.iban) : null),
    h('td', { class: 'num' }, fmtMoney(p.balance ?? p.principal ?? p.outstanding)),
    h('td', { class: 'num' }, fmtMoney(p.accrued_interest)),
    h('td', { class: 'small' }, p.maturity ? 'scadent ' + fmtDate(p.maturity) : '', p.insurance ? ' ' + p.insurance : '',
      p.insurance_settled ? h('div', {}, badge('stins de asigurător ' + fmtMoney(p.insurance_settled), 'ok')) : '')));
  return h('div', { class: 'card' }, h('h3', {}, 'Produse la data decesului (', fmtDate(c.products_as_of), ')'),
    rows.length ? h('div', { class: 'table-wrap' }, h('table', {}, h('tr', {}, h('th', {}, 'Produs'), h('th', { class: 'num' }, 'Sold'), h('th', { class: 'num' }, 'Dobândă'), h('th', {}, '')), rows))
      : h('p', { class: 'muted' }, 'Necerute încă.'));
}

const CORE_ACTION = { freeze: 'Blocare conturi', reverse_fees: 'Stornare comisioane', pay: 'Plată', loan_settled_by_insurer: 'Credit stins de asigurător' };
// Detaliile din jurnalul core: sumele sunt în bani, booleenii în da/nu; cheile necunoscute rămân brute.
function coreDetail([k, v]) {
  if (typeof v === 'boolean') v = v ? 'da' : 'nu';
  else if (typeof v === 'number' && /total|amount|suma|bani/.test(k)) v = fmtMoney(v);
  else if (typeof v === 'object') v = JSON.stringify(v);
  return `${{ reversible: 'reversibil', total: 'total', amount: 'sumă', at: 'la' }[k] || k}: ${v}`;
}

function escalationsCard(c) {
  const escs = [...(c.escalations || [])].sort((x, y) => ((x.status || 'deschis') === 'închis') - ((y.status || 'deschis') === 'închis'));
  const docType = Object.fromEntries((c.documents || []).map((d) => [d.document_id, DOC_TYPES[d.document_type] || d.document_type]));
  return h('div', { class: 'card' }, escs.length ? h('ul', { class: 'esc-list' }, escs.map((e) => {
    const open = (e.status || 'deschis') !== 'închis';
    const id = e.id || e.escalation_id;
    return h('li', { class: 'esc-item' + (open ? ' open' : ''), 'data-esc': id },
      h('div', { class: 'esc-top' }, badge(open ? 'de rezolvat' : 'rezolvată', open ? 'bad' : 'ok'),
        e.code === 'suspicious_document' || e.code === 'unsafe_output' ? badge(e.severity === 'info' ? 'Suspect (informativ)' : 'Suspect', e.severity === 'info' ? 'warn' : 'bad') : null,
        h('b', { title: e.code || '' }, human(ESC_LABEL, e.code)), docType[e.document_id] ? h('span', { class: 'muted small' }, ' · din ', docType[e.document_id]) : null),
      h('p', {}, cleanText(e.reason)), guardFlags(e.flags),
      id ? docActionsFor(c.case_id, (d) => d.escalation_id === id) : null,   // propunerea investigatorului, dacă există
      open && id ? resolveControls(c.case_id, id, () => select(c.case_id)) : null);
  })) : h('p', { class: 'muted' }, 'Nicio escaladare.'));
}

function bankJournalCard(c) {
  const bankCard = h('div', { class: 'card' }, h('h3', {}, 'Jurnalul băncii (acțiuni pe core)'), h('p', { class: 'muted small' }, 'Se încarcă…'));
  api.audit().then((rows) => {
    const mine = (rows || []).filter((r) => !r.cif || r.cif === (c.cif || c.deceased?.cif));
    const fromEvents = (c.events || []).filter((e) => e.audit_id).map((e) => ({ audit_id: e.audit_id, action: e.action, at: e.at }));
    const list = mine.length ? mine : fromEvents;
    bankCard.replaceChildren(h('h3', {}, 'Jurnalul băncii (acțiuni pe core)'), list.length
      ? h('div', { class: 'table-wrap' }, h('table', {}, h('tr', {}, h('th', {}, 'Audit'), h('th', {}, 'Acțiune'), h('th', {}, 'Detalii')),
        list.map((r) => h('tr', {}, h('td', {}, h('code', {}, r.audit_id)), h('td', {}, CORE_ACTION[r.action] || r.action),
          h('td', { class: 'small muted' }, Object.entries(r).filter(([k]) => !['audit_id', 'action', 'cif'].includes(k)).map(coreDetail).join(' · '))))))
      : h('p', { class: 'muted' }, 'Nicio acțiune pe core încă.'));
  }).catch((e) => bankCard.replaceChildren(h('h3', {}, 'Jurnalul băncii'), h('p', { class: 'muted' }, e.message)));
  return bankCard;
}

function humanDecisionsCard(c) {
  const decisions = (c.events || []).filter((e) => e.kind === 'decision' && /operator|aprobat|respins|rezolvat/i.test(e.detail || e.action || ''));
  return h('div', { class: 'card' }, h('h3', {}, 'Decizii umane'), decisions.length
      ? h('ul', {}, decisions.map((e) => h('li', {}, fmtDate(e.at), ' · ', cleanText(e.detail || e.action))))
    : h('p', { class: 'muted' }, 'Nicio decizie umană încă (aprobare, respingere, escaladare rezolvată).'));
}

function tabAudit(c) {
  return [escalationsCard(c), h('div', { class: 'grid2' }, deadlinesCard(c.deadlines || [], c), productsCard(c)), bankJournalCard(c), humanDecisionsCard(c)];
}

// ---- document fără dosar
function selectUnmatched(u) {
  ui.selected = u.escalation_id;
  ui.unmatched = true;   // #dosare/SC-NEIDENTIFICAT (demo-dosare.js: demoHash)
  showView('cases');
  setCasesMode('case');
  if (typeof demoHash === 'function') demoHash();
  const focus = ui.focus; ui.focus = null;
  if (focus) setTimeout(() => { const el = document.querySelector('#detail .esc-actions'); if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 2600); el.querySelector('input')?.focus({ preventScroll: true }); } }, 60);
  $('#detail').replaceChildren(
    h('div', { class: 'card' },
      h('h3', {}, 'Document fără dosar ', u.status === 'închis' ? badge('Rezolvat', 'ok') : badge('Escaladat', 'bad')),
      h('dl', { class: 'kv' },
        h('dt', {}, 'Escaladare'), h('dd', {}, u.escalation_id),
        h('dt', {}, 'Motiv'), h('dd', {}, u.rule === 'suspicious_document' ? [badge('Suspect', 'bad'), ' '] : null, cleanText(u.reason), guardFlags(u.flags)),
        h('dt', {}, 'Ce a făcut sistemul'), h('dd', {}, u.agent_action),
        h('dt', {}, 'Regula'), h('dd', { class: 'small' }, u.rule)),
      h('p', { class: 'muted small' }, 'Necesită un operator: identifică clientul sau cere un document lizibil. Agentul nu blochează nimic pe baza lui.'),
      u.status !== 'închis' ? resolveControls(u.case_id, u.escalation_id, async () => {
        const fresh = (await api.listUnmatched()).find((x) => x.escalation_id === u.escalation_id);
        fresh ? selectUnmatched(fresh) : refresh();
      }) : badge('rezolvată', 'ok')),
    h('div', { class: 'card' }, h('h3', {}, 'Document'), docBlock(u, true, u.case_id)));
  refresh();
}

// ---------- Impact (043): sinteză pentru juriu ----------
// Ipotezele din docs/pitch/business-case.md (scenariul central), afișate lângă cifre.
const BUSINESS = { casesPerYear: 24000, manualHoursPerCase: 3, automated: 0.65, hourlyCost: 90, tokenCostPerCase: 0.64, usdRon: 4.5 };

async function renderImpact() {
  const root = $('#view-impact');
  root.replaceChildren(h('div', { class: 'card muted' }, 'Se calculează…'));
  try {
    const list = await api.listCases();
    const cases = await Promise.all(list.map((c) => api.getCase(c.case_id)));
    const latest = cases;
    const unmatched = await api.listUnmatched();
    const s = latest.map(savings);
    const manualMin = s.reduce((a, x) => a + x.manualMin, 0);
    const humanMin = s.reduce((a, x) => a + x.humanMin, 0);
    const agentSec = s.reduce((a, x) => a + x.agentSec, 0);
    const docs = latest.reduce((a, c) => a + (c.documents || []).length, 0) + unmatched.length;
    const fees = latest.reduce((a, c) => a + (c.flags || []).filter((f) => f.code === 'fee_to_reverse').reduce((x, f) => x + f.amount, 0)
      + (c.flags ? 0 : (c.events || []).filter((e) => /stornare/i.test(e.action || '')).reduce((x, e) => x + (e.amount || 0), 0)), 0);
    const dl = latest.flatMap((c) => c.deadlines || []);
    const dlMet = dl.filter((d) => d.status === 'îndeplinit').length;
    const dlMissed = dl.filter((d) => d.status === 'depășit').length;
    const escOpen = latest.reduce((a, c) => a + (c.escalations || []).filter((e) => e.status !== 'închis').length, 0) + unmatched.filter((u) => u.status !== 'închis').length;
    const escAll = latest.reduce((a, c) => a + (c.escalations || []).length, 0) + unmatched.length;
    const paid = latest.filter((c) => c.state === 'PAID').length;
    const b = BUSINESS;
    const yearHours = b.casesPerYear * b.manualHoursPerCase * b.automated;
    const kpi = (v, l, note) => h('div', { class: 'kpi' }, h('div', { class: 'l' }, l), h('div', { class: 'v' }, v), note ? h('div', { class: 'small muted' }, note) : null);
    root.replaceChildren(
      h('div', { class: 'hero' },
        h('div', {}, h('div', { class: 'v' }, fmtDuration(manualMin)), h('div', {}, 'timp manual evitat în dosarele de azi')),
        h('div', {}, h('div', { class: 'v' }, agentSec < 60 ? `${fmtNum(agentSec, 1)} s` : fmtDuration(agentSec / 60)), h('div', {}, 'timp de procesare al agentului')),
        h('div', {}, h('div', { class: 'v' }, fmtDuration(humanMin)), h('div', {}, 'timp de om rămas (decizii)'))),
      h('div', { class: 'kpis' },
        kpi(fmtNum(latest.length), 'Dosare procesate', `${paid} plătite · ${docs} documente primite`),
        kpi(fmtMoney(fees), 'Comisioane stornate', 'reținute după data decesului'),
        kpi(`${dlMet} / ${dl.length}`, 'Termene îndeplinite', dlMissed ? `${dlMissed} depășite` : 'niciun termen depășit'),
        kpi(`${escAll}`, 'Escaladări către om', `${escOpen} deschise · niciun document nesigur procesat automat`),
        kpi(fmtNum(latest.reduce((a, x) => a + savings(x).steps.length, 0)), 'Interacțiuni manuale evitate', `${MANUAL_MIN} min fiecare (ipoteză)`)),
      h('div', { class: 'card' }, h('h3', {}, 'Extrapolare la volumul băncii (scenariul central)'),
        h('div', { class: 'kpis' },
          kpi(fmtNum(b.casesPerYear), 'Dosare / an', '240.000 decese/an × 7–14% clienți'),
          kpi(fmtNum(yearHours), 'Ore economisite / an', `${b.manualHoursPerCase} h/dosar × ${Math.round(b.automated * 100)}% automatizat`),
          kpi(`${fmtNum(yearHours * b.hourlyCost / 1e6, 1)} mil. lei`, 'Economie / an', `la ${b.hourlyCost} lei/oră`),
          kpi(`${fmtNum(b.casesPerYear * b.tokenCostPerCase * b.usdRon / 1000)} mii lei`, 'Cost LLM / an', `≈ ${b.tokenCostPerCase} $/dosar`))),
      h('div', { class: 'card' }, h('h3', {}, 'Ipoteze (afișate, nu ascunse)'),
        h('ul', { class: 'assumptions small' },
          h('li', {}, `${MANUAL_MIN} min per interacțiune manuală evitată (business-case: 3–6 interacțiuni × 30–60 min / dosar); ${HUMAN_DECISION_MIN} min per decizie umană (aprobare, escaladare).`),
          h('li', {}, 'Interacțiuni numărate din cronologia dosarului: blocare, stornare comisioane, răspuns către notar, dosar de daună, calcul cote, plan de plată.'),
          h('li', {}, 'Timpul agentului vine din trace (processed_at), fără timpul de așteptare dintre documente.'),
          h('li', {}, 'Extrapolarea: scenariul central din docs/pitch/business-case.md (24.000 dosare/an, 3 h/dosar, 65% automatizat, 90 lei/oră, 0,64 $/dosar, 1 $ = 4,5 lei). Toate sunt estimări proprii, de validat cu banca.'),
          h('li', {}, 'Nu sunt incluse: reclamații evitate, pensii returnate corect, timpul moștenitorilor (necunoscute, nemonetizate).'))));
  } catch (e) {
    root.replaceChildren(h('div', { class: 'card' }, h('h3', {}, 'Eroare'), h('p', {}, e.message)));
  }
}

document.querySelectorAll('.nav-btn').forEach((b) => b.addEventListener('click', () => {
  if (b.dataset.view === 'cases' && ui.view === 'cases' && ui.selected) backToList();   // „Dosare” din dosar: înapoi la listă
  showView(b.dataset.view);
}));
$('#back-to-list').addEventListener('click', backToList);
$('#decisions-pill').addEventListener('click', (ev) => { ev.stopPropagation(); toggleDecisionsMenu(); });

// Contorul din antet, clicabil: lista scurtă (dosar · acțiune); fiecare rând duce direct la locul acțiunii în dosar
async function toggleDecisionsMenu() {
  const old = $('#decisions-menu');
  if (old) { old.remove(); $('#decisions-pill').setAttribute('aria-expanded', 'false'); return; }
  const pill = $('#decisions-pill');
  const menu = h('div', { id: 'decisions-menu', class: 'dec-menu card', role: 'menu', 'aria-label': 'Deciziile care te așteaptă' },
    h('p', { class: 'muted small' }, h('span', { class: 'spinner' }), ' Se încarcă…'));
  const r = pill.getBoundingClientRect();
  menu.style.top = `${Math.round(r.bottom + 8)}px`;
  menu.style.right = `${Math.max(8, Math.round(window.innerWidth - r.right))}px`;
  document.body.append(menu);
  pill.setAttribute('aria-expanded', 'true');
  const close = () => { menu.remove(); pill.setAttribute('aria-expanded', 'false'); document.removeEventListener('click', onDoc); document.removeEventListener('keydown', onKey); };
  const onDoc = (ev) => { if (!menu.contains(ev.target)) close(); };
  const onKey = (ev) => { if (ev.key === 'Escape') { close(); pill.focus(); } };
  document.addEventListener('click', onDoc);
  document.addEventListener('keydown', onKey);
  let work;
  try { work = await http('/worklist'); } catch (e) { menu.replaceChildren(h('p', { class: 'small' }, e.message)); return; }
  // aceeași acțiune pe același dosar (de ex. două escaladări cu același motiv) = un singur rând, cu numărul lor
  const seen = new Map();
  for (const row of work.rows) for (const d of row.decisions) {
    const k = `${row.case_id}|${d.text}`;
    if (seen.has(k)) seen.get(k).n += 1; else seen.set(k, { row, d, n: 1 });
  }
  const items = [...seen.values()];
  const go = ({ row, d }) => {
    close();
    if (row.kind === 'unmatched') { const u = ui.lastUnmatched.find((x) => x.status !== 'închis') || ui.lastUnmatched[0]; if (u) { ui.focus = 'esc'; selectUnmatched(u); } return; }
    ui.focus = { kind: d.kind, match: d.kind === 'escaladare' ? d.text.replace(/^Escaladare: /, '') : null };
    showView('cases'); select(row.case_id);
  };
  const ICO = { plata: 'bank', semnatura: 'notary', escaladare: 'fileAlert', scara: 'heirs' };
  menu.replaceChildren(h('div', { class: 'dec-head' }, h('b', {}, items.length ? `${items.length} ${plural(items.length, 'decizie te așteaptă', 'decizii te așteaptă', 'de decizii te așteaptă')}` : 'Nicio decizie nu te așteaptă'),
    h('button', { type: 'button', class: 'link', onclick: () => { close(); ui.filter = null; showView('cases'); backToList(); } }, 'Lista de lucru')),
    items.length ? h('ul', { class: 'dec-list' }, items.map((it) => h('li', {}, h('button', { type: 'button', role: 'menuitem', class: 'dec-item ' + it.d.kind, onclick: () => go(it) },
      svgIcon(ICO[it.d.kind] || 'hand'), h('span', {}, h('b', {}, it.row.name), h('span', { class: 'muted small' }, ' · ', it.row.case_id), h('div', { class: 'small' }, decText(it.d.text), it.n > 1 ? ` (×${it.n})` : '')),
      h('span', { class: 'dec-go', 'aria-hidden': 'true' }, '→'))))) : h('p', { class: 'muted small' }, 'Toate dosarele merg singure acum.'));
  menu.querySelector('.dec-item')?.focus();
}
let searchTimer = null;
$('#wl-search').addEventListener('input', (ev) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { ui.q = ev.target.value.trim(); refresh(); }, 200);
});
$('#theme-toggle').addEventListener('click', () => {
  const t = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.classList.add('theme-anim');   // culorile trec lin dintr-o temă în alta
  document.documentElement.dataset.theme = t;
  localStorage.setItem('theme', t);
  clearTimeout(window.themeAnim); window.themeAnim = setTimeout(() => document.documentElement.classList.remove('theme-anim'), 450);
});
init();
