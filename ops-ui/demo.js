// Demo ghidat: dosarul Mariei Ionescu în 6 pași. Fiecare pas trimite un document și arată, pe rând, ce a citit
// extractorul, ce a făcut sistemul (reguli, pe core) și cui predă sistemul mai departe (agenții).
// Folosește doar API-ul real: POST /demo/reset, /demo/step/{n}, GET /cases/{id}, /handoffs, /payments/{id}/approve.
// Mod „scanate” (implicit): pașii 2–6 trimit scanarea originală (registries/documents/scan/) în inbox; extractorul o citește
// vizual, ca la ghișeu, iar pasul afișează ce a citit el (GET /demo/received/{fișier}). Mod „pre-extrase”: *.mvp.json, instant.
// Mod „pas cu pas” (implicit, demo-manual.js): fiecare apel AI pornit de operator, cu stațiile și panoul „Activitate AI”.
// Depinde de app.js (h, http, json, fmtMoney, badge, stateBadge, STATE_LABEL, DOC_TYPES, fieldLabel, fieldValue, toast,
// showView, select, refresh, api, previewDocument) și de live.js (ACTION_LABEL).

const STORY = [
  { title: 'Semnalul DGEP', from: 'Direcția de Evidență a Persoanelor (lot săptămânal)', date: '20.09.2026',
    why: 'Banca află că Maria Ionescu a decedat pe 3 septembrie. Până azi, un om căuta manual clientul și bloca fiecare produs.',
    expect: 'Blocare reversibilă (nu definitivă pe un semnal), stornarea comisionului de după deces, termenul de opțiune succesorală.' },
  { title: 'Adresa notarului', from: 'Notarul public (dosar succesoral 123/2026)', date: '28.09.2026',
    why: 'Notarul cere soldurile la data decesului. Răspunsul greșit (sold de azi, nu de la deces) e cea mai frecventă eroare.',
    expect: 'Soldurile calculate la 03.09.2026 și răspunsul redactat pentru semnare.' },
  { title: 'Certificatul de asigurare UNIQA', from: 'Dosarul creditului', date: '30.09.2026',
    why: 'Creditul are asigurare de viață. Dacă banca nu avizează dauna la timp, datoria trece la moștenitori.',
    expect: 'Dosar de daună deschis, termenul de avizare, avizarea redactată către asigurător.' },
  { title: 'Certificatul de moștenitor', from: 'Notarul public', date: '22.10.2026', variant: true,
    why: 'Cotele moștenitorilor. Certificatul uită depozitul, iar Elena are 15 ani: două capcane clasice.',
    expect: 'Cotele verificate (suma = 1), supliment cerut pentru depozit, partea minorei blocată până la reprezentare.' },
  { title: 'Răspunsul asigurătorului', from: 'UNIQA Asigurări de viață', date: '27.10.2026',
    why: 'Asigurătorul plătește creditul. Notarul și moștenitorii trebuie să afle ce datorie mai rămâne.',
    expect: 'Creditul stins; Corespondentul scrie nota către notar cu datoria rămasă a masei.' },
  { title: 'Certificatul suplimentar', from: 'Notarul public', date: '10.11.2026',
    why: 'Acum toate produsele sunt acoperite. Planul de plată se calculează exact, în bani, după cote.',
    expect: 'Plan de plată; banii se mișcă doar după aprobarea unui om.' },
];
const DEMO_CASE = 'SC-2026-0001';
const SHOWN_FIELDS = ['cnp', 'date_of_death', 'case_file', 'hearing_date', 'notary_name', 'insurer', 'policy_id', 'loan_contract',
  'document_number', 'heirs', 'testament', 'decision', 'amount', 'initial_certificate', 'ibans', 'name', 'birth_date'];

const demo = { step: 0, variant: 'A', results: [], cases: [], docs: null, busy: false, auto: null, handoffs: [], open: 0, timer: null,
  source: localStorage.getItem('demoSource') || 'scan', read: [], pending: null };
const SCAN_TIMEOUT_MS = 5 * 60 * 1000;   // extracția + agenții documentului anterior (care țin coada) pot dura minute

function renderDemo() {
  const root = $('#view-demo');
  if (demo.pick) {   // un dosar din portofoliu (demo-dosare.js); demo-ul Mariei rămâne neatins dedesubt
    if (!demo.pf && !demo.pfBusy) pfLoad();
    renderPortfolio(root);
    return;
  }
  const manual = demo.mode === 'manual';
  const done = demo.step;
  if (manual && !demo.open) demo.open = mDefaultOpen();
  const cur = demo.open || done;
  root.replaceChildren(
    demoHero(done),
    h('div', { class: 'd-main' },
      h('div', { class: 'd-col' }, ...[
        manual ? demoRoadmap(done, cur) : demoStepper(done, cur),
        manual ? mNextBar(cur) : null,
        manual ? mStage(cur) : cur ? demoStage(cur) : demoWelcome(),
      ].filter(Boolean))));
  mTick();
  if (!demo.timer) demo.timer = setInterval(pollHandoffs, 3000);
  if (manual) mStartPolling();
}

function demoHero(done) {
  const next = STORY[done];
  const manual = demo.mode === 'manual';
  return h('section', { class: 'd-hero' },
    h('div', { class: 'd-hero-text' }, flowBack(),
      demoPerson(done),
      manual ? null : h('div', { class: 'd-hero-actions' },
        h('button', { type: 'button', class: 'primary big', disabled: demo.busy || done >= STORY.length, onclick: nextStep },
          done >= STORY.length ? 'Toate documentele au fost trimise' : `Trimite: ${next.title}  →`),
        h('button', { type: 'button', disabled: demo.busy || done >= STORY.length, onclick: toggleAuto },
          demo.auto ? '⏸ Oprește derularea' : '▶ Derulează singur'),
        h('button', { type: 'button', class: 'ghost-dark', disabled: demo.busy, onclick: resetDemo }, '↺ De la zero'),
        modeSeg(),
        variantSeg(done),
        h('div', { class: 'seg', role: 'group', 'aria-label': 'Forma documentelor' },
          h('span', { class: 'muted small' }, 'Documente:'),
          ...[['scan', 'scanate', 'Scanarea originală intră în inbox; agentul o citește vizual (10–20 s pe document)'],
            ['extracted', 'pre-extrase', 'Câmpurile deja extrase (fără LLM), instant']].map(([v, l, t]) => h('button', {
            type: 'button', class: demo.source === v ? 'on' : '', 'aria-pressed': String(demo.source === v), title: t,
            disabled: demo.busy || done > 0, onclick: () => { demo.source = v; localStorage.setItem('demoSource', v); renderDemo(); } }, l))),
      ),
      manual ? null : h('p', { class: 'muted small' }, 'Tastatură: → sau spațiu = următorul document · Pas ', String(done), ' din ', String(STORY.length))));
}

// antetul: cine a decedat, dosarul, și cifrele care contează acum; în dreapta, butonul pasului deschis
function demoPerson(done) {
  const c = (demo.mode === 'manual' && demo.caseNow) || demo.cases.filter((x) => x && x.id === DEMO_CASE).pop();
  const n = demo.open || Math.min(done + 1, STORY.length);
  return personHeader(c, { name: 'Maria Ionescu', done, total: STORY.length, label: 'Pași parcurși',
    side: demo.mode === 'manual' ? [pipeButton(n), mPipe(n).status === 'done' ? null : pipeStatus(n)] : null });
}

// cine a decedat, dosarul, și cifrele care contează acum; `side` = butonul din dreapta (pasul deschis)
function personHeader(c, { name, done, total, label, side }) {
  name = c?.deceased?.name || name || c?.id || 'Dosar';
  const initials = name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();
  const assets = (c?.products || []).filter((p) => p.type !== 'loan' && p.outstanding == null)
    .reduce((a, p) => a + (p.balance ?? p.principal ?? 0) + (p.accrued_interest || 0), 0);
  const payNow = c?.payment_plan?.status === 'pending_approval'
    ? (c.payment_plan.lines || []).filter((l) => !l.blocked).reduce((a, l) => a + l.amount, 0) : 0;
  const tile = (label, value, sub, tone = '', num = null) => {
    const v = h('div', { class: 'dp-value' }, value);
    if (num) countTo(v, `${c?.id}:${label}`, num.to, num.fmt);
    return h('div', { class: `dp-tile ${tone}` }, h('div', { class: 'dp-label' }, label), v, sub ? h('div', { class: 'dp-sub' }, sub) : null);
  };
  return h('div', { class: 'd-person' },
    h('div', { class: 'dp-top' },
      h('div', { class: 'dp-avatar', 'aria-hidden': 'true' }, initials),
      h('div', { class: 'dp-id' },
        h('div', { class: 'dp-kicker' }, 'Dosar de succesiune', c ? ` · ${c.id}` : ''),
        h('h1', {}, name),
        h('div', { class: 'dp-meta' },
          h('span', {}, '† ', c?.deceased?.date_of_death ? fmtDate(c.deceased.date_of_death) : 'în curs de confirmare'),
          c?.deceased?.cnp ? h('span', {}, 'CNP ', String(c.deceased.cnp).slice(0, 7), '••••••') : null,
          c ? h('button', { type: 'button', class: 'link dp-open', onclick: () => { showView('cases'); select(c.id); } }, 'Dosarul complet →') : null)),
      side ? h('div', { class: 'dp-side' }, side) : null),
    h('div', { class: 'dp-tiles' },
      tile(label, `${done} / ${total}`, h('div', { class: 'dp-bar' }, h('span', { style: `width:${(done / total) * 100}%` })), '',
        { to: done, fmt: (x) => `${Math.round(x)} / ${total}` }),
      tile('Moștenitori', (c?.heirs || []).length ? String(c.heirs.length) : '—', (c?.heirs || []).length ? 'din certificat' : 'după certificat'),
      tile('Active la deces', assets ? fmtMoney(assets) : '—', assets ? 'solduri + dobânzi' : 'după semnalul DGEP', '',
        assets ? { to: assets, fmt: (x) => fmtMoney(Math.round(x)) } : null),
      payNow ? tile('De plătit acum', fmtMoney(payNow), 'după aprobarea ta', 'ok', { to: payNow, fmt: (x) => fmtMoney(Math.round(x)) }) : null));
}

// o cifră care s-a schimbat de la randarea anterioară urcă (sau coboară) animat până la valoarea nouă
const tileLast = {};
function countTo(el, key, to, fmt) {
  const from = tileLast[key];
  tileLast[key] = to;
  if (from == null || from === to || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  el.classList.add('bump');
  const t0 = performance.now(), dur = 800;
  const step = (t) => {
    const k = Math.min(1, (t - t0) / dur);
    el.textContent = fmt(from + (to - from) * (1 - (1 - k) ** 3));
    if (k < 1) requestAnimationFrame(step);
  };
  el.textContent = fmt(from);
  requestAnimationFrame(step);
}

function variantSeg(done) {
  const locked = done >= 4 || (demo.mode === 'manual' && mExtractJob(4));
  return h('div', { class: 'seg', role: 'group', 'aria-label': 'Varianta certificatului de moștenitor' },
    h('span', { class: 'muted small' }, 'Moștenire:'),
    ...[['A', 'legală'], ['B', 'testament']].map(([v, l]) => h('button', {
      type: 'button', class: demo.variant === v ? 'on' : '', 'aria-pressed': String(demo.variant === v),
      disabled: demo.busy || locked, title: locked ? 'Certificatul a fost deja trimis; pornește de la zero ca să schimbi' : '',
      onclick: () => { demo.variant = v; renderDemo(); } }, l)));
}

function demoStepper(done, cur) {
  return h('ol', { class: 'd-steps' }, STORY.map((s, i) => {
    const n = i + 1;
    const r = demo.results[i];
    const pipe = demo.mode === 'manual' ? mPipe(n).status : null;   // pipeline-ul pasului: rulează / așteaptă decizia ta
    const waits = pipe === 'awaiting' || (demo.mode === 'manual' && Object.values(demo.srv?.[n]?.gates || {}).some((g) => g.status === 'pending'));
    const state = (waits ? 'waits ' : pipe === 'running' ? 'busy ' : '') + (n <= done ? (r?.escalation ? 'attn' : 'done') : n === done + 1 ? 'next' : 'todo');
    return h('li', { class: `d-step ${state} ${n === cur ? 'current' : ''}` },
      h('button', { type: 'button', disabled: n > done + (demo.mode === 'manual' ? 1 : 0), onclick: () => { demo.open = n; renderDemo(); },
        title: n > done ? 'Încă netrimis' : r?.escalation ? 'Are o escaladare de verificat de operator' : 'Vezi ce s-a întâmplat la acest document' },
        h('span', { class: 'dot' }, waits ? '‖' : pipe === 'running' ? h('span', { class: 'spinner' }) : n <= done ? (r?.escalation ? '!' : '✓') : String(n)),
        h('span', { class: 'd-step-title' }, s.title)));
  }));
}

function demoWelcome() {
  return h('section', { class: 'card welcome' },
    h('h3', {}, 'Cum citești demo-ul'),
    h('div', { class: 'd-flow' },
      flowBox('1', 'Documentul', 'sosește pe orice canal: lot DGEP, e-mail de la notar, scanare la ghișeu'),
      h('span', { class: 'arrow' }, '→'),
      flowBox('2', 'Extractorul (LLM)', 'citește tipul și câmpurile, cu un scor de încredere'),
      h('span', { class: 'arrow' }, '→'),
      flowBox('3', 'Sistemul (cod)', 'aplică regulile: blocări, solduri la deces, cote, plan de plată. Fiecare acțiune citează regula.'),
      h('span', { class: 'arrow' }, '→'),
      flowBox('4', 'Agenții (LLM)', 'scriu ce e de scris: scrisori, propuneri pentru operator, mesaje către moștenitori')),
    h('p', { class: 'muted' }, 'Apasă „Trimite” ca să trimiți primul document.'));
}
const flowBox = (n, t, d) => h('div', { class: 'd-flow-box' }, h('span', { class: 'd-flow-n' }, n), h('b', {}, t), h('span', { class: 'small muted' }, d));

function demoPending(n) {
  const p = demo.pending;
  const s = STORY[n - 1];
  const secs = Math.round((Date.now() - p.since) / 1000);
  const text = p.status === 'extracting' ? 'Extractorul citește scanarea, ca un operator la ghișeu…'
    : p.autopilot === false ? 'Autopilotul nu rulează: documentul așteaptă în inbox (porniți-l: scripts/test-instance.sh start).'
    : 'În inbox, la rând: agenții termină documentul anterior.';
  return h('section', { class: 'd-stage' },
    h('div', { class: 'd-stage-head' },
      h('span', { class: 'd-stage-icon', 'aria-hidden': 'true' }, String(n)),
      h('div', {}, h('h2', { class: 'd-stage-title' }, `Pasul ${n}: ${s.title}`),
        h('p', { class: 'muted' }, `${s.date} · de la ${s.from}`), h('p', {}, s.why))),
    h('div', { class: 'card' }, h('p', {}, h('span', { class: 'spinner', 'aria-hidden': 'true' }), ' ', h('b', {}, text), ` (${secs} s)`),
      h('p', { class: 'muted small' }, 'Fișier: ', p.name, ' · scanare PDF, fără strat de text')));
}

function demoStage(n) {
  if (demo.pending && demo.pending.n === n) return demoPending(n);
  const s = STORY[n - 1];
  const r = demo.results[n - 1] || {};
  const read = demo.read[n - 1];   // mod „scanate”: documentul așa cum l-a citit extractorul
  const doc = read ? { id: read.document_id, document_type: read.document_type, confidence: read.confidence, raw_name: read.source,
    fields: Object.fromEntries((read.fields || []).map((f) => [f.name, f.value])) } : demoDoc(n);
  const after = demo.cases[n - 1];
  const before = demo.cases[n - 2]?.id === after?.id ? demo.cases[n - 2] : null;
  const newEvents = demoNewEvents(before, after, r.case_id);
  const enter = demo.shown !== n;   // animația doar când se schimbă pasul, nu la fiecare reîmprospătare
  demo.shown = n;
  return h('section', { class: 'd-stage' + (enter ? ' enter' : '') },
    h('div', { class: 'd-stage-head' },
      h('span', { class: 'd-stage-icon', 'aria-hidden': 'true' }, String(n)),
      h('div', {}, h('h2', { class: 'd-stage-title' }, `Pasul ${n}: ${s.title}`),
        h('p', { class: 'muted' }, `${s.date} · de la ${s.from}`), h('p', {}, s.why))),
    h('div', { class: 'lanes' },
      lane('1', read ? 'Ce a citit extractorul din scanare' : 'Ce a citit extractorul', [
        doc ? h('p', {}, badge(DOC_TYPES[doc.document_type] || doc.document_type, 'info'), ' ',
          badge(`încredere ${Math.round((doc.confidence || 0) * 100)}%`, (doc.confidence || 0) >= 0.8 ? 'ok' : 'bad')) : null,
        doc ? h('dl', { class: 'kv' }, SHOWN_FIELDS.filter((k) => doc.fields && k in doc.fields)
          .flatMap((k) => [h('dt', {}, fieldLabel(k)), h('dd', {}, doc.fields[k] == null ? badge('necitit', 'bad') : fieldValue(doc.fields[k], k))])) : null,
        doc && r.case_id ? h('button', { type: 'button', class: 'link', onclick: () => previewDocument(r.case_id,
          { document_id: doc.id, document_type: doc.document_type, source: doc.raw_name }) },
          read ? 'Vezi scanarea originală' : 'Vezi documentul original') : null]),
      lane('2', 'Ce a făcut sistemul', [
        r.escalation ? h('div', { class: 'callout warn' }, h('b', {}, 'De verificat de operator: '), escText(after, r)) : null,
        (r.actions || []).length ? h('ul', { class: 'checks' }, r.actions.map((a) => h('li', {}, ACTION_LABEL[a] || a))) : null,
        newEvents.length ? h('details', { class: 'events' }, h('summary', {}, `${newEvents.length} pași în jurnal, fiecare cu regula aplicată`),
          h('ul', {}, newEvents.map((e) => h('li', {}, h('span', {}, e.detail), e.rule ? h('span', { class: 'rule' }, e.rule) : null)))) : null,
        h('p', { class: 'muted small' }, 'Așteptat: ', s.expect)]),
      lane('3', 'Cui predă sistemul', handoffList(r)),
    ));
}

function lane(n, title, kids) {
  return h('div', { class: 'lane card' }, h('div', { class: 'lane-head' }, h('span', { class: 'd-flow-n' }, n), h('h3', {}, title)), ...kids);
}

function escText(c, r) {
  const e = (c?.escalations || []).find((x) => x.id === r.escalation);
  return e ? e.reason : (r.escalation_reason || r.escalation);
}

function handoffList(r) {
  const planned = r.handoffs_planned || [];
  if (!planned.length) return [h('p', { class: 'muted' }, 'Nimic de scris la acest document: acțiunile sunt pe core și se văd în dosar.')];
  return [h('ul', { class: 'handoffs' }, planned.map((p) => {
    // același trigger („lipsesc documente”) apare la mai mulți pași: legăm predarea de documentul ei, după numele fișierului
    const stem = (r._doc || '').split('/').pop().replace(/\.(pdf|md|json|png|jpe?g)$/i, '').replace(/\.mvp$/, '');
    const real = demo.handoffs.filter((x) => x.case_id === r.case_id && x.to === p.agent && x.trigger === p.trigger
      && (!stem || !x.document || String(x.document).startsWith(stem))).pop();
    const st = !real ? ['planificat', 'info'] : real.skipped ? ['deja trimis', 'info'] : real.ok ? ['scris ✓', 'ok'] : ['eșuat', 'bad'];
    return h('li', { class: 'handoff' },
      h('div', { class: 'handoff-line' }, h('span', { class: 'from' }, 'Sistemul'), h('span', { class: 'arrow' }, '→'),
        h('b', {}, p.label), badge(st[0], st[1])),
      h('p', { class: 'small' }, 'scrie ', p.what),
      real?.error ? h('p', { class: 'small bad-text' }, real.error) : null);
  })),
  h('p', { class: 'muted small' }, demo.handoffs.length
    ? 'Starea vine din jurnalul de predări al autopilotului (GET /handoffs).'
    : 'Agenții scriu efectiv doar cu autopilotul pornit (scripts/test-instance.sh start 8010). Aici vezi ce le predă sistemul și de ce.'),
  r.case_id && r.case_id !== 'SC-NEIDENTIFICAT'
    ? h('button', { type: 'button', class: 'link', onclick: () => { ui.tab = 'corr'; showView('cases'); select(r.case_id); } }, 'Vezi corespondența dosarului')
    : null];
}

function demoNewEvents(before, after, cid) {
  if (!after || after.id !== cid) return [];
  const seen = before && before.id === cid ? before.events.length : 0;
  return after.events.slice(seen);
}

function demoDoc(n) {
  if (!demo.docs) return null;
  if (n === 4 && demo.variant === 'B') return demo.docs.find((d) => d.id === 'doc-04-B') || demo.docs[3];
  return demo.docs.filter((d) => d.id !== 'doc-04-B')[n - 1];
}

function planCard(c, plan) {
  const lines = plan.lines || [];
  return h('div', { class: 'plan' },
    h('h3', {}, 'Planul de plată ', h('span', { class: 'muted small' }, plan.variant_label || '')),
    h('div', { class: 'table-wrap' }, h('table', {},
      h('thead', {}, h('tr', {}, h('th', {}, 'Moștenitor'), h('th', {}, 'Cotă'), h('th', {}, 'Produs'), h('th', { class: 'num' }, 'Sumă'), h('th', {}, 'Când'))),
      h('tbody', {}, lines.map((l) => h('tr', { class: l.blocked_reason ? 'blocked' : '' },
        h('td', {}, l.name, l.minor ? ' ' : '', l.minor ? badge('minor', 'warn') : ''), h('td', {}, l.share),
        h('td', {}, productLabel(c, l.product_id)), h('td', { class: 'num' }, fmtMoney(l.amount)),
        h('td', { title: l.blocked_reason || '' }, whenPaid(l))))))),
    // alt dosar decât al Mariei (demo-dosare.js): aprobarea e în oprirea „Rândul tău” de dedesubt
    plan.status === 'pending_approval' && c.id !== DEMO_CASE ? null
    : plan.status === 'pending_approval' && demo.mode === 'manual'
      ? h('p', { class: 'callout warn' }, h('b', {}, 'Rândul omului. '), 'Aprobarea plății e o oprire în pipeline-ul pasului 6 („Rândul tău: Aprobă plata”).')
      : plan.status === 'pending_approval'
      ? h('div', { class: 'approve-bar' },
          h('p', {}, h('b', {}, 'Rândul omului. '), 'Plata e ireversibilă, deci sistemul nu o face singur. Liniile blocate (minora, depozitul nescadent) rămân pe loc.'),
          h('button', { type: 'button', class: 'primary', disabled: demo.busy, onclick: () => approveDemo(plan) }, '✔ Aprobă plata'))
      : h('p', { class: 'callout ok' }, `Plan ${plan.status === 'approved' ? 'aprobat' : plan.status}${plan.approved_by || demo.approvedBy ? ' de ' + (plan.approved_by || demo.approvedBy) : ''}. Banii au plecat doar pe liniile neblocate.`));
}

function whenPaid(l) {
  const r = l.blocked_reason || '';
  if (!r) return l.pay_on && l.pay_on !== 'acum' ? fmtDate(l.pay_on) : 'acum';
  if (r.startsWith('minor')) return badge('blocat: minor', 'bad');
  if (r.startsWith('depozit')) return badge(`la scadență, ${fmtDate(l.pay_on)}`, 'info');
  return badge('blocat', 'bad');
}

// ---------- acțiuni ----------
async function nextStep() {
  if (demo.busy || demo.step >= STORY.length) return;
  demo.busy = true; renderDemo();
  const n = demo.step + 1;
  try {
    if (n === 1 && !demo.results.length) await http(`/demo/reset?variants=pensie${demo.source === 'scan' ? '&inbox=true' : ''}`, { method: 'POST' });
    if (!demo.docs) demo.docs = await http('/demo/documents');
    demo.open = n;
    let r = await http(`/demo/step/${n}?variant=${demo.variant}&source=${demo.source}`, { method: 'POST' });
    let name = demoDoc(n)?.raw_name;
    if (r.queued) { name = r.queued; r = await waitReceived(n, name); }
    demo.results[n - 1] = { ...r, _doc: name };
    demo.cases[n - 1] = await http(`/cases/${encodeURIComponent(r.case_id)}`).catch(() => null);
    demo.read[n - 1] = r.document_id && demo.source === 'scan'
      ? (demo.cases[n - 1]?.documents || []).find((d) => d.document_id === r.document_id) || null : null;
    demo.step = n; demo.open = n;
  } catch (e) {
    toast(e.message, true); stopAuto();
    demo.open = demo.step;
  } finally {
    demo.busy = false; demo.pending = null;
    if (demo.step >= STORY.length) stopAuto();
    renderDemo();
    refresh();
  }
}

// mod „scanate”: autopilotul ia fișierul din inbox, îl citește și îl trimite pipeline-ului; așteptăm rezultatul
async function waitReceived(n, name) {
  demo.pending = { n, name, status: 'waiting', since: Date.now() };
  while (Date.now() - demo.pending.since < SCAN_TIMEOUT_MS) {
    const st = await http(`/demo/received/${encodeURIComponent(name)}`);
    if (st.status === 'done') return st.result;
    if (st.status === 'failed') throw new Error(`Documentul ${name} nu a putut fi procesat (vezi inbox/failed).`);
    Object.assign(demo.pending, { status: st.status, autopilot: st.autopilot });
    renderDemo();
    await new Promise((ok) => setTimeout(ok, 1500));
  }
  throw new Error(`${name}: niciun rezultat după ${SCAN_TIMEOUT_MS / 60000} minute (rulează autopilotul?).`);
}

async function resetDemo() {
  stopAuto();
  demo.busy = true; renderDemo();
  try { await http(`/demo/reset?variants=pensie${demo.source === 'scan' ? '&inbox=true' : ''}`, { method: 'POST' }); toast('Pornit de la zero.'); }
  catch (e) { toast(e.message, true); }
  Object.assign(demo, { step: 0, results: [], cases: [], read: [], handoffs: [], open: 0, busy: false, approvedBy: null, pending: null });
  renderDemo(); refresh();
}

async function approveDemo(plan) {
  demo.busy = true; renderDemo();
  try {
    await api.approve(plan.plan_id, 'operator demo');
    demo.approvedBy = 'operator demo';
    const c = await http(`/cases/${DEMO_CASE}`);
    demo.cases[demo.cases.length - 1 - [...demo.cases].reverse().findIndex((x) => x?.id === DEMO_CASE)] = c;
    toast('Plata a fost aprobată. Liniile blocate rămân pe loc.');
  } catch (e) { toast(e.message, true); }
  demo.busy = false; renderDemo(); refresh();
}

function toggleAuto() { if (demo.auto) stopAuto(); else { demo.auto = setInterval(nextStep, 3500); nextStep(); } }
function stopAuto() { if (demo.auto) clearInterval(demo.auto); demo.auto = null; }

async function pollHandoffs() {
  if (ui.view !== 'demo') return;
  try {
    const hs = await http('/handoffs');
    if (hs.length !== demo.handoffs.length) { demo.handoffs = hs; renderDemo(); }
  } catch { /* server vechi fără /handoffs: rămânem pe „planificat” */ }
}

document.addEventListener('keydown', (ev) => {
  if (ui.view !== 'demo' || ev.target.closest('input, textarea, select, .modal')) return;
  if (ev.key === 'Escape') { ev.preventDefault(); closeFlow(); return; }   // fluxul se închide, înapoi la dosare
  const onButton = ev.target.closest('button');
  if (demo.mode === 'manual') {   // pe roadmap (orice dosar): ← → schimbă pasul deschis (oricare; scanarea se vede oricând)
    const to = demo.open + (ev.key === 'ArrowRight' ? 1 : ev.key === 'ArrowLeft' ? -1 : 0);
    if (to !== demo.open && to >= 1 && to <= mCount()) { ev.preventDefault(); demo.open = to; renderDemo(); }
    return;
  }
  if (ev.key === 'ArrowRight' || (ev.key === ' ' && !onButton)) { ev.preventDefault(); nextStep(); }
  if (ev.key === 'ArrowLeft' && demo.open > 1) { demo.open -= 1; renderDemo(); }
});
