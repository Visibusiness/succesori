
## Reparațiile din simulare și scalabilitate (089, bedrock-bugs)
Bug-urile din `registries/simulare/RAPORT-seed82.md` (082) și cursa din raportul 083, reparate în `agent/`. Unde legea / kb nu
spun direct ce face banca, am ales varianta prudentă:
- 2026-10-28 · bedrock-bugs · **Soțul supraviețuitor = calitatea din certificat**, nu primul rând. Dacă certificatul (extracția)
  nu dă calitatea niciunui moștenitor (ex. extracția demo), soțul e moștenitorul cu numele soțului din evidențele băncii
  (KYC, `customer.spouse`). Dacă tot nu e unul singur (niciunul, doi „soți”, toate calitățile date fără soț) **și** există
  bunuri comune ⇒ escaladare `spouse_unidentified`, fără plan. Motiv: jumătatea de proprietar (C.civ. art. 339, 343) dată
  cui nu trebuie e o plată greșită ireversibilă; ghicitul după poziție a greșit 13/200 dosare. La bunuri proprii soțul nu
  contează, deci nu se escaladează. De făcut (neaplicat aici): `relationship` adăugat ca opțional în schema extractorului
  (`.claude/skills/extract-documents`), ca certificatele reale să aibă calitatea.
- 2026-10-28 · bedrock-bugs · **Se stornează orice comision debitat după deces, oricare ar fi codul** (BRIEF §2 „stornare
  comisioane de la data decesului”; cazul Bragadiru era tocmai un comision de administrare, nu PREMIUM). `fees_to_reverse`
  poate fi îngustat explicit cu `fee_codes`, dar implicit ia tot. Prudent pentru că un comision încasat greșit e exact
  reclamația din presă; dacă banca are comisioane legitime după deces, se exclud explicit (de confirmat cu banca).
- 2026-10-28 · bedrock-bugs · **Datoria peste contul curent**: contul nu coboară sub 0; restul se scade din depozit(e) (valoarea
  la scadență), iar ce rămâne după tot activul de la bancă e escaladare informativă `debt_exceeds_estate` (moștenitorii
  răspund în limita activului, C.civ. art. 1114; recuperarea restului o decide operatorul). `approve_payment` refuză orice
  linie negativă. Informativă (nu blochează), pentru că planul are deja liniile la 0 și nu plătește nimic în plus.
- 2026-10-28 · bedrock-bugs · **Depozitul ajuns la scadență la data planului** (data documentului care completează planul:
  certificatul, suplimentul sau răspunsul asigurătorului) e plătibil acum, cu dobânda până la scadență; altfel rămâne blocat
  până la scadență, ca înainte. Dobânda după scadență (prelungire / cont curent) nu e modelată; de confirmat cu banca.
- 2026-10-28 · bedrock-bugs · **Refuzul asigurătorului face planul** (cu toată datoria în masă), indiferent de ordinea
  documentelor. Un plan deja aprobat nu se mai reface la un document ulterior.
- 2026-10-28 · bedrock-bugs · **Concurență**: `Pipeline.lock` (RLock) în jurul `receive` / `approve_payment` /
  `confirm_freeze`, iar API-ul îl ține pe toată procesarea unui document (pipeline + trace). Documentele se procesează
  serial; la ~1 ms/document nu e o limită pentru un singur proces. Mai multe procese cer stare partajată (ramura `persistenta`).
