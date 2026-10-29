# ops-ui: panoul operatorului

Aspect în stilul Raiffeisen (galben #FFEE00 pe negru, gri deschis, Arial), antet text „Raiffeisen Bank · Succesiuni” (fără logo-ul oficial).
Aplicație statică, fără build și fără framework: `index.html` + `live.js` + `app.js` + `style.css`. Servită de backend la `/ui/` (API pe aceeași
origine), altfel API la `http://localhost:8000`. **Lucrează doar cu serverul real: nu are mock, date de probă sau bară de demo.** Fără server arată
„Nu mă pot conecta la server” și un buton de reîncercare.

## Taburile (câte unul pe vizualizare)
- **Demo ghidat** (implicit, `demo.js` + `demo.css`): dosarul Mariei Ionescu în 7 pași. Un buton trimite următorul document
  (sau → / spațiu; „Derulează singur”; „De la zero”; moștenire legală / testament). La fiecare pas, trei coloane: ce a citit
  extractorul (câmpuri, încredere, documentul original) → ce a făcut sistemul (acțiuni, jurnalul cu regula, starea înainte/după) →
  cui predă sistemul (agentul, de ce, ce va scrie; din `handoffs_planned`, iar cu autopilotul pornit starea reală din `GET /handoffs`).
  Dedesubt: progresul dosarului, ce lipsește, planul de plată și butonul de aprobare (omul).
  **Selecția de dosar** (`demo-dosare.js`, sus în hero): implicit Maria; un dosar din portofoliu (`GET /worklist`) arată, cu
  aceleași componente (roadmap, banner, stații, „Rândul tău”), etapele lui (DGEP → notar → asigurare → moștenitori → plan → plată),
  unde e oprit și de ce, și decizia care îl așteaptă: aprobă plata (dialogul cu numele), semnează răspunsul către notar, rezolvă
  escaladarea. Selectorul e un câmp de căutare (nume, CNP, număr de dosar, fără diacritice; ↑ ↓ Enter Esc). Selecția și tabul stau
  în URL (`#demo/SC-2026-0107`, `#dosare`, `#agenti`, `#impact`), cu înapoi / înainte; în tabul Dosare, un clic pe rând deschide dosarul aici.
- **Dosare**: contoare „Ce ai de făcut acum” (plăți de aprobat / escaladări / așteaptă documente, filtrează lista) și căutarea; lista are câte un rând
  pe dosar (cine, etapa, ce urmează, termenul, insigna cu deciziile). Detaliul dosarului, de sus în jos: antetul (nume, dosar, stare, termen, o linie de
  cifre), panoul **„Ce ai de făcut”** (fiecare acțiune cu „Du-mă acolo”: deschide secțiunea, derulează și evidențiază locul; plata se poate aproba direct
  de aici; „Nimic de făcut acum” + ce urmează automat), parcursul pe etape (ca în Demo ghidat), filtrele pe activitate (Toate / De făcut de mine /
  Documente / Scrisori și mesaje / Plăți / Escaladări / Agenți AI: aleg secțiunile și intrările din jurnal) și secțiunile restrânse (Plată, Escaladări,
  Termene, Documente, Scrisori și mesaje, Agenți AI, Jurnal, Detalii tehnice); numai prima secțiune cu o acțiune e deschisă.
  Contorul din antet („X decizii te așteaptă”) deschide lista deciziilor din toată banca; fiecare rând duce la locul acțiunii.
  **Dosare e ecranul principal** (`/ui/` = `#dosare`); un clic pe rând (acțiunea lui: decizia care așteaptă sau „Deschide fluxul →”) deschide
  fluxul dosarului (`#demo/<id>`, tabul „Flux dosar”); „Deschide dosarul complet” (CTA-ul din antetul fluxului) = `#dosare/<id>`; înapoi / reîncărcarea
  păstrează locul. Secțiunea Documente: lista (tip, data, sursa, încrederea, suspect) și vizualizatorul mare (fișierul în stânga, câmpurile citite cu
  dovada și scorul în dreapta, Anterior / Următor, ← →; pe mobil ocupă tot ecranul). Stilurile detaliului și ale listei: `dosar.css`.
- **Agenți**: câte un card pentru Sistem (cod) și pentru fiecare agent LLM (Extractor, Investigator, Corespondent, Comunicator cu moștenitorii, Auditor): ce face,
  dacă lucrează acum și la ce, câte apeluri / secunde / dolari, ultimele lui scrieri (deschizi ieșirea).
- **Impact**: sinteză pentru juriu, cu ipotezele afișate.
- **Indicatorul din antet** (pe orice tab): ce face autopilotul acum („Extractorul citește X”, „Corespondentul scrie…”, „Agenți: la dispoziție”). Click → tabul Agenți.

## Documentele generate: previzualizare și descărcare (`doc-actions.js` + `doc-actions.css`)
Orice document scris de bancă sau de agenți (scrisori către notar și asigurător, cererea de supliment, mesajele către moștenitori
și pașii scării de contact, propunerile investigatorului, rapoartele auditorului, planul de plată) vine dintr-un singur registru:
`GET /cases/{id}/generated` (`agent/generated_docs.py`) dă lista (`id`, `kind`, `kind_label`, `group` = corr | ai | pay, `title`,
`created`, `author`, `recipient`, `status`, `formats`, `url`, `download_url`, `urls`, `filename`, plus `event_id` / `escalation_id` /
`message_id` când documentul ține de o intrare din jurnal, de o escaladare sau de un mesaj trimis), iar
`GET /cases/{id}/generated/{doc}?format=pdf|md|txt[&download=1]` îl servește (PDF-ul din `agent/letter_pdf.py`). `doc` e opac.
Funcțiile globale, aceleași peste tot (dosarul complet, fluxul, orice ecran nou):
- `docActions(doc)` → `div.doc-actions` cu „Previzualizează” (`button.doc-preview`) și „Descarcă” (`a.doc-download`, fișierul cu
  numele din `doc.filename`), pentru un obiect din `/generated`;
- `openDocPreview({title, subtitle, url, markdown, markdownUrl, downloadUrl, downloadName, back})` → fereastra mare (`.modal.mdv`):
  PDF-ul (`url`) în iframe și/sau textul (`markdown` sau `markdownUrl`) formatat cu `mdRender`, comutator PDF / Text când există
  amândouă; „Descarcă”, „Deschide în filă nouă”, „Închide” / Esc (Esc închide doar fereastra, nu și dialogul de dedesubt). Pe mobil
  ocupă tot ecranul și începe cu textul. Fără `url`, descărcarea e textul;
- `generatedDocs(caseId)` → Promise cu lista (o cerere la 3 s pe dosar, oricâte secțiuni o cer);
- `generatedDocsList(caseId, {group, kinds, filter, title, empty})` → cardul cu lista (tip, titlu, autor, dată, destinatar, stare + butoanele);
- `docActionsFor(caseId, match)` → un loc care se umple cu `docActions` pentru documentele cu `match(doc)` (ex. `d => d.event_id === e.id`).
În dosarul complet: secțiunea „Documente generate de bancă” (toate), „Scrisori și mesaje” (`group: 'corr'`), „Agenți AI” (`'ai'`),
„Plată” (`'pay'`), „Escaladări” (propunerea, după `escalation_id`), „Jurnal” (după `event_id`), mesajele pentru documente cu probleme
(după `message_id`). În flux (`demo-manual.js`) previzualizarea porților (`mDocView`) e `openDocPreview`.
Exemplu pentru un ecran nou (de exemplu fluxul dosarelor din portofoliu):
```js
generatedDocs(caseId).then((docs) => docs.filter((d) => d.kind === 'notary_answer').forEach((d) => station.append(docActions(d))));
openDocPreview({ title: 'Scrisoarea', url: pdfUrl, downloadUrl: pdfUrl + '&download=1', downloadName: 'SC-2026-0107-raspuns-notar.pdf' });
```

## De unde vin datele
Toate din API: `GET /cases`, `/cases/{id}`, `/cases/{id}/artifacts` (forma `{artifacts, audit}`), `/cases/{id}/generated` (documentele generate), `/escalations`, `/audit`, `/autopilot/status` (sondat la 2 s),
`/inbox` (portalul: `POST` fișiere, `GET` coada), `/cases/{id}/documents/{doc}/preview`. Fără portal (`/inbox` 404) fișierele merg direct la extractor
(`POST /cases/x/documents`), fără scrisori, investigații sau audit; UI-ul spune asta.

## Pornire
- Instanță proprie, goală, cu agenți reali: `scripts/test-instance.sh start 8010` (port 8010, `stop` / `status`). Costă apeluri `claude -p` pe contul care o rulează.
- Servere comune: :8000 stabil (`coordonare/bin/promoveaza`), :8001 dezvoltare. UI-ul se citește de pe disc, deci o schimbare apare după Ctrl+Shift+R.
- `?view=intake|cases|agents|impact` deschide direct un tab; `?case=SC-2026-0001` deschide un dosar.

## Limite
- Core-ul bancar din spatele API-ului e simulat (`agent/core_mock.py`, doi clienți); trimiterea mesajelor merge în coada de trimitere, nu pe canale externe.
- `mock-data.json` și `mock/gen_mock.py` nu mai sunt folosite de UI; au rămas în repo (munca altcuiva, nu le-am șters).
