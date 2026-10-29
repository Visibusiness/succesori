<!-- {"generated_at": "2026-10-28T20:42:59+00:00", "agent": "case-investigator", "ok": true, "seconds": 17.2, "cost_usd": 0.049007499999999996} -->
# Investigație ESC-1 — SC-NEIDENTIFICAT

# Propunere pentru operator: ESC-1 (document_illegible)

**Dosar:** SC-NEIDENTIFICAT (documente neidentificate, fără client legat) · **Document:** doc-7 (`07-certificat-deces-ilizibil.md`, primit 2026-10-28)

## Fapte
- Tip declarat: `death_certificate`. Încredere 0.40, lizibilitate `illegible`. Paznicul a dat risc `low`, fără semnale, deci nu e suspect, ci doar slab citibil.
- Extractorul a citit doar `document_series` = „XX” (încredere 0.8, dovadă: „Certificat seria XX nr. 0000███”).
- Nu a putut citi: CNP, nume (0.2, fără dovadă), data nașterii, data decesului, numărul documentului, numărul actului de deces, părinții.
- Validarea V3 a trecut. A picat `cnp_missing` (block): nu există CNP și nici identitate alternativă (nume + data nașterii).
- Dosarul nu are produse, moștenitori, termene sau plăți. Nu s-a făcut nicio acțiune pe core (E1, E2).
- Expeditorul este necunoscut (`sender: null`), deci nu există un canal către care să răspundem automat.

## Variante
1. **Cerere de re-scanare (recomandată).**
   - Acțiune: cere o fotografie sau scanare clară a întregului certificat. Textul problemei „illegible” e deja pregătit.
   - Temei: GDPR art. 22 și principiul „nu ghicim”.
   - Risc: mic. Dacă nu se știe expeditorul, cererea nu are destinatar.
   - Lipsește: certificatul de deces lizibil, cu toate paginile.
2. **Original la agenție.**
   - Acțiune: cere prezentarea originalului sau a unei copii certificate la agenție, cu act de identitate. Verifică acolo identitatea decedatului și leagă documentul de client.
   - Temei: același ca la varianta 1. Rezolvarea acceptată anterior pentru doc-07 a fost identificarea la ghișeu.
   - Risc: întârziere.
   - Lipsește: originalul și identificarea la ghișeu.
3. **Identificare prin notar.**
   - Acțiune: dacă se află care notar a deschis succesiunea, cere confirmarea identității decedatului pe canalul din registru. Nu se răspunde cu date despre solduri.
   - Temei: secretul bancar (`kb/legal/secret-bancar.md`).
   - Risc: confirmarea nu înlocuiește certificatul.
   - Lipsește: adresa notarului și un CNP verificabil.

## Ce NU pot decide
- Identitatea decedatului și legarea doc-7 de un client: se face doar cu act de identitate la ghișeu sau cu CNP verificat. Decide operatorul.
- Nu deduc nimic din seria „XX”. Nu pornesc deschiderea succesiunii și nu fac nicio acțiune pe core până nu există CNP sau nume + data nașterii cu dovadă.
- Nu există semnale de fraudă sau litigiu. Dacă apar, merg la securitate.

**Operatorul confirmă** că s-a cerut re-scanarea sau prezentarea originalului.
