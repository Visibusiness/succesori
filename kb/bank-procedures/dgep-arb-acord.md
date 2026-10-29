Sursă: https://www.raiffeisen.ro/ro/persoane-fizice/in-sprijinul-tau/informatii-utile/colaborarea-raiffeisen-bank-cu-directia-generala-pentru-evidenta-persoanelor-dgep.html ; https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/informatii-utile/pf/nota-de-informare-privind-prelucrarea-datelor-cu-caracter-personal-in-contextul-colaborarii-dintre-raiffeisen-bank-si-dgep/nota-de-informare-privind-prelucrarea-datelor-cu-caracter-personal-in-contextul-colaborarii-dintre-raiffeisen-bank-si-dgep.pdf ; https://www.bcr.ro/content/dam/ro/bcr/www_bcr_ro/informatii-utile/Contract-DGEP-BCR-2023.pdf ; https://ing.ro/dam/ingro/doc/Contract-ING-DGEP.pdf ; https://ing.ro/ing-in-romania/informatii-utile/colaborare-evidenta-populatiei ; https://www.brd.ro/colaborare-brd-evidenta-populatiei ; https://www.brd.ro/sites/default/files/_files/pdf/Informare_prelucrare_date_DGEP.pdf ; https://www.unicredit.ro/content/dam/cee2020-pws-ro/DocumentePDF/Contract-UniCredit-DGEP-pentru-site.pdf ; https://economedia.ro/?p=345791 · Accesat: 2026-10-28 · Owner: DOMAIN

# Acordul-cadru ARB–DGEP și contractele bancă–DGEP: ce date despre deces primesc băncile

Originale descărcate (doar citite): `kb/_downloads/nicolas/dgep/`. Textul PDF-urilor l-am extras cu un script propriu. Diacriticele lipsă sau spațiile în plus vin din extragere, nu din original.

## 1. Pe scurt (explicația noastră)

| Întrebare | Răspuns | Sursa |
|---|---|---|
| Există un acord ARB–DGEP? | Da. **Acordul-cadru de colaborare nr. 3494479/07.12.2022 (DGEP), respectiv 1352/14.12.2022 (ARB)**. Textul acordului NU e public. Îl citează toate contractele bilaterale. | contractele BCR, ING, UniCredit |
| Ce fel de document semnează banca? | Un **contract bilateral** cu DGEP: „Contract privind validarea și furnizarea de date din Registrul Național de Evidență a Persoanelor”. | toate |
| Primesc băncile data decesului? | **Da**: „informații privind data decesului, după caz”. Prin serviciul web, versiunile mai noi dau și **„data și locul decesului”**. | BCR art.1(6), 2(2), 3(4), 4(1); Raiffeisen; UniCredit art.7–8 |
| Cât de des? | Actualizarea periodică e **săptămânală**, prin **SFTP**. În plus, există un **serviciu web online** (CNP + nume → true/false + date). | BCR art.3–4; UniCredit art.8 |
| Raiffeisen are contract? | **Da**. Contractul e înregistrat la bancă sub nr. **CDR73700/11.06.2025** și la DGEP pe **25.06.2025**. Raiffeisen are pagină publică și notă de informare. Pagina leagă un PDF de contract datat 20260216. Integrarea API s-a finalizat în **T1 2026**. | raiffeisen.ro; economedia |
| Din ce dată la BRD? | **Februarie 2025**: contractul nr. 3781382 a fost semnat pe 25.02.2025. | brd.ro |
| Din ce dată la ING? | Pilot din **aprilie 2023** (contract din 21.03.2023). Interogări periodice pentru tot portofoliul din **ianuarie 2025**. | ing.ro, contract ING |
| Temei legal | Art. 3 din acordul-cadru; Legea 129/2019 art. 11 alin. (1) lit. a), b) și alin. (4), art. 15 alin. (1); OUG 99/2006; Reg. BNR 2/2019; Reg. BNR 5/2013; OUG 97/2005 art. 10–11; HG 295/2021 art. 97; HG 1367/2009; OG 84/2001 (mod. OUG 148/2022); HG 387/2005 (tarife). | preambul contract BCR |
| Scop declarat | **KYC / AML**, nu succesiuni. Decesul e doar un câmp „după caz”. | toate |
| Cost | 1 leu/persoană prelucrată (validare și actualizare periodică). La actualizarea periodică se plătește doar pentru persoanele cu modificări. Actualizarea inițială costă 120 lei/oră de exploatare. | BCR, ING art.6 |

## 2. Temeiul legal și acordul-cadru (citate)

Contract DGEP–BCR (model 2023, preambul):
> „În temeiul prevederilor: -art. 3 din Acordul-cadru de colaborare nr. 3494479/07.12.2022, respectiv 1352/14.12.2022, încheiat între Direcția Generală pentru Evidența Persoanelor și Asociația Română a Băncilor;- art. 11 alin. 1) lit. a) si b) si alin. 4), art. 15 alin. 1 din Legea nr. 129/2019 pentru prevenirea și combaterea spălării banilor și finanțării terorismului;- Ordonanței de Urgență nr. 99/2006 privind instituțiile de credit şi adecvarea capitalului;- art. 11 alin 2 si art. 12 alin 2 si art. 18 din Regulamentul Băncii Naționale Române nr. 2/2019 [...]; - art.10 şi art.11 din Ordonanţa de urgenţă a Guvernului nr.97/2005 privind evidenţa, domiciliul, reşedinţa şi actele de identitate ale cetăţenilor români [...]; - Hotărârii Guvernului nr.387/2005 privind aprobarea bazei de calcul pentru stabilirea taxelor privind furnizarea datelor din Registrul naţional de evidenţă a persoanelor”

Notă BRD de informare:
> „Asociația Româna a Băncilor (in continuare „A.R.B.”), in care BRD–Groupe Societe Generale S.A. este membra, impreuna cu Directia pentru Evidenta Persoanelor si Administrarea Bazelor de Date (in continuare „D.G.E.P.”) au incheiat in decembrie 2022 un Acord cadru privind stabilirea cadrului organizatoric și procedural pentru colaborarea interinstituțională intre D.G.E.P. si Bancile membre ale A.R.B. [...]”
> „Între Băncile membre A.R.B. si D.G.E.P. se incheie contracte, în vederea îndeplinirii obiectului Acordului menționat mai sus. BRD a semnat contractul nr.3781382 în data 25.02.2025.”

Scopul (contract BCR, art. 1 alin. (3)):
> „Scopul prezentului contract îl constituie îndeplinirea obligațiilor legale ale Băncii de cunoaștere a clientelei si de actualizare a datelor acesteia, in vederea prevenirii și combaterii spălării banilor, finanțării terorismului și comportamentului fraudulos.”

Persoane vizate (BCR art. 1 alin. (4); la fel la ING, Raiffeisen, BRD): titulari, inclusiv „reprezentanții legali (ex. tutori, curatori) si cei convenționali ai acestora (împuterniciți, delegați, mandatari etc.)”, reprezentanți și beneficiari reali ai PJ, „terți garanți (semnatari ai contractelor de ipotecă mobiliară sau imobiliară)”. Raiffeisen adaugă: „În categoria Persoanelor vizate sunt incluși și minorii cu vârsta cuprinsă între 14–18 ani (neîmpliniți) care sunt clienți ai Băncii.”

**Pentru noi:** fluxul acoperă și **împuterniciții** și **garanții**. Banca poate afla deci și de decesul unui împuternicit sau al unui garant, nu doar al titularului.

## 3. Ce date primește banca: cele trei fluxuri

### 3.1 Actualizarea inițială (o dată, la pornire), art. 2 BCR
> „(1) [...] Banca formulează o solicitare de validare a datelor clienților aflați în propria evidență și pune la dispoziția D.G.E.P., pe suport optic de memorare, dispozitive portabile de memorare de tip carduri de memorie (MemoryStick/Memory USB) sau prin linie securizată, fişiere text, cu delimitatori, ce conțin datele clienților, respectiv codul numeric personal, numele și prenumele, însoțite de codul Băncii, astfel cum este stabilit prin Anexa nr.1 la Acordul-cadru.
> (2) D.G.E.P. prelucrează și validează prin proceduri automate datele prevăzute la alin.(1) și furnizează suplimentar: nume, prenume, tipul, seria și nr. actului de identitate, data de emitere a actului de identitate, data de expirare a actului de identitate, locul nașterii, emitentul actului de identitate, adresa de domiciliu, adresa de reședință și informații privind data decesului, după caz.”
> „(4) Banca transmite ulterior, după finalizarea actualizării inițiale, lista cu codurile numerice personale pentru care solicită actualizarea periodică, iar D.G.E.P. constituie datele sub formă de microregistre.”

### 3.2 Serviciul web (online, la cerere), art. 3 BCR
> „(1) La solicitarea băncii, D.G.E.P. identifică şi realizează, potrivit competenţelor, soluţia tehnică necesară pentru validarea on-line a datelor introduse de Bancă [...]. Validarea se realizează prin intermediul unui serviciu web dezvoltat în acest scop [...]”
> „(3) Datele cu caracter personal care sunt supuse validării prevăzute la alin.(1) sunt: a) codul numeric personal;b) numele și prenumele.(4) Prin intermediul serviciului web se întorc informații de răspuns,,true/false” și în cazul în care datele sunt valide, se furnizează suplimentar următoarele informații:a) adresa de domiciliu;b) adresa de reședință, după caz;c) informații privind data decesului, după caz;d) ultima fotografie a titularului actului de identitate;e) data de emitere a actului de identitate, data de expirare a actului de identitate;f) locul nașterii;g) emitentul actului de identitate;h) tipul, seria și nr. actului de identitate.i) nume şi prenume(5) Prin serviciul web pot fi introduse sau eliminate, punctual, coduri numerice personale în vederea actualizării microregistrelor [...]”

UniCredit (contract nr. 3782318/09.07.2025, art. 7 alin. (5)) și Raiffeisen dau o listă mai lungă. Raiffeisen (pagina publică, pct. c):
> „Prin intermediul serviciului web, dacă datele sunt valide, DGEP furnizează Băncii, la cerere, următoarele informații actualizate: codul numeric personal, numele de familie și prenumele, sexul, data și locul nașterii, data și locul decesului (după caz), adresa de domiciliu, adresa de reședință (după caz), tipul, seria și numărul actului de identitate, data emiterii și data expirării actului de identitate, emitentul actului de identitate, ultima fotografie a titularului actului de identitate, numele și prenumele părinților (în cazul clienților minori).”

### 3.3 Actualizarea periodică (SĂPTĂMÂNAL): aici vine „semnalul de deces”, art. 4 BCR
> „Art.4 Actualizarea periodică(1) În vederea actualizării periodice a datelor clienților aflați în evidența Băncii, D.G.E.P. comunică săptămânal, pe baza informațiilor transmise săptămânal de Bancă și informațiilor referitoare la baza de clienți existentă în microregistre, modificările intervenite în R.N.E.P. în ceea ce privește:a) numele și prenumele;b) tipul, seria și nr. actului de identitate;c) adresa de domiciliu;d) adresa de reședință, după caz;e) emitentul actului de identitate, data de emitere a actului de identitate, data de expirare a actului de identitate;f) informații privind data decesului, după caz;(2) Schimbul de informații prevăzut în prezentul articol se realizează printr-un canal de comunicații securizat, utilizând o conexiune SFTP, gestionată de Serviciul de Telecomunicații Speciale.”
> „(3) Actualizarea menționată la alin. (1) este efectuată de D.G.E.P. în baza informațiilor comunicate săptămânal de Bancă, prin canalul menționat la alin. (2), respectiv:a) cod Bancă;b) numele și prenumele clientului, cu menţiunea daca este client nou sau client închis;c) codul numeric personal.”

UniCredit (2025), art. 8 alin. (1): „D.G.E.P. comunică săptămânal, pe baza informațiilor transmise de Bancă, constituite în microregistre, modificările intervenite în R.N.E.P. [...] g) data decesului, după caz”.

Raiffeisen (pagina publică, pct. b):
> „După finalizarea actualizării inițiale, Banca poate transmite lista cu codurile numerice personale pentru care solicită actualizarea periodică. În vederea actualizării periodice a datelor persoanelor vizate aflate în evidența Băncii, DGEP comunică Băncii: numele de familie și prenumele, codul numeric personal, tipul, seria și numărul actului de identitate, data emiterii și data expirării actului de identitate, adresa de domiciliu, adresa de reședință (după caz), data decesului (după caz).”

### 3.4 Ce NU primește banca (din textele de mai sus)
- **Nu** primește numărul/seria actului (certificatului) de deces și nici primăria/SPCLEP care l-a întocmit.
- **Nu** primește cauza decesului, moștenitorii sau notarul.
- Fluxul periodic dă **data** decesului. **Locul** decesului apare doar în lista serviciului web (Raiffeisen, UniCredit).
- Fluxul periodic nu are „data comunicării” ca dată juridică. Data relevantă e momentul în care banca primește fișierul săptămânal.

## 4. Raiffeisen Bank: ce a publicat

Pagina „Colaborarea Raiffeisen Bank cu Direcția Generală pentru Evidența Persoanelor (D.G.E.P.)” (URL în linia de sursă):
> „Raiffeisen Bank și D.G.E.P. au încheiat Contractul privind validarea și furnizarea de date din Registrul Național de Evidență a Persoanelor (R.N.E.P.) in vederea asigurarii si respectarii de catre banca a prevederilor legale in materie de cunoastere a clientelei din surse credibile si independente”
> „Validarea și furnizarea datelor conform Contractului se realizează [...] prin următoarele modalități: a) actualizarea inițială, b) prin intermediul serviciului web, c) actualizarea periodică.”
> „În cadrul procesului de deschidere de relație la distanta prin aplicația Smart Mobile, este integrat serviciul web și sunt verificate, în timp real, datele furnizate pe flux cu datele din evidențele D.G.E.P. [...]”

Nota de informare Raiffeisen (PDF):
> „[...] au încheiat Contractul privind validarea și furnizarea de date din Registrul Național de Evidență a Persoanelor (R.N.E.P.), care a fost înregistrat sub nr. CDR73700/11.06.2025 la Raiffeisen Bank și, respectiv, sub nr. 3178213[?]/25.06.2025 la DGEP”

(Numărul DGEP a ieșit din extragere ca „31782130”. Prin analogie cu numerele DGEP din 2025, 3781382 la BRD și 3782318 la UniCredit, probabil e „3782130”. Trebuie verificat vizual în PDF.)

Nota Raiffeisen, decizii automate:
> „Banca nu va adopta măsuri de natură să producă efecte juridice sau care să afecteze în mod similar într-o măsură semnificativă Persoanele vizate doar pe baza prelucrării automate a datelor furnizate de DGEP, decât cu respectarea prevederilor art. 22 din GDPR”

Contractul-tip are aceeași regulă (ING/BCR art. 21 alin. (3)):
> „Banca nu poate adopta niciun fel de măsură de natură să producă efecte juridice care privesc persoana vizată sau o afectează în mod similar într-o măsură semnificativă doar pe baza prelucrării datelor furnizate de către D.G.E.P., fără respectarea prevederilor art. 22 din Regulamentul (UE) 2016/679.”

Economedia, 05.05.2026, rezultate Raiffeisen T1 2026:
> „În primul trimestru, Raiffeisen Bank a finalizat integrarea prin API cu Direcția Generală de Evidență a Persoanelor.”

CGB Raiffeisen PF menționează și ele sursa externă pentru „informatii privind data decesului”. Vezi `kb/bank-procedures/raiffeisen-cgb-pf-extras.md`, §12.

## 5. Alte bănci (cine a publicat și când)

| Bancă | Contract / dată | Ce spune public | Sursă |
|---|---|---|---|
| ING | DGEP nr. 3496706/21.03.2023; pilot aprilie 2023; interogări periodice pentru tot portofoliul din ianuarie 2025 | „informații privind data decesului și ultima fotografie a titularului actului de identitate” | ing.ro + PDF contract |
| BCR | model contract „2023”, cu număr și dată necompletate în PDF-ul publicat | text complet: art. 3 (web), art. 4 (săptămânal, SFTP) | bcr.ro PDF |
| BT | DGEP nr. 3497232/08.05.2023 (după rezultatele căutării; nota BT a dat 403) | nedescărcat | bancatransilvania.ro (403) |
| BRD | nr. 3781382 din 25.02.2025 | „informații privind data decesului, după caz”; verificare CNP „în timp real [...] împreună cu o fotografie” | brd.ro |
| UniCredit | DGEP nr. 3782318/09.07.2025 | serviciul web: „data și locul decesului, după caz”; actualizare săptămânală | unicredit.ro PDF |
| Raiffeisen | CDR73700/11.06.2025 (bancă), 25.06.2025 (DGEP); API finalizat în T1 2026 | vezi §4 | raiffeisen.ro |
| ProCredit, Libra | contracte publicate (neanalizate) | n/a | procreditbank.ro, librabank.ro |

BRD (pagina publică):
> „BRD a început să colaboreze cu Direcția Generala Pentru Evidența Persoanelor (DGEP) din februarie 2025 [...]. Relația se bazează pe un acord cadru intre DGEP și Asociația Română a Băncilor, în care BRD este membră [...]”
> „DGEP pune la dispoziția BRD cele mai recente date: nume, prenume, CNP, tipul, seria și nr. actului de identitate, adresa de domiciliu/reședință, data de emitere a actului de identitate, data de expirare a actului de identitate, locul nașterii, emitentul actului de identitate și informații privind data decesului, după caz.”
> „Totodată, BRD poate verifica un client în funcție de CNP și va primi de la DGEP în timp real datele de mai sus împreună cu o fotografie a titularului.”

ING (pagina publică):
> „Începând cu ianuarie 2025, ING va interoga periodic D.G.E.P. pentru toți clienții români rezidenți, adulți și minori care împlinesc 14 ani [...]”
> „ING va transmite periodic către D.G.E.P. o solicitare de interogare care va cuprinde CNP-ul, numele și prenumele clienților din portofoliul nostru existent.”

## 6. Alte clauze relevante (contractul-tip, aceeași numerotare la ING/BCR)
- Durata, art. 5 alin. (2)–(3): „Prezentul contract are o valabilitate de 1 an” și se prelungește automat cu câte un an.
- Publicare obligatorie, art. 12 alin. (1) și (3): contractul se publică pe site în 10 zile lucrătoare. Altfel urmează „suspendarea de drept a instrumentului juridic de colaborare şi sistarea furnizării ș i validării datelor”. (De aceea toate băncile au pagină publică.)
- Suspendare, art. 27: „D.G.E.P. îşi rezervă dreptul de a suspenda temporar furnizarea datelor, strict pe perioada desfășurării activităților circumscrise proiectelor de modernizare, cu notificarea expresă a A.R.B. în timp util.”
- Neplată, art. 7 alin. (3): „Neplata contravalorii prestaţiei [...] duce la întreruperea transmisiilor de date către Bancă, cu notificarea prealabilă a Băncii cu 15 zile înainte”.
- Neconcordanțe, art. 20 alin. (1): „În cazul în care Banca sesizează neconcordanţe între datele furnizate potrivit art.2 şi cele înscrise în actele de identitate ale cetăţenilor, acestea vor fi aduse la cunoștința D.G.E.P.”
- Structura datelor e în „Anexa 2, document nedestinat publicității” (art. 13 alin. (2)).

## Necunoscut
- **Textul acordului-cadru ARB–DGEP** (nr. 3494479/07.12.2022 / 1352/14.12.2022) și **Anexa 1** (formatul fișierului). Nu sunt publice. Am căutat pe arb.ro și depabd.mai.gov.ro (prin WebSearch) și n-am găsit nimic.
- **Anexa 2** (structura datelor transmise) e declarată „nedestinată publicității”. Nu cunoaștem câmpurile exacte, formatul datei sau codurile de stare.
- **Contractul Raiffeisen**: PDF-ul (20260216, 5,4 MB) e scanat, iar fără OCR nu l-am putut citi. Nu știm dacă Raiffeisen a activat efectiv actualizarea periodică săptămânală. Pagina spune „Banca poate transmite lista [...]”. Nu știm nici dacă decesul se folosește intern pentru blocare.
- **Contractul BRD** (7 MB) e scanat și necitit. Pagina 4 din contractul ING (art. 3 alin. (2) – art. 5 alin. (1)) e imagine, deci n-am văzut art. 4 la ING. L-am luat din BCR și UniCredit, care au aceeași structură.
- **Întârzierea** dintre deces și apariția lui în fluxul săptămânal nu e publică. Declararea decesului la starea civilă se face, după paginile primăriilor, în 3 zile (Legea 119/1996). Nu am verificat textul legii și nici cât durează propagarea în RNEP.
- Nu am găsit dacă DGEP semnalează și **anularea sau rectificarea** unui act de deces (de ex. deces înregistrat greșit).
- Legea 129/2019 nu obligă banca să folosească data decesului pentru blocare. Utilizarea în scop de succesiune ține de interpretarea băncii (KYC = date „actualizate”).

## Ce înseamnă pentru agent
1. **Semnalul DGEP e real și săptămânal.** În demo, decesul e pe 3 sept. și semnalul DGEP vine pe 20 sept. (17 zile), ceea ce e plauzibil: declarare în ≤3 zile, propagare în RNEP, apoi lotul săptămânal (estimare proprie). Adaptorul de intake tratează un **lot săptămânal** (fișier SFTP) cu modificări pe CNP. Un câmp `data_decesului` nenul = eveniment `DEATH_SIGNAL`.
2. **Semnalul conține DOAR CNP, nume și data decesului** (plus date de act de identitate și adresă). Agentul **nu** așteaptă un număr de act de deces de la DGEP. Numărul vine din certificatul de deces adus de familie sau de la notar.
3. **Data decesului din DGEP = `date_of_death` provizoriu** pentru `balance_at_death` și `fees_to_reverse`. Dacă certificatul de deces sau adresa notarului dau altă dată, agentul escaladează (conflict de date) și nu alege singur.
4. **Art. 22 GDPR / art. 21(3) din contract:** banca nu poate lua decizii cu efect juridic semnificativ „doar pe baza” datelor DGEP. Deci la semnalul DGEP agentul face doar **măsuri conservatorii reversibile**: blochează debitul, suspendă împuterniciții și cardurile suplimentare, pune flag pe comisioane. Cere **confirmare umană** (sau certificatul de deces) înainte de pași ireversibili: stornări definitive, închideri, răspunsuri către terți.
5. **Verificare la cerere:** când vine întâi un alt document (adresa notarului, polița), agentul poate chema **serviciul web** (CNP + nume → true/false + data și locul decesului) ca să confirme decesul înainte de a deschide dosarul.
6. **Și împuterniciții, și garanții sunt în flux.** Un semnal de deces pentru un CNP care e împuternicit sau garant (nu titular) produce alt tip de acțiune: revocarea mandatului, respectiv notificarea creditului. Nu se deschide dosar de succesiune pe contul titularului.
7. **Fluxul poate tăcea:** DGEP poate suspenda temporar livrarea (art. 27), iar neplata întrerupe fluxul (art. 7). Agentul nu presupune „niciun deces” pentru că lipsește semnalul. Intrările din alte canale (familie, notar) deschid dosarul la fel.
