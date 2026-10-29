Sursă: https://platform.claude.com/docs/en/build-with-claude/pdf-support ; https://platform.claude.com/docs/en/build-with-claude/vision ; https://platform.claude.com/docs/en/build-with-claude/structured-outputs ; registries/documents/*.json (ground truth, DOCS) ; kb/tech/claude-tool-use-notes.md · Accesat: 2026-10-28 · Owner: TECH

# Extracția documentelor: PDF cu text vs. scan, schemă, praguri, validări, calibrare

Pasul 2 („Extracție”) din arhitectura din `claude-tool-use-notes.md`. Intrarea e un fișier venit pe orice canal
(e-mail notar, ghișeu, upload în ops-ui, lot DGEP). Ieșirea e un obiect pe schema de extracție. Pe acest obiect rulează
apoi validările deterministe și, numai dacă trec, orchestrarea.

## 1. Fapte din documentația Claude (citate)

PDF (`pdf-support`):
- „Maximum request size: 32 MB (varies by platform)”; „Maximum pages per request: 600 (100 when the request's context
  window is under 1M tokens)”; „Format: Standard PDF (no passwords/encryption)”.
- Cum e procesat un PDF: „The system converts each page of the document into an image. The text from each page is
  extracted and provided alongside each page's image.” Rezultă că un PDF scanat (fără strat de text) e citit tot
  vizual, din imaginea paginii.
- Cost: „Each page typically uses 1,500–3,000 tokens per page depending on content density”, plus costul imaginii
  paginii, calculat ca la vision.
- „Dense PDFs … can fill the context window before reaching the page limit”: soluția recomandată e împărțirea
  documentului pe secțiuni.

Imagini (`vision`):
- Formate: „JPEG, PNG, GIF, and WebP”.
- Mărime: „10 MB (base64-encoded) on the Claude API”, „5 MB (base64-encoded) on Amazon Bedrock”; dimensiune maximă
  „8000x8000 px”. Peste 20 de imagini într-o cerere se aplică o limită mai strictă (≤ 2000 px pe latură e sigur).
- Rezoluție: modelele Claude 4.7+ au „2,576 px” pe latura lungă și „4,784” tokeni vizuali maxim; peste limită,
  imaginea e micșorată. Cost: `⌈w/28⌉ × ⌈h/28⌉` tokeni vizuali.
- Limitări: „Claude might hallucinate or make mistakes when interpreting low-quality, rotated, or very small images
  under 200 pixels.” Compresia JPEG agresivă „can make text difficult to read”.
- „On Amazon Bedrock and Claude Models on Google Cloud (Google managed), only base64-encoded sources are currently
  available.” Varianta „LLM în regiune UE” din BRIEF §2 înseamnă deci: fără Files API și fără URL, doar base64.

Ieșiri structurate (`structured-outputs`, plus nota din `claude-tool-use-notes.md`): `output_config.format` cu JSON
Schema garantează forma. Restricția importantă e că **nu se poate combina cu citations**. Dovada (citatul) o cerem
deci ca un câmp din schemă (`evidence`) și o verificăm noi în cod (§4, V11).

## 2. Ce bloc trimitem: `document` vs `image`

| Intrare | Detectare (cod, înainte de LLM) | Bloc trimis | Pre-procesare |
|---|---|---|---|
| Lot DGEP (JSON/CSV) | extensie + schemă `mosteniri.dgep.death_signal/v0` | **niciunul**: parsare deterministă, fără LLM | validare de schemă |
| PDF nativ (cu strat de text: adresa notarului, răspunsul asigurătorului, certificatele trimise electronic) | `pypdf` extrage ≥ 200 caractere/pagină | `document` (`application/pdf`, base64) | niciuna; păstrăm textul extras local pentru V11 |
| PDF scanat (fără text sau cu text sub prag) | `pypdf` dă text gol/sub prag | `document` (modelul citește oricum imaginea paginii) | marcăm `source_kind=scan` ⇒ praguri mai stricte (§3) |
| Fotografie / scanare (JPEG, PNG, TIFF de la ghișeu) | MIME | `image` | TIFF → PNG; rotire după EXIF; latura lungă ≤ 2576 px; fără recompresie JPEG; sub 200 px ⇒ respins direct, cerem altă scanare |
| PDF > 32 MB sau > 100 pagini | dimensiune / număr de pagini | `document` pe bucăți | împărțire pe pagini; cerem câte o extracție pe secțiune |
| PDF cu parolă | `pypdf` raportează criptare | **niciunul** | escaladare „document protejat”, cerem copie fără parolă |

Reguli:
- Un PDF merge mereu ca `document`, chiar și scanat. Pentru o pagină scanată nu câștigăm nimic dacă o convertim noi
  în imagine, iar blocul `document` păstrează ordinea și numărul paginilor.
- Fiecare document se trimite într-o cerere separată. Nu punem mai multe documente în aceeași cerere: așa nu
  atingem pragul de 20 de imagini și un document nu poate contamina extracția altuia.
- Documentul vine înaintea instrucțiunii în mesaj (recomandarea din vision/PDF).
- Documentele din demo au 1–2 pagini, deci limitele de 32 MB și 100 de pagini nu ne afectează. Le aplicăm totuși ca
  verificări în cod, cu mesaj clar.

## 3. Schema de extracție pe tipuri, câmpuri critice și praguri

Forma comună e cea din `claude-tool-use-notes.md`, cu `document_type` în vocabularul EN canonic (decizie în
`docs/DECISIONS.md`, mapare RO→EN în `kb/glosar.md`): `document_type`, `type_confidence`, `subject`,
`fields[{name, value, confidence, evidence}]`, `legibility`, `issues`. Numele câmpurilor de mai jos sunt cele din
ground truth-ul lui Ștefan (`registries/documents/NN-*.json`, cheia `fields`), ca testele să compare direct.

Niveluri de criticitate:
- **C1: câmpuri pe baza cărora banca acționează** (blocare, sume, plată). Prag de **0,90** pe câmp, `evidence`
  obligatoriu și validare deterministă trecută (§4). Dacă `source_kind=scan`, pragul urcă la **0,95**.
- **C2: câmpuri care leagă documentul de dosar sau de un termen.** Prag de **0,80**; sub prag, câmpul se cere
  confirmat de operator în ops-ui, iar restul dosarului continuă.
- **C3: câmpuri informative.** Fără prag; se afișează cu scorul lor.
- Gate pe document (escaladare totală, nimic automat): `type_confidence < 0,80` sau `legibility = illegible` sau un
  câmp C1 de identificare (CNP) lipsă sau sub prag. E aceeași poartă ca `CONFIDENCE_THRESHOLD = 0.80` din
  `agent/pipeline.py`, plus condiția pe C1.

| `document_type` (EN, canonic; între paranteze numele RO din `registries/documents`) | C1 (≥ 0,90; scan ≥ 0,95) | C2 (≥ 0,80) | C3 |
|---|---|---|---|
| `dgep_signal` (01) | fără LLM: `cnp`, `date_of_death` validate pe schemă | `message_id`, `batch_week` | restul |
| `notary_request` (02, `adresa_notar`) | `defunct_cnp`, `defunct_data_decesului`, `data_referinta_sold` | `nr_dosar_succesoral`, `termen_dezbatere`, `data_adresa`, `notar`, `informatii_solicitate` | `notar_adresa`, `notar_email`, `temei_invocat`, `semnatura_stampila_prezente` |
| `insurance_certificate` (03, `polita_asigurare`) | `insured_cnp`, `loan_contract_number`, `certificate_number` | `insurer`, `start_date`, `beneficiary`, `termen_avizare_zile`, `covered_risks` | `product_name`, `initial_sum_insured_bani`, `cap_bani` |
| `heir_certificate` (04A/04B, `certificat_mostenitor`) | `defunct.cnp`, `defunct.data_decesului`, `mostenitori[].cota`, `mostenitori[].minor`, `masa_activ[].iban`, `masa_activ[].cota_defunct` | `nr_certificat`, `data_certificat`, `nr_dosar_succesoral`, `temei_devolutiune`, `testament`, `mostenitori[].reprezentant_legal`, `regim_matrimonial` | `masa_activ[].valoare_bani` (o calculează banca), `masa_pasiv`, `domiciliu` |
| `insurer_response` (05, `raspuns_asigurator`) | `insured_cnp`, `decizie`, `indemnizatie_bani`, `loan_contract_number` | `nr_dosar_dauna`, `certificate_number`, `data_eveniment`, `motiv_refuz` | `termen_plata`, `nr_raspuns` |
| `supplementary_certificate` (06, `certificat_mostenitor_suplimentar`) | `defunct.cnp`, `masa_activ[].iban`, `masa_activ[].cota_defunct`, `ref_certificat_initial` | `nr_certificat`, `data_certificat`, `nr_dosar_succesoral`, `cote_din` | `scadenta` (o știe banca) |
| `death_certificate` (07, `certificat_deces`) | `cnp`, `data_decesului`, `nume_familie`, `prenume` | `certificat_serie`, `certificat_nr`, `data_nasterii` | `sex`, `format` |

Note:
- Sumele din certificat (`valoare_bani`) sunt C3 intenționat: banca nu plătește după suma scrisă de notar, ci după
  `balance_at_death` din core. Suma din certificat se compară doar ca semnal (V7).
- Cotele se extrag ca text exact („3/8”), nu ca număr zecimal. Conversia în `Fraction` se face în cod.
- Pentru doc 7 e esențial să nu ghicim: schema permite `value: null` + `issues`, iar promptul cere explicit `null`
  pentru orice caracter acoperit. Ground truth-ul are `cnp: null` și `nume_familie_partial: "POP"`.

## 4. Validări deterministe după extracție (cod, nu LLM)

| # | Validare | Unde se aplică | Eșec ⇒ | Legătura cu `expected_agent` (Ștefan) |
|---|---|---|---|---|
| V1 | CNP: 13 cifre, cifra de control (algoritmul oficial) | toate | escaladare `cnp_invalid` | — (în demo CNP-urile sunt mascate cu `X`: cu `DEMO_MODE=1` (decis în DECISIONS) se acceptă masca `^[1-8]X{11}.$\|^[1-8]X{12}$`) |
| V2 | CNP din document = CNP-ul unui client; la documentele 02–06, același cu clientul dosarului | toate | `409` / escaladare `customer_not_found` sau `cnp_mismatch`; niciun freeze | 07: `escalation_reason: "illegible_cnp"`, `freeze: false`, `case_opened: false`, `fuzzy_name_match: false` |
| V3 | data decesului ≤ data documentului ≤ azi; egală cu data din dosar, dacă există | 01, 02, 04, 05, 06, 07 | escaladare `date_conflict` | starea după fiecare doc (`state_after`) rămâne cea așteptată doar dacă V3 trece |
| V4 | suma cotelor = 1, calculată exact cu `Fraction` | 04 | escaladare `shares_invalid`, niciun plan | 04A/04B: `sum_cote: "1/1"`, `escalation: false` |
| V5 | produsele din certificat ⊆ produsele clientului (potrivire după IBAN normalizat, apoi după tip); `coverage_gaps` = produsele clientului minus cele certificate | 04, 06 | produs necunoscut ⇒ escaladare; lipsă ⇒ cerere de supliment | 04: `coverage_gaps: ["DEP-1"]`, acțiunea `request_supplementary_certificate`; 06: `coverage_gaps: []` |
| V6 | IBAN: format RO (`RO` + 2 cifre + 4 litere + 16 alfanumerice), codul băncii `RZBR`, cifra de control mod-97 | 04, 06 | IBAN străin ⇒ produs la altă bancă, ignorat cu notă; mod-97 greșit ⇒ C1 eșuat | IBAN-urile din demo au controlul `00` (invalid intenționat): cu `DEMO_MODE=1` se sare doar peste mod-97; restul validărilor rămân active |
| V7 | `masa_activ[].valoare_bani` față de `balance_at_death` + încasările după deces (320.000 + 210.000 = 530.000 bani) | 04, 06 | doar avertisment în dosar, plata se face după calculul băncii | 04: `split_cc1_bani_after_debts.baza_bani: 527337` |
| V8 | poliță/răspuns: `certificate_number` și `loan_contract_number` = cele de pe creditul clientului; `indemnizatie_bani` ≤ principalul la D | 03, 05 | escaladare `policy_mismatch` | 03: `product_id: "CRD-1"`, `exclusion_flags: []`; 05: `credit_stins_de_asigurator: true`, `datorie_ramasa_masa_bani: 2663` |
| V9 | supliment: `ref_certificat_initial` = un certificat deja în dosar (nr 87, 2026-10-22); același `nr_dosar_succesoral` | 06 | escaladare `supplement_without_certificate` | 06: `state_after: "PAYMENT_PENDING_APPROVAL"` |
| V10 | moștenitor cu `minor: true` ⇒ trebuie să existe `reprezentant_legal`; partea lui se blochează | 04, 06 | blocare + cerere de documente (nu escaladare) | 04: `flags: ["MINOR_HEIR", "CONFLICT_INTERESE_PARINTE_MINOR"]`; 06: `blocked_heirs: ["ELENA"]` |
| V11 | `evidence` pentru fiecare câmp C1 se regăsește în textul extras local (după normalizarea spațiilor și diacriticelor) | PDF nativ | câmpul coboară la C2 (îl confirmă un om); nu blochează dosarul | — (protecție împotriva valorilor inventate; la scanări nu se aplică) |

Testele din `tests/` iau `fields` din fiecare JSON ca intrare pentru validări (fără LLM) și compară efectul cu
`expected_agent`. Un test separat, opțional și cu cost, rulează extracția reală pe PDF-urile generate și compară
câmpurile cu `fields`.

## 5. Calibrarea pragurilor pe cele 7 documente

Scorurile declarate de model nu sunt probabilități calibrate (vezi `claude-tool-use-notes.md` § Necunoscut). Cu doar
8 documente (7 + varianta 4B) nu putem calibra statistic, dar putem verifica că pragurile **separă** cazurile:

1. Rulăm extracția de **5 ori** pe fiecare PDF generat de `registries/generator` (docs 02–07, 04A și 04B).
   Înregistrăm, pentru fiecare câmp, scorul declarat și dacă valoarea e egală cu ground truth-ul.
2. **Criteriul de acceptare**:
   - (a) pe docs 02–06, toate câmpurile C1 corecte au scor ≥ 0,90 în toate cele 5 rulări;
   - (b) pe doc 7, gate-ul de document se declanșează în 5/5 rulări (`legibility=illegible` sau CNP `null`);
   - (c) niciun câmp C1 greșit nu trece de 0,90.
3. Dacă (c) pică, pragul C1 urcă până la primul scor care exclude toate erorile. Dacă atunci pică (a), nu forțăm
   pragul: câmpul respectiv devine „confirmare umană obligatorie” (vezi mai jos).
4. **Mai multe puncte de măsură (amânat, fără prioritate acum):** generatorul lui Ștefan (020) ar putea produce variante degradate și ale docs 02–06 (rotire
   3–10°, pată pe un câmp C1, JPEG de calitate mică). Ar fi ~20 de documente: puține pentru statistică, dar suficiente
   ca să vedem dacă scorul scade când se degradează documentul.
5. **Auto-consistență:** extracția câmpurilor C1 se face de două ori, independent. Dacă valorile diferă, escaladăm
   indiferent de scor. Aceasta e verificarea care nu depinde de calibrare.

**Ce facem dacă scorul nu e calibrat** (implicit, până trece pasul 2):
- Scorul se folosește doar ca semnal de ordine („mai sigur / mai puțin sigur”), nu ca probabilitate.
- Orice acțiune ireversibilă rămâne cu om în buclă, indiferent de scor (plata e deja așa). Blocarea pe semnal DGEP
  rămâne reversibilă (decizia D-DGEP).
- Acțiunile automate pe un câmp C1 cer **toate** condițiile: scor ≥ prag, validarea deterministă trecută (V1–V10),
  auto-consistență și, la PDF-urile native, V11.
- Raportăm în ops-ui scorul **și** validările trecute, ca operatorul să vadă de ce a acționat agentul.

## Ce înseamnă pentru agent
- Rutarea pe tip de bloc o face codul, nu modelul: DGEP fără LLM; PDF ⇒ `document`; imagine ⇒ `image` după
  normalizare. PDF-urile cu parolă și imaginile sub 200 px se escaladează înainte de orice apel.
- Extracția folosește `output_config.format` cu schema tipului, plus `evidence` ca text (nu citations, incompatibile).
  Un apel per document, base64 (compatibil cu Bedrock/Vertex în UE).
- Pragurile: gate de document 0,80 (deja în `agent/pipeline.py`); C1 0,90 (0,95 la scan); C2 0,80 cu confirmare
  umană sub prag.
- Validările V1–V11 sunt funcții pure în `agent/rules/` și au teste pe `fields` + `expected_agent` din
  `registries/documents/`.
- Doc 7 trebuie să se oprească la gate: niciun freeze, niciun dosar, nicio potrivire „aproximativă” pe nume.

## Necunoscut
- Cât de bine e calibrat scorul declarat pe documente românești scanate. Se măsoară cu protocolul din §5; până
  atunci, regula „necalibrat” de mai sus.
- Dacă modelul citește corect diacriticele și ștampilele peste text pe scanări reale. Avem doar documente generate
  de noi.
- Limitele exacte de mărime a cererii pe Bedrock/Vertex în UE („varies by platform”). De verificat la alegerea
  platformei.
- Formatul real al scanărilor de la ghișeu (TIFF multipagină? PDF/A?). Nu avem date de la Raiffeisen.
