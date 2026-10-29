Sursă: https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/conditii-general-bancare-pf/2026026-Conditii-general-bancare-Persoane-Fizice.pdf.coredownload.inline.pdf (ediția 26.02.2026, versiunea folosită) ; https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/conditii-general-bancare-pf/20240220-Conditii-generale-de-derulare-a-operatiunilor-bancare-pentru-persoane-fizice.pdf.coredownload.inline.pdf (ediția 20.02.2024, din BRIEF §8, pentru comparație) ; https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/pf/tarife-comisioane-standard-pf.sv.pdf (Tarife standard PF, 1 septembrie 2026, pentru definiția contului „dormant”) · Accesat: 2026-10-28 · Owner: DOMAIN

# CGB Raiffeisen PF: extrase despre deces, împuterniciți, moștenitori, inactivitate, comisioane, compensare

## Versiunea folosită
- **Am folosit ediția 26.02.2026.** Pe raiffeisen.ro există o versiune mai nouă decât cea din brief (20.02.2024). Mai există și edițiile 01.08.2024 și 08.04.2025.
- Originalele sunt în `kb/_downloads/nicolas/`: `cgb-pf-20260226.pdf` (68 de pagini) și `cgb-pf-20240220.pdf` (60 de pagini).
- Cum am extras textul: `pdftotext` nu e instalat și Read nu poate randa PDF-ul. Nicio bibliotecă PDF nu era disponibilă pentru python3. Am scris un extractor minimal care decomprimă fluxurile cu zlib, fără să instalez nimic, și l-am rulat izolat (`python3 -I`).
- Despre diacritice: PDF-ul din 2026 e scris de bancă **fără diacritice**, așa că citatele de mai jos le reproduc exact așa.
- Numerotarea clauzelor relevante (3.2.x, 3.5, 3.7, 3.8, 5.10.4, 7.7.1) e **identică** în 2024 și în 2026. Textul clauzelor citate e la fel, cu excepția diacriticelor.
- Notă pentru master: brieful citează „CGB 3.2 b/d”. Clauza exactă e **3.2.5 lit. b) și d)**.

## 1. Definiții (cap. 1, „Definitii”)
> Imputernicit - persoana cu capacitate deplina de exercitiu, autorizata de Client, prin intermediul formularelor speciale furnizate de Banca sau prin procura notariala, sa aiba acces in numele si pe seama Clientului la un Cont deschis pe numele acestuia, actionand in limitele prevazute in Contractele specifice;

> Mandatar - persoana autorizata de Client prin procura sa il reprezinte in relatia cu Banca pentru incheierea si/sau executarea unui contract. Procura de reprezentare trebuie autentificata de un notar public din Romania sau la un consulat romanesc; in cazul procurilor emise la un notariat din strainatate, procura va fi apostilata sau supralegalizata, dupa caz, si se va prezenta si traducerea legalizata a acesteia, daca este redactata intr-o limba straina;

## 2. Clauza 3.2: cine poate opera în conturi
**3.2.1.**
> Indiferent de numarul si tipurile Conturilor, Clientul care are capacitate deplina de exercitiu, in calitate de titular al acestora, poate numi in relatia cu Banca un numar maxim de doi Imputerniciti pentru fiecare Cont, care au dreptul sa dispuna de fondurile din Conturile indicate expres de Client (efectuand in cazul Conturilor de plati si operatiuni de plata), neavand dreptul sa solicite inchiderea acestor Conturi. Prin exceptie, in cazul Conturilor de depozit la termen si a Conturilor de economii, Imputernicitul poate solicita lichidarea depozitului la termen, respectiv inchiderea Contului de economii. Prin exceptie, pe conturile de card de credit nu se pot numi Imputerniciti.

**3.2.2. (2)**
> Imputernicirea de reprezentare data de Client va fi considerata valabila pana la revocarea acesteia efectuata de catre Client, prin una din urmatoarele modalitati: completarea unei noi liste a Imputernicitilor pe Contul curent pentru care va opera modificarea in unitatile Bancii; completarea unei solicitari exprese de revocare in cuprinsul formularelor standard ale Bancii, pentru alte tipuri de Cont.

**3.2.2. (4)**
> Numirea, respectiv, revocarea Imputernicitilor de catre Client devin opozabile Bancii incepand cu ziua lucratoare imediat urmatoare datei depunerii listei de Imputerniciti/cererii de revocare a Imputernicitilor.

**3.2.5.** Aceasta e clauza-cheie.
> Asupra sumelor aflate in Conturile curente, de economii sau de depozit deschise in evidenta Bancii pentru acesti Clienti, pot dispune liber, cu respectarea normelor in vigoare, urmatoarele persoane:
> a) titularul Contului;
> b) Imputernicitii pe cont, numai pe timpul vietii titularului;
> c) mostenitorii titularului, care dovedesc cu certificat de mostenitor sau cu hotarare judecatoreasca aceasta calitate.
> d) Utilizatorii Cardurilor suplimentare atasate Contului (numai prin intermediul acestor Carduri), pe timpul vietii titularului Contului;
> e) Reprezentantul legal al Clientului, in cazul in care Clientul este minor sau major fara capacitate de exercitiu; [...]

**4.8.12.**
> Imputernicitul pe cont nu are dreptul sa solicite extras de cont, ci doar informatii exclusiv cu privire la soldul contului si la operatiunile efectuate de el pe Contul titularului.

## 3. Utilizatori de card suplimentar (5.2.2)
> Utilizatorul suplimentar de card are dreptul sa dispuna de sumele din contul titularului de Cont in aceleasi conditii ca acesta, si, daca este cazul, cu respectarea limitelor de utilizare sume impuse de Utilizatorul principal, fara a avea insa dreptul sa primeasca extrase de cont/Rapoarte de activitate [...], sa initieze transferuri din cont fara utilizarea Cardului, sa inchida/modifice contul curent/de card [...].

## 4. Încetarea cardului: 5.10.4 c) și clauzele legate
**5.10.4**
> Contractul pentru emiterea si utilizarea Cardului inceteaza in una din urmatoarele situatii:
> a) prin acordul partilor, exprimat in scris;
> b) prin denuntarea unilaterala, oricand pe durata contractului, de catre Utilizatorul de card sau de catre Banca;
> c) in cazul decesului sau incapacitatii Utilizatorului principal de card;
> d) prin rezilierea Contractului aferent Cardului de debit in conditiile pct. 5.10.7 din de mai jos;
> e) in caz de forta majora sau caz fortuit;
> f) prin retragerea produsului de catre Banca;
> g) in cazul inchiderii Contului curent la care este atasat Cardul de debit;
> h) in orice alte cazuri prevazute de lege;

**5.10.7 (3)**
> In cazul in care exista tranzactii efectuate cu Cardul aflate in decontare, Banca poate bloca la tranzactionare instrumentul de plata, pana la decontarea tuturor tranzactiilor si rezilierea Cardului.

**5.10.9**
> Utilizatorul principal de card sau mandatarul/succesorii legali ai acestuia au obligatia ca la incetarea contractului sa acopere integral eventualele sume datorate. Orice debit neacoperit de Utilizatorul principal de card generat de utilizarea Cardului trebuie restituit de acesta Bancii. In cazul incetarii acestora, Clientul este obligat la plata taxelor si comisioanelor aferente Operatiunilor efectuate pana la data incetarii.

**5.3.6** (debitare automată pentru card), extras:
> Banca este autorizata de catre Utilizatorul principal de card sa debiteze automat contul curent/de card cu urmatoarele sume: a) tranzactiile/operatiunile efectuate prin Card in tara si in strainatate, de catre Utilizatorul pricipal si Utilizatorii suplimentari; [...] c) comisioane, taxe si dobanzi datorate Bancii pentru operatiuni curente, emiterea /inlocuirea Cardurilor si/sau pentru servicii speciale, in baza Contractului specific; [...]

## 5. Debitarea directă încetează la deces: 7.7.1 c)
> Mandatul de debit direct se incheie pe perioada nedeterminata sau determinata. Mandatul inceteaza in una din urmatoarele situatii, Platitorul fiind obligat la plata comisionanelor aferente operatiunilor efectuate pana la data incetarii:
> [...] c) in cazul decesului Platitorului;
> [...] k) in situatia in care Platitorul solicita inchiderea Contului aferent Mandatului sau daca acesta este inchis sau blocat din alte motive, fara ca Platitorul sa indice Bancii un alt cont din care se vor face plati catre Beneficiar.

## 6. Comisioane, dobânzi, debitare automată
**2.3.1.**
> Pentru produsele si serviciile oferite, Banca percepe Clientilor sai taxe, comisioane, speze si dupa caz, percepe sau acorda dobanzi la valorile standard cuprinse in listele specifice, cu exceptia situatiilor in care in Contractele specifice se prevad alte niveluri ale acestora. [...]

**2.3.3.** Formula dobânzii, care se folosește la `balance_at_death`:
> Orice dobanda este calculata zilnic la sumele inregistrate in soldul debitor, dupa caz, sold creditor al Contului (curent/de depozit/de economii/de credit), pe baza formulei: D - C*Rd*n/N, unde: D - dobanda calculata; C - capitalul asupra caruia se calculeaza dobanda [...]; Rd - Rata dobanzii; n - numarul de zile din luna (care poate fi determinat conventional [...] ca fiind numarul efectiv de zile ale lunii pentru care se calculeaza dobanda sau 30); N - Numarul de zile din an (care poate fi determinat conventional [...] ca fiind numarul efectiv de zile ale anului, 360 sau 365).

(Notă: în PDF scrie „D - C*Rd*n/N”. Sensul e evident D = C×Rd×n/N.)

**2.3.4.** (extras)
> In cazul conturilor de economii si de depozit la termen Rata dobanzii si modalitatea de calcul a dobanzii aplicabile sunt precizate in Contractul specific.

**3.1.7.** (extras)
> [...] Toate costurile aferente consultarii acestor baze de date, precum si orice speze, comisioane si taxe aferente, inclusiv postale, sunt si raman in sarcina Clientului, Banca avand mandat de debitare automata a oricarui cont al Clientului pentru recuperarea acestora.

**3.9.1.** Dobânda pe contul curent:
> Dobanda creditoare se calculeaza conform sectiunii 2.3.3., cu precizarea ca ”n” este numarul efectiv de zile pentru care se calculeaza dobanda si ”N” este 365/366. Dobanda creditoare se calculeaza zilnic pentru soldul existent la sfarsitul zilei bancare. Dobanda se calculeaza pentru luna si anul calendaristic si se va credita lunar, capitalizandu-se in cont. Creditarea dobanzii se efectueaza numai dupa retinerea impozitului pe venit din dobanzi conform prevederilor legale in vigoare

**3.9.2.** Taxa de administrare:
> Taxa de administrare a Contului curent se datoreaza lunar in ultima zi lucratoare a lunii, pentru luna in cursul careia este scadenta plata acesteia, in lipsa unei dispozitii contrare in cererea de deschidere de cont. Taxa de admininistrare Cont curent se percepe pro-rata atat in luna deschiderii, cat si in luna inchiderii Contului curent, proportional cu perioada in care Contul a fost deschis.

**3.9.3.**
> Banca este autorizata de Client sa debiteze Contul curent, la scadenta oricarei taxe/comision aferent acestuia, cu suma necesara achitarii. Sunt acceptate si plati partiale. Daca nu exista in Contul curent disponibil suficient pentru stingerea in totalitate a obligatiei de plata se vor aplica prevederile art. 3.4 privind descoperitul de cont neautorizat acordat de Banca si art. 3.5 privind dreptul de compensare din prezentele CGB.

**3.4.1.** (extras) Descoperitul de cont neautorizat:
> Banca va putea decide efectuarea unei plati cerute de catre Client sau recuperarea de taxe, comisioane, speze, dobanzi, orice alte sume datorate Bancii in baza Contractelor specifice etc., care depasesc limita soldului creditor al Contului curent, chiar daca nu exista un Contract specific pentru o facilitate de descoperit de cont deja incheiat cu Clientul. [...]

**4.8.13.**
> Banca pune la dispozitia Clientului, o data pe an, in mod gratuit, o situatie a tuturor comisioanelor aferente Contului, suportate pe pacursul unei perioade anterioare de 12 luni implinite. [...]

## 7. Dreptul de compensare: 3.5
**3.5.1.**
> Clientul autorizeaza Banca, prin prezenta, sa compenseze in orice moment orice suma datorata Bancii cu fondurile disponibile in orice Cont curent, de economii si/sau de depozit la termen, indiferent de valuta in care sunt disponibile si/sau indiferent de scadenta depozitului, fara a fi necesar in acest sens un alt acord prealabil al Clientului.

**3.5.3.**
> In situatia in care in Conturile Clientului nu exista disponibil suficient pentru acoperirea oricaror sume datorate Bancii, Banca este autorizata sa debiteze oricare dintre Conturile Clientului, chiar daca prin aceasta s-ar genera descoperit de cont neautorizat in conditiile sectiunii 3.4. [...]

**3.5.4.**
> Clientul va fi instiintat de catre Banca dupa efectuarea compensarii prin extrasul de cont.

## 8. Încetarea contului și a depozitului: 3.6
**3.6.1.** (extras)
> [...] Inchiderea Contului se va efectua la data solicitarii; prin exceptie, inchiderea Contului curent cu card de debit atasat (Card principal si/sau suplimentare) se va efectua dupa 30 de zile calendaristice de la data la care titularul a solicitat Bancii in scris incetarea contractului de Cont curent , daca exista inregistrate tranzactii in decontare [...]

**3.6.3.** (extras) Banca poate rezilia contul curent de plin drept, printre altele dacă:
> e) Soldul Contului nu mai acopera costurile aferente executarii Contractului specific de Cont Curent;
> f) in cazul Conturilor ”dormant” reglementate la sectiunea 3.7;

**3.6.4.** (extras)
> [...] In cazul prevazut la art. 3.6.3 lit e) inchiderea Contului se face fara notificare.

**3.6.5.**
> In toate cazurile in care initiativa inchiderii contului apartine Bancii, de la data inchiderii contului, Banca va inceta creditarea cu dobanda a Contului, urmand ca suma care constituie la acea data soldul creditor al Contului sa fie pastrata la dispozitia Clientului in conturi nepurtatoare de dobanda. [...]

**3.6.6.**
> Contractul de depozit la termen/contul de economii inceteaza de drept in cazul in care inceteaza din orice motiv contractul de Cont curent deschis in valuta produsului de economisire incheiat cu Banca. In acest caz, incetarea de depozit la termen/contul de economii va avea loc la aceeasi data cu data incetarii contractului de Cont curent si Clientul accepta ca Banca va proceda la virarea sumei depozitului/contului de economii in respectivul Cont curent dupa lichidarea depozitului/contului de economii cu aceasta data, chiar in situatia in care nu a ajuns la scadenta si cu bonificarea dobanzii pana la data incetarii contractului de depozit/contului de economii.

## 9. Conturi „dormant” (inactive): 3.7
Notă: CGB nu folosește termenul „inactiv”, ci „dormant”.

**3.7.1.**
> Daca pe parcursul unei perioade de timp, stabilita de Banca si adusa la cunostinta Clientului prin afisare la unitatile si pe site-ul Bancii, pentru Contul curent sau Contul de economii nu s-a inregistrat si aprobat nicio cerere a Clientului de modificare cont sau daca in Contul curent sau Contul de economii activ, Clientul, tertii sau Banca nu a/au efectuat nicio miscare de debitare sau creditare a Contului, Contul va deveni “dormant”.
> Perioada de timp stabilita de Banca pentru ca un Cont curent sa devina „dormant” este generala si se aplica tuturor Conturilor Curente.
> In aceast caz, Banca va continua sa perceapa taxe si comisoane conturilor respective, atata timp cat exista sold creditor. De asemenea, Banca va continua sa calculeze dobanda creditoare/debitoare in functie de caracteristicile fiecarui Cont, atata timp cat exista sold creditor/debitor.

**3.7.2.**
> Prin exceptie de la prevederile art. 3.6.4 de mai sus, Banca va putea decide oricand inchiderea Contului declarat “dormant” cu sold zero sau debitor, fara notificarea prealabila sau ulterioara a Clientului.

**3.7.3.** (extras)
> In urma aprobarii unei cereri de modificare a Contului sau in urma procesarii unei tranzactii de debitare sau creditare pe Contul ”dormant”, acesta va fi reactivat automat de catre Banca; [...]

**3.7.4.**
> Banca nu va anunta clientul cu privire la trecerea Contului in stare ”dormant”.
> Nu sunt considerate miscari in Cont, operatiunile de debitare sau creditare efectuate de catre Banca, reprezentand exclusiv plata dobanzilor de catre Banca si plata comisioanelor/taxelor aferente Contului.

Perioada vine din **Tarife și comisioane standard PF, 1 septembrie 2026**, nota *** de la „Administrarea contului curent”:
> *** Cont dormant: cont fără activitate în ultimele 6 luni.

## 10. Blocarea conturilor: 3.8
**3.8.1.**
> Conturile Curente ale Clientului pot fi blocate (i) total, caz in care nu se vor executa niciun fel de Operatiuni de plata (depunere/retragere de fonduri, transfer fonduri, incasare) sau (ii) partial, caz in care se vor executa doar Operatiunile de plata de creditare a Contului Curent (incasari).

**3.8.2. (1)** (extras) Banca poate bloca, printre altele:
> d) in orice alte cazuri prevazute de prezentele CGB si a prevederilor legale in vigoare;

**3.8.3.**
> (1) Pe durata blocarii partiale a Contului Curent: (i) se va calcula si va inregistra dobanda creditoare sau, dupa caz debitoare; (ii) se va percepe comisionul de administrare a Contului prevazut in Contractul specific; (iii) se vor inregistra orice Operatiuni de plata finalizate prin creditarea Contului curent; (iv) Banca nu va executa ordinele de plata ce au ca efect debitarea Contului curent.
> (2) Pe durata blocarii totale a Contului Curent: (i) nu se vor executa niciun fel de Operatiuni de plata (depunere/retragere de fonduri, transfer fonduri, incasare); (ii) nu se va percepe comisionul de administrare a Contului prevazut in Contractul specific si (iii) nu se va calcula si inregistra dobanda creditoare sau, dupa caz, debitoare.

**3.8.4.**
> In cazul in care Contul Curent este blocat conform prevederilor de mai sus, Banca poate bloca si orice instrument/ serviciu de plata care da acces la respectivul Cont.

**3.8.5.**
> (1) In situatiile prevazute la pct. 3.8.2 alin. (1) de mai sus, Banca este indreptatita sa blocheze Conturile de depozit si Conturile de economii ale Clientului.
> (2) Pe durata blocarii Conturilor de depozit si Conturilor de economii: (i) Clientul nu va putea efectua operatiuni de retragere partiala sau totala a fondurilor; (ii) celelalte prevederi contractuale se vor aplica in conditiile prevazute in Contractele specifice.

## 11. Prescripție: 3.10
> In toate cazurile de inchidere a unui Cont, termenul in care Clientul va putea solicita restituirea sumelor care au reprezentat soldul creditor al respectivului Cont la data inchiderii acestuia, este termenul legal de prescriptie care incepe sa curga de la data la care notificarea de inchidere a Contului se considera primita de catre Client conform sectiunii 8.2. ”Notificari”. [...] In aceasta perioada, sumele inregistrate in soldurile conturilor inchise se vor pastra de catre Banca la dispozitia Clientului, in conturi nepurtatoare de dobanda.

## 12. Data decesului din surse externe (DGEP): secțiunea 2.1.5 (date personale)
Printre sursele externe sunt enumerate:
> [...] Transfond, Directia Generala de Evidenta a Persoanelor (DGEP).

> In vederea: (i) respectarii obligatiilor legale ce revin Bancii privind aplicarea de masuri standard de cunoastere a clientelei [...] Banca va putea obtine din surse sigure, credibile, independente , permise de lege, date cu caracter personal cum ar fi: nume, prenume, CNP, tipul, seria si nr. actului de identitate, [...] adresa de domiciliu, adresa de resedinta, informatii privind data decesului si ultima fotografie a titularului actului de identitate etc.

## 13. Căutări fără rezultat
Am căutat (grep) în textul CGB 2026: „decedat”, „succesiune”, „certificat de moștenitor”, „notar”.
- **„decedat” și „succesiune”: 0 apariții.**
- „mostenitor”: apare numai la 3.2.5 c).
- „succesorii legali”: apare numai la 5.10.9.
- „notar”: apare numai în definiția Mandatarului/Împuternicitului și în lista de destinatari ai datelor personale.

## Ce lipsește din CGB
(Concluziile mele, din lectura integrală a cuvintelor-cheie de mai sus.)
1. **Nu există o procedură de deces.** CGB nu spune cum se notifică banca, ce documente cere (certificat de deces etc.), cine blochează contul și când. Nu spune nici că decesul e motiv de blocare. 3.8.2 enumeră AML, fraudă, securitate și „orice alte cazuri prevazute de [...] CGB si a prevederilor legale”. Decesul intră doar indirect.
2. **Comisioanele după deces nu sunt reglementate.** Nicio clauză nu oprește comisioanele de la data decesului. Din contră:
   - la cont „dormant”, banca „va continua sa perceapa taxe si comisoane” (3.7.1);
   - la blocare **parțială** se percepe în continuare comisionul de administrare (3.8.3(1)(ii)).
   Numai blocarea **totală** oprește comisionul și dobânda (3.8.3(2)). Asta explică mecanic cazul Bragadiru (comisioane încasate 2 ani după deces).
3. **Nu există un termen de răspuns către notar** și nicio clauză despre relația cu notarul public sau despre conținutul răspunsului (sold la data decesului etc.).
4. **Nu se spune cum plătesc moștenitorii.** 3.2.5 c) spune doar că moștenitorii „pot dispune liber” cu certificat de moștenitor sau cu hotărâre. Nu spune nimic despre:
   - cote;
   - prezența tuturor moștenitorilor sau plata separată pe cote;
   - moștenitorul minor;
   - certificatul suplimentar;
   - depozitul nescadent.
5. **Nu e definit momentul încetării împuternicirii.** „numai pe timpul vietii titularului” (3.2.5 b) înseamnă de drept de la data decesului. Totuși, CGB nu spune ce se întâmplă cu operațiunile făcute de împuternicit între deces și momentul în care banca află. Regula de opozabilitate de la 3.2.2(4) privește doar revocarea de către client. (Corelare cu C. civ. art. 2030: vezi `kb/legal/cod-civil-succesiuni.md`.)
6. **Încasările după deces (pensie) nu sunt tratate.** CGB nu spune nimic despre returnarea sumelor virate după deces.
7. **Compensarea (3.5.1) nu are limită la deces.** Clauza permite compensarea „in orice moment”, „indiferent de scadenta depozitului”. CGB nu spune dacă banca o aplică după deces pe masa succesorală (de ex. credit contra depozit). Asta e o întrebare juridică pentru `kb/legal/`.
8. **Perioada „dormant”** nu e în CGB. E doar în Tarife: „6 luni”.

## Necunoscut
- Contractele specifice: contul curent, contractul de depozit la termen și contractul de credit. Ele pot avea clauze proprii despre deces, dar nu sunt publice. Am căutat pe raiffeisen.ro și cu WebSearch. Am găsit doar pagini de produs (vezi `raiffeisen-tarife-produse.md`).
- Procedura internă a băncii la deces (norme interne). Nu e publică.

## Ce înseamnă pentru agent
1. **La semnalul de deces (`date_of_death` = D):**
   - marchează toți împuterniciții pe toate conturile ca *inactivi retroactiv de la D* (3.2.5 b);
   - încetează cardurile principale (5.10.4 c) și pe cele suplimentare (3.2.5 d, „pe timpul vietii titularului”);
   - încetează mandatele de debit direct (7.7.1 c).
   Orice operațiune de debit inițiată de împuternicit sau prin card suplimentar cu data > D intră în lista `post_death_debits_for_review`. Agentul nu o anulează automat; decizia e umană.
2. **Modul de blocare:** folosește **blocare parțială** (3.8.1 ii) ca să intre în continuare încasările (pensia, apoi returnată la CNPP). Atenție: la blocare parțială CGB 3.8.3(1)(ii) **lasă comisionul de administrare activ**, deci agentul trebuie să **suprime explicit** comisionul de pachet de la D și să stornoze ce s-a încasat după D (`fees_to_reverse(D)`). Blocarea totală oprește comisionul, dar respinge și încasările.
3. **Dormant:** dacă un cont al unui client decedat trece „dormant” (6 luni fără activitate), comisioanele continuă (3.7.1). Agentul ridică alertă dacă există un dosar de deces deschis și contul încasează comisioane.
4. **Cine poate primi bani:** doar moștenitorii cu certificat de moștenitor sau cu hotărâre judecătorească (3.2.5 c). Fără unul dintre ele, nicio plată. Împuternicitul nu mai e persoană îndreptățită după D, chiar dacă vine cu procura băncii.
5. **Dobânda:** `balance_at_death` folosește formula 2.3.3 D = C×Rd×n/N. Pentru contul curent n = zile efective și N = 365/366 (3.9.1). Taxa de administrare e pro-rata în luna închiderii (3.9.2). Pentru depozit, Rd și convenția n/N vin din contractul specific (2.3.4); în demo sunt parametri.
6. **Compensare (3.5.1):** agentul **nu aplică automat** compensarea credit contra depozit sau cont după D. Marchează `setoff_requires_legal_review`, pentru că CGB permite compensarea, dar nu tratează situația succesorală.
7. **Notarul:** nu există un termen contractual. Termenul îl setează regula din `kb/legal/` (Legea 36/1995), nu CGB.
