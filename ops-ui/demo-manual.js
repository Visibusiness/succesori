// Demo ghidat, modul „Pas cu pas”: operatorul pornește fiecare apel AI (sau tot pipeline-ul unui document) și vede tot
// timpul ce face AI-ul. Fiecare document trece prin stații: Documentul (scanarea) → AI Extractorul → Regulile băncii (cod)
// → câte un agent AI pe fiecare predare → „Rândul tău” (OM) înainte să plece ceva din bancă: scrisoarea către notar sau
// asigurător, mesajul către moștenitor, decizia pe propunerea investigatorului, plata. Pipeline-ul unui pas rulează pe
// server, stație după stație, se oprește la fiecare decizie a omului și poate fi oprit oricând (■).
// Panoul „Activitate AI” arată fiecare apel: în coadă, lucrează (cu secunde), gata (durată, cost), eșuat, anulat.
// API: agent/ai_jobs.py (POST /demo/ai/extract|apply|agent|gate|pipeline|audit, GET /demo/ai/jobs|steps, GET /demo/scan/{n}.png).
// Același flux pe ORICE dosar (?case=<id>): Maria are cei 6 pași ai ei (STORY); un dosar din portofoliu are pașii lui de la server
// (documentele din dosar, făcute; documentele care n-au venit încă; apoi ce așteaptă dosarul acum: agentul, poarta).
// Starea (pași, apeluri AI, porți, ce e deschis) se ține pe dosar, în demo.byCase[id]: comuți și te întorci exact unde erai.
// Depinde de demo.js (demo, STORY, SHOWN_FIELDS, renderDemo, demoNewEvents, escText, demoDoc), app.js (confirmApprove,
// lsGet/lsSet, …) și live.js (ACTION_LABEL, AGENT_LABEL, apState, stripMeta).

const AI_TONE = { queued: 'info', running: 'warn', done: 'ok', failed: 'bad', cancelled: 'info' };
const AI_STATUS = { queued: 'în coadă', running: 'lucrează', done: 'gata', failed: 'eșuat', cancelled: 'anulat' };
// simboluri din fonturile obișnuite (pe unele mașini nu există font emoji și ar apărea ca pătrățele)
const AGENT_ICON = { extractor: '◉', correspondent: '✉', 'case-investigator': '⚑', 'heir-communicator': '✆', auditor: '✔' };
// textele unei opriri la om, pe tipul ei (agent/ai_jobs.py: extract, letter, message, investigation, payment)
const GATE_TEXT = {
  extract: { yes: '✔ Am verificat scanarea, continuă', no: '✗ Respinge documentul' },
  letter: { yes: '✔ Aprob și trimit', no: '✗ Nu trimite' },
  message: { yes: '✔ Aprob și trimit', no: '✗ Nu trimite' },
  investigation: { yes: '✔ Accept propunerea și închid escaladarea', no: '✗ O las deschisă' },
  payment: { yes: '✔ Aprob plata…', no: '✗ Resping' },
};
const PIPE_TEXT = { idle: 'nepornit', running: 'rulează', awaiting: 'așteaptă decizia ta', stopping: 'se oprește', stopped: 'oprit',
  done: 'complet', failed: 'eșuat' };
// fără comutatoare pe pagină: mereu pas cu pas, cu pipeline-uri, pe moștenirea legală (varianta A)
Object.assign(demo, { mode: 'manual', variant: 'A', manualOn: false, mTimer: null, byCase: {} });

// ---------- starea pe dosar: demo.step, demo.srv, demo.jobs… sunt ale dosarului ales acum (demo.pick, altfel Maria) ----------
const curCase = () => demo.pick || DEMO_CASE;
const isMaria = (cid = curCase()) => cid === DEMO_CASE;
const caseQ = (cid = curCase()) => `case=${encodeURIComponent(cid)}`;
const newCaseState = () => ({ step: 0, results: [], cases: [], caseNow: null, open: 0, srv: {}, jobs: [], sig: '', gsig: '',
  outOpen: {}, mBusy: {}, notes: {}, popShown: {}, previewOpen: {}, approvedBy: null, shownStage: null, rmFill: null, rmDone: null, started: false });
const caseState = (cid = curCase()) => (demo.byCase[cid] ||= newCaseState());
['step', 'results', 'cases', 'caseNow', 'open', 'srv', 'jobs', 'sig', 'gsig', 'outOpen', 'mBusy', 'notes', 'popShown', 'previewOpen',
  'approvedBy', 'shownStage', 'rmFill', 'rmDone'].forEach((k) => Object.defineProperty(demo, k,
  { get: () => caseState()[k], set: (v) => { caseState()[k] = v; }, enumerable: true, configurable: true }));

// pașii dosarului ales: la Maria povestea ei (STORY + STEP_LOOK), la celelalte ce spune serverul (meta fiecărui pas)
const DOC_ICON = { dgep_signal: 'signal', death_certificate: 'fileAlert', notary_request: 'notary', insurance_certificate: 'shield',
  insurer_response: 'shieldOk', heir_certificate: 'heirs', supplementary_certificate: 'filePlus' };
const DOC_SHORT = { dgep_signal: 'Semnal DGEP', death_certificate: 'Certificat de deces', notary_request: 'Adresa notarului',
  insurance_certificate: 'Asigurare', insurer_response: 'Răspuns asigurător', heir_certificate: 'Moștenitori', supplementary_certificate: 'Supliment' };
const ACTION_LOOK = { 'case-investigator': ['fileAlert', 'Escaladarea'], correspondent: ['notary', 'Răspunsul către notar'],
  'heir-communicator': ['heirs', 'Mesajul către moștenitori'], payment: ['bank', 'Plata'] };
function mSteps() {
  if (isMaria()) return STORY.map((s, i) => ({ ...s, ...STEP_LOOK[i], n: i + 1, kind: 'doc', scan: i > 0 }));
  return Object.keys(demo.srv).map(Number).sort((a, b) => a - b).map((n) => {
    const m = demo.srv[n].meta || {};
    const act = m.kind === 'action' ? ACTION_LOOK[m.action] || ['hand', 'Rândul tău'] : null;
    return { n, kind: m.kind, pending: Boolean(m.pending), history: m.kind === 'doc' && !m.pending, scan: Boolean(m.scan), meta: m,
      title: m.title || DOC_TYPES[m.document_type] || `Pasul ${n}`, short: act ? act[1] : DOC_SHORT[m.document_type] || m.title || `Pasul ${n}`,
      icon: act ? act[0] : DOC_ICON[m.document_type] || 'notary', accent: 'var(--step)', sender: m.from || '', from: m.from || '',
      date: m.date ? fmtDate(m.date) : '', why: demo.srv[n].result?.why || '' };
  });
}
const mStep = (n) => mSteps()[n - 1] || { n, title: `Pasul ${n}`, short: `Pasul ${n}`, icon: 'notary', accent: 'var(--step)', sender: '' };
const mCount = () => mSteps().length;
// rezultatul pasului: la un pas „ce așteaptă dosarul” vine de la server de la început (agenții de pornit), deși nu e încă făcut
const mResult = (n) => demo.results[n - 1] || demo.srv[n]?.result || null;
const mHasScan = (n) => (isMaria() ? n > 1 : Boolean(demo.srv[n]?.meta?.scan));
// pasul deschis implicit: primul care așteaptă ceva (o decizie, un apel AI, documentul următor), altfel ultimul
function mDefaultOpen() {
  return mCount() ? mCurrentStep() : 0;   // același criteriu pe orice dosar (mCurrentStep, mai jos)
}

// ---------- date ----------
const mLast = (pred) => demo.jobs.filter(pred).pop() || null;
const mExtractJob = (n) => mLast((j) => j.kind === 'extract' && j.step === n);
const mAgentJob = (n, key) => mLast((j) => j.kind === 'agent' && j.step === n && j.key === key);
const mApplied = (n) => Boolean(demo.results[n - 1]);
const mGate = (n, key) => demo.srv[n]?.gates?.[key] || null;
const mPipe = (n) => demo.srv[n]?.pipeline || { status: 'idle' };
const mPipeLive = (n) => ['running', 'awaiting', 'stopping'].includes(mPipe(n).status);
const mPending = () => Object.values(demo.srv).flatMap((s) => Object.values(s.gates || {})).filter((g) => g.status === 'pending');
const mActive = () => demo.jobs.some((j) => j.status === 'queued' || j.status === 'running')
  || Object.keys(demo.srv).some((n) => mPipeLive(Number(n)));

// starea vine de pe server: pipeline-ul aplică regulile și deschide opririle la om fără browser
async function mPoll() {
  if (ui.view !== 'demo' || demo.mode !== 'manual') return;
  const cid = curCase();
  // un dosar din URL care nu e în bancă: nicio cerere (pfLoad îl verifică în lista de lucru și revine la Maria)
  if (!isMaria(cid) && !(demo.wl || []).some((r) => r.case_id === cid)) return;
  const S = caseState(cid);   // răspunsul merge în dosarul pentru care s-a cerut, chiar dacă între timp s-a ales altul
  try {
    const [jobs, steps] = await Promise.all([http(`/demo/ai/jobs?${caseQ(cid)}`), http(`/demo/ai/steps?${caseQ(cid)}`)]);
    const was = Object.fromEntries(S.jobs.map((j) => [j.id, j.status]));
    S.jobs = jobs;
    S.srv = Object.fromEntries(Object.entries(steps).map(([k, v]) => [Number(k), v]));
    const changed = new Set();
    for (const [k, s] of Object.entries(S.srv)) {
      const n = Number(k);
      // pasul cu ce așteaptă dosarul are rezultatul de la început: contează „făcut” abia când e complet
      if (s.result && !S.results[n - 1] && (s.meta?.kind !== 'action' || s.next?.do === 'done')) {   // reguli aplicate (de pipeline sau din alt tab)
        S.results[n - 1] = { ...s.result, _doc: s.result.source };
        S.step = Math.max(S.step, n);
        changed.add(n);
      }
    }
    // un agent sau o decizie a omului a schimbat dosarul (mesaj trimis, plată aprobată, escaladare închisă): îl recitim
    jobs.filter((j) => j.kind === 'agent' && j.status !== was[j.id] && ['done', 'failed'].includes(j.status)).forEach((j) => changed.add(j.step));
    const gsig = Object.values(S.srv).flatMap((s) => Object.values(s.gates || {}).map((g) => g.step + g.key + g.status)).join(',');
    if (gsig !== S.gsig) { S.gsig = gsig; S.results.forEach((r, i) => r && changed.add(i + 1)); }
    if (!S.caseNow && !isMaria(cid)) changed.add(1);
    if (isMaria(cid)) for (const n of changed) await mRefreshCase(n, S);
    else if (changed.size) await mRefreshCase([...changed], S, cid);   // un singur dosar: o singură citire
    const sig = jobs.map((j) => j.id + j.status).join(',') + JSON.stringify(Object.values(S.srv).map((s) => [s.pipeline, s.next])) + gsig;
    if ((sig !== S.sig || changed.size) && cid === curCase()) { S.sig = sig; renderDemo(); }
    if (cid === curCase()) mAutoSendPopup();
  } catch { /* server fără /demo/ai: rămâne ultima stare */ }
  mTick();
}

// ---------- verificarea a ce pleacă din bancă: fereastra cu documentul întreg, înainte de trimitere ----------
const SEND_KINDS = ['letter', 'message'];
// când pasul ajunge la o scrisoare sau un mesaj de trimis, fereastra se deschide singură (o dată pe oprire)
// Pe pasul deschis întâi; altfel pe pasul care chiar așteaptă (fluxul redeschis din listă, reîncărcat sau deschis pe alt pas):
// fluxul trece pe pasul acela, ca fereastra și butoanele opririi să fie pe ecran.
function mAutoSendPopup() {
  if (document.querySelector('.modal') || ui.view !== 'demo') return;   // pe dosarul deschis (oricare: popShown e al lui)
  const unseen = (x) => x.status === 'pending' && SEND_KINDS.includes(x.kind) && !demo.popShown[`${x.step}:${x.key}`];
  const g = Object.values(demo.srv[demo.open || 1]?.gates || {}).find(unseen) || mPending().find(unseen);
  if (!g) return;
  demo.popShown[`${g.step}:${g.key}`] = true;
  if (demo.open !== g.step) { demo.open = g.step; renderDemo(); }
  mSendFlow(g.step, g);
}

// pasul pe care se deschide fluxul Mariei: cel care așteaptă decizia ta, altfel cel care lucrează, altfel următorul de făcut
function mCurrentStep() {
  const g = mPending()[0];
  if (g) return g.step;
  const live = Object.keys(demo.srv).map(Number).filter((n) => mPipeLive(n))
    .concat(demo.jobs.filter((j) => j.step && ['queued', 'running'].includes(j.status)).map((j) => j.step));
  if (live.length) return Math.min(...live);
  if (isMaria()) return Math.min(demo.step + 1, mCount());
  return mSteps().find((s) => demo.srv[s.n]?.next?.do !== 'done')?.n || mCount();   // alt dosar: primul pas nefăcut
}

// deschide fereastra; la „Trimite” decizia merge pe server ca la butonul din oprire
async function mSendFlow(n, g) {
  const by = await mConfirmSend(n, g);
  if (!by) return;
  const who = h('input', { type: 'text', value: by });
  await mDecide(n, g, true, who);
}

const mPdfUrl = (n, g) => `${API_BASE}/demo/ai/gate/${n}/${encodeURIComponent(g.key)}/pdf${isMaria() ? '' : `?${caseQ()}`}`;
const mPdfName = (g) => `${g.case_id || 'scrisoare'}-${g.action || g.key}.pdf`;

// ---------- previzualizarea unui document generat de bancă: fereastra comună din doc-actions.js (openDocPreview) ----------
// opts: { title, sub, pdf (URL) | text (markdown), name (fișierul descărcat) }; stilurile sunt în doc-actions.css.
const mDocViewStyle = () => {};
const mDocView = (opts) => openDocPreview({ title: opts.title, subtitle: opts.sub, url: opts.pdf || null,
  markdown: opts.pdf ? null : (opts.text || '(agentul nu a produs text)'), downloadName: opts.name, back: opts.back });
const mEyeIcon = () => docIcon('eye');

// Previzualizează + Descarcă pentru orice document scris de agenți, pe orice dosar: un singur punct de apel.
// Componenta generică (doc-actions.js, window.docActions) când există; până atunci fereastra de aici (mDocButtons).
// `match`: documentul din registrul GET /cases/{id}/generated (doc-actions.js); până apare acolo, fereastra de aici
function mDocActions(opts, match) {
  if (!match || typeof generatedDocs !== 'function' || typeof docActions !== 'function') return mDocButtons(opts);
  const slot = h('div', { class: 'doc-slot' }, mDocButtons(opts));
  generatedDocs(curCase()).then((all) => { const d = all.find(match); if (d) slot.replaceChildren(docActions(d)); }).catch(() => {});
  return slot;
}

// butonul principal „Previzualizează” + descărcarea, secundară
function mDocButtons(opts) {
  const dl = opts.pdf ? h('a', { href: opts.pdf, download: opts.name, class: 'doc-download' }, '⤓ Descarcă PDF')
    : opts.text ? h('a', { href: '#', class: 'doc-download', onclick: (ev) => {
      const u = URL.createObjectURL(new Blob([opts.text], { type: 'text/markdown;charset=utf-8' }));
      ev.currentTarget.href = u; ev.currentTarget.download = opts.name || 'document.md';
      setTimeout(() => URL.revokeObjectURL(u), 5000);
    } }, '⤓ Descarcă') : null;
  return h('div', { class: 'doc-actions' },
    h('button', { type: 'button', class: 'doc-preview', onclick: (ev) => mDocView({ ...opts, back: ev.currentTarget }) }, mEyeIcon(), 'Previzualizează'),
    opts.noDownload ? null : dl);
}

// ce se previzualizează pentru o oprire la om: scrisoarea ca PDF, restul ca text
function mGateDoc(n, g) {
  const s = mStep(n);
  const sub = `Pasul ${n} (${s?.title || ''}) · ${['investigation', 'extract'].includes(g.kind) ? 'pentru' : 'către'} ${g.recipient || g.email || g.to || '—'}`;
  if (g.kind === 'letter') return { title: `Scrisoarea către ${g.recipient ? g.recipient.split(/[(,]/)[0].trim() : 'destinatar'}`, sub, pdf: mPdfUrl(n, g), name: mPdfName(g) };
  const title = { message: 'Mesajul către moștenitor', investigation: 'Propunerea investigatorului' }[g.kind] || g.title;
  return { title, sub, text: g.preview || '', name: `${String(g.key).startsWith(`${g.case_id}-`) ? g.key : `${g.case_id || 'dosar'}-${g.key}`}.md` };
}

// Rezolvă cu numele celui care a verificat sau null (renunțat). Trimite e activ doar după bifa „am verificat”.
function mConfirmSend(n, g) {
  mDocViewStyle();
  return new Promise((resolve) => {
    const who = h('input', { type: 'text', placeholder: 'Numele tău (apare în audit)', value: lsGet('approver'), 'aria-label': 'Numele tău' });
    const send = h('button', { type: 'button', class: 'primary', disabled: true }, g.kind === 'message' ? '✔ Trimite mesajul' : '✔ Trimite scrisoarea');
    const check = h('input', { type: 'checkbox', onchange: (ev) => { send.disabled = !ev.target.checked; } });
    const onKey = (ev) => { if (ev.key === 'Escape') close(null); };
    const close = (v) => { document.removeEventListener('keydown', onKey); overlay.remove(); resolve(v); };
    send.onclick = () => {
      const v = who.value.trim();
      if (!v) { who.focus(); toast('Scrie numele tău, ca să rămână în audit.', true); return; }
      lsSet('approver', v); close(v);
    };
    const s = mStep(n);
    const overlay = h('div', { class: 'modal', onclick: (ev) => { if (ev.target === overlay) close(null); } },
      h('div', { class: 'card modal-card send-card', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Verifică ce trimiți' },
        h('h3', {}, g.kind === 'message' ? 'Verifică mesajul înainte să plece' : 'Verifică scrisoarea înainte să plece'),
        h('p', { class: 'small muted' }, `Pasul ${n} (${s.title}). Nimic nu pleacă până nu apeși „Trimite”.`),
        h('dl', { class: 'kv send-meta' }, h('dt', {}, 'Către'), h('dd', {}, h('b', {}, g.email || g.to || '—')),
          h('dt', {}, 'Dosar'), h('dd', {}, g.case_id || demo.results[n - 1]?.case_id || '—')),
        // scrisoarea pleacă ca PDF (atașat la e-mail), ca să poată fi semnată; mesajul către moștenitor e textul e-mailului
        g.kind === 'letter'
          ? h('div', { class: 'gate-preview send-doc' }, h('div', { class: 'gate-preview-head' }, 'Documentul exact care pleacă (PDF atașat, de semnat)',
              h('span', { class: 'doc-actions' },
                h('button', { type: 'button', class: 'doc-preview', onclick: (ev) => mDocView({ ...mGateDoc(n, g), back: ev.currentTarget }) }, mEyeIcon(), 'Mărește'),
                h('a', { href: mPdfUrl(n, g), download: mPdfName(g), class: 'doc-download' }, '⤓ Descarcă'),
                h('a', { href: mPdfUrl(n, g), target: '_blank', rel: 'noopener', class: 'doc-download pdf-link' }, '↗ Filă nouă'))),
            h('iframe', { class: 'send-pdf', src: mPdfUrl(n, g), title: 'Scrisoarea în PDF' }))
          : h('div', { class: 'gate-preview send-doc' }, h('div', { class: 'gate-preview-head' }, 'Mesajul exact care pleacă'),
            h('div', { class: 'gate-preview-body' }, mdRender(g.preview || '(agentul nu a produs text)'))),
        h('label', { class: 'send-check' }, check, ' Am citit documentul: destinatarul e corect, sumele și datele sunt ale dosarului, nu conține date despre alte persoane.'),
        h('label', { class: 'small' }, 'Cine verifică ', who),
        h('div', { class: 'upload', style: 'margin-top:12px' }, send,
          h('button', { type: 'button', onclick: () => close(null) }, 'Înapoi (nu trimit acum)'))));
    document.addEventListener('keydown', onKey);
    document.body.append(overlay);
    check.focus();
  });
}

// demo.cases[n-1] = dosarul imediat după documentul n (instantaneu, nu se mai schimbă: „Starea dosarului: înainte → după”);
// demo.caseNow = dosarul acum (după agenți și deciziile omului), pentru cardul de sus și oprirea la plată
async function mRefreshCase(n, S = caseState(), cid = null) {
  if (cid) {   // un dosar din portofoliu: îl citesc o dată pentru toți pașii schimbați
    const c = await http(`/cases/${encodeURIComponent(cid)}`).catch(() => null);
    if (!c) return;
    S.caseNow = c;
    for (const k of n) if (S.results[k - 1] && !S.cases[k - 1]) S.cases[k - 1] = c;
    return;
  }
  const r = S.results[n - 1];
  if (!r?.case_id) return;
  const c = await http(`/cases/${encodeURIComponent(r.case_id)}`).catch(() => null);
  if (!c) return;
  if (!S.cases[n - 1]) S.cases[n - 1] = c;
  if (c.id === DEMO_CASE) S.caseNow = c;
}

// pornit o singură dată: sondează des cât rulează ceva, rar altfel; cronometrele se actualizează fără re-randare
function mStartPolling() {
  if (demo.mTimer) return;
  mRestore();
  let last = 0;
  demo.mTimer = setInterval(() => {
    if (Date.now() - last >= (mActive() ? 1000 : 4000)) { last = Date.now(); mPoll(); } else mTick();
  }, 500);
}

// după un refresh al paginii: dacă serverul e în modul pas cu pas, pașii lui revin pe ecran
async function mRestore() {
  try {
    const st = await http('/autopilot/status');
    if (!st.paused) return;
    demo.manualOn = true;
    if (!demo.docs) demo.docs = await http('/demo/documents');
    await mPoll();
    demo.open = mCurrentStep();   // nu pasul de după: oprirea care așteaptă (scrisoarea către notar) ar ieși de pe ecran
    renderDemo();
    mAutoSendPopup();
  } catch { /* server fără modul pas cu pas */ }
}

function mTick() {
  document.querySelectorAll('[data-since]').forEach((el) => {
    el.textContent = `${Math.max(0, Math.round((Date.now() - Number(el.dataset.since)) / 1000))} s`;
  });
}

// ---------- acțiuni ----------
// Pornirea pas cu pas nu mai resetează banca: Maria pornește de la zero doar ea (prima oară), un dosar din portofoliu
// continuă de unde e; autopilotul intră în pauză (POST /demo/ai/manual)
async function mEnsureManual() {
  const cid = curCase();
  const S = caseState(cid);
  if (isMaria(cid) && !S.started && !S.srv[1]?.result) {
    await http(`/demo/reset?variants=pensie&manual=true&${caseQ(cid)}`, { method: 'POST' });
    demo.manualOn = true;
  }
  S.started = true;
  if (!demo.manualOn) { await http('/demo/ai/manual', { method: 'POST' }); demo.manualOn = true; }
  if (!demo.docs) demo.docs = await http('/demo/documents');
}

async function mAct(id, fn) {
  const S = caseState();
  if (S.mBusy[id]) return;
  S.mBusy[id] = true; renderDemo();
  try { await fn(); } catch (e) {
    // 404 pe /demo/ai/*: interfața e nouă, dar procesul serverului e pornit înainte de modul pas cu pas
    toast(e.status === 404 && /"detail":"Not Found"/.test(e.message)
      ? 'Serverul rulează o versiune fără modul „pas cu pas” (404). Repornește-l (scripts/test-instance.sh start) sau treci pe modul automat.'
      : (e.message.match(/"detail":"([^"]+)"/) || [])[1] || e.message, true);
  }
  delete S.mBusy[id];
  await mPoll(); renderDemo();
}

const post = (path, body) => http(path, body ? json('POST', body) : { method: 'POST' });
const mExtract = (n) => mAct(`x${n}`, async () => { await mEnsureManual(); await post(`/demo/ai/extract/${n}?variant=${demo.variant}&${caseQ()}`); });
const mApply = (n) => mAct(`a${n}`, async () => { await mEnsureManual(); await post(`/demo/ai/apply/${n}?variant=${demo.variant}&${caseQ()}`); refresh(); });
const mAgent = (n, key) => mAct(`g${n}:${key}`, async () => { await mEnsureManual(); await post(`/demo/ai/agent/${n}/${encodeURIComponent(key)}?${caseQ()}`); });
const mAudit = () => mAct('audit', () => post('/demo/ai/audit'));
const mRunPipe = (n) => mAct(`p${n}`, async () => { await mEnsureManual(); await post(`/demo/ai/pipeline/${n}/run?variant=${demo.variant}&${caseQ()}`); });
const mStopPipe = (n) => mAct(`p${n}`, () => post(`/demo/ai/pipeline/${n}/stop?${caseQ()}`));

// decizia omului: numele lui rămâne în audit; la „nu” spune de ce (e o lecție pentru agenți); plata trece prin dialogul ei
async function mDecide(n, g, ok, who) {
  const id = `${n}:${g.key}`;
  let by = who.value.trim();
  const note = (demo.notes[id] || '').trim();
  if (ok && g.kind === 'payment') {
    if (by) lsSet('approver', by);
    const c = demo.caseNow || demo.cases[n - 1];
    const pay = (c?.payments || []).find((x) => x.plan_id === c?.payment_plan?.plan_id) || (c?.payments || [])[0];
    by = c?.payment_plan && pay ? await confirmApprove(c.payment_plan, pay, c) : by;
    if (!by) return;
  }
  if (!by) { who.focus(); toast('Scrie numele tău, ca să rămână în audit.', true); return; }
  lsSet('approver', by);
  if (!ok && !note) { toast('Scrie de ce spui „nu”: e o lecție pentru agenți.', true); document.getElementById(`note-${id}`)?.focus(); return; }
  await mAct(`d${id}`, async () => {
    const r = await post(`/demo/ai/gate/${n}/${encodeURIComponent(g.key)}/${ok ? 'approve' : 'reject'}?${caseQ()}`, { by, note });
    toast(ok ? `Aprobat de ${by}. ${mPipeLive(n) ? 'Pipeline-ul continuă.' : ''}` : `Respins: ${r.title}. Nu a plecat nimic.`);
    refresh();
  });
}

// Următoarea acțiune a pasului deschis (butonul mare și tasta →), după ce spune serverul că urmează
function mNext(n = demo.open || 1) {
  const nx = demo.srv[n]?.next || { do: mHasScan(n) ? 'extract' : 'apply' };
  if (mPipe(n).status === 'awaiting' || nx.do === 'wait_gate') return { label: 'Rândul tău: aprobă sau respinge mai jos', run: mScrollGate };
  if (mPipeLive(n)) return null;
  switch (nx.do) {
    case 'extract': return { label: 'AI: Extractorul citește scanarea', run: () => mExtract(n) };
    case 'apply': return { label: 'Aplică regulile băncii (cod)', run: () => mApply(n) };
    case 'agent': return { label: `AI: ${nx.label}`, run: () => mAgent(n, nx.key) };
    case 'done': return n < mCount() ? { label: `${mStep(n + 1).kind === 'action' ? 'Pasul următor' : 'Documentul următor'}: ${mStep(n + 1).title}`, run: () => { demo.open = n + 1; renderDemo(); } } : null;
    default: return null;
  }
}

function mScrollGate() { document.querySelector('.station.gate.pending')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }

// „De la zero”: doar dosarul ales (POST /demo/reset?case=); celelalte rămân exact cum sunt
async function mReset() {
  const cid = curCase();
  demo.byCase[cid] = { ...newCaseState(), started: true };
  try {
    await http(`/demo/reset?variants=pensie&manual=true&${caseQ(cid)}`, { method: 'POST' });
    demo.manualOn = true;
    toast(isMaria(cid) ? 'Maria pornește de la zero, pas cu pas: niciun AI nu pornește singur.'
      : `Dosarul ${cid} a revenit la starea din portofoliu; celelalte dosare au rămas cum erau.`);
  } catch (e) { toast(e.message, true); }
  if (!isMaria(cid) && typeof pfLoad === 'function') await pfLoad();
  await mPoll(); demo.open = mDefaultOpen(); renderDemo(); refresh();
}

function setDemoMode(mode) {
  if (demo.mode === mode) return;
  demo.mode = mode; localStorage.setItem('demoMode', mode);
  demo.manualOn = false;
  Object.assign(demo, { step: 0, results: [], cases: [], caseNow: null, read: [], handoffs: [], open: mode === 'manual' ? 1 : 0, jobs: [], srv: {}, sig: '', gsig: '' });
  // ieșirea din „pas cu pas” scoate autopilotul din pauză (reset fără manual)
  if (mode === 'auto') http('/demo/reset?variants=pensie', { method: 'POST' }).catch(() => null).then(() => refresh());
  renderDemo();
}

// ---------- randare ----------
function mHeroActions() {
  const next = mNext();
  const busy = Object.keys(demo.mBusy).length > 0;
  return [
    h('button', { type: 'button', class: 'primary big', disabled: !next || busy, onclick: () => next?.run() },
      next ? `${next.label}  →` : (mActive() ? 'AI-ul lucrează…' : 'Pasul e complet')),
    pipeButton(demo.open || 1),
    h('button', { type: 'button', class: 'ghost-dark', disabled: busy, onclick: mReset }, '↺ De la zero'),
  ];
}

// butonul pipeline-ului unui pas: ▶ pornește; cât rulează sau așteaptă decizia ta devine ■ Oprește
function pipeButton(n) {
  const p = mPipe(n);
  const blocked = n > 1 && !mApplied(n - 1);
  const complete = demo.srv[n]?.next?.do === 'done' && mApplied(n)
    && !Object.values(demo.srv[n]?.gates || {}).some((g) => g.status === 'pending');
  const doc = mStep(n).short;
  if (complete) return h('span', { class: 'pipe-done', role: 'status' }, `✓ ${doc}: procesat`);
  if (p.status === 'stopping') return h('button', { type: 'button', class: 'pipe stop', disabled: true }, '■ Se oprește…');
  if (mPipeLive(n)) return h('button', { type: 'button', class: 'pipe stop', disabled: demo.mBusy[`p${n}`], onclick: () => mStopPipe(n),
    title: 'Oprește pipeline-ul: apelurile AI din coadă se anulează, cel care rulează se termină' }, '■ Oprește procesarea');
  return h('button', { type: 'button', class: 'pipe run', disabled: blocked || complete || demo.mBusy[`p${n}`], onclick: () => mRunPipe(n),
    title: blocked ? `Întâi pasul ${n - 1}` : complete ? 'Pasul e complet' : 'Pornește tot pasul, stație după stație; se oprește la fiecare decizie a ta' },
    ['stopped', 'failed'].includes(p.status) ? `↻ Reia: ${doc}` : `▶ Procesează: ${doc}`);
}

// Bara pasului deschis, sub roadmap: UN buton mare cu ce urmează (procesează documentul, rulează agentul, decizia ta,
// pasul următor), lipită sus la derulare (jos, fixă, pe mobil); pulsează când e singurul lucru de făcut
function mNextBar(n) {
  const total = mCount();
  if (!n || !total) return null;
  const s = mStep(n);
  const p = mPipe(n);
  const nx = demo.srv[n]?.next || {};
  const busy = Object.keys(demo.mBusy).length > 0;
  const gate = Object.values(demo.srv[n]?.gates || {}).find((g) => g.status === 'pending');
  const complete = nx.do === 'done' && mApplied(n) && !gate;
  const cta = (label, run, { pulse = false, disabled = false } = {}) => h('button', { type: 'button',
    class: `primary big next-cta${pulse && !disabled ? ' pulse' : ''}`, disabled: disabled || busy, onclick: run }, label);
  let main;
  // o escaladare fără propunere încă: întâi investigatorul (CTA), decizia care așteaptă (ex. plata) rămâne a doua
  const agentFirst = gate && nx.do === 'agent' && !mPipeLive(n);
  if (p.status === 'stopping') main = cta('■ Se oprește…', null, { disabled: true });
  else if (gate && !agentFirst) main = cta(`◆ Rândul tău: ${gate.title} ↓`, mScrollGate, { pulse: true });
  else if (mPipeLive(n)) main = h('button', { type: 'button', class: 'primary big next-cta', disabled: true },
    h('span', { class: 'spinner', 'aria-hidden': 'true' }), ` ${p.stage || 'AI-ul lucrează'}…`);
  else if (complete && n < total) main = cta(`Treci la pasul ${n + 1}: ${mStep(n + 1).title}  →`, () => { demo.open = n + 1; renderDemo(); window.scrollTo?.({ top: 0, behavior: 'smooth' }); }, { pulse: true });
  else if (complete) main = h('span', { class: 'pipe-done next-cta', role: 'status' }, isMaria() ? '✓ Toți pașii sunt făcuți' : '✓ Dosarul e la zi: nu mai așteaptă nimic de la tine acum');
  else if (n > 1 && !mApplied(n - 1)) main = cta(`← Întâi pasul ${n - 1}: ${mStep(n - 1).title}`, () => { demo.open = n - 1; renderDemo(); });
  else if (s.kind === 'action') main = cta(`▶ Rulează: ${nx.do === 'agent' ? nx.label : s.title}`, () => mRunPipe(n), { pulse: true, disabled: demo.mBusy[`p${n}`] });
  else main = cta(`▶ Procesează: ${s.short}`, () => mRunPipe(n), { pulse: true, disabled: demo.mBusy[`p${n}`] });
  const bar = h('section', { class: 'next-bar', 'aria-label': 'Ce urmează la pasul deschis' },
    h('div', { class: 'next-where' }, h('span', { class: 'next-kicker' }, `Pasul ${n} din ${total}`), h('b', {}, s.title)),
    h('div', { class: 'next-actions' }, main,
      agentFirst ? h('button', { type: 'button', class: 'link next-second', onclick: mScrollGate }, `apoi: ${gate.title} ↓`) : null,
      mPipeLive(n) && p.status !== 'stopping' ? h('button', { type: 'button', class: 'pipe stop', disabled: demo.mBusy[`p${n}`], onclick: () => mStopPipe(n),
        title: 'Oprește procesarea', 'aria-label': 'Oprește procesarea' }, '■', h('span', { class: 'next-stop-text' }, ' Oprește')) : null),
    p.status === 'idle' || p.status === 'done' ? null : pipeStatus(n));
  setTimeout(() => mBarLayout(bar));
  return bar;
}

// înălțimea antetului (bara se lipește sub el) și a barei (spațiul de jos pe mobil); pe mobil bara se ascunde cât
// timp o oprire „Rândul tău” e pe ecran, ca butoanele ei să se poată atinge
let mBarObs = null;
function mBarLayout(bar) {
  if (!bar.isConnected) return;
  const root = document.documentElement;
  const top = document.querySelector('.topbar');
  root.style.setProperty('--topbar-h', `${top ? Math.round(top.getBoundingClientRect().height) : 61}px`);
  root.style.setProperty('--next-bar-h', `${Math.round(bar.getBoundingClientRect().height)}px`);
  mBarObs?.disconnect();
  const gates = document.querySelectorAll('.station.gate.pending');
  if (!gates.length || typeof IntersectionObserver !== 'function') { root.classList.remove('gate-in-view'); return; }
  const seen = new Set();
  mBarObs = new IntersectionObserver((es) => {
    es.forEach((e) => (e.isIntersecting ? seen.add(e.target) : seen.delete(e.target)));
    root.classList.toggle('gate-in-view', seen.size > 0);
  }, { threshold: 0.15 });
  gates.forEach((g) => mBarObs.observe(g));
}

function pipeStatus(n) {
  const p = mPipe(n);
  if (p.status === 'idle') return null;
  const tone = { running: 'warn', awaiting: 'warn', stopping: 'info', stopped: 'info', done: 'ok', failed: 'bad' }[p.status];
  return h('p', { class: `pipe-status ${p.status}` },
    ['running', 'stopping'].includes(p.status) ? [h('span', { class: 'spinner', 'aria-hidden': 'true' }), ' '] : p.status === 'awaiting' ? '‖ ' : '',
    badge(p.status === 'running' ? 'rulează pașii' : PIPE_TEXT[p.status] || p.status, tone), ' ', p.stage || '', p.error ? [' · ', h('span', { class: 'bad-text' }, p.error)] : '');
}

function modeSeg() {
  return h('div', { class: 'seg', role: 'group', 'aria-label': 'Modul demo-ului' },
    h('span', { class: 'muted small' }, 'Mod:'),
    ...[['manual', 'pas cu pas', 'Tu pornești AI-ul (stație cu stație sau tot pipeline-ul) și aprobi ce pleacă'], ['auto', 'automat', 'Autopilotul face totul singur, document după document']]
      .map(([v, l, t]) => h('button', { type: 'button', class: demo.mode === v ? 'on' : '', 'aria-pressed': String(demo.mode === v), title: t,
        onclick: () => setDemoMode(v) }, l)));
}

function stationHead(icon, kind, title, sub) {
  const tag = { ai: 'AI', code: 'COD', doc: 'DOC', human: 'OM' }[kind];
  return h('div', { class: 'st-head' }, h('span', { class: 'st-icon', 'aria-hidden': 'true' }, icon),
    h('div', {}, h('div', { class: 'st-title' }, h('span', { class: `st-kind ${kind}` }, tag), ' ', title),
      sub ? h('div', { class: 'muted small' }, sub) : null));
}

function jobState(job) {
  if (!job) return null;
  if (job.status === 'running') return h('p', { class: 'st-live' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), ' ',
    h('b', {}, `${job.agent_label} lucrează`), ' · ', h('span', { 'data-since': String(Date.parse(job.started_at)) }, `${Math.round(job.elapsed || 0)} s`));
  if (job.status === 'queued') return h('p', { class: 'st-live queued' }, h('span', { class: 'spinner slow', 'aria-hidden': 'true' }), ' ',
    h('b', {}, 'În coadă'), ': așteaptă să termine apelul AI de dinainte · ', h('span', { 'data-since': String(Date.parse(job.queued_at)) }, '0 s'));
  if (job.status === 'failed') return h('div', { class: 'callout bad' }, h('b', {}, `${job.agent_label}: eșuat după ${job.seconds} s. `), job.error || '');
  if (job.status === 'cancelled') return h('p', { class: 'muted' }, badge('anulat', 'info'), ' pipeline-ul a fost oprit înainte să pornească apelul');
  return h('p', { class: 'st-done' }, badge(`gata în ${job.seconds} s`, 'ok'), job.output?.cost_usd ? ` · ${fmtNum(job.output.cost_usd, 3)} $` : '');
}

function mStage(n) {
  const r = mResult(n);
  const after = demo.cases[n - 1];
  const prevIdx = demo.cases.slice(0, n - 1).map((c, i) => (c?.id === after?.id ? i : -1)).filter((i) => i >= 0).pop();
  const before = prevIdx != null ? demo.cases[prevIdx] : null;
  const blocked = n > 1 && !mApplied(n - 1);
  const pay = mGate(n, 'payment');
  const enter = demo.shownStage !== n;   // intrarea animată doar când se schimbă pasul, nu la fiecare sondare
  demo.shownStage = n;
  const action = demo.srv[n]?.meta?.kind === 'action';
  return h('section', { class: `d-stage${enter ? ' enter' : ''}`, style: `--accent:${mStep(n).accent}` },
    blocked ? h('div', { class: 'callout warn' }, 'Documentele vin în ordine: întâi termină pasul ', String(n - 1), '.') : null,
    h('ol', { class: 'stations' },
      action ? mStationWaits(n, r) : mStationDoc(n),
      ...(action ? [] : mHasScan(n) || r?.history ? mStationExtract(n, blocked) : []),
      action ? null : mStationRules(n, r, before, after, blocked),
      ...(r?.handoffs_planned || []).flatMap((p) => [mStationAgent(n, p), mGate(n, p.key) ? mStationGate(n, mGate(n, p.key)) : null]),
      pay ? mStationGate(n, pay) : null));
}

// ce a primit banca la pasul n (scanarea; la pasul 1, linia din lotul DGEP), oricând, și înainte de procesare
const SCAN_NAME = ['01-dgep-semnal.json', '02-adresa-notar.pdf', '03-certificat-asigurare.pdf', '04-certificat-mostenitor-A.pdf',
  '05-raspuns-asigurator.pdf', '06-certificat-suplimentar.pdf'];
function mPreviewScan(n) {
  if (!isMaria()) {   // alt dosar: fișierul pe care îl citește extractorul, altfel documentul cum a fost extras la primire
    const m = demo.srv[n]?.meta || {};
    return previewFile(`Pasul ${n}: ${mStep(n).title}`, m.scan || m.document_id || '', `${API_BASE}/demo/ai/doc/${n}?${caseQ()}`);
  }
  const name = SCAN_NAME[n - 1];
  return previewFile(`Pasul ${n}: ${STORY[n - 1].title}`, name, `${API_BASE}/demo/scan/${n}/file?variant=${demo.variant}`);
}

// „escaladare minor_heir; plan de plată de aprobat” → etichetele din app.js (ESC_LABEL), fără coduri
function mWhy(r) {
  return String(r?.why || '').split('; ').filter(Boolean).map((t) => {
    const m = /^escaladare (\w+)$/.exec(t);
    return m ? `Escaladare: ${human(ESC_LABEL, m[1]).toLowerCase()}` : t === 'notary_answer_drafted' ? 'Răspunsul către notar, de semnat'
      : t === 'lipsesc documente' ? 'Lipsesc documente de la moștenitori' : t === 'plan de plată de aprobat' ? 'Plan de plată de aprobat' : roText(t);
  }).join(' · ');
}

// pasul „ce așteaptă dosarul acum”: regulile spun ce e deschis (escaladări, răspunsul de semnat, plata, moștenitorii)
function mStationWaits(n, r) {
  const c = demo.caseNow;
  const open = (c?.escalations || []).filter((e) => (r?.handoffs_planned || []).some((p) => p.key === `${c.id}-${e.id}`));
  return h('li', { class: 'station code done' },
    stationHead('⚙', 'code', 'Regulile băncii: ce așteaptă dosarul acum', mWhy(r)),
    open.length ? h('ul', { class: 'checks' }, open.map((e) => { const lab = human(ESC_LABEL, e.code); const why = roText(e.reason || '');
      return h('li', {}, why.startsWith(lab) ? why : [h('b', {}, `${lab}: `), why]); })) : null,
    mGate(n, 'payment') ? h('p', { class: 'small' }, 'Planul de plată e calculat și așteaptă aprobarea unui om.') : null,
    h('p', { class: 'muted small' }, 'Fiecare agent pornește doar din butonul lui sau din „Procesează”; ce pleacă din bancă așteaptă aprobarea ta.'));
}

// miniatura e previzualizarea: un click deschide documentul întreg (la pasul 1, linia JSON din lotul DGEP)
function mStationDoc(n) {
  const s = mStep(n);
  if (!isMaria()) {
    const m = s.meta || {};
    return h('li', { class: 'station done' },
      stationHead('▤', 'doc', m.pending ? 'Documentul sosit la bancă' : 'Documentul primit (în dosar)',
        [s.date ? `primit ${s.date}` : null, s.from ? `de la ${s.from}` : null].filter(Boolean).join(' · ')),
      h('button', { type: 'button', class: 'scan-open', onclick: () => mPreviewScan(n), 'aria-label': `Deschide documentul: ${s.title}`, title: 'Deschide documentul' },
        h('span', { class: 'scan-thumb json-thumb', 'aria-hidden': 'true' }, h('b', {}, m.scan ? 'TXT' : '{ }'), h('span', {}, s.short), h('span', {}, m.scan ? 'de citit' : 'extras'))));
  }
  return h('li', { class: 'station done' },
    stationHead('▤', 'doc', n === 1 ? 'Linia din lotul electronic DGEP' : 'Scanarea primită la bancă'),
    h('button', { type: 'button', class: 'scan-open', onclick: () => mPreviewScan(n), 'aria-label': `Deschide documentul: ${s.title}`, title: 'Deschide documentul' },
      n > 1 ? h('img', { class: 'scan-thumb', src: `${API_BASE}/demo/scan/${n}.png?variant=${demo.variant}`, alt: '', loading: 'lazy' })
        : h('span', { class: 'scan-thumb json-thumb', 'aria-hidden': 'true' }, h('b', {}, '{ }'), h('span', {}, 'lot DGEP'), h('span', {}, 'JSON'))));
}

function mStationExtract(n, blocked) {
  const r = mResult(n);
  if (r?.history) {   // un document din dosar: citit la primire, înainte de acest flux
    const out = r.extracted || {};
    const fields = out.fields || {};
    return [h('li', { class: 'station ai done' }, stationHead(AGENT_ICON.extractor, 'ai', 'Extractorul', 'a citit documentul la primire'),
      h('div', { class: 'st-out' },
        h('p', {}, badge(DOC_TYPES[out.document_type] || out.document_type || 'document', 'info'), ' ',
          out.confidence != null ? badge(`încredere ${Math.round(out.confidence * 100)}%`, out.confidence >= 0.8 ? 'ok' : 'bad') : ''),
        h('dl', { class: 'kv' }, SHOWN_FIELDS.filter((k) => k in fields)
          .flatMap((k) => [h('dt', {}, fieldLabel(k)), h('dd', {}, fields[k] == null ? badge('necitit', 'bad') : fieldValue(fields[k], k))]))))];
  }
  const job = mExtractJob(n);
  const out = job?.status === 'done' ? job.output : null;
  const busy = demo.mBusy[`x${n}`] || ['queued', 'running'].includes(job?.status) || mPipeLive(n);
  const fields = out?.fields || {};
  const gate = mGate(n, 'extract');
  return [h('li', { class: `station ai ${job ? job.status : 'idle'}` },
    stationHead(AGENT_ICON.extractor, 'ai', 'Extractorul'),
    !job || job.status === 'cancelled' ? h('button', { type: 'button', class: 'run', disabled: blocked || busy, onclick: () => mExtract(n) }, '▶ Pornește extractorul') : null,
    jobState(job),
    job?.status === 'failed' ? h('button', { type: 'button', class: 'run', disabled: busy, onclick: () => mExtract(n) }, '↻ Încearcă din nou') : null,
    out ? h('div', { class: 'st-out' },
      h('p', {}, badge(DOC_TYPES[out.document_type] || out.document_type, 'info'), ' ',
        badge(`încredere ${Math.round((out.confidence || 0) * 100)}%`, (out.confidence || 0) >= 0.8 ? 'ok' : 'bad'),
        out.error ? [' ', badge(out.error, 'bad')] : ''),
      h('dl', { class: 'kv' }, SHOWN_FIELDS.filter((k) => k in fields)
        .flatMap((k) => [h('dt', {}, fieldLabel(k)), h('dd', {}, fields[k] == null ? badge('necitit', 'bad') : fieldValue(fields[k], k))]))) : null),
  gate ? mStationGate(n, gate) : null];
}

function mStationRules(n, r, before, after, blocked) {
  const nx = demo.srv[n]?.next?.do;
  const ready = !mHasScan(n) || nx === 'apply';
  const busy = demo.mBusy[`a${n}`] || mPipeLive(n);
  const newEvents = r?.history ? r.events || [] : r ? demoNewEvents(before, after, r.case_id) : [];
  if (r?.history) after = demo.caseNow || after;
  return h('li', { class: `station code ${r ? 'done' : 'idle'}` },
    stationHead('⚙', 'code', 'Regulile băncii'),
    !r ? h('button', { type: 'button', class: 'run code', disabled: blocked || !ready || busy, onclick: () => mApply(n),
      title: ready ? '' : 'Întâi extractorul (și decizia ta, dacă e cerută)' }, demo.mBusy[`a${n}`] ? 'Se aplică…' : '▶ Aplică regulile') : null,
    !r && !ready && mHasScan(n) ? h('p', { class: 'muted small' }, nx === 'wait_gate' ? 'Așteaptă decizia ta pe extracție.' : 'Așteaptă extractorul.') : null,
    r ? h('div', { class: 'st-out' },
      r.escalation ? h('div', { class: 'callout warn' }, h('b', {}, 'De verificat de operator: '), roText(escText(after, r))) : null,
      (r.actions || []).length ? h('ul', { class: 'checks' }, r.actions.map((a) => h('li', {}, ACTION_LABEL[a] || a))) : null,
      newEvents.length ? h('details', { class: 'events' }, h('summary', {}, `${newEvents.length} pași în jurnal, fiecare cu regula aplicată`),
        h('ul', {}, newEvents.map((e) => h('li', {}, h('span', {}, roText(e.detail)), e.rule ? h('span', { class: 'rule' }, e.rule) : null)))) : null) : null);
}

function mStationAgent(n, p) {
  const job = mAgentJob(n, p.key);
  const busy = demo.mBusy[`g${n}:${p.key}`] || ['queued', 'running'].includes(job?.status) || mPipeLive(n);
  const out = job?.status === 'done' ? job.output : null;
  const gated = Boolean(mGate(n, p.key));
  return h('li', { class: `station ai ${job ? job.status : 'idle'}` },
    stationHead(AGENT_ICON[p.agent] || '●', 'ai', p.label, p.what),
    !job || job.status === 'cancelled' ? h('button', { type: 'button', class: 'run', disabled: busy, onclick: () => mAgent(n, p.key) }, `▶ Pornește ${p.label}`) : null,
    jobState(job),
    job?.status === 'failed' ? h('button', { type: 'button', class: 'run', disabled: busy, onclick: () => mAgent(n, p.key) }, '↻ Încearcă din nou') : null,
    out && !out.text ? h('p', { class: 'muted small' }, out.skipped || 'Nimic de trimis.') : null,
    // cu oprire la om, textul se vede o singură dată: în previzualizarea de dedesubt
    out?.text && !gated ? mDocActions({ title: `${p.label}: ${p.what || 'ce a scris'}`, sub: out.artifact || `Pasul ${n}`, text: out.text,
      name: out.artifact ? String(out.artifact).split('/').pop() : `pasul${n}-${p.key}.md` }) : null,
    out?.text && !gated ? h('details', { class: 'st-text', open: demo.outOpen[job.id] ?? true, ontoggle: (ev) => { demo.outOpen[job.id] = ev.target.open; } },
      h('summary', {}, out.artifact ? `Ce a scris (${out.artifact})` : 'Ce a scris'), h('div', { class: 'md-box' }, mdRender(out.text))) : null);
}

// oprirea la om: ce a făcut AI-ul până aici, ce pleacă (previzualizare), către cine; numele tău; da / nu (cu motiv)
function mStationGate(n, g) {
  const id = `${n}:${g.key}`;
  const pending = g.status === 'pending';
  const r = mResult(n);
  const c = ((demo.cases[n - 1]?.id === DEMO_CASE || !isMaria()) && demo.caseNow) || demo.cases[n - 1];
  const t = GATE_TEXT[g.kind] || { yes: '✔ Aprob', no: '✗ Resping' };
  const who = h('input', { type: 'text', placeholder: 'Numele tău (apare în audit)', value: lsGet('approver'), 'aria-label': 'Numele tău' });
  const note = h('input', { type: 'text', id: `note-${id}`, value: demo.notes[id] || '', 'aria-label': 'Observație',
    placeholder: g.kind === 'payment' ? 'Motivul respingerii (obligatoriu la „nu”)' : 'Observație (opțional; obligatorie la „nu”)',
    oninput: (ev) => { demo.notes[id] = ev.target.value; } });
  const ex = mExtractJob(n)?.output;
  const did = [
    ex ? `Extractorul a citit documentul (încredere ${Math.round((ex.confidence || 0) * 100)}%).` : null,
    ...(r?.actions || []).map((a) => `Reguli: ${ACTION_LABEL[a] || a}`),
    ...(r?.handoffs_planned || []).filter((p) => mAgentJob(n, p.key)?.status === 'done').map((p) => `${p.label}: ${p.what}`),
  ].filter(Boolean);
  const busy = demo.mBusy[`d${id}`];
  return h('li', { class: `station gate ${pending ? 'pending' : g.status === 'approved' ? 'done' : 'refused'}` },
    stationHead('◆', 'human', `Rândul tău: ${g.title}`),
    did.length ? h('details', { class: 'events', open: pending }, h('summary', {}, 'Ce a făcut AI-ul până aici'), h('ul', {}, did.map((x) => h('li', {}, x)))) : null,
    h('p', { class: 'small' }, h('b', {}, ['investigation', 'extract'].includes(g.kind) ? 'Pentru: ' : 'Către: '), g.email || g.to),
    // ce pleacă (sau asupra căruia s-a decis) se previzualizează în fereastra mare: scrisoarea ca PDF, restul ca text formatat
    g.kind === 'letter' || (g.preview && g.kind !== 'extract' && g.kind !== 'payment') ? mDocActions(mGateDoc(n, g), (d) => d.gate === `${n}:${g.key}` || (g.kind === 'investigation' && d.kind === 'investigation' && d.escalation_id === g.escalation)) : null,
    g.kind === 'extract' ? h('p', {}, h('button', { type: 'button', class: 'link', onclick: () => previewScan(n) }, 'Deschide scanarea')) : null,
    g.kind === 'payment' && c?.payment_plan ? h('p', {}, 'Plan ', c.payment_plan.variant_label || '', ': liniile și sumele sunt în dosarul complet (link sus). ',
      isMaria() ? 'Liniile blocate (minora, depozitul nescadent) rămân pe loc.' : 'Liniile blocate rămân pe loc.') : null,
    pending
      ? h('div', { class: 'gate-form' }, who, note,
        // ce pleacă din bancă trece prin fereastra de verificare, cu documentul întreg
        h('button', { type: 'button', class: 'primary', disabled: busy, onclick: () => {
          if (!SEND_KINDS.includes(g.kind)) return mDecide(n, g, true, who);
          if (who.value.trim()) lsSet('approver', who.value.trim());
          return mSendFlow(n, g);
        } }, SEND_KINDS.includes(g.kind) ? '✔ Verifică și trimite…' : t.yes),
        h('button', { type: 'button', class: 'danger', disabled: busy, onclick: () => mDecide(n, g, false, who) }, t.no))
      : h('p', { class: `callout ${g.status === 'approved' ? 'ok' : 'warn'}` }, g.status === 'approved' ? '✔ Aprobat' : '✗ Respins',
        g.decided_by ? ` de ${g.decided_by}` : '', g.decided_at ? ` la ${String(g.decided_at).slice(11, 16)} UTC` : '', g.note ? `: „${g.note}”` : '',
        g.status === 'rejected' && g.kind !== 'investigation' ? '. Nu a plecat nimic.' : '.'));
}

const previewScan = mPreviewScan;

// Panoul „Activitate AI”: fiecare apel AI al demo-ului, cel mai nou sus; în modul automat, ce face autopilotul
function mActivity() {
  const auto = demo.mode !== 'manual';
  const list = auto ? autoFeed() : [...demo.jobs].reverse();
  const running = list.filter((j) => j.status === 'running' || j.status === 'queued');
  const total = demo.jobs.filter((j) => j.status === 'done').reduce((a, j) => a + (j.output?.cost_usd || 0), 0);
  const waiting = auto ? [] : mPending();
  return h('aside', { class: 'card ai-feed', 'aria-label': 'Activitate AI', 'aria-live': 'polite' },
    h('div', { class: 'ai-feed-head' }, h('h3', {}, 'Activitate AI'),
      running.length ? badge(`${running.length} în lucru`, 'warn') : badge('nimic în lucru', 'ok')),
    h('p', { class: 'muted small' }, auto
      ? 'Mod automat: autopilotul preia documentele și pornește singur agenții.'
      : 'Pas cu pas: autopilotul e în pauză. AI-ul pornește doar din butoanele ▶, iar ce pleacă din bancă așteaptă aprobarea ta.'),
    waiting.length ? h('div', { class: 'callout warn' }, h('b', {}, waiting.length === 1 ? 'Rândul tău (1): ' : `Rândul tău (${waiting.length}): `),
      ...waiting.map((g, i) => [i ? '; ' : '', h('button', { type: 'button', class: 'link', onclick: () => { demo.open = g.step; renderDemo(); setTimeout(mScrollGate, 50); } },
        `pasul ${g.step}: ${g.title}`)])) : null,
    list.length ? h('ol', { class: 'ai-list' }, list.map((j) => h('li', { class: `ai-item ${j.status}` },
      h('span', { class: 'ai-ico', 'aria-hidden': 'true' }, j.status === 'running' ? h('span', { class: 'spinner' }) : j.status === 'queued' ? '…' : j.status === 'done' ? '✓' : j.status === 'cancelled' ? '–' : '✗'),
      h('div', {}, h('b', {}, AGENT_ICON[j.agent] || '●', ' ', j.agent_label), j.step ? h('span', { class: 'muted small' }, ` · pasul ${j.step}`) : null,
        h('div', { class: 'small' }, j.label),
        h('div', { class: 'small muted' }, badge(AI_STATUS[j.status] || j.status, AI_TONE[j.status] || 'info'), ' ',
          j.status === 'running' && j.started_at ? h('span', { 'data-since': String(Date.parse(j.started_at)) }, '') : j.seconds != null ? `${j.seconds} s` : '',
          j.output?.cost_usd ? ` · ${fmtNum(j.output.cost_usd, 3)} $` : ''))))) : h('p', { class: 'muted' }, 'Încă niciun apel AI.'),
    !auto && total ? h('p', { class: 'small muted' }, `Cost AI în această rulare: ${fmtNum(total, 3)} $`) : null,
    !auto ? h('div', { class: 'ai-feed-foot' },
      h('button', { type: 'button', class: 'run', disabled: !demo.step || demo.mBusy.audit || demo.jobs.some((j) => j.kind === 'audit' && ['queued', 'running'].includes(j.status)),
        onclick: mAudit, title: demo.step ? '' : 'Întâi un document în dosar' }, `${AGENT_ICON.auditor} ▶ Auditorul verifică dosarele`),
      mAuditOut()) : null);
}

function mAuditOut() {
  const job = mLast((j) => j.kind === 'audit');
  if (!job) return null;
  if (job.status !== 'done') return jobState(job);
  return h('div', {}, job.output?.text ? mDocActions({ title: 'Raportul auditorului', sub: `${job.seconds} s`, text: job.output.text, name: 'raport-auditor.md' }) : null,
    h('details', { class: 'st-text' }, h('summary', {}, `Raportul auditorului (${job.seconds} s)`), h('div', { class: 'md-box' }, mdRender(job.output?.text || ''))));
}

// modul automat: aceeași listă, din bătaia autopilotului (GET /autopilot/status)
function autoFeed() {
  const ap = apState();
  if (!ap) return [];
  const done = (ap.agent_calls || []).map((c) => ({ agent: c.agent, agent_label: AGENT_LABEL[c.agent] || c.agent, label: c.file,
    status: c.ok ? 'done' : 'failed', seconds: c.seconds, output: { cost_usd: c.cost_usd } }));
  const reads = (ap.processed || []).map((p) => ({ agent: 'extractor', agent_label: 'Extractorul', label: `a citit ${p.file}`, status: 'done', seconds: null }));
  const now = [];
  if (ap.state === 'extracting') now.push({ agent: 'extractor', agent_label: 'Extractorul', label: `citește ${ap.current || ''}`, status: 'running', started_at: ap.last_poll });
  if (ap.state === 'agent') { const [a, ...k] = String(ap.current || '').split(':'); now.push({ agent: a, agent_label: AGENT_LABEL[a] || a, label: k.join(':'), status: 'running', started_at: ap.last_poll }); }
  return [...now, ...[...reads, ...done].reverse()].slice(0, 30);
}
