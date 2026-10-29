// Demo ghidat, selecția de dosar: deasupra demo-ului, o listă cu dosarele băncii (GET /worklist). Implicit Maria Ionescu
// (demo-ul în 6 pași). Un dosar din portofoliu arată parcursul lui cu aceleași componente: roadmap-ul (etapele,
// cele făcute bifate, cea oprită evidențiată), bannerul etapei, stațiile (documentul, regulile, „Rândul tău”) și, la
// etapa oprită, butonul deciziei: aprobă plata (dialogul cu numele aprobatorului), semnează răspunsul către notar,
// rezolvă escaladarea. După decizie, parcursul se recitește și trece la etapa următoare.
// Selecția stă în URL: #demo/SC-2026-0107. Tabul Dosare: un clic pe un rând deschide dosarul aici (openInDemo).
// Depinde de app.js (h, http, api, badge, stateBadge, confirmApprove, previewDocument, guardFlags, human, ESC_LABEL,
// DOC_TYPES, lsGet/lsSet, showView, select, refresh), demo.js (demo, DEMO_CASE, renderDemo, planCard),
// demo-manual.js (stationHead, mPending, mScrollGate) și demo-look.js (svgIcon).

// etapele unui dosar, în ordinea din realitate; `docs` = tipurile de document care o hrănesc
const PF_STAGES = [
  { key: 'dgep', short: 'Semnal DGEP', title: 'Semnalul de deces (DGEP)', icon: 'signal', accent: 'var(--step)', docs: ['dgep_signal', 'death_certificate'],
    from: 'DGEP · Evidența Persoanelor', what: 'blocare reversibilă, stornarea comisioanelor de după deces, pensia de returnat' },
  { key: 'notar', short: 'Răspuns notar', title: 'Răspunsul către notar', icon: 'notary', accent: 'var(--step)', docs: ['notary_request'],
    from: 'Notarul public', what: 'soldurile la data decesului, redactate de sistem, semnate de un om' },
  { key: 'asig', short: 'Asigurare', title: 'Dosarul de daună la asigurător', icon: 'shield', accent: 'var(--step)', docs: ['insurance_certificate', 'insurer_response'],
    from: 'Asigurătorul creditului', what: 'dauna avizată la timp; creditul stins de asigurător sau rămas în masa succesorală' },
  { key: 'cert', short: 'Moștenitori', title: 'Certificatul de moștenitor', icon: 'heirs', accent: 'var(--step)', docs: ['heir_certificate', 'supplementary_certificate'],
    from: 'Notarul public', what: 'cotele moștenitorilor (suma = 1), acoperirea tuturor produselor' },
  { key: 'plan', short: 'Plan de plată', title: 'Planul de plată', icon: 'filePlus', accent: 'var(--step)', docs: [],
    from: 'Regulile băncii (cod)', what: 'sumele exacte, în bani, pe cote; liniile blocate (minor, depozit nescadent)' },
  { key: 'plata', short: 'Plată', title: 'Plata către moștenitori', icon: 'bank', accent: 'var(--step)', docs: [],
    from: 'Aprobatorul (om)', what: 'banii pleacă doar după aprobarea unui om' },
];
// escaladarea stă la etapa pe care o oprește
const ESC_STAGE = { minor_heir: 'plata', insurance_refused: 'asig', policy_mismatch: 'asig', indemnity_mismatch: 'asig',
  shares_invalid: 'cert', supplement_without_certificate: 'cert', post_death_mandate_withdrawal: 'dgep' };
const PF_CHIP = { done: 'făcut', waits: 'rândul tău', next: 'aici e oprit', locked: 'urmează', skip: 'nu a fost cazul' };

Object.assign(demo, { pick: null, wl: null, pf: null, pfOpen: null, pfBusy: false, pfNotes: {} });

// ---------- selecția și URL-ul (înapoi / înainte merg: fiecare schimbare a utilizatorului e o intrare în istoric) ----------
// #dosare (ecranul principal, și fără hash) · #dosare/<dosar> (dosarul complet) · #demo/<dosar> (fluxul dosarului) · #agenti · #impact
const VIEW_HASH = { cases: '#dosare', agents: '#agenti', impact: '#impact', results: '#rezultate', home: '#acasa' };
const pickFromHash = () => (/^#demo\/([\w-]+)/.exec(location.hash) || [])[1] || null;
let navPop = false, navReady = false, navPushed = 0;

// chemat de showView (app.js) și la schimbarea dosarului; `replace` = corectează intrarea curentă (pornire, hash greșit)
function demoHash(replace = false) {
  if (navPop) return;   // suntem în popstate: URL-ul e deja cel bun
  const want = ui.view === 'demo' ? `#demo/${demo.pick || DEMO_CASE}`
    : ui.view === 'cases' && ui.unmatched ? '#dosare/SC-NEIDENTIFICAT'
    : ui.view === 'cases' && /^SC-/.test(ui.selected || '') ? `#dosare/${ui.selected}` : VIEW_HASH[ui.view] || '';
  if (location.hash === want) { navReady = true; return; }
  const url = location.pathname + location.search + want;
  // „tab Dosare, apoi dosarul” în același clic (showView + select): o singură intrare în istoric
  const sameClick = want.startsWith('#dosare/') && location.hash === '#dosare' && Date.now() - navPushed < 400;
  if (replace || !navReady || sameClick) history.replaceState(null, '', url); else { history.pushState(null, '', url); navPushed = Date.now(); }
  navReady = true;
}

async function setPick(id, { stage = null } = {}) {
  demo.pick = id && id !== DEMO_CASE ? id : null;
  demo.cb.open = false;
  if (ui.view === 'demo') demoHash();
  demo.pf = null; demo.pfOpen = stage; demo.pfSig = '';
  if (demo.pick) await pfLoad();
  else renderDemo();
}

// fluxul unui dosar e un ecran peste lista de lucru: se deschide doar de pe un dosar și se închide cu „Înapoi” (sau Esc)
function flowBack() {
  return h('div', { class: 'flow-back' },
    h('button', { type: 'button', class: 'flow-back-btn', onclick: closeFlow, title: 'Înapoi la lista de dosare (Esc)' }, '← Înapoi la dosare'));
}
function closeFlow() {
  ui.selected = null; ui.unmatched = false;   // înapoi la listă (nu la ultimul dosar complet deschis): o singură intrare în istoric
  showView('cases');
  backToList();
}

// Din tabul Dosare: dosarul se deschide în demo, la etapa (pasul) unde e oprit; o singură intrare în istoric
async function openInDemo(id) {
  demo.pick = id && id !== DEMO_CASE ? id : null;
  demo.pf = null; demo.pfOpen = null; demo.pfSig = '';
  showView('demo');   // randează (și încarcă dosarul) și scrie #demo/<id>
  if (demo.pick) { await pfLoad(); await mPoll(); demo.open = mDefaultOpen(); renderDemo(); }
  else {   // Maria: pasul ei curent (cel care așteaptă o decizie, cel care lucrează, altfel următorul de făcut)
    await mPoll();   // starea pașilor de pe server: la prima intrare după încărcarea paginii nu e încă citită
    demo.open = mCurrentStep();
    renderDemo();
    mAutoSendPopup();
  }
  setTimeout(() => (document.querySelector('.station.gate.pending') || document.querySelector('.d-stage'))
    ?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 80);
}

// înapoi / înainte: vizualizarea și dosarul din URL
window.addEventListener('popstate', async () => {
  const view = location.hash.startsWith('#demo') ? 'demo' : location.hash.startsWith('#dosare') || !location.hash ? 'cases'
    : Object.keys(VIEW_HASH).find((v) => VIEW_HASH[v] === location.hash) || 'cases';
  const caseId = (/^#dosare\/([\w-]+)/.exec(location.hash) || [])[1] || null;
  navPop = true;
  try {
    if (view === 'demo') {
      const id = pickFromHash();
      const pick = id && id !== DEMO_CASE ? id : null;
      if (pick !== demo.pick) { demo.pick = pick; demo.pf = null; demo.pfOpen = null; demo.pfSig = ''; demo.cb.open = false; }
    } else if (view === 'cases' && caseId) { showView('cases'); if (ui.selected !== caseId) await select(caseId); return; }
    else if (view === 'cases' && ui.selected) backToList();
    showView(view);
  } finally { navPop = false; }
});

// lista din selector: întreaga bancă, nefiltrată (filtrele tabului Dosare rămân ale lui)
async function pfLoadList() {
  try { demo.wl = (await http('/worklist')).rows.filter((r) => r.kind !== 'unmatched'); } catch { demo.wl = demo.wl || []; }
}

async function pfLoad() {
  const id = demo.pick;
  demo.pfBusy = true;
  try {
    await pfLoadList();
    // un dosar care nu e în bancă (hash greșit): fără cerere care știm că dă 404
    if (demo.wl.length && !demo.wl.some((r) => r.case_id === id)) throw Object.assign(new Error('dosar inexistent'), { status: 404 });
    const c = await api.getCase(id);
    if (demo.pick !== id) return;   // între timp s-a ales alt dosar
    demo.pf = c;
  } catch (e) {
    toast(e.status === 404 ? `Dosarul ${id} nu există în bancă.` : e.message, true);
    demo.pick = null; demo.pf = null;
    if (ui.view === 'demo') demoHash(true);   // URL-ul greșit devine cel al Mariei, fără intrare nouă în istoric
  } finally { demo.pfBusy = false; }
  demo.pfSig = '';
  renderDemo();
}

// Selectorul e un combobox: câmp de căutare (nume, CNP, dosar; fără diacritice) cu lista filtrată pe loc sub el.
// ↑ ↓ mută selecția, Enter deschide dosarul, Esc închide; clic pe rezultat îl deschide.
const foldRo = (s) => String(s || '').toLocaleLowerCase('ro').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
demo.cb = { open: false, q: '', active: 0 };

function pickRows() {
  const rows = demo.wl || [];
  const maria = rows.find((r) => r.case_id === DEMO_CASE);
  // CNP-ul și clientul Mariei vin din scenariu (core_mock RC1001): înainte de primul document /worklist n-o are încă
  const out = [{ case_id: DEMO_CASE, name: 'Maria Ionescu', cnp: maria?.cnp || '2XXXXXXXXXXXX', cif: 'RC1001', state_label: maria?.state_label || null,
    decisions_count: 0, demo: true }, ...rows.filter((r) => r.case_id !== DEMO_CASE)];
  if (demo.pick && !out.some((r) => r.case_id === demo.pick)) out.push({ case_id: demo.pick, name: demo.pick });
  return out;
}

const pickLabel = (r) => `${r.name} · ${r.case_id}${r.demo ? ' · demo ghidat în 6 pași' : ''}${r.state_label ? ` · ${r.state_label}` : ''}`;

function pickMatches() {
  const words = foldRo(demo.cb.q).split(/\s+/).filter(Boolean);
  return pickRows().filter((r) => {
    const hay = foldRo(`${r.name} ${r.case_id} ${r.cnp || ''} ${r.cif || ''}`);
    return words.every((w) => hay.includes(w));
  });
}

function casePicker() {
  if (!demo.wl) pfLoadList().then(() => { if (demo.wl.length) renderDemo(); });
  const cb = demo.cb;
  const current = pickRows().find((r) => r.case_id === (demo.pick || DEMO_CASE));
  const list = h('ul', { id: 'demo-pick-list', class: 'cb-list', role: 'listbox', 'aria-label': 'Dosare',
    onmousedown: (ev) => ev.preventDefault() });   // clicul pe listă nu ia focusul câmpului (altfel s-ar închide înainte)
  const input = h('input', { id: 'demo-pick', type: 'text', role: 'combobox', autocomplete: 'off', spellcheck: 'false',
    'aria-label': 'Caută dosarul: nume, CNP sau număr de dosar', 'aria-controls': 'demo-pick-list', 'aria-autocomplete': 'list',
    'aria-expanded': String(cb.open), placeholder: 'Caută: nume, CNP sau dosar',
    value: cb.open ? cb.q : current ? pickLabel(current) : '' });
  const choose = (r) => {
    Object.assign(cb, { open: false, q: '', active: 0 });
    input.blur();
    if (r.case_id === (demo.pick || DEMO_CASE)) { demo.pfSig = ''; renderDemo(); return; }   // același dosar: doar eticheta revine
    setPick(r.case_id);
  };
  const paint = () => {
    const rows = pickMatches();
    cb.active = Math.max(0, Math.min(cb.active, rows.length - 1));
    input.setAttribute('aria-expanded', String(cb.open));
    list.hidden = !cb.open;
    if (!cb.open) { input.removeAttribute('aria-activedescendant'); return; }
    list.replaceChildren(...(rows.length ? rows.map((r, i) => h('li', { id: `demo-pick-${i}`, role: 'option', class: 'cb-opt' + (i === cb.active ? ' active' : ''),
      'aria-selected': String(i === cb.active), onclick: () => choose(r), onmousemove: () => { if (cb.active !== i) { cb.active = i; paint(); } } },
      h('b', {}, r.name), r.demo ? [' ', badge('demo ghidat', 'info')] : null,
      h('span', { class: 'cb-meta' }, [r.case_id, r.cnp ? `CNP ${r.cnp}` : null, r.state_label].filter(Boolean).join(' · ')),
      r.decisions_count ? h('span', { class: 'cb-dec' }, `${r.decisions_count} ${plural(r.decisions_count, 'decizie', 'decizii', 'de decizii')}`) : null))
      : [h('li', { class: 'cb-empty', role: 'option', 'aria-disabled': 'true' }, 'Niciun dosar nu se potrivește.')]));
    if (rows.length) {
      input.setAttribute('aria-activedescendant', `demo-pick-${cb.active}`);
      list.children[cb.active]?.scrollIntoView({ block: 'nearest' });
    }
  };
  const open = () => { if (!cb.open) { Object.assign(cb, { open: true, q: '', active: 0 }); input.value = ''; } paint(); };
  const close = () => { Object.assign(cb, { open: false, q: '', active: 0 }); input.value = current ? pickLabel(current) : ''; paint(); };
  input.addEventListener('focus', open);
  input.addEventListener('click', open);
  input.addEventListener('blur', () => { if (cb.open && input.isConnected) close(); });   // scos din pagină de o re-randare: nu închide
  input.addEventListener('input', () => { cb.open = true; cb.q = input.value; cb.active = 0; paint(); });
  input.addEventListener('keydown', (ev) => {
    const rows = pickMatches();
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
      ev.preventDefault();
      if (!cb.open) { open(); return; }
      if (rows.length) cb.active = (cb.active + (ev.key === 'ArrowDown' ? 1 : -1) + rows.length) % rows.length;
      paint();
    } else if (ev.key === 'Enter') {
      ev.preventDefault();
      if (cb.open && rows[cb.active]) choose(rows[cb.active]);
    } else if (ev.key === 'Escape') {
      ev.preventDefault(); close(); input.blur();
    }
  });
  paint();
  // o re-randare a demo-ului (sondările) în timp ce cauți: câmpul nou își ia înapoi focusul și textul
  if (cb.open) setTimeout(() => { if (document.activeElement !== input && input.isConnected) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); } });
  return h('div', { class: 'd-pick' }, h('label', { for: 'demo-pick' }, 'Dosar:'), h('div', { class: 'cb' }, input, list));
}

// ---------- parcursul unui dosar din portofoliu ----------
function pfRow() { return (demo.wl || []).find((r) => r.case_id === demo.pick) || null; }

// împarte jurnalul pe etape: evenimentele de după „Primit: <document>” îi aparțin documentului, până la următorul
function pfEvents(c) {
  const byStage = Object.fromEntries(PF_STAGES.map((s) => [s.key, []]));
  const docStage = Object.fromEntries((c.documents || []).map((d) => [d.document_id, PF_STAGES.find((s) => s.docs.includes(d.document_type))?.key]));
  let cur = 'dgep';
  for (const e of c.events || []) {
    if (e.kind === 'document' && e.document_id && /^Primit:/.test(e.detail || '')) { cur = docStage[e.document_id] || cur; continue; }
    const d = e.detail || '';
    const k = /Plata aprobată|Plan de plată respins|Plată .*aprobat/i.test(d) ? 'plata' : /Plan de plată (generat|amânat)/i.test(d) ? 'plan' : cur;
    byStage[k].push(e);
  }
  return byStage;
}

function pfStages(c, row) {
  const hist = new Set((c.state_history || []).map((x) => x.state));
  const decisions = row?.decisions || [];
  const insured = (c.products || []).some((p) => p.insurance) || hist.has('INSURANCE_CLAIM_OPEN');
  const miss = c.missing || [];
  const done = {
    dgep: hist.has('DEATH_SIGNALLED') || hist.has('FROZEN'),
    notar: hist.has('NOTARY_ANSWERED') && !decisions.some((d) => d.kind === 'semnatura'),
    asig: hist.has('INSURANCE_SETTLED'),
    cert: hist.has('HEIR_CERT_RECEIVED') && !miss.some((m) => /suplimentar/.test(m)),
    plan: hist.has('PLAN_DRAFTED'),
    plata: hist.has('PAID'),
  };
  const touched = { notar: hist.has('NOTARY_ANSWERED'), asig: hist.has('INSURANCE_CLAIM_OPEN'), cert: hist.has('HEIR_CERT_RECEIVED') };
  const esc = (c.escalations || []).filter((e) => e.status !== 'închis');
  const docType = Object.fromEntries((c.documents || []).map((d) => [d.document_id, d.document_type]));
  const list = PF_STAGES.map((s, i) => ({ ...s, i, done: done[s.key], touched: touched[s.key] || done[s.key], insured, gates: [] }));
  const at = (key) => list.find((s) => s.key === key);
  // „Rândul tău”: deciziile care așteaptă un om, pe etapa lor
  for (const d of decisions) {
    if (d.kind === 'plata') at('plata').gates.push({ kind: 'plata', text: d.text });
    if (d.kind === 'semnatura') at('notar').gates.push({ kind: 'semnatura', text: d.text });
  }
  // asigurarea contează doar la un credit asigurat; adresa notarului vine când o cere notarul, deci nu oprește dosarul
  const applies = (s) => s.key !== 'asig' || insured;
  const firstOpen = () => list.find((s) => !s.done && applies(s) && (s.key !== 'notar' || s.touched)) || null;
  for (const e of esc) {
    const byDoc = PF_STAGES.find((s) => s.docs.includes(docType[e.document_id]))?.key;
    const st = at(ESC_STAGE[e.code] || byDoc) || firstOpen() || list[list.length - 1];
    st.gates.push({ kind: 'escaladare', esc: e, text: `Escaladare: ${human(ESC_LABEL, e.code)}` });
  }
  const ladder = decisions.find((d) => d.kind === 'scara');
  if (ladder) (firstOpen() || list[list.length - 1]).gates.push({ kind: 'scara', text: ladder.text });
  // complet = toate etapele care se aplică sunt făcute (asigurarea fără credit asigurat, notarul care n-a cerut nimic nu țin dosarul)
  const stop = list.find((s) => s.gates.length) || firstOpen();
  const laterDone = (i) => list.slice(i + 1).some((s) => s.done);
  for (const s of list) {
    s.state = s.gates.length ? 'waits' : s.done ? 'done' : s === stop ? 'next'
      : !applies(s) || (laterDone(s.i) && !s.touched) || (!stop && !s.done) ? 'skip' : 'locked';
  }
  return { list, stop };
}

// „Ce urmează” la etapa unde e oprit: textul listei de lucru (decizie, scara de contact, documente), apoi ce lipsește, pe scurt
function pfNext(c, row) {
  const n = row?.next;
  const miss = c.missing || [];
  return [
    h('p', {}, h('b', {}, n?.text || 'Așteptăm următorul document.'),
      n?.due ? h('span', { class: 'muted small' }, ` · ${fmtDate(n.due)}${n.status ? ' · ' + n.status : ''}`) : null),
    miss.length ? h('div', { class: 'small' }, h('b', {}, 'Mai lipsește: '),
      // „documentele pentru dosarul de daună: a; b; c” → doar capul; lista întreagă rămâne în title și în dosarul complet
      miss.map((m, i) => [i ? '; ' : '', h('span', { title: m }, m.split(': ')[0])])) : null];
}

// Același flux ca la Maria (demo-manual.js): roadmap-ul pașilor dosarului, bara cu ce urmează, stațiile și porțile;
// starea e a dosarului (demo.byCase), deci comuți între dosare și te întorci exact unde erai
function renderPortfolio(root) {
  const c = demo.caseNow || demo.pf;
  mStartPolling();
  if (!c || !mCount()) {
    if (!Object.keys(demo.srv).length) mPoll();
    root.replaceChildren(pfHero(null), h('div', { class: 'card' }, h('p', {}, h('span', { class: 'spinner' }), ' Se încarcă dosarul ', demo.pick, '…')));
    return;
  }
  if (!demo.open || demo.open > mCount()) demo.open = mDefaultOpen();
  root.replaceChildren(h('div', { class: 'pf-view' }, pfHero(c, pfRow()),
    h('div', { class: 'd-main' }, h('div', { class: 'd-col' }, demoRoadmap(demo.step, demo.open), mNextBar(demo.open), mStage(demo.open)))));
  mTick();
}

// pfStages / pfRoadmap / pfStage / pfGate (parcursul pe etape, fără pași de rulat) nu mai sunt folosite de flux

// același antet ca la Maria: persoana decedată, dosarul, etapele parcurse și cifrele lui (fără starea dosarului)
function pfHero(c, row, stop) {
  const n = demo.open || mDefaultOpen();
  return h('section', { class: 'd-hero' },
    h('div', { class: 'd-hero-text' }, flowBack(),
      c ? personHeader(c, { done: demo.step, total: mCount(), label: 'Pași parcurși',
        side: n ? [pipeButton(n), mPipe(n).status === 'done' ? null : pipeStatus(n)] : null })
        : h('h1', {}, 'Dosar din portofoliu')));
}

// CTA-ul spre vizualizarea completă a dosarului: iconiță, rezumat (documente · scrisori · decizii), săgeată.
// Scrisorile vin din GET /cases/{id}/artifacts (asincron, o dată pe versiunea dosarului); rezumatul se completează pe loc.
const ctaLetters = {};
function fullCaseCta(c, row) {
  const id = c.id || c.case_id;
  const docs = (c.documents || []).length;
  const dec = row ? row.decisions_count : ((c.payments || []).some((p) => p.status === 'pending_approval') ? 1 : 0)
    + (c.escalations || []).filter((e) => (e.status || 'deschis') !== 'închis').length;
  const key = `${id}:${c.updated_at}:${(c.events || []).length}`;
  const parts = (letters) => [`${fmtNum(docs)} ${plural(docs, 'document', 'documente', 'de documente')}`,
    letters == null ? null : `${fmtNum(letters)} ${plural(letters, 'scrisoare', 'scrisori', 'de scrisori')}`,
    dec ? `${fmtNum(dec)} ${plural(dec, 'decizie', 'decizii', 'de decizii')}` : 'nicio decizie'].filter(Boolean).join(' · ');
  const sum = h('span', { class: 'cta-sum' }, parts(ctaLetters[key]));
  if (ctaLetters[key] == null) api.artifacts(id).then((a) => { ctaLetters[key] = (a.letters || []).length; sum.textContent = parts(ctaLetters[key]); }).catch(() => {});
  return h('button', { type: 'button', class: 'case-cta' + (dec ? ' has-dec' : ''), 'data-cta': id,
    'aria-label': `Deschide dosarul complet ${id}: ${parts(ctaLetters[key])}`,
    onclick: () => { ui.focus = dec ? 'todo' : null; showView('cases'); select(id); } },
    h('span', { class: 'cta-ico' }, svgIcon('folder')),
    h('span', { class: 'cta-main' }, h('span', { class: 'cta-k' }, 'Vizualizarea completă'), h('b', {}, 'Deschide dosarul complet'), sum),
    h('span', { class: 'cta-arrow', 'aria-hidden': 'true' }, '→'));
}

// antetul persoanei (demo.js, Maria și portofoliu) primește CTA-ul în rândul cifrelor, în locul linkului mic „Dosarul complet →”
{
  const base = personHeader;
  // eslint-disable-next-line no-func-assign
  personHeader = function (c, opts) {
    const el = base(c, opts);
    if (!c) return el;
    el.querySelector('.dp-open')?.remove();
    el.querySelector('.dp-tiles')?.append(h('div', { class: 'dp-cta' }, fullCaseCta(c, (demo.wl || []).find((r) => r.case_id === c.id) || null)));
    return el;
  };
}

function pfRoadmap(c, list, stop) {
  const total = list.length;
  const lastDone = list.reduce((a, s) => (s.state === 'done' || s.state === 'skip' ? s.i : a), -1);
  const to = lastDone <= 0 ? 0 : lastDone / (total - 1);
  const waiting = list.reduce((a, s) => a + s.gates.length, 0);
  const nodes = list.map((s) => {
    const icon = s.state === 'done' ? 'check' : s.state === 'skip' ? 'x' : s.state === 'locked' ? 'lock' : s.state === 'waits' ? 'hand' : s.icon;
    return h('li', { class: `rm-node ${s.state}${s.i === demo.pfOpen ? ' open' : ''}`, style: `--accent:${s.accent}` },
      h('button', { type: 'button', class: 'rm-dot', 'aria-current': s.i === demo.pfOpen ? 'step' : null,
        'aria-label': `Etapa ${s.i + 1}: ${s.title} (${PF_CHIP[s.state]})`, onclick: () => { demo.pfOpen = s.i; renderDemo(); } },
        svgIcon(icon), h('span', { class: 'rm-num' }, String(s.i + 1))),
      h('span', { class: 'rm-title' }, s.short),
      s.state === 'done' ? h('span', { class: 'rm-chip done' }, 'complet')
        : s.state === 'waits' || s.state === 'next' ? h('span', { class: 'rm-chip partial' }, s.state === 'waits' ? 'Rândul tău' : 'aici e oprit')
        : s.state === 'skip' ? h('span', { class: 'rm-chip skip' }, s.key === 'asig' && !s.insured ? 'fără asigurare' : 'nu a fost cazul') : null,
      h('div', { class: 'rm-tip', role: 'tooltip' },
        h('div', { class: 'rm-tip-head' }, svgIcon(s.icon), h('div', {}, h('b', {}, `Etapa ${s.i + 1}: ${s.title}`), h('div', { class: 'small muted' }, s.from))),
        h('p', { class: 'small' }, s.what)));
  });
  return h('section', { class: 'card roadmap' },
    h('div', { class: 'rm-head' },
      h('div', {}, h('h3', {}, 'Drumul dosarului'),
        h('p', { class: 'small muted' }, stop ? `${list.filter((s) => s.state === 'done').length} din ${list.filter((s) => s.state !== 'skip').length} etape făcute`
          : 'Dosar complet: toate etapele sunt făcute', waiting ? ' · ' : '',
          waiting ? h('b', { class: 'bad-text' }, `${waiting} ${waiting === 1 ? 'decizie te așteaptă' : 'decizii te așteaptă'}`) : ''))),
    h('div', { class: 'rm-track' },
      h('div', { class: 'rm-line' },
        h('div', { class: 'rm-fill', style: `width:${to * 100}%` }),
        stop && stop.i > 0 ? h('div', { class: 'rm-next', style: `left:${((stop.i - 1) / (total - 1)) * 100}%;width:${100 / (total - 1)}%` }) : null),
      h('ol', { class: 'rm-nodes', style: `grid-template-columns:repeat(${total}, minmax(0, 1fr))` }, nodes)));
}

function pfStage(c, row, s, stop) {
  const events = pfEvents(c)[s.key];
  const docs = (c.documents || []).filter((d) => s.docs.includes(d.document_type));
  const isStop = stop && s.i === stop.i;
  return h('section', { class: 'd-stage', style: `--accent:${s.accent}` },
    h('ol', { class: 'stations' },
      docs.map((d) => h('li', { class: 'station done' },
        stationHead('▤', 'doc', DOC_TYPES[d.document_type] || d.document_type, `primit ${fmtDate(d.received_at)}`),
        h('button', { type: 'button', class: 'link', onclick: () => previewDocument(c.id, d) }, 'Vezi documentul'))),
      events.length ? h('li', { class: 'station code done' },
        stationHead('⚙', 'code', 'Regulile băncii', `${events.length} ${plural(events.length, 'pas', 'pași', 'de pași')} în jurnal, fiecare cu regula aplicată`),
        h('ul', { class: 'checks' }, events.map((e) => h('li', {}, e.detail, e.rule ? h('span', { class: 'rule' }, ' · ', e.rule) : null)))) : null,
      s.key === 'plata' || s.key === 'plan' ? (c.payment_plan ? h('li', { class: 'station note' }, planCard(c, pfPlan(c))) : null) : null,
      s.gates.map((g) => pfGate(c, g)),
      !s.gates.length && s.state !== 'done' ? h('li', { class: 'station note' },
        stationHead('→', 'code', s.state === 'skip' ? 'Nu a fost cazul la acest dosar' : isStop ? 'Ce urmează' : 'Încă nesosit'),
        s.state === 'skip' ? h('p', {}, 'Etapa nu se aplică sau a fost sărită: dosarul a mers mai departe fără ea.')
          : isStop ? pfNext(c, row) : h('p', {}, 'Vine după etapa unde e oprit dosarul.')) : null,
      s.state === 'done' && stop && s.i < stop.i ? h('li', { class: 'station note' },
        h('p', { class: 'small' }, 'Etapa e făcută. ', h('button', { type: 'button', class: 'link', onclick: () => { demo.pfOpen = stop.i; renderDemo(); } },
          `Mergi la etapa unde e oprit: ${stop.short} →`))) : null));
}

// planul, cu aprobatorul din jurnal (GET /cases nu-l pune pe plan), ca în cardul Mariei: „Plan aprobat de …”
function pfPlan(c) {
  const ev = [...(c.events || [])].reverse().find((e) => /^Plata aprobată de /.test(e.detail || ''));
  return { ...c.payment_plan, approved_by: c.payment_plan.approved_by || (/^Plata aprobată de (.+?)(?: \(|:)/.exec(ev?.detail || '') || [])[1] };
}

// „Rândul tău”: aceeași oprire la om ca în demo-ul Mariei; numele rămâne în audit
function pfGate(c, g) {
  const id = `${c.id}:${g.kind}:${g.esc?.id || ''}`;
  const keep = (k) => (ev) => { demo.pfNotes[`${id}:${k}`] = ev.target.value; };
  const who = h('input', { type: 'text', placeholder: g.kind === 'semnatura' ? 'Numele semnatarului' : 'Numele tău (apare în audit)',
    value: demo.pfNotes[`${id}:who`] ?? lsGet('approver'), 'aria-label': 'Numele tău', oninput: keep('who') });
  const note = h('input', { type: 'text', value: demo.pfNotes[`${id}:note`] || '', oninput: keep('note'),
    placeholder: g.kind === 'escaladare' ? 'Decizia ta (obligatorie): ce ai verificat, ce faci' : 'Motivul respingerii (obligatoriu la „nu”)', 'aria-label': 'Observație' });
  const busy = demo.pfBusy;
  const name = () => { const v = who.value.trim(); if (!v) { who.focus(); toast('Scrie numele tău, ca să rămână în audit.', true); } else lsSet('approver', v); return v; };
  const pay = (c.payments || []).find((p) => p.status === 'pending_approval');
  let body = [], buttons = [];
  if (g.kind === 'plata' && pay) {
    body = [h('p', { class: 'small' }, h('b', {}, 'Către: '), 'moștenitorii din plan (liniile neblocate). ', fmtMoney(pay.total), ' de aprobat; liniile blocate rămân pe loc.')];
    buttons = [h('button', { type: 'button', class: 'primary', disabled: busy, onclick: async () => {
      if (who.value.trim()) lsSet('approver', who.value.trim());
      const by = await confirmApprove(c.payment_plan, pay, c);
      if (by) pfAct(() => api.approve(pay.payment_id, by), `Plata ${fmtMoney(pay.total)} aprobată de ${by}.`);
    } }, '✔ Aprob plata…'), note,
    h('button', { type: 'button', class: 'danger', disabled: busy, onclick: () => {
      if (!note.value.trim()) { note.focus(); toast('Scrie de ce respingi planul.', true); return; }
      pfAct(() => api.reject(pay.payment_id, note.value.trim()), 'Planul a fost respins. Nu a plecat nimic.');
    } }, '✗ Resping')];
  } else if (g.kind === 'semnatura') {
    body = [h('p', { class: 'small' }, h('b', {}, 'Către: '), 'notarul din dosar. Răspunsul (soldurile la data decesului) e redactat de sistem; pleacă doar semnat de un om.'),
      h('p', {}, h('button', { type: 'button', class: 'link', onclick: () => { ui.tab = 'corr'; showView('cases'); select(c.id); } }, 'Citește răspunsul în corespondența dosarului'))];
    buttons = [who, h('button', { type: 'button', class: 'primary', disabled: busy, onclick: () => {
      const by = name(); if (by) pfAct(() => api.signNotaryAnswer(c.id, by), `Răspunsul către notar a fost semnat de ${by}.`);
    } }, '✔ Semnez răspunsul către notar')];
  } else if (g.kind === 'escaladare') {
    const e = g.esc;
    body = [h('div', { class: 'callout warn' }, h('b', {}, 'De verificat: '), e.reason), guardFlags(e.flags),
      h('p', {}, h('button', { type: 'button', class: 'link', onclick: () => { ui.tab = 'audit'; showView('cases'); select(c.id); } }, 'Vezi escaladarea în dosar (Audit)'))];
    buttons = [who, note, h('button', { type: 'button', class: 'primary', disabled: busy, onclick: () => {
      const by = name(); if (!by) return;
      if (!note.value.trim()) { note.focus(); toast('Scrie decizia ta: rămâne în dosar.', true); return; }
      pfAct(() => api.resolveEscalation(c.id, e.id, `${note.value.trim()} (${by})`), `${e.id} rezolvată de ${by}.`);
    } }, '✔ Rezolv escaladarea')];
  } else {   // scara de contact: pasul operatorului se face din corespondența dosarului
    buttons = [h('button', { type: 'button', class: 'primary', onclick: () => { ui.tab = 'corr'; showView('cases'); select(c.id); } }, 'Deschide scara de contact →')];
  }
  return h('li', { class: 'station gate pending' },
    stationHead('◆', 'human', `Rândul tău: ${g.text}`), ...body, h('div', { class: 'gate-form' }, ...buttons));
}

// decizia pleacă la API; apoi recitim dosarul și deschidem etapa unde a rămas oprit
async function pfAct(fn, okMsg) {
  demo.pfBusy = true; demo.pfSig = ''; renderDemo();
  try {
    await fn();
    toast(okMsg);
    demo.pfOpen = null;
    Object.keys(demo.pfNotes).forEach((k) => { if (k.endsWith(':note')) delete demo.pfNotes[k]; });
  } catch (e) { toast((e.message.match(/"detail":"([^"]+)"/) || [])[1] || e.message, true); }
  demo.pfBusy = false;
  await pfLoad();
  refresh();
}

demo.pick = pickFromHash() === DEMO_CASE ? null : pickFromHash();
