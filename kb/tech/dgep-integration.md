Sursă: https://www.bcr.ro/content/dam/ro/bcr/www_bcr_ro/informatii-utile/Contract-DGEP-BCR-2023.pdf ; https://www.unicredit.ro/content/dam/cee2020-pws-ro/DocumentePDF/Contract-UniCredit-DGEP-pentru-site.pdf ; https://ing.ro/dam/ingro/doc/Contract-ING-DGEP.pdf ; https://www.raiffeisen.ro/ro/persoane-fizice/in-sprijinul-tau/informatii-utile/colaborarea-raiffeisen-bank-cu-directia-generala-pentru-evidenta-persoanelor-dgep.html ; https://economedia.ro/?p=345791 · Accesat: 2026-10-28 · Owner: TECH

# Integrarea DGEP (RNEP): ce știm despre interfața reală și ce mock-uim

Partea juridică și contractuală (temei, cine, de când) e în `kb/bank-procedures/dgep-arb-acord.md`. Aici e doar partea tehnică.
Originale: `kb/_downloads/nicolas/dgep/`.

## 1. Interfața reală (din contractele publicate)

RNEP = Registrul Național de Evidență a Persoanelor, gestionat de DGEP (MAI). Contractul-tip prevede **trei canale**:

| Canal | Direcție | Transport | Intrare | Ieșire | Frecvență |
|---|---|---|---|---|---|
| **Actualizare inițială** (art. 2) | bancă → DGEP → bancă | suport optic/USB „sau prin linie securizată”, „fişiere text, cu delimitatori” | CNP, nume, prenume, cod bancă (format: Anexa 1 la acordul-cadru) | date act identitate, adrese, „informații privind data decesului, după caz” | o dată |
| **Serviciu web de validare** (art. 3 BCR / art. 7 UniCredit) | bancă → DGEP, sincron | serviciu web prin rețeaua STS → RCVD (MAI) | CNP + nume și prenume | „true/false”; dacă e valid: adrese, data decesului (UniCredit/Raiffeisen: „data și locul decesului”), foto, date act | la cerere, online |
| **Actualizare periodică** (art. 4 BCR / art. 8 UniCredit) | DGEP → bancă (modificări) | „conexiune SFTP, gestionată de Serviciul de Telecomunicații Speciale” | lista săptămânală a băncii: cod bancă, nume, CNP, „client nou sau client închis” | modificările din RNEP, inclusiv „informații privind data decesului, după caz” | **săptămânal** |

Citate tehnice (contract BCR):
> „Prin intermediul serviciului web se întorc informații de răspuns,,true/false” și în cazul în care datele sunt valide, se furnizează suplimentar următoarele informații:a) adresa de domiciliu;b) adresa de reședință, după caz;c) informații privind data decesului, după caz;[...]”
> „(5) Prin serviciul web pot fi introduse sau eliminate, punctual, coduri numerice personale în vederea actualizării microregistrelor”
> „(6) Serviciul de Telecomunicații Speciale asigură administrarea şi funcţionarea permanentă a sistemului de comunicaţii şi certificatelor necesare pentru autentificarea şi asigurarea schimbului de informaţii, în mediul on-line, între D.G.E.P.și Bancă [...](7) Conectarea stațiilor de lucru ale băncii va fi asigurată prin punctul de prezență existent al rețelei de comunicații de date de intercooperare, asigurat de Serviciul Telecomunicații Speciale, până la punctul de interconectare al acestei rețele cu Rețeaua de Comunicații Voce – Date a MAI (RCVD).”
> „D.G.E.P. comunică săptămânal, pe baza informațiilor transmise săptămânal de Bancă și informațiilor referitoare la baza de clienți existentă în microregistre, modificările intervenite în R.N.E.P. [...] f) informații privind data decesului, după caz;(2) Schimbul de informații prevăzut în prezentul articol se realizează printr-un canal de comunicații securizat, utilizând o conexiune SFTP, gestionată de Serviciul de Telecomunicații Speciale.”

UniCredit 2025, art. 9: STS asigură „rețelei de comunicații de tip VPN a Băncii” conectarea cu RCVD „prin intermediul rețelei de Cooperare Extranet STS”.

„Microregistru” = lista de CNP-uri urmărite de bancă la DGEP. Banca adaugă sau scoate CNP-uri prin web service sau prin lista săptămânală („client nou / client închis”).

Raiffeisen: „În primul trimestru, Raiffeisen Bank a finalizat integrarea prin API cu Direcția Generală de Evidență a Persoanelor.” (economedia, 05.05.2026). Pagina Raiffeisen confirmă cele trei modalități și serviciul web integrat în Smart Mobile.

Cost (art. 6): 1 leu/persoană prelucrată pentru validare și actualizare periodică. La actualizarea periodică se plătește „strict pentru persoanele cu privire la care s-au înregistrat modificări”.

## 2. Ce NU știm (interfața exactă)
Vezi `## Necunoscut`. Pe scurt: nu există specificație publică. Formatul fișierului e în Anexa 1 la acordul-cadru (nepublică), iar structura datelor în Anexa 2, „document nedestinat publicității”. Nu cunoaștem WSDL/REST, autentificarea (certificate STS), numele câmpurilor, formatul datei sau codurile de eroare.

## 3. Ce mock-uim: mesajul „semnal deces” (GENERAT DE NOI)

> **Atenție: formatul de mai jos e GENERAT DE NOI.** Nu e formatul DGEP, care nu e public. Câmpurile marcate `real` corespund unor date pe care contractele spun că DGEP le livrează. Câmpurile marcate `mock` nu vin de la DGEP în realitate și le simulăm pentru demo sau pentru alte canale.

### 3.1 Lotul săptămânal (simulează canalul SFTP, art. 4)
Fișier `dgep_delta_<cod_banca>_<AAAA-SS>.jsonl`, câte o linie per CNP cu modificări. Real e „fişiere text, cu delimitatori”. Noi folosim JSON Lines pentru simplitate.

```json
{
  "schema": "mosteniri.dgep.death_signal/v0",
  "_generated_by_us": true,
  "_fields_source": "Nota de informare Raiffeisen Bank–DGEP, „Categoriile de date”, lit. b) actualizarea periodică: numele de familie și prenumele, CNP, tipul, seria și numărul actului de identitate, data emiterii și data expirării, adresa de domiciliu, adresa de reședință (după caz), data decesului (după caz). Locul decesului și certificatul de deces nu se transmit pe acest canal.",
  "message_id": "DGEP-MOCK-2026-09-20-000123",
  "channel": "periodic_sftp",
  "batch_week": "2026-W38",
  "bank_code": "RZBR",
  "last_name": "IONESCU",
  "first_name": "MARIA",
  "cnp": "2XXXXXXXXXXXX",
  "id_document": {
    "type": "CI",
    "series": "XX",
    "number": "000000",
    "issue_date": "2020-01-01",
    "expiry_date": "2030-01-01"
  },
  "domicile_address": "Municipiul Exemplu, Str. Fictivă nr. 1, Jud. Exemplu",
  "residence_address": null,
  "date_of_death": "2026-09-03",
  "communicated_at": "2026-09-20T06:00:00+03:00",
  "changed_fields": ["date_of_death"]
}
```

| Câmp | Real/mock | Observație |
|---|---|---|
| `cnp`, `last_name`, `first_name` | real | cheia de potrivire, art. 4 alin. (3) |
| `date_of_death` | real | „data decesului (după caz)”. Formatul ISO e ales de noi. |
| `id_document.*` (tip, serie, număr, `issue_date`, `expiry_date`) | real | nota Raiffeisen–DGEP, „Categoriile de date” lit. b). Ignorat de agent; util doar la potrivire. |
| `domicile_address`, `residence_address` | real | idem lit. b); reședința „după caz”, altfel `null`. |
| `communicated_at` | **mock** (derivat) | data la care banca primește lotul. O folosim pentru SLA și pentru „data aflării” (CGB/Cod civil art. 2030). |
| `changed_fields`, `batch_week`, `message_id`, `bank_code` | mock | metadate de procesare |

Ce **nu** e în lotul periodic (058, după nota Raiffeisen): locul decesului vine doar pe web service (lit. c), „data și locul decesului”), iar seria/numărul actului de deces nu le trimite DGEP pe niciun canal; se completează din certificatul adus de familie sau de notar.

### 3.2 Verificare la cerere (simulează web service-ul, art. 3)
`POST /mock/dgep/validate` (endpoint GENERAT DE NOI)

```json
// request
{ "cnp": "2XXXXXXXXXXXX", "last_name": "IONESCU", "first_name": "MARIA" }
// response
{ "_generated_by_us": true, "valid": true,
  "date_of_death": "2026-09-03", "place_of_death": "București",
  "address": "...", "id_document": { "type": "CI", "series": "XX", "number": "000000" } }
```
Pentru CNP + nume care nu se potrivesc: `{ "valid": false }`, fără alte date (contractul: răspuns „true/false”).

### 3.3 Cazuri de test pentru mock (GENERAT DE NOI)
1. Semnal normal (Maria Ionescu, 20 sept.).
2. CNP necunoscut băncii → se ignoră și se loghează.
3. CNP = împuternicit, nu titular → acțiune „revocare împuternicire”, fără dosar de succesiune.
4. Data decesului din DGEP diferă de data din certificatul de deces → escaladare.
5. Semnal duplicat în două loturi → idempotent pe `cnp + date_of_death`.
6. `valid:false` la web service → nu se deschide dosarul, se cere certificatul de deces.

## Necunoscut
- Specificația tehnică DGEP: protocol web service (SOAP/REST), schema, autentificarea (certificate STS), formatul fișierului SFTP (Anexa 1 la acordul-cadru) și structura datelor (Anexa 2, nepublică). Am căutat contractele publicate (BCR, ING, UniCredit, BRD, Raiffeisen) și depabd.mai.gov.ro prin WebSearch, fără rezultat.
- Ziua din săptămână în care vine lotul și latența RNEP față de înregistrarea decesului la SPCLEP.
- Dacă Raiffeisen folosește deja câmpul „data decesului” din lotul săptămânal. Contractul Raiffeisen (PDF scanat) nu a putut fi citit fără OCR.
- Cum se semnalează o rectificare sau anulare de act de deces.

## Ce înseamnă pentru agent
1. Adaptorul `registries/dgep-mock` expune **două** interfețe: un lot săptămânal (fișier JSONL într-un folder „inbox”, care simulează SFTP) și `POST /mock/dgep/validate` (care simulează serviciul web). Ambele sunt marcate `_generated_by_us: true`.
2. Agentul tratează `date_of_death` din DGEP ca **sursă oficială, dar provizorie**. Măsurile la semnal sunt conservatorii și reversibile (vezi `dgep-arb-acord.md`, regula 4).
3. Câmpul `death_certificate` e `null` la semnalul DGEP. Agentul nu blochează fluxul pentru că lipsește. Îl completează când vine certificatul.
4. Idempotență pe `(cnp, date_of_death)`. Un al doilea semnal identic nu deschide un al doilea dosar.
5. Potrivirea se face pe CNP. Dacă numele diferă de cel din core (de ex. schimbare de nume), agentul nu acționează automat și escaladează.
6. Pentru ce documentul vine întâi pe alt canal (notar, familie), agentul **poate** apela `validate` ca să confirme decesul. Rezultatul se loghează ca dovadă în dosar.
