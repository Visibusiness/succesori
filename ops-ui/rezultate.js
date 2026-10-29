/* Ecranul „Rezultate” (tab în aplicație, #view-results): citește results.json (generat de scripts/build_results.py) și arată
   fiecare cifră cu sursa și data. Deschis din fișier (file://) folosește results-data.js, aceleași date încărcate ca script.
   Totul stă într-o funcție (nimic global în afară de renderResults), ca să nu se bată cu numele din app.js. */
(() => {
'use strict';

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const NF = new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 2 });
const NF_SMALL = new Intl.NumberFormat('ro-RO', { maximumSignificantDigits: 2 });

function fmtDate(d) {
  if (!d) return 'fără dată';
  const g = String(d).match(/^(\d{4})-(\d\d)-(\d\d)(?:[T ](\d\d):(\d\d))?/);
  if (!g) return String(d);
  return `${g[3]}.${g[2]}.${g[1]}` + (g[4] ? ` ${g[4]}:${g[5]}` + (String(d).includes('+00:00') ? ' UTC' : '') : '');
}
const srcList = (s) => (Array.isArray(s) ? s : s ? [s] : []);
function fmtVal(v, unit) {
  if (v === null || v === undefined) return null;
  if (Array.isArray(v)) return v.map((x) => fmtVal(x, '')).join('–');
  if (typeof v === 'number') return (Math.abs(v) > 0 && Math.abs(v) < 0.1 ? NF_SMALL : NF).format(v) + (unit === '%' ? '%' : '');
  return String(v);
}
function unitOf(m) { return m.unitate && m.unitate !== '%' ? m.unitate : ''; }

function tipText(m) {
  const srcs = srcList(m.sursa);
  let t = `<b>Sursa:</b> ${srcs.length ? srcs.map(esc).join('<br>') : '—'}<br><b>Data:</b> ${esc(fmtDate(m.data))}`;
  if (m.nota) t += `<br>${esc(m.nota)}`;
  if (m.motiv) t += `<br><b>De ce lipsește:</b> ${esc(m.motiv)}`;
  return t;
}
function srcLine(m) {
  const srcs = srcList(m.sursa);
  const first = srcs.length > 1 ? `${srcs[0]} (+${srcs.length - 1})` : srcs[0] || '—';
  return `<span class="src">${esc(first)} · ${esc(fmtDate(m.data))}</span>`;
}
/* o cifră: valoarea cu tooltip (sursa, data, nota); `caption` = sursa și sub ea */
function fig(m, { caption = false, unit = false } = {}) {
  if (!m) return '<span class="na">—</span>';
  const v = fmtVal(m.valoare, m.unitate);
  const body = v === null
    ? `<span class="na fig" tabindex="0" data-tip="${esc(tipText(m))}">nemăsurat</span>`
    : `<span class="fig" tabindex="0" data-tip="${esc(tipText(m))}">${esc(v)}${unit && unitOf(m) ? `<span class="unit">${esc(unitOf(m))}</span>` : ''}</span>`;
  return body + (caption ? (v === null ? `<span class="src">${esc(m.motiv || '')}</span>` : srcLine(m)) : '');
}
function tile(label, m, { hero = false, note = '' } = {}) {
  return `<div class="tile${hero ? ' hero' : ''}"><div class="label">${label}</div><div class="big">${fig(m, { unit: true })}</div>`
    + (note ? `<div class="note">${note}</div>` : '') + (m ? (m.valoare === null ? `<span class="src">${esc(m.motiv || '')}</span>` : srcLine(m)) : '') + '</div>';
}
const table = (head, rows) => `<div class="table-wrap"><table><thead><tr>${head.map((h) => `<th${h.startsWith('#') ? ' class="num"' : ''}>${esc(h.replace(/^#/, ''))}</th>`).join('')}</tr></thead>`
  + `<tbody>${rows.map((r) => `<tr>${r.map((c) => (typeof c === 'object' && c && c.num ? `<td class="num">${c.html}</td>` : `<td>${c ?? ''}</td>`)).join('')}</tr>`).join('')}</tbody></table></div>`;
const num = (html) => ({ num: true, html });
const card = (id, title, lead, html) => `<section class="card" id="${id}"><h2>${title}</h2><p class="lead">${lead}</p>${html}</section>`;
const DOCS = { '01': 'semnal DGEP', '02': 'adresa notarului', '03': 'certificat de asigurare', '04': 'certificat de moștenitor',
  '05': 'răspunsul asigurătorului', '06': 'certificat suplimentar', '07': 'certificat de deces ilizibil' };   // scripts/smoke_e2e.py STEPS
const EST = '<span class="tag est">estimare proprie</span>';

/* ---------- graficul: evoluția prin bucla de antrenare ---------- */
const SERIES = [['holdout_aug', 'Holdout augmentat', 'var(--s1)', 'Holdout aug.'], ['holdout', 'Holdout', 'var(--s2)', 'Holdout'],
  ['train', 'Antrenare', 'var(--s3)', 'Antrenare']];

function trainingChart(tr) {
  const pts = tr.puncte || [];
  if (pts.length < 2) return `<p class="na">Fără date despre bucla de antrenare (${esc(tr.motiv || 'log lipsă')}).</p>`;
  const W = 640, H = 280, L = 44, R = 132, T = 16, B = 34;
  const vals = pts.flatMap((p) => SERIES.map(([k]) => p[k]));
  const lo = Math.floor(Math.min(...vals) - 0.5), hi = Math.min(100, Math.ceil(Math.max(...vals) + 0.3));
  const x = (i) => L + (i * (W - L - R)) / (pts.length - 1);
  const y = (v) => T + ((hi - v) * (H - T - B)) / (hi - lo);
  const step = hi - lo > 4 ? 1 : 0.5;
  let grid = '';
  for (let v = lo; v <= hi + 1e-9; v += step) grid += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="lbl" x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${NF.format(v)}%</text>`;
  const xl = pts.map((p, i) => `<text class="lbl" x="${x(i)}" y="${H - 12}" text-anchor="middle">${esc(p.pas)}</text>`).join('');
  const lines = SERIES.map(([k, , col, name]) => {
    const d = pts.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p[k]).toFixed(1)}`).join(' ');
    const dots = pts.map((p, i) => `<circle cx="${x(i)}" cy="${y(p[k])}" r="4" style="fill:${col};stroke:var(--panel)" stroke-width="2"/>`).join('');
    const last = pts[pts.length - 1];
    return `<path d="${d}" fill="none" style="stroke:${col}" stroke-width="2" stroke-linejoin="round"/>${dots}`
      + `<text class="val" x="${x(pts.length - 1) + 9}" y="${y(last[k]) + 4}">${esc(name)} ${NF.format(last[k])}%</text>`;
  }).join('');
  const meta = { sursa: tr.sursa, data: tr.data };
  const hits = pts.map((p, i) => {
    const w = (W - L - R) / (pts.length - 1);
    const t = `<b>${esc(p.pas)}</b><br>` + SERIES.map(([k, n]) => `${esc(n)}: ${NF.format(p[k])}%`).join('<br>') + '<br>' + tipText(meta);
    return `<rect class="hit" x="${x(i) - w / 2}" y="${T}" width="${w}" height="${H - T - B}" data-tip="${esc(t)}"/>`;
  }).join('');
  const start = pts[0].holdout_aug, end = pts[pts.length - 1].holdout_aug;
  return `<div class="legend">${SERIES.map(([, n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join('')}</div>`
    + `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Acuratețea pe câmpuri prin bucla de antrenare: holdout augmentat de la ${NF.format(start)}% la ${NF.format(end)}%">`
    + `<g class="grid">${grid}</g><g class="axis">${xl}</g>${lines}${hits}</svg></div>`
    + `<p class="muted small">Acuratețea pe câmpuri (% din câmpurile din ground truth), măsurată după fiecare ciclu; axa începe la ${lo}%. ${srcLine(meta)}</p>`;
}

/* ---------- secțiunile ---------- */
function secCitire(c) {
  const by = Object.fromEntries(c.seturi.map((s) => [s.set, s]));
  const tr = c.antrenare || {};
  const tiles = `<div class="tiles">
    <div class="tile hero"><div class="label">Holdout augmentat (OCR, fără diacritice, formate), prin antrenare</div>
      <div class="big compare">${fig(tr.holdout_aug_pornire)}<span class="arrow">→</span>${fig(tr.holdout_aug_acum)}</div>
      <div class="note">${fig(tr.cicluri)} cicluri ale buclei eval → retro → eval</div>${tr.holdout_aug_acum ? srcLine(tr.holdout_aug_acum) : ''}</div>
    ${tile('Holdout (documente nevăzute la antrenare)', by.holdout?.campuri)}
    ${tile('Texte reale (formulare publice)', by['real-text']?.campuri)}
    ${tile('Certificate de deces din PDF/scan/foto', by.forms?.campuri)}</div>`;
  const rows = c.seturi.map((s) => [
    `<b>${esc(s.eticheta)}</b><br><code>${esc(s.set)}</code>`, num(s.n ?? '—'),
    num(fig(s.campuri)), num(fig(s.tip)), num(fig(s.prag)),
    num(s.prima_rulare_valida ? fig(s.prima_rulare_valida) : '—'),
    s.campuri.valoare === null ? `<span class="na">${esc(s.campuri.motiv)}</span>` : (s.rulari ? `${fig(s.rulari)} rulări${srcLine(s.campuri)}` : ''),
  ]);
  const ab = c.ab_haiku_sonnet || {};
  const abRows = (ab.modele || []).map((r) => [`<b>${esc(r.model)}</b>`, num(fig(r.train)), num(fig(r.holdout)), num(fig(r.tip))]);
  return card('citire', 'Cât de bine citește', 'Extractorul (Claude) transformă documentul în câmpuri, cu scor de încredere; sub prag, documentul merge la om. Evaluat pe seturi cu ground truth, inclusiv seturi pe care bucla de învățare nu le-a văzut niciodată.',
    tiles
    + `<h3>Pe seturi (ultima evaluare)</h3>${table(['Set', '#Documente', '#Câmpuri corecte', '#Tip corect', '#Prag corect', '#Prima rulare validă', 'Rulări / sursa'], rows)}`
    + `<p class="muted small">${esc(c.nota)}. „Prima rulare validă” = prima evaluare a setului, cu versiunea de atunci a extractorului (exclude testele parțiale sub 5 documente și rulările în care extractorul n-a răspuns); reparațiile din aceeași zi explică saltul până la bucla de antrenare, care pornește de la starea de după ele.</p>`
    + `<h3>Evoluția prin bucla de antrenare (28.10.2026)</h3><div class="chart-box"><div>${trainingChart(tr)}</div>`
    + `<div><p class="small">${esc(tr.descriere || '')}</p>`
    + table(['Pas', '#Antrenare', '#Holdout', '#Holdout aug.'], (tr.puncte || []).map((p) => [esc(p.pas), num(NF.format(p.train) + '%'), num(NF.format(p.holdout) + '%'), num(NF.format(p.holdout_aug) + '%')]))
    + `<p class="muted small">Rapoartele retro: ${(tr.rapoarte_retro || []).map((r) => `<code>${esc(r)}</code>`).join(' ')}</p></div></div>`
    + `<h3>A/B: Haiku vs Sonnet pe extracție (decizia 050)</h3>${table(['Model', '#Antrenare', '#Holdout', '#Tip (holdout)'], abRows)}`
    + `<p class="small"><b>Decizie:</b> ${esc(ab.decizie || 'nu e găsită în DECISIONS.md')} Haiku ar costa ${fig(ab.haiku_cost_document, { unit: true })}. <span class="src">${esc(ab.decizie_sursa || '')} · ${esc(fmtDate(ab.decizie_data))}</span></p>`);
}

function secCost(cost, timp) {
  const man = timp.manual || {};
  const dc = cost.dosar_complet || {};
  const agentMin = timp.dosar_cap_coada?.valoare;
  const manualMin = man.central?.valoare != null ? man.central.valoare * 60 : null;
  const bars = agentMin != null && manualMin != null ? `<div class="bars">
      <div class="row"><div>Agentul, cap-coadă (măsurat)</div><div class="bar-wrap"><div class="bar" style="width:${Math.max(0.6, (100 * agentMin) / manualMin)}%"></div><span>${fig(timp.dosar_cap_coada, { unit: true })}</span></div></div>
      <div class="row"><div>Manual, scenariul central ${EST}</div><div class="bar-wrap"><div class="bar manual" style="width:85%"></div><span>${fig(man.central, { unit: true })}</span></div></div>
    </div><p class="muted small">Bara manuală e la scară (${NF.format(manualMin)} min = 85% din lățime); interval ${EST}: ${fig(man.prudent)}–${fig(man.optimist)} ore/dosar, din <code>docs/pitch/business-case.md</code>. La operator rămân aprobarea plății și cazurile escaladate.</p>` : '';
  const tiles = `<div class="tiles">
    ${tile('Cost per dosar complet (7 documente, toți agenții)', dc.valoare !== undefined ? dc : null, { hero: true, note: dc.lei ? `≈ ${NF.format(dc.lei)} lei (curs 4,5 lei/$, ${EST})` : '' })}
    ${tile('Timp cap-coadă per dosar', timp.dosar_cap_coada, { note: timp.dosar_cap_coada?.interval_secunde ? `interval ${timp.dosar_cap_coada.interval_secunde.join('–')} s, ${timp.rulari_verzi} rulări verzi` : '' })}
    ${tile('Timp per document', timp.document, { note: timp.document?.interval_secunde ? `interval ${timp.document.interval_secunde.join('–')} s (cu agenții care rulează după el)` : '' })}
    ${tile('Manual per dosar, scenariul central', man.central, { note: EST })}</div>`;
  const runs = (cost.rulari || []).map((r) => [`<code>${esc(r.run)}</code>`, num(r.documente), esc(r.agenti.join(', ')), num(r.apeluri_agenti),
    num(NF.format(r.extractie_usd) + ' $'), num(NF.format(r.agenti_usd) + ' $'), num(fig(r.cost) + ' $')]);
  const perDoc = Object.entries(timp.pe_document || {}).map(([k, m]) => [`${esc(k)} · ${esc(DOCS[k] || 'document')}`, num(fig(m) + ' s'), num(m.rulari)]);
  return card('cost', 'Cât costă și cât durează', 'Costul vine din <code>total_cost_usd</code> raportat de fiecare apel Claude (<code>scripts/cost_dosar.py</code>); timpul, din smoke-ul cap-coadă pe dosarul demo (7 documente prin inbox, cu toți agenții).',
    tiles + `<h3>Timpul agentului față de lucrul manual</h3>${bars}`
    + `<h3>Din ce e făcut costul</h3><div class="tiles">${tile('Auditorul, din costul dosarului', cost.auditor_pondere)}${tile('Extracția celor 7 documente', cost.extractie_dosar, { unit: true })}`
    + `${tile('Interval pe rulările cu agenți', cost.interval, { note: esc(cost.interval?.nota || '') })}${tile('Variantă optimizată', cost.optimizat, { note: EST + ' nemăsurată cap-coadă' })}</div>`
    + `<h3>Rulările măsurate</h3>${table(['Rulare', '#Doc.', 'Agenți apelați', '#Apeluri', '#Extracție', '#Agenți', '#Total'], runs)}`
    + (perDoc.length ? `<h3>Timp per document (mediana rulărilor verzi)</h3>${table(['Document', '#Timp', '#Rulări'], perDoc)}` : '')
    + `<p class="muted small">Detalii: <code>${esc(cost.doc)}</code>, <code>${esc(timp.raport)}</code>.</p>`);
}

function secStabil(s) {
  const rows = (s.rulari || []).slice().reverse().map((r) => [
    `<code>${esc(r.rulare)}</code><span class="src">${esc(r.sursa)}</span>`, esc(fmtDate(r.data)), esc(r.instanta),
    num(`<span class="fig" tabindex="0" data-tip="${esc(tipText({ sursa: r.sursa, data: r.data }))}">${r.pass}/${r.total}</span>`),
    r.pass === r.total ? '<span class="tag ok">✓ PASS</span>' : '<span class="tag bad">✗ FAIL</span>',
    num(r.secunde != null ? `${r.secunde} s` : '—'),
    r.esecuri.length ? esc(r.esecuri.slice(0, 3).join('; ')) + (r.esecuri.length > 3 ? ` (+${r.esecuri.length - 3})` : '') : '—']);
  return card('stabilitate', 'Cât de stabil e', `Smoke-ul cap-coadă (<code>scripts/smoke_e2e.py</code>) pornește curat, trimite cele 7 documente și verifică ${esc(s.ce_verifica || '')}.`,
    `<div class="tiles">${tile('Ultimele rulări complet verzi', s.ultimele)}${tile('Verificări per rulare', s.verificari_pe_rulare)}</div>`
    + `<h3>Rulările (cele mai noi sus)</h3>${table(['Rulare', 'Data', 'Instanța', '#Verificări', 'Rezultat', '#Durată', 'Ce a picat'], rows)}`
    + `<p class="muted small">Rulările pe MVP-ul viu (:8001) pot fi perturbate de oamenii care folosesc demo-ul în paralel (reset); de aceea testele noi rulează pe o instanță izolată (<code>coordonare/bin/test-instance</code>). Raport: <code>${esc(s.raport)}</code>.</p>`);
}

function secSigur(g) {
  const state = g.stare === 'gata' ? '<span class="tag ok">raportul 076 gata</span>' : '<span class="tag wip">în lucru</span>';
  const rows = (g.detalii || []).map((r) => [`<code>${esc(r.fisier)}</code>`, esc(r.atac), esc(r.asteptat), esc(r.obtinut),
    esc(r.decizie || ''), r.ok ? '<span class="tag ok">✓ ca așteptat</span>' : '<span class="tag bad">✗ diferit</span>']);
  return card('siguranta', `Cât de sigur e ${state}`, 'Set adversarial: documente rău-intenționate (instrucțiuni ascunse în PDF, text invizibil, cereri de schimbare a IBAN-ului, JSON „deja aprobat”) și controale legitime care trebuie să treacă. O poartă deterministă (<code>agent/guard.py</code>, fără LLM) le inspectează înainte de extractor; ce e suspect intră în carantină, fără nicio acțiune pe dosar.',
    `<div class="tiles">${tile('Documente în set', g.documente)}${tile('Atacuri oprite de poartă', g.atacuri_oprite)}${tile('Controale trecute fără alarmă falsă', g.controale_trecute)}${tile('Verdict corect, total', g.poarta)}</div>`
    + (g.poarta?.nota ? `<p class="muted small">${esc(g.poarta.nota)}.</p>` : '')
    + (rows.length ? `<h3>Pe document</h3>${table(['Fișier', 'Atac', 'Risc așteptat', 'Risc obținut', 'Decizie așteptată', 'Verdict'], rows)}` : '')
    + `<p class="muted small">Setul: <code>${esc(g.set)}</code>${g.raport_076 ? `, raport <code>${esc(g.raport_076)}</code>` : ''}.</p>`);
}

function secDate(d) {
  const rows = (d.categorii || []).map((c) => [`<b>${esc(c.eticheta)}</b><br><code>${esc(c.categorie)}</code>`, num(fig(c.surse)), num(fig(c.fisiere)),
    c.surse.valoare === null ? `<span class="na">${esc(c.surse.motiv)}</span>` : srcLine(c.surse)]);
  const pj = d.portal_just || {};
  const banks = (pj.pe_banca || []).map((b) => [esc(b.banca), num(fig(b.dosare))]);
  return card('date', 'Pe ce date reale ne bazăm', 'Surse publice descărcate și indexate (condiții de asigurare, proceduri ale băncilor, formulare oficiale, hotărâri anonimizate, statistici). Aici sunt doar numărătorile; conținutul rămâne în <code>kb/_downloads/realsurse/</code>.',
    `<div class="tiles">${tile('Surse reale indexate', d.total_surse)}${tile('Dosare de instanță cu Raiffeisen parte, 2023–2026', pj.raiffeisen_toate)}`
    + `${tile('…dintre ele cu termeni de succesiune', pj.raiffeisen_termeni)}${tile('…nucleu succesoral (succesiune, moștenire, indiviziune, deces)', pj.raiffeisen_nucleu)}</div>`
    + `<div class="chart-box"><div><h3>Pe categorii</h3>${table(['Categorie', '#Surse în index', '#Fișiere', 'Index'], rows)}<p class="muted small">${esc(d.nota)}.</p></div>`
    + `<div><h3>Dosare cu termeni de succesiune, pe bancă</h3>${table(['Bancă', '#Dosare 2023–2026'], banks)}`
    + `<p class="muted small">Din ${fig(pj.raspunsuri_api)} răspunsuri ale API-ului portalquery.just.ro, doar agregate. ${pj.sursa ? srcLine({ sursa: pj.sursa, data: pj.data }) : esc(pj.motiv || '')}</p></div></div>`);
}

function secInvatare(l) {
  const rows = (l.skills || []).map((s) => [`<code>${esc(s.skill)}</code>`, num(fig(s.lectii)), esc(s.sectiuni.join(', ') || '—'), srcLine(s.lectii)]);
  const ex = (l.exemple || []).map((e) => `<li><b>${esc(e.skill)}</b>: ${esc(e.text)}<span class="src">${esc(e.sursa)} · ${esc(fmtDate(e.data))}</span></li>`).join('');
  return card('invatare', 'Ce au învățat agenții', 'Agentul retro-learner citește erorile din evaluări și corecțiile operatorului și le scrie ca lecții în skill-urile agenților. Codul nu se schimbă; o lecție rămâne doar dacă evaluarea nu regresează.',
    `<div class="tiles">${tile('Lecții învățate, total', l.total)}</div><div class="chart-box"><div><h3>Pe skill</h3>${table(['Skill', '#Lecții', 'Secțiuni', 'Sursa'], rows)}<p class="muted small">${esc(l.nota)}.</p></div>`
    + `<div><h3>Trei exemple</h3><ul class="lessons">${ex}</ul></div></div>`);
}

/* ---------- 082: impact măsurat ---------- */
const TASK_LABELS = { T1: 'Soldurile la data decesului', T2: 'Răspunsul către notar', T3: 'Comisioane de stornat',
  T4: 'Pensia de returnat', T5: 'Cotele și planul de plată', T6: 'Ce lipsește + mesajul + doc. 7' };

function secImpact(im) {
  if (!im) return '';
  const a = im.automatizare || {}, s = im.simulare || {}, st = im.studiu || {};
  const wait = st.stare === 'gata' ? '<span class="tag ok">date primite</span>' : '<span class="tag wip">în așteptare</span>';
  const twelve = (a.douasprezece || []).map((r) => [num(r.nr), esc(r.operatiune), esc(r.acum),
    num(r.reactie_s != null ? `${NF.format(r.reactie_s)} s` : '—'), `<code>${esc(r.eveniment || '—')}</code>${r.artefact_ai ? `<span class="src">${esc(r.artefact_ai)}</span>` : ''}`]);
  const sum12 = a.douasprezece_sumar ? `${a.douasprezece_sumar.fara_om} din 12 fără om (${a.douasprezece_sumar.complet_automat} complet automate, ${a.douasprezece_sumar.cu_agent_ai} cu un agent AI care scrie textul); omul rămâne la ${a.douasprezece_sumar.cu_om}: semnarea răspunsului către notar și aprobarea plății.` : '';
  const traps = (s.capcane || []).map((t) => [esc(t.eticheta), num(t.dosare), num(`${t.prinse}/${t.dosare}`),
    t.prinse === t.dosare ? '<span class="tag ok">✓</span>' : '<span class="tag bad">✗</span>']);
  const causes = Object.entries(s.cauze || {}).sort((x, y) => y[1] - x[1]).map(([k, v]) => [`<code>${esc(k)}</code>`, num(v)]);
  const tasks = Object.entries(st.agent_pe_sarcina || {}).map(([t, v]) => [`${esc(t)} · ${esc(TASK_LABELS[t] || '')}`,
    num(v.secunde != null ? `${NF.format(v.secunde)} s` : '—'), num(`${v.corecte}/${v.campuri}`), esc(v.greseli.join(', ') || '—'),
    st.stare === 'gata' ? '' : '<span class="na">în așteptare</span>']);
  const meta = (x) => (x && x.sursa ? srcLine({ sursa: x.sursa, data: x.data }) : '');
  return card('impact', 'Impact măsurat', 'Trei dovezi că procesul e automatizat și corect: jurnalul unui dosar demo complet, o simulare pe 200 de dosare comparate la ban cu o implementare de referință scrisă separat și un studiu de timp om vs. agent. Detalii și ce e estimare: <code>docs/IMPACT.md</code>.',
    `<h3>1. Automatizarea pe dosar (jurnalul rulării ${esc(a.rulare || '—')}, smoke ${esc(a.smoke || '—')})</h3>`
    + `<div class="tiles">${tile('Operațiuni pe dosar', a.operatiuni, { hero: true, note: a.agent_ai ? `${fig(a.automat)} automate · ${fig(a.agent_ai)} agent AI · ${fig(a.uman)} umane` : '' })}`
    + `${tile('Fără om, din total', a.fara_om)}${tile('Reacție: de la sosirea documentului la acțiune', a.reactie_pipeline, { note: 'include citirea cu LLM' })}`
    + `${tile('…până la scrisori și mesaje gata', a.reactie_agenti)}</div>`
    + (twelve.length ? `<p class="small">Cele 12 operațiuni manuale din brief (§2, „Face singur” + plata): ${esc(sum12)}</p>${table(['#', 'Operațiunea de azi (manuală)', 'Cine o face acum', '#Reacție', 'Dovada în dosar'], twelve)}` : '')
    + (a.decizii_umane ? `<p class="muted small">Decizii umane: ${esc(a.decizii_umane.join('; '))}. ${meta(a)}</p>` : '')
    + `<h3>2. Simularea la scară (seed ${esc(s.seed ?? '—')}, fără LLM)</h3>`
    + `<div class="tiles">${tile('Dosare complet corecte', s.corecte, { hero: true })}${tile('Linii de plată exacte la ban', s.linii_exacte)}`
    + `${tile('Plăți fără aprobare', s.plati_fara_aprobare)}${tile('Timp pentru toate dosarele', s.timp_total)}</div>`
    + `<div class="chart-box"><div><h3>Capcane prinse</h3>${table(['Capcană', '#Dosare', '#Prinse', ''], traps)}</div>`
    + `<div><h3>Nepotriviri, pe cauză (dosare)</h3>${table(['Cauză', '#Dosare'], causes)}<p class="muted small">Fiecare cauză e un bug raportat, cu exemplul minim, în <code>${esc(s.raport || '')}</code>. Codul agentului nu a fost modificat. Referința: <code>${esc(s.referinta || '')}</code>.</p></div></div>`
    + `<h3>3. Studiul de timp om vs. agent ${wait}</h3>`
    + `<div class="tiles">${tile('Agentul: timp de lucru pe dosar', st.agent_timp)}${tile('Agentul: câmpuri greșite (aceeași cheie)', st.agent_greseli)}`
    + `${tile('Doi colegi, de mână', st.om_timp)}${st.raport ? tile('Raport om / agent', st.raport) : ''}</div>`
    + (tasks.length ? table(['Sarcina', '#Agent', '#Agent corecte', 'Agent: greșit', 'Om'], tasks) : '')
    + `<p class="muted small">Fișa de lucru, tabelul și cheia: <code>${esc(st.fisa || 'docs/studiu-timp/')}</code>. Cifrele oamenilor apar după <code>scripts/impact_studiu.py</code> + <code>scripts/build_results.py</code>.</p>`);
}

function render(d) {
  document.getElementById('res-meta').innerHTML = `Generat ${esc(fmtDate(d.generat))} de <code>${esc(d.generator)}</code> (se reface oricând: <code>.venv/bin/python ${esc(d.generator)}</code>).`;
  setTimeout(() => showSec('toate'), 0);   // după randare: toate secțiunile
  document.getElementById('res-content').innerHTML = [secCitire(d.citire), secCost(d.cost, d.timp), secStabil(d.stabilitate),
    secSigur(d.siguranta), secDate(d.date_reale), secInvatare(d.invatare), secImpact(d.impact)].join('');
}

/* tooltip comun pentru [data-tip]: mouse și focus de la tastatură */
const tip = document.getElementById('res-tip');
function showTip(el, x, y) {
  tip.innerHTML = el.getAttribute('data-tip');
  tip.hidden = false;
  const r = tip.getBoundingClientRect();
  tip.style.left = Math.max(6, Math.min(x + 12, window.innerWidth - r.width - 6)) + 'px';
  tip.style.top = (y + 16 + r.height > window.innerHeight ? y - r.height - 10 : y + 16) + 'px';
}
document.addEventListener('mousemove', (e) => {
  const el = e.target.closest && e.target.closest('[data-tip]');
  if (el) showTip(el, e.clientX, e.clientY); else tip.hidden = true;
});
document.addEventListener('focusin', (e) => {
  const el = e.target.closest && e.target.closest('[data-tip]');
  if (!el) return;
  const r = el.getBoundingClientRect();
  showTip(el, r.left, r.bottom - 8);
});
document.addEventListener('focusout', () => { tip.hidden = true; });

function fail(msg) {
  document.getElementById('res-content').innerHTML = `<section class="card"><h2>Fără date</h2><p>${esc(msg)}</p><p>Rulează <code>.venv/bin/python scripts/build_results.py</code>.</p></section>`;
}
// butoanele de sub titlu: „Toate” (implicit, la fiecare deschidere a tabului) sau doar secțiunea aleasă, fără derulare
function showSec(id) {
  const secs = [...document.querySelectorAll('#res-content > section.card')];
  if (!secs.length) return;
  if (id !== 'toate' && !secs.some((s) => s.id === id)) id = 'toate';
  secs.forEach((s) => { const on = id === 'toate' || s.id === id; s.hidden = !on; s.classList.toggle('sec-in', on); });
  document.querySelectorAll('#view-results .res-nav [data-sec]').forEach((b) => {
    b.classList.toggle('on', b.dataset.sec === id); b.setAttribute('aria-selected', String(b.dataset.sec === id)); b.setAttribute('role', 'tab');
  });
}
document.addEventListener('click', (e) => {
  const b = e.target.closest && e.target.closest('#view-results .res-nav [data-sec]');
  if (b) showSec(b.dataset.sec);
});

let loaded = false;
// chemat de showView('results'): datele se citesc o singură dată, la prima deschidere a tabului
window.renderResults = () => {
  if (loaded) { showSec('toate'); return; }   // la fiecare deschidere a tabului: „Toate”
  loaded = true;
  if (location.protocol === 'file:') {
    if (window.RESULTS_DATA) render(window.RESULTS_DATA); else fail('results-data.js lipsește lângă pagină.');
  } else {
    fetch('results.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(render)
      .catch((e) => (window.RESULTS_DATA ? render(window.RESULTS_DATA) : fail(`results.json nu s-a putut citi (${e.message}).`)));
  }
};
})();
