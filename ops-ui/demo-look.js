// Demo ghidat: aspectul fiecărui pas (culoare, iconiță, expeditor, ce se joacă) și roadmap-ul prin care navighezi.
// Roadmap-ul: linia de progres se umple animat până la ultimul pas terminat, pasul deschis pulsează, cel cu pipeline-ul
// pornit are un inel care se rotește, cel care așteaptă decizia ta are semnal roșu; la hover/focus, o fișă cu scanarea
// și ce se joacă; click sau ← → pentru a naviga. Iconițele sunt SVG (nu depind de fonturile mașinii).
// Depinde de demo.js (demo, STORY, renderDemo), demo-manual.js (mPipe, mPending, mReset) și app.js (h, badge, STATE_LABEL).

const ICON = {
  signal: '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49M7.76 16.24a6 6 0 0 1 0-8.49M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14"/>',
  notary: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  heirs: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  shieldOk: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
  filePlus: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M12 18v-6M9 15h6"/>',
  fileAlert: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M12 11v3M12 17h.01"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  folder: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><path d="M8 14h8M8 17h5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  hand: '<path d="M18 11V6a2 2 0 0 0-4 0v5M14 10V4a2 2 0 0 0-4 0v6M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>',
  bank: '<path d="M3 21h18M5 21V10M19 21V10M9 21V10M15 21V10M12 3l9 5H3z"/>',
};

function svgIcon(name, cls = 'ico') {
  const el = document.createElement('span');
  el.className = cls;
  el.setAttribute('aria-hidden', 'true');
  el.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICON[name] || ''}</svg>`;
  return el;
}

// identitatea fiecărui pas: iconiță, cine trimite; culoarea e a temei (negru pe deschis, galben pe întunecat)
const STEP_LOOK = [
  { icon: 'signal', accent: 'var(--step)', sender: 'DGEP · Evidența Persoanelor', short: 'Semnal DGEP' },
  { icon: 'notary', accent: 'var(--step)', sender: 'Notarul public · dosar 123/2026', short: 'Adresa notarului' },
  { icon: 'shield', accent: 'var(--step)', sender: 'UNIQA · dosarul creditului', short: 'Asigurare' },
  { icon: 'heirs', accent: 'var(--step)', sender: 'Notarul public · certificat nr. 87', short: 'Moștenitori' },
  { icon: 'shieldOk', accent: 'var(--step)', sender: 'UNIQA · Daune Viață', short: 'Răspuns UNIQA' },
  { icon: 'filePlus', accent: 'var(--step)', sender: 'Notarul public · certificat suplimentar', short: 'Supliment' },
];

// starea unui pas pe roadmap: done | current | running | waits | next | locked
function rmState(n, done, cur) {
  const pipe = mPipe(n).status;
  const waits = pipe === 'awaiting' || mPending().some((g) => g.step === n);
  if (waits) return 'waits';
  if (['running', 'stopping'].includes(pipe) || demo.jobs.some((j) => j.step === n && ['queued', 'running'].includes(j.status))) return 'running';
  if (n <= done) return 'done';
  if (n === done + 1) return 'next';
  return 'locked';
}

const RM_LABEL = { done: 'terminat', running: 'AI-ul lucrează', waits: 'rândul tău', next: 'urmează', locked: 'încă nesosit' };

// sub fiecare pas: verde „complet”, galben cu subpasul la care a rămas (dacă e început), nimic dacă nu a început
function rmProgress(n) {
  const gates = Object.values(demo.srv[n]?.gates || {});
  const gate = gates.find((g) => g.status === 'pending');
  if (demo.srv[n]?.next?.do === 'done' && mApplied(n) && !gate) return { tone: 'done', text: 'complet' };
  const job = demo.jobs.find((j) => j.step === n && ['queued', 'running'].includes(j.status));
  const p = mPipe(n);
  const started = mApplied(n) || gates.length || p.status !== 'idle' || demo.jobs.some((j) => j.step === n);
  if (!started) return null;
  const nx = demo.srv[n]?.next;
  const text = gate ? `Rândul tău: ${gate.title}`
    : mPipeLive(n) && p.stage ? p.stage
    : job ? (job.kind === 'extract' ? 'Extractorul citește scanarea' : job.kind === 'agent' ? `${job.agent_label}: ${job.label}` : 'AI-ul lucrează')
    : nx?.do === 'extract' ? 'Urmează: extracția'
    : nx?.do === 'apply' ? 'Urmează: regulile băncii'
    : nx?.do === 'agent' ? `Urmează: ${nx.label}`
    : 'început';
  // pe roadmap doar cine lucrează („Corespondentul”); textul întreg rămâne în tooltip
  return { tone: 'partial', text: gate ? text : text.split(':')[0], full: text };
}

function demoRoadmap(done, cur) {
  const steps = mSteps();   // Maria: cei 6 pași ai ei; alt dosar: pașii lui (demo-manual.js)
  const total = steps.length;
  const span = Math.max(1, total - 1);
  // linia se umple până la ultimul pas terminat; animată de la valoarea de la randarea anterioară
  const to = done <= 1 ? 0 : Math.min(1, (done - 1) / span);
  const from = demo.rmFill ?? to;
  demo.rmFill = to;
  const fresh = demo.rmDone ?? done;   // pașii terminați de la ultima randare „sar” o dată
  demo.rmDone = done;
  const nodes = steps.map((s, i) => {
    const n = i + 1;
    const look = s;
    const st = rmState(n, done, cur);
    const prog = rmProgress(n);
    const reachable = n <= done + 1;
    const icon = st === 'done' ? 'check' : st === 'locked' ? 'lock' : st === 'waits' ? 'hand' : look.icon;
    return h('li', { class: `rm-node ${st}${n === cur ? ' open' : ''}${n > fresh && n <= done ? ' pop' : ''}`, style: `--accent:${look.accent}` },
      // orice pas se poate deschide (scanarea lui se vede oricând); pipeline-ul rămâne blocat până la rândul lui
      h('button', { type: 'button', class: 'rm-dot', 'aria-current': n === cur ? 'step' : null,
        'aria-label': `Pasul ${n}: ${s.title} (${RM_LABEL[st]})`, onclick: () => { demo.open = n; renderDemo(); } },
        svgIcon(icon), h('span', { class: 'rm-num' }, String(n))),
      h('span', { class: 'rm-title' }, look.short),
      prog ? h('span', { class: `rm-chip ${prog.tone}`, title: prog.full || prog.text }, prog.text) : null,
      h('div', { class: 'rm-tip', role: 'tooltip' },
        h('div', { class: 'rm-tip-head' }, svgIcon(look.icon), h('div', {}, h('b', {}, `Pasul ${n}: ${s.title}`), h('div', { class: 'small muted' }, look.sender))),
        n > 1 && isMaria() ? h('img', { class: 'rm-thumb', src: `${API_BASE}/demo/scan/${n}.png?variant=A`, alt: '', loading: 'lazy' }) : null,
        factChips(n, 4),
        reachable ? null : h('p', { class: 'small muted' }, `Poți vedea scanarea; procesarea începe după pasul ${n - 1}.`)));
  });
  const waiting = mPending();
  return h('section', { class: 'card roadmap' },
    h('div', { class: 'rm-head' },
      h('div', {}, h('h3', {}, 'Drumul dosarului'),
        h('p', { class: 'small muted' }, `${done} din ${total} ${isMaria() ? 'documente procesate' : 'pași făcuți'}`, waiting.length ? ' · ' : '',
          waiting.length ? h('b', { class: 'bad-text' }, `${waiting.length} ${waiting.length === 1 ? 'decizie te așteaptă' : 'decizii te așteaptă'}`) : '')),
      h('button', { type: 'button', class: 'link', onclick: mReset, title: isMaria() ? 'Golește dosarul și pornește din nou de la pasul 1' : 'Doar acest dosar revine la starea din portofoliu; celelalte rămân cum sunt' }, '↺ De la zero')),
    h('div', { class: isMaria() ? 'rm-track' : 'rm-track rm-var', style: isMaria() ? null : `--rm-n:${total}` },
      h('div', { class: 'rm-line' },
        h('div', { class: `rm-fill${from !== to ? ' grow' : ''}`, style: `--from:${from * 100}%;--to:${to * 100}%;width:${to * 100}%` }),
        done < total && done >= 1 ? h('div', { class: 'rm-next', style: `left:${to * 100}%;width:${100 / span}%` }) : null),
      h('ol', { class: 'rm-nodes' }, nodes)));
}

// ce s-a citit din document, doar după ce a fost parsat (pasul 1: linia DGEP, după reguli; 2–6: după extractor)
const FACT_FIELDS = ['date_of_death', 'name', 'case_file', 'hearing_date', 'insurer', 'policy_id', 'loan_contract', 'document_number',
  'heirs', 'decision', 'amount', 'cnp'];
function factChips(n, max, tone = '') {
  const fields = !isMaria() ? (mResult(n)?.extracted?.fields || (mExtractJob(n)?.status === 'done' ? mExtractJob(n).output?.fields : null))
    : n === 1 ? (demo.results[0] ? demoDoc(1)?.fields : null) : (mExtractJob(n)?.status === 'done' ? mExtractJob(n).output?.fields : null);
  if (!fields) return null;
  const chips = FACT_FIELDS.filter((k) => fields[k] != null && fields[k] !== '').slice(0, max)
    .map((k) => h('span', { class: `chip ${tone}` }, fieldLabel(k), ': ', h('b', {}, fieldValue(fields[k], k))));
  return chips.length ? h('div', { class: 'chips' }, chips) : null;
}
