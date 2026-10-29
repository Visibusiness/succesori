# Extras din core: clienta RC1001 (pentru studiul de timp)

Sursă: `agent/core_mock.py` (clienta demo) și `kb/scenariu-demo/maria-ionescu.md` §1, §2.2 · Accesat: 2026-10-28 ·
Owner: LEAD. Date **fictive**. Aici sunt doar datele brute din core, nimic calculat.

## Clientul
| Câmp | Valoare |
|---|---|
| Nume | IONESCU MARIA |
| CIF | RC1001 |
| CNP | 2XXXXXXXXXXXX |
| Data nașterii | 12.05.1958 |
| Stare civilă (KYC) | căsătorită cu IONESCU ION |
| Împuterniciți pe cont | IONESCU ANDREI (mandat M-7) |
| Carduri | C-1 (principal), C-2 (suplimentar) |
| Pachet de cont | Premium, 60,00 lei/lună, debitat pe 5 ale lunii |
| Cutii de valori închiriate | niciuna |

## Produse
| Produs | IBAN / contract | Valută | Date |
|---|---|---|---|
| Cont curent CC-1 | RO00 RZBR 0000 0000 0000 01 | RON | sold la sfârșitul zilei de 03.09.2026: **3.200,00 lei** |
| Depozit la termen DEP-1 | RO00 RZBR 0000 0000 0000 02 | RON | 20.000,00 lei, constituit 03.01.2026, 12 luni, scadent 03.01.2027, dobândă fixă 5,20%/an, plătită la scadență; lichidarea anticipată pierde dobânda |
| Credit nevoi personale CRD-1 | contract NP-2023-001001 din 10.05.2023 | RON | sold principal la 03.09.2026: 9.000,00 lei; dobândă 12,00%/an; ultima rată plătită (cu dobânda la zi) pe 25.08.2026; asigurare de viață UNIQA, certificat UQ-0000000-FICTIV, primele plătite la zi |

## Mișcări pe CC-1 (august – octombrie 2026)
| Data | Descriere | Sumă (lei) |
|---|---|---|
| 05.08.2026 | Comision pachet Premium | −60,00 |
| 15.08.2026 | Pensie (CNPP) | +2.100,00 |
| 05.09.2026 | Comision pachet Premium | −60,00 |
| 15.09.2026 | Pensie (CNPP) | +2.100,00 |
| 20.09.2026 | (blocare cont după semnalul DGEP) | — |
| 15.10.2026 | Pensie (CNPP) | +2.100,00 |

Nu sunt alte mișcări (nicio retragere, nicio plată cu cardul) după 03.09.2026.
