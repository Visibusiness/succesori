// doc-actions.js: previzualizarea și descărcarea oricărui document generat de bancă sau de agenți, aceeași peste tot.
// Datele: GET /cases/{id}/generated (lista) și GET /cases/{id}/generated/{doc}?format=pdf|md|txt[&download=1] (agent/generated_docs.py).
// Expune global:
//   openDocPreview({ title, subtitle, url, markdown, markdownUrl, downloadUrl, downloadName, back })
//       fereastra mare: PDF-ul (url) în iframe și/sau textul (markdown sau markdownUrl) formatat cu mdRender; „Descarcă”,
//       „Deschide în filă nouă”, „Închide” / Esc. Pe mobil ocupă tot ecranul și începe cu textul (PDF-ul rămâne la un clic).
//   docActions(doc)              butoanele „Previzualizează” și „Descarcă” pentru un obiect din /generated
//   generatedDocs(caseId)        Promise cu lista din /generated (ținută 3 s: mai multe secțiuni ale aceluiași dosar fac o cerere)
//   generatedDocsList(caseId, { group, kinds, filter, title, empty })
//       lista documentelor dosarului (titlu, tip, autor, dată, destinatar, stare + docActions); group = corr | ai | pay
//   docActionsFor(caseId, match) un element care se umple cu docActions pentru documentele care îndeplinesc match(doc)
//       (o escaladare: d => d.escalation_id === id; o intrare din jurnal: d => d.event_id === e.id)
// Depinde de h, mdRender, fmtDate, badge, API_BASE (app.js). Iconițele sunt SVG: mașina n-are font de emoji.

const DOC_ICON_PATHS = {
  eye: '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
  external: '<path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  close: '<path d="M6 6l12 12"/><path d="M18 6 6 18"/>',
};
function docIcon(name, size = 16) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [k, v] of Object.entries({ viewBox: '0 0 24 24', width: String(size), height: String(size), fill: 'none', stroke: 'currentColor',
    'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', class: 'doc-ico' })) svg.setAttribute(k, v);
  svg.innerHTML = DOC_ICON_PATHS[name] || '';
  return svg;
}
const docEsc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const docNarrow = () => matchMedia('(max-width: 640px)').matches;

function openDocPreview(opts) {
  document.querySelector('.modal.mdv')?.close?.();
  document.querySelector('.modal.mdv')?.remove();
  const urls = [];
  const blob = (text, type) => { const u = URL.createObjectURL(new Blob([text], { type })); urls.push(u); return u; };
  let markdown = opts.markdown ?? null;
  const hasText = markdown != null || !!opts.markdownUrl;
  const textBox = h('div', { class: 'mdv-text' }, h('p', { class: 'muted' }, 'Se încarcă…'));
  const pdfBox = opts.url ? h('iframe', { title: opts.title, class: 'mdv-pdf' }) : null;   // src la prima afișare
  const body = h('div', { class: 'mdv-body' });
  const download = h('a', { class: 'mdv-btn mdv-download', download: opts.downloadName || (opts.url ? 'document.pdf' : 'document.md') },
    docIcon('download'), 'Descarcă');
  const newTab = h('a', { class: 'mdv-btn mdv-newtab', target: '_blank', rel: 'noopener' }, docIcon('external'), 'Deschide în filă nouă');
  const loadText = async () => {
    if (markdown == null) {
      try {
        const r = await fetch(opts.markdownUrl);
        if (!r.ok) throw new Error(`serverul a răspuns ${r.status}`);
        markdown = await r.text();
      } catch (e) { textBox.replaceChildren(h('p', {}, h('strong', {}, 'Nu pot afișa textul. '), e.message)); return; }
    }
    const md = mdRender(markdown || '(documentul nu are text)');
    textBox.replaceChildren(md);
    if (!opts.url) {   // fără PDF: descarci textul, fila nouă arată textul formatat
      download.href = opts.downloadUrl || blob(markdown || '', 'text/markdown;charset=utf-8');
      newTab.href = blob(`<!doctype html><meta charset="utf-8"><title>${docEsc(opts.title)}</title>`
        + '<style>body{font:15px/1.55 Arial,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;color:#1a1a1a}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}</style>'
        + `<h1 style="font-size:20px">${docEsc(opts.title)}</h1>${md.outerHTML}`, 'text/html;charset=utf-8');
    }
  };
  if (opts.url) { download.href = opts.downloadUrl || opts.url; newTab.href = opts.url; }
  const tabs = {};
  const show = (which) => {
    if (which === 'pdf' && pdfBox) {
      if (!pdfBox.getAttribute('src')) pdfBox.src = opts.url;
      body.replaceChildren(pdfBox);
    } else {
      body.replaceChildren(textBox);
      if (textBox.dataset.loaded !== '1') { textBox.dataset.loaded = '1'; loadText(); }
    }
    Object.entries(tabs).forEach(([k, b]) => { b.classList.toggle('on', k === which); b.setAttribute('aria-pressed', String(k === which)); });
  };
  const seg = opts.url && hasText ? h('div', { class: 'mdv-seg', role: 'group', 'aria-label': 'Cum arăt documentul' },
    tabs.pdf = h('button', { type: 'button', 'data-view': 'pdf', onclick: () => show('pdf') }, 'PDF'),
    tabs.text = h('button', { type: 'button', 'data-view': 'text', onclick: () => show('text') }, 'Text')) : null;
  const onKey = (ev) => { if (ev.key === 'Escape') { ev.stopImmediatePropagation(); ev.preventDefault(); close(); } };
  const close = () => {
    window.removeEventListener('keydown', onKey, true);
    urls.forEach((u) => URL.revokeObjectURL(u));
    overlay.remove();
    opts.back?.focus?.();
  };
  const closeBtn = h('button', { type: 'button', class: 'mdv-close', onclick: close, title: 'Închide (Esc)' }, docIcon('close'), 'Închide');
  const overlay = h('div', { class: 'modal mdv', onclick: (ev) => { if (ev.target === overlay) close(); } },
    h('div', { class: 'mdv-card', role: 'dialog', 'aria-modal': 'true', 'aria-label': `Previzualizare: ${opts.title}` },
      h('div', { class: 'mdv-head' },
        h('div', { class: 'mdv-title' }, h('h3', {}, opts.title), opts.subtitle ? h('div', { class: 'small muted' }, opts.subtitle) : null),
        seg, download, newTab, closeBtn),
      body));
  overlay.close = close;
  window.addEventListener('keydown', onKey, true);   // înaintea altor ferestre (ex. trimiterea scrisorii): Esc închide doar previzualizarea
  document.body.append(overlay);
  show(opts.url && !(hasText && docNarrow()) ? 'pdf' : 'text');
  closeBtn.focus();
  return overlay;
}

// subtitlul ferestrei și al rândului: tipul, cine l-a scris, când, către cine
const docMeta = (d) => [d.kind_label, d.author, d.created ? fmtDate(d.created) : null, d.recipient ? `către ${d.recipient}` : null]
  .filter(Boolean).join(' · ');

function docPreviewOpts(d) {
  const fmts = d.formats || [];
  return { title: d.title, subtitle: docMeta(d), url: fmts.includes('pdf') ? d.url : null, markdownUrl: d.urls?.md || null,
    downloadUrl: d.download_url, downloadName: d.filename };
}

function docActions(d) {
  const abs = (u) => (u && u.startsWith('/') ? API_BASE + u : u);
  const doc = { ...d, url: abs(d.url), download_url: abs(d.download_url), urls: Object.fromEntries(Object.entries(d.urls || {}).map(([k, v]) => [k, abs(v)])) };
  return h('div', { class: 'doc-actions', 'data-doc': d.id },
    h('button', { type: 'button', class: 'doc-preview', title: `Previzualizează: ${d.title}`,
      onclick: (ev) => openDocPreview({ ...docPreviewOpts(doc), back: ev.currentTarget }) }, docIcon('eye'), 'Previzualizează'),
    h('a', { class: 'doc-download', href: doc.download_url, download: d.filename, title: `Descarcă ${d.filename}` }, docIcon('download'), 'Descarcă'));
}

const docCache = new Map();   // caseId -> { at, p }
function generatedDocs(caseId, fresh) {
  const hit = docCache.get(caseId);
  if (!fresh && hit && Date.now() - hit.at < 3000) return hit.p;
  const p = fetch(`${API_BASE}/cases/${encodeURIComponent(caseId)}/generated`).then(async (r) => {
    if (!r.ok) throw Object.assign(new Error(r.status === 404 ? 'Serverul nu știe încă lista documentelor generate (trebuie repornit).' : `Eroare ${r.status}`), { status: r.status });
    return r.json();
  });
  docCache.set(caseId, { at: Date.now(), p });
  p.catch(() => docCache.delete(caseId));
  return p;
}

const DOC_TONE = { letter: 'info', notary_answer: 'info', supplement_request: 'info', insurance_notice: 'info', message: 'warn',
  deficiency_message: 'warn', contact_step: '', investigation: 'bad', audit: 'ok', payment_plan: 'ok' };

function generatedDocItem(d) {
  return h('li', { class: 'gdoc', 'data-kind': d.kind },
    h('div', { class: 'gdoc-main' },
      h('div', { class: 'gdoc-top' }, badge(d.kind_label, DOC_TONE[d.kind]), h('strong', { class: 'gdoc-title' }, d.title)),
      h('div', { class: 'gdoc-meta small muted' }, docMeta(d).split(' · ').slice(1).join(' · '),
        d.status ? [' · ', h('span', { class: 'gdoc-status' }, d.status)] : null)),
    docActions(d));
}

function generatedDocsList(caseId, opts = {}) {
  const title = opts.title === undefined ? 'Documente generate de bancă' : opts.title;
  const head = () => (title ? h('h3', {}, title) : null);
  const box = h('div', { class: 'card gdocs', 'data-gdocs': opts.group || 'toate' }, head(), h('p', { class: 'muted small' }, 'Se încarcă…'));
  generatedDocs(caseId).then((all) => {
    const list = all.filter((d) => (!opts.group || d.group === opts.group) && (!opts.kinds || opts.kinds.includes(d.kind))
      && (!opts.filter || opts.filter(d)));
    box.replaceChildren(...[head(), list.length ? h('ul', { class: 'gdoc-list' }, [...list].reverse().map(generatedDocItem))
      : h('p', { class: 'muted' }, opts.empty || 'Niciun document generat încă.')].filter(Boolean));
  }).catch((e) => box.replaceChildren(...[head(), h('p', { class: 'muted small' }, e.message)].filter(Boolean)));
  return box;
}

function docActionsFor(caseId, match) {
  const slot = h('div', { class: 'doc-slot' });
  generatedDocs(caseId).then((all) => {
    const mine = all.filter(match);
    slot.replaceChildren(...mine.map((d) => h('div', { class: 'doc-slot-item' },
      h('span', { class: 'small' }, h('strong', {}, d.title), h('span', { class: 'muted' }, ` · ${d.author}`)), docActions(d))));
  }).catch(() => slot.remove());
  return slot;
}
