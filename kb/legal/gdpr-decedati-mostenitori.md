Sursă: https://gdpr-text.com (recital 27, art. 5, 6, 22 în RO; copii în kb/_downloads/visi/gdprtext-*.html, privreg-r27-ro.html) ; https://legislatie.just.ro (Legea 190/2018, copie just-legea190-2018.html) · Accesat: 2026-10-28 · Owner: DOMAIN

# GDPR: decedați, moștenitori, ce păstrăm în dosar

## Persoane decedate
**Considerentul 27 GDPR:** „Prezentul regulament nu se aplică datelor cu caracter personal referitoare la persoane decedate. Statele membre pot să prevadă norme privind prelucrarea datelor cu caracter personal referitoare la persoane decedate.”

**Legea 190/2018:** am căutat în textul salvat „decedat” și „deces” — **zero apariții**. România nu pare să fi prevăzut norme speciale pentru datele decedaților în această lege (nu am căutat în alte acte). Deci datele defunctului (sold, produse) nu sunt protejate de GDPR, dar rămân protejate de **secretul bancar** (vezi `secret-bancar.md`), care nu depinde de GDPR.

Atenție: în dosar apar și date despre **persoane vii** (moștenitori, soț, reprezentanți, beneficiari de asigurare) — pentru acestea GDPR se aplică integral. Datele defunctului care dezvăluie ceva despre un om viu (ex. cine e beneficiar) tot sunt date ale celui viu.

## Datele moștenitorilor (persoane vii) — temei
**GDPR art. 6 alin. (1):** „Prelucrarea este legală numai dacă și în măsura în care se aplică cel puțin una dintre următoarele condiții:”
- lit. b): „prelucrarea este necesară pentru executarea unui contract la care persoana vizată este parte sau pentru a face demersuri la cererea persoanei vizate înainte de încheierea unui contract” — moștenitorul cere plata/deblocarea.
- lit. c): „prelucrarea este necesară în vederea îndeplinirii unei obligații legale care îi revine operatorului” — identificare AML (vezi `aml-kyc-mostenitori.md`), păstrare înregistrări.

Recomandare (interpretare): lit. c) pentru KYC și păstrare; lit. b) nu se potrivește perfect (moștenitorul nu e încă parte într-un contract cu banca) — a se valida cu DPO-ul băncii, nu cu noi.

**CNP / număr de identificare național — Legea 190/2018 art. 4 alin. (1):** „Prelucrarea unui număr de identificare național, inclusiv prin colectarea sau dezvăluirea documentelor ce îl conțin, se poate efectua în situațiile prevăzute de art. 6 alin. (1) din Regulamentul general privind protecția datelor.”

## Ce reținem și cât timp
**GDPR art. 5 alin. (1) lit. e):** datele sunt „păstrate într-o formă care permite identificarea persoanelor vizate pe o perioadă care nu depășește perioada necesară îndeplinirii scopurilor în care sunt prelucrate datele”.

Perioade concrete din ce am verificat:
- Înregistrările KYC: **5 ani** de la încetarea relației de afaceri sau de la tranzacția ocazională — Legea 129/2019 art. 21 alin. (1), citat în `aml-kyc-mostenitori.md`.
- Restul (copii de certificate, corespondență cu notarul): **nu am găsit o perioadă legală**; durata o stabilește banca (nomenclatorul ei de arhivare) → `## Necunoscut`.
- Minimizare pentru agent (propunere proprie, nu citat): nu stocăm în conversația agentului CI/CNP în clar mai mult decât durata cazului; după predare către operatorul băncii, doar referința dosarului.

## Decizii automate (art. 22)
**GDPR art. 22 alin. (1):** „Persoana vizată are dreptul de a nu face obiectul unei decizii bazate exclusiv pe prelucrarea automată, inclusiv crearea de profiluri, care produce efecte juridice care privesc persoana vizată sau o afectează în mod similar într-o măsură semnificativă.”

Legătură cu proiectul: `docs/TASKS.md` notează că contractul DGEP interzice decizii cu efect juridic semnificativ doar pe date DGEP. Pentru agent (propunere): agentul **pregătește și verifică** dosarul; **blocarea conturilor, plata și respingerea** unei cereri a moștenitorului rămân decizii ale unui om din bancă. Art. 22 vizează persoane vii — moștenitorul — nu defunctul (considerentul 27).

## Necunoscut
- Art. 22 alin. (2)–(4) (excepții, garanții): am salvat pagina, nu am extras citatul; de completat dacă designul agentului ajunge să depindă de excepții.
- Norme românești speciale despre date ale decedaților în alte acte decât Legea 190/2018: neverificat.
- Durata de păstrare a dosarului de succesiune în afara KYC: nu e publică la Raiffeisen.
- `eurlex-gdpr-ro.html` are 0 octeți: EUR-Lex răspunde HTTP 202 fără conținut la curl (HTML și PDF, CELEX 32016R0679), probabil protecție anti-bot. Textul GDPR vine de pe gdpr-text.com; de descărcat manual din browser dacă e nevoie de sursa oficială.
