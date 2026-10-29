# Studiu de timp: dosarul Mariei Ionescu, de mână vs. agentul

Sursă: generat de noi (sarcina 082), pe baza `kb/scenariu-demo/maria-ionescu.md` și a documentelor din
`ops-ui/_documente-demo/` · Accesat: 2026-10-28 · Owner: LEAD

**Scop.** Măsurăm cât durează și câte greșeli apar când un om face de mână ce face agentul pe dosarul demo, și comparăm
cu timpii agentului măsurați în rularea cap-coadă (`registries/simulare/e2e/<run>/`). Rezultatul îl calculează
`scripts/impact_studiu.py` din tabelul completat. Până nu vin datele, ecranul Rezultate arată studiul „în așteptare”.

## Cine și cum
- **2 colegi**, fiecare singur, fără agent și fără acces la `kb/scenariu-demo/maria-ionescu.md`, la `CHEIE.md` sau la
  `cheie.json`. Pot folosi calculatorul, Excel și un editor de text.
- Fiecare primește un exemplar al **tabelului** `tabel-de-completat.csv`, salvat ca `date/<prenume>.csv`.
- Pentru fiecare sarcină, notați ora de **start** (când deschideți primul document pentru ea) și de **stop** (când ați
  scris ultimul rezultat), cu secunde (`HH:MM:SS`), pe primul rând al sarcinii. Pauzele nu se cronometrează: dacă vă
  opriți, notați stop-ul și adăugați un rând nou cu același `sarcina` și un start nou (timpul se adună).
- Sumele se scriu în **lei, cu două zecimale**, fără separator de mii (`5273.37`), cotele ca fracții (`3/16`), datele ca
  `AAAA-LL-ZZ`, răspunsurile da/nu ca `da` sau `nu`.
- Nu corectați după ce ați trecut la sarcina următoare: vrem și greșelile, nu doar timpul.

## Materialele (în ordinea în care au sosit la bancă)
| # | Fișier | Ce e |
|---|---|---|
| 1 | `ops-ui/_documente-demo/01-dgep-semnal.mvp.json` (printat) | semnalul DGEP din 20.09.2026 (CNP, data decesului) |
| 2 | `ops-ui/_documente-demo/02-adresa-notar-scan.pdf` | adresa notarului, 28.09.2026 |
| 3 | `ops-ui/_documente-demo/03-certificat-asigurare-scan.pdf` | certificatul de asigurare UNIQA |
| 4 | `ops-ui/_documente-demo/04-certificat-mostenitor-A-scan.pdf` | certificatul de moștenitor (moștenire legală) |
| 5 | `ops-ui/_documente-demo/05-raspuns-asigurator-scan.pdf` | răspunsul asigurătorului |
| 6 | `ops-ui/_documente-demo/06-certificat-suplimentar-scan.pdf` | certificatul suplimentar |
| 7 | `ops-ui/_documente-demo/07-certificat-deces-ilizibil-scan.pdf` | un certificat de deces scanat prost |
| + | `docs/studiu-timp/extras-de-cont-RC1001.md` | ce vede operatorul în core: produse, dobânzi, mișcări |
| + | `docs/studiu-timp/reguli.md` | regulile băncii pe care le aplică și agentul |

`04-certificat-mostenitor-B-scan.pdf` (varianta cu testament) **nu** face parte din studiu: agentul a fost măsurat pe
varianta A.

## Sarcinile
| Cod | Sarcina | Ce scrieți în tabel |
|---|---|---|
| T1 | Soldurile fiecărui produs la data decesului, cu dobânda acumulată | `sold_cc`, `dep_principal`, `dep_dobanda`, `credit_principal`, `credit_dobanda` |
| T2 | Răspunsul scris către notar (la adresa nr. 412), ca document gata de semnat | `scrisoare` = numele fișierului; corectorul completează `v_*` |
| T3 | Ce comisioane se stornează | `comision_stornat` (total), `comision_data` (data fiecărui comision, separate prin `;`) |
| T4 | Ce pensie se returnează și ce pensie rămâne în masă | `pensie_retur`, `pensie_retur_data`, `pensie_pastrata` |
| T5 | Cotele pe fiecare produs și planul de plată | `net_cc`, `cota_ion`, `cota_andrei`, `cota_elena`, `cc_ion`, `cc_andrei`, `cc_elena`, `elena_blocat`, `dep_ion`, `dep_andrei`, `dep_elena`, `depozit_plata_data`, `platibil_acum` |
| T6 | Ce mai lipsește ca să se poată plăti tot, mesajul către moștenitor, ce faceți cu documentul 7 | `lipseste` (text), `mesaj` = numele fișierului, `doc7` (text); corectorul completează `v_*` |

Detalii pentru T5: `cota_*` = fracția din **fiecare produs** care revine moștenitorului (după lichidarea comunității),
`cc_*` = suma din contul curent, `dep_*` = suma din depozit, `platibil_acum` = totalul care se poate plăti azi.

## După ce terminați
Predați `date/<prenume>.csv`, scrisoarea (T2) și mesajul (T6). Corectorul (al treilea coleg) completează coloanele
`v_*` după `CHEIE.md` (doar da/nu) și rulează:

```bash
.venv/bin/python scripts/impact_studiu.py          # citește docs/studiu-timp/date/*.csv → docs/studiu-timp/rezultat.json
.venv/bin/python scripts/build_results.py           # ecranul Rezultate, secțiunea „Impact măsurat”
```

Același barem se aplică și agentului: `impact_studiu.py` citește răspunsurile lui din dosarul rulării (`cases/`,
`letters/`, `messages/`) și le punctează cu aceeași cheie, inclusiv lista `v_*` pentru scrisoare.
