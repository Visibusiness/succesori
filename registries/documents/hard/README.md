# registries/documents/hard — cazuri de test grele (H1–H5: „și dacă…?”, H6–H11: formate dificile)

Sunt luate din `kb/scenariu-demo/maria-ionescu.md` §4 și folosesc aceiași identificatori ca setul principal
(`documente-demo.md` §0). Fiecare caz are trei fișiere:
- `.md`: textul documentului;
- `.json`: ground truth, cu `fields` și `expected_agent`;
- `.mvp.json`: forma din `agent/demo_documents.py`.

Pentru documentele scanate, PDF-ul e în `pdf/` și se regenerează cu `python -m registries.generator`.

| Caz | Document | Ce testează | Rezultat așteptat |
|---|---|---|---|
| H1 | adresa notarului nr. 398/17.09.2026, primită 18.09, **înainte** de semnalul DGEP | ordinea inversă | adresa deschide dosarul și face freeze; DGEP-ul de pe 20.09 doar confirmă; aceleași valori |
| H2 | semnalul DGEP din nou, în lotul W39 (`.json` + `.expected.json`, fără PDF: e structurat) | idempotență | un singur freeze, o singură stornare de 6.000 bani |
| H3 | certificatul 87 cu Elena trecută la 3/4 în loc de 3/8 (suma 11/8) | cote ≠ 1 | escaladare `shares_invalid`, fără plan de plată |
| H4 | certificatul 87 cu CNP-ul defunctei `2XXXXXXXXXXX8` | CNP diferit | `409`, escaladare `cnp_mismatch`, dosarul RC1001 neatins |
| H5 | certificatul 87 fără IBAN la contul curent | potrivire fără IBAN | potrivire unică după tip + sumă (5.300 lei) → CC-1, flagul `matched_without_iban` |
| H6 | adresa notarului 412 cu toate datele scrise în litere | normalizare dată | aceleași valori ca 02 (date ISO) |
| H7 | certificatul 87 cu cotele doar în cuvinte („o doime”, „o pătrime”, „trei optimi”) | parsare fracții | 1/2 · 1/4 · 3/8 · 3/8, fracții exacte, ca 04-A |
| H8 | certificatul de asigurare cu „C.N.P. 2 XX XX XX XX XXX X” | normalizare CNP | CNP-ul fără spații/puncte = clientul; ca 03 |
| H9 | certificatul 87 cu titlul „ADRESĂ” | clasificare după conținut | `certificat_mostenitor` (nu `adresa_notar`), flagul `misleading_header`; ca 04-A |
| H10 | extras multilingv de deces (CIEC nr. 16), fără CNP | identitate fără CNP | potrivire unică nume + prenume + data nașterii, confirmată de data decesului și de soț → fără escaladare; dacă nu e unică → `identity_unconfirmed` |
| H11 | extras multilingv pentru un omonim (aceeași dată a nașterii, alt deces, alt soț, alți părinți) | ramura ambiguă a lui H10 | escaladare `identity_unconfirmed`; nu se atașează nicăieri, RC1001 neatins |

H3, H4, H5, H7 și H9 înlocuiesc documentul 04-A în secvență; H6 înlocuiește 02, H8 înlocuiește 03, iar H10 vine după 01 (2026-10-01); restul secvenței e cea din setul principal.
