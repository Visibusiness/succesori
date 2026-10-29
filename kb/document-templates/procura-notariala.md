Sursă: Cod civil (Legea 287/2009) art. 2.009–2.036, text din `kb/_downloads/nicolas/codcivil-175630.html` (legislatie.just.ro) ; https://notari.pro/dictionar-juridic-dex/rnnepr (RNNEPR) ; https://tallinn.mae.ro/node/263 (procuri la consulat, nota despre RNNEPR) ; https://notari.pro/legalizari/supralegalizare-acte-la-notariat (apostilă/supralegalizare); CGB Raiffeisen PF 2026 (definiția Mandatarului, vezi `kb/bank-procedures/raiffeisen-cgb-pf-extras.md`) · Accesat: 2026-10-28 · Owner: DOMAIN

Copii locale: `kb/_downloads/visi/notaripro-rnnepr.html`, `legalbadger-rnnepr.html`, `mae-tallinn-procuri.html`, `notaripro-supralegalizare.html`, `legalex-procuri.html`.

# Procura notarială (la bancă, în succesiune)

Prioritate P1. Apare în două roluri: (A) procura **dată de defunct** unui împuternicit (încetează la deces) și (B) procura **dată de un moștenitor** (de ex. din străinătate) unei persoane care încasează sau semnează pentru el.

## Texte legale (Cod civil)
**Art. 2.009 – Noțiune:** „Mandatul este contractul prin care o parte, numită mandatar, se obligă să încheie unul sau mai multe acte juridice pe seama celeilalte părți, numită mandant.”

**Art. 2.012 alin. (2):** „Împuternicirea pentru reprezentare sau, dacă este cazul, înscrisul care o constată se numește procură.”

**Art. 2.013 alin. (1)–(2) – Forma:** „Contractul de mandat poate fi încheiat în formă scrisă, autentică ori sub semnătură privată, sau verbală. […] (2) Mandatul dat pentru încheierea unui act juridic supus, potrivit legii, unei anumite forme trebuie să respecte acea formă, sub sancțiunea aplicabilă actului însuși.”

**Art. 2.015 – Durata:** „Dacă părțile nu au prevăzut un termen, contractul de mandat încetează în 3 ani de la încheierea lui.”

**Art. 2.016 – Întinderea:** „(1) Mandatul general îl autorizează pe mandatar să efectueze numai acte de conservare și de administrare. […] (2) Pentru a încheia acte de înstrăinare sau grevare, tranzacții ori compromisuri […] precum și pentru a încheia orice alte acte de dispoziție, mandatarul trebuie să fie împuternicit în mod expres.”

**Art. 2.030 alin. (1) lit. c) – Încetarea:** mandatul încetează prin „moartea, incapacitatea sau falimentul mandantului ori a mandatarului” (excepția pentru acte succesive într-o activitate cu caracter de continuitate, aflată în curs). Textul complet și art. 2.031–2.037 sunt în `kb/legal/cod-civil-succesiuni.md` §6; aici doar cele necesare:
- **Art. 2.033 alin. (2):** „Notarul public care autentifică actul pentru încheierea căruia a fost dată procura are obligația să verifice la Registrul național notarial dacă acea procură a fost revocată.”
- **Art. 2.035 alin. (1):** moștenitorii mandantului „au obligația de a informa de îndată cealaltă parte”.
- **Art. 2.036:** „Tot ceea ce mandatarul a făcut, în numele mandantului, înainte de a cunoaște sau de a fi putut cunoaște cauza de încetare a mandatului este socotit ca valabil făcut în executarea acestuia.”

**Cum se verifică (RNNEPR).** Registrul național notarial de evidență a procurilor și a revocărilor acestora este, potrivit notari.pro, „un registru electronic ținut la nivel național de către UNNPR în care se înregistrează toate procurile şi revocările acestora”, precum și „alte cauze de încetare a mandatului (punere sub interdicție, moarte, incapacitate, faliment, hotărâre judecătorească, renunţare a mandatarului)”. Una dintre rubrici este „numărul şi seria actului de deces”. Ambasada României în Estonia notează că RNNEPR a fost înființat de la 01.01.2013 prin Legea 77/2012 (modificare a Legii 36/1995).

**Procură pentru bancă din străinătate.** CGB Raiffeisen PF 2026, definiția Mandatarului: „Procura de reprezentare trebuie autentificata de un notar public din Romania sau la un consulat romanesc; in cazul procurilor emise la un notariat din strainatate, procura va fi apostilata sau supralegalizata, dupa caz, si se va prezenta si traducerea legalizata a acesteia, daca este redactata intr-o limba straina”. Apostila (Convenția de la Haga, 1961) se aplică în statele participante; altfel supralegalizare (notari.pro: Camera Notarilor Publici apostilează/supralegalizează actele notariale românești).

## Schema de extracție

| Câmp | Tip | Obligatoriu | Note |
|---|---|---|---|
| `doc_type` | `procura_notariala` | da | |
| `mandant` {nume, prenume, cnp, domiciliu} | obiect | da | defunctul (rol A) sau moștenitorul (rol B) |
| `mandatar` {nume, prenume, cnp, domiciliu, act_identitate} | obiect | da | |
| `autentificare` {nr, data, birou_sau_consulat, tara, localitate} | obiect | da | formă autentică (notar RO / consulat / notar străin) |
| `forma` | enum `autentica_ro` \| `consulat_ro` \| `strain_apostilata` \| `strain_supralegalizata` \| `sub_semnatura_privata` | da | privata = nu o acceptăm fără om |
| `apostila` {nr, data, autoritate} | obiect | da pt. străin | |
| `traducere_legalizata` | bool | da pt. limbă străină | |
| `obiect` | text | da | ce actele i se permit |
| `acte_dispozitie_expres` | bool | da | ex. „să încaseze sume”, „să dispună de conturi”, „să semneze cererea de eliberare” |
| `institutie_vizata` | string | nu | ex. „Raiffeisen Bank” sau „orice instituție” |
| `valabilitate` {data_inceput, data_sfarsit \| fara_termen} | obiect | da | |
| `inregistrat_rnnepr` {verificat, data_verificarii, revocata} | obiect | da | rezultatul interogării, dacă e disponibil |
| `data_deces_mandant` | date | da pt. rol A | din certificatul de deces |
| `confidence` | float per câmp | da | |

## Exemplu fictiv (rol B: moștenitor în străinătate)
```
doc_type: procura_notariala
mandant: Ionescu Andrei, CNP 1900101000000 (fictiv), dom. Torino, Italia
mandatar: Ionescu Paula (soră), CNP 2920202000000 (fictiv), București
autentificare: nr. 1234 / 03.09.2026, notar public din Torino (fictiv)
forma: strain_apostilata ; apostila nr. IT-0000 / 05.09.2026 (fictiv) ; traducere_legalizata: true
obiect: „să mă reprezinte în fața Raiffeisen Bank pentru încasarea sumelor cuvenite din moștenirea defunctei Ionescu Maria, să semneze cererea de eliberare a sumelor și să indice contul de destinație”
acte_dispozitie_expres: true ; valabilitate: 12 luni de la autentificare
```

## Necunoscut
- **Cine poate interoga RNNEPR.** O căutare web (neverificată la sursă) indică acces doar prin notar, la cererea persoanei interesate, cu taxă mică (menționat 15 lei, dată incertă) și un protocol Infonot–CEC Bank pentru verificarea procurilor. Nu am găsit dacă Raiffeisen are acces direct, nici un formular public cu cod de verificare. Încercări: căutări „RNNEPR verificare”, notari.pro, legalbadger.org, notariat.
- **Textul din Legea 36/1995 care înființează RNNEPR** (articol): nu l-am extras; copia locală `legea36-1995.html` nu conține cuvântul „procur”. De identificat pe notari.pro.
- Dacă banca acceptă procură sub semnătură privată pentru încasarea sumelor moștenirii: CGB cere autentificare pentru Mandatar; practică internă nepublică.
- Dacă încasarea unei sume de către mandatar este „act de dispoziție” cu cerința „împuternicit în mod expres” (art. 2.016 alin. 2): raționament, nu există text special.
- Cerințele de traducere (cine o legalizează) și valabilitatea apostilei în timp: nu apar în sursele salvate.
- Textul exact al Convenției de la Haga/actul de aderare al României: neextras.

## Ce înseamnă pentru agent
1. **Rol A (procura defunctului):** împuternicitul pe cont nu mai are drepturi de la deces (CGB 3.2.5 b: „numai pe timpul vietii titularului”; art. 2.030 alin. 1 lit. c). Agentul nu execută și nu discută cont cu mandatarul defunctului; operațiunile făcute înainte ca el sau banca să afle decesul sunt tratate separat (art. 2.036), cu escaladare la om. Vezi `secret-bancar.md`.
2. **Rol B (procura moștenitorului):** acceptăm procura doar dacă: (a) e autentică (notar RO, consulat RO sau străină apostilată/supralegalizată + traducere legalizată); (b) obiectul include **expres** încasarea/dispoziția și semnarea cererii (art. 2.016 alin. 2); (c) nu e expirată (termen din procură sau 3 ani, art. 2.015); (d) mandatarul e identificat (CI/pașaport) și trece KYC ca persoană care acționează în numele clientului (Legea 129/2019 art. 11 alin. 4, vezi `aml-kyc-mostenitori.md`).
3. **Verificarea revocării:** agentul **nu poate** presupune acces la RNNEPR; creează sarcină „verificare RNNEPR/notar” pentru operator sau cere declarație pe propria răspundere că procura nu a fost revocată (propunere proprie). Fără rezultat, plata nu pleacă.
4. **IBAN:** plata rămâne în contul **moștenitorului** (mandantului), nu al mandatarului, decât dacă procura permite expres alt cont, caz în care escaladare la om.
5. **Moștenitor minor + procură:** nu se acceptă procura părintelui ca înlocuitor al încuviințării/autorizării din `mostenitor-minor.md`; escaladare.
6. **Câmpuri cu scor mic** (`apostila`, `traducere_legalizata`, `obiect`) → document nevalidat, nu respins automat; se cere operatorului.
