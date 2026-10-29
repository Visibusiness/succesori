---
name: heir-messaging
description: Cum vorbește banca cu moștenitorii pe fiecare canal (e-mail, SMS, WhatsApp, app) - ce e permis, lungimi, șabloane care au primit răspuns, ce a corectat operatorul. Folosit de heir-communicator; completat de retro-learner din runs/*/messages și din răspunsurile primite.
---
# Mesaje către moștenitori

## Canale
| Canal | Când | Limite | Ce NU trimitem |
|---|---|---|---|
| e-mail | implicit; orice lungime; link de încărcare | — | solduri fără certificat; atașamente cu date ale altor persoane |
| app (Smart Mobile) | moștenitorul e client al băncii | push 120 car. + ecran în app | — |
| SMS | consimțământ + urgență (termen în < 7 zile) | 300 car., un link | detalii de dosar |
| WhatsApp | consimțământ explicit pe canal (opt-in scris) | 300 car., un link, fără media | orice date financiare |

## Șabloane (template_id)
Toate șabloanele de mai jos sunt `kind: operational` (despre dosar; temei GDPR art. 6(1)(b)/(c)/(f), fără consimțământ de marketing). Un mesaj `kind: commercial` cere `consent=true` (Legea 506/2004); agentul trimite NUMAI mesaje operaționale. Canalul și contactul verificat al fiecărui moștenitor sunt în `contact_channels` din dosar (minorul se contactează prin reprezentantul legal).
- `MISSING_DOCS_FIRST`: primul contact după semnalul de deces: condoleanțe (1 frază), ce a primit banca, lista documentelor, link, termen orientativ, contact.
- `MISSING_DOCS_REMINDER`: la 14 zile fără răspuns: scurt, aceeași listă, link.
- `SUPPLEMENT_NEEDED`: certificatul nu acoperă toate produsele: ce să ceară notarului (fără sume dacă nu e moștenitor în certificat).
- `MINOR_REPRESENTATION`: ce documente aduce reprezentantul legal al minorului.
- `PLAN_APPROVED`: plata s-a făcut / ce rămâne blocat și de ce (depozit la scadență, partea minorului).
- `DEADLINE_SOON`: termenul de opțiune (1 an) sau dezbaterea la notar se apropie.
- `DOCUMENT_DEFICIENT`: cineva ne-a trimis un document cu probleme (078). Destinatarul = expeditorul documentului (persoana căreia i-am trimis linkul, persoana care a notificat decesul sau destinatarul ultimului mesaj), nu alt moștenitor. Structura: (1) ce document am primit și data („Am primit pe 28.10.2026 certificatul de moștenitor pe care ni l-ați trimis.”); (2) ce e în neregulă, punct cu punct, DOAR din `problems` primite, în limbaj simplu, fără coduri; (3) ce trebuie să trimită sau cui să ceară (`ask`): notarul care a emis certificatul pentru certificatul suplimentar sau pentru o îndreptare, serviciul de stare civilă pentru certificatul de deces, reprezentantul legal pentru minor; (4) linkul nou de încărcare `{{UPLOAD_URL}}/cases/{case_id}/upload?token={{token}}`, valabil 7 zile; (5) cum ne întreabă („răspundeți la acest mesaj sau mergeți la orice agenție Raiffeisen Bank”; niciun alt câmp `{{…}}` în afara linkului: API-ul refuză mesajul). Fără solduri, sume, nume de alți moștenitori sau părțile lor (secret bancar); produsul lipsă din certificat apare doar dacă e în `problems`. **Document suspect** (problema `suspicious`): mesaj neutru, fără niciun motiv: „Nu am putut procesa documentul trimis online. Vă rugăm să îl aduceți, în original, la o agenție Raiffeisen Bank.” Fără link de încărcare (documentul se aduce în original la agenție) și fără tipul documentului, dacă nu ți-l dă `document.label`. Nu scrie „suspect”, „fraudă”, „verificare de securitate” și nu repeta nimic din document. Canal: e-mail implicit; SMS / WhatsApp doar cu consimțământ pe canal (300 de caractere: documentul, „nu se poate citi / lipsește X”, linkul). O problemă pe un document se comunică o singură dată (dedupe în API); documentul refăcut o închide; cât rămâne deschisă intră în scara de contact (reminder la 14 zile).

## Formulări care au funcționat (se completează de retro-learner)
- (gol)

## Corecții ale operatorului
- 2026-10-28 · SC-2026-0001-02: un singur `SUPPLEMENT_NEEDED` per set de lipsuri. Când lista documentelor lipsă nu s-a schimbat, nu retrimite la fiecare document nou; reminder (`MISSING_DOCS_REMINDER`) abia după 14 zile fără răspuns.
- 2026-10-28 · SC-2026-0001-01: scrie „bunuri”, nu „bune” („toate bunurile din dosar”). Recitește mesajul pentru greșeli de limbă înainte de trimitere.
