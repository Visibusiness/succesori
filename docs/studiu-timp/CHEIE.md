# Cheia de corectare (NU se dă participanților)

Sursă: `kb/scenariu-demo/maria-ionescu.md` §2.1–2.5 (varianta A, cu pensia din octombrie) · Accesat: 2026-10-28 · Owner: LEAD.
Aceleași valori sunt în `cheie.json`, citit de `scripts/impact_studiu.py`. Sumele se compară **la ban**; cotele ca fracții
(`10/16` = `5/8`); datele exact. Câmpurile `v_*` le completează corectorul cu `da` (punctul e în document, corect) sau `nu`.

## T1: Soldurile la 03.09.2026 cu dobânda

| Câmp | Tip | Răspuns corect |
|---|---|---|
| `sold_cc` | lei | 3200.00 |
| `dep_principal` | lei | 20000.00 |
| `dep_dobanda` | lei | 692.38 |
| `credit_principal` | lei | 9000.00 |
| `credit_dobanda` | lei | 26.63 |

## T2: Răspunsul către notar

| Câmp | Tip | Răspuns corect |
|---|---|---|
| `v_solduri` | corector: da/nu | soldurile la D ale celor 3 produse, cu dobânda (3.200,00; 20.000,00 + 692,38; 9.000,00 + 26,63) |
| `v_iban_valuta` | corector: da/nu | IBAN-ul și valuta fiecărui cont/depozit (punctul 1 din adresă) |
| `v_credit_asigurare` | corector: da/nu | creditul, cu mențiunea asigurării UNIQA UQ-0000000-FICTIV (punctul 3) |
| `v_pensie_sept` | corector: da/nu | pensia din 15.09.2026 (2.100,00) raportată ca încasare după deces, care se cuvine |
| `v_cutii` | corector: da/nu | mențiunea despre cutiile de valori: nu există (punctul 4) |
| `v_imputerniciti` | corector: da/nu | împuternicitul numit (IONESCU ANDREI), cu încetarea mandatului la deces (punctul 5) |

## T3: Comisioane de stornat

| Câmp | Tip | Răspuns corect |
|---|---|---|
| `comision_stornat` | lei | 60.00 |
| `comision_data` | data | 2026-09-05 |

## T4: Pensia de returnat / păstrat

| Câmp | Tip | Răspuns corect |
|---|---|---|
| `pensie_retur` | lei | 2100.00 |
| `pensie_retur_data` | data | 2026-10-15 |
| `pensie_pastrata` | lei | 2100.00 |

## T5: Cotele și planul de plată

| Câmp | Tip | Răspuns corect |
|---|---|---|
| `net_cc` | lei | 5273.37 |
| `cota_ion` | fractie | 5/8 |
| `cota_andrei` | fractie | 3/16 |
| `cota_elena` | fractie | 3/16 |
| `cc_ion` | lei | 3295.85 |
| `cc_andrei` | lei | 988.76 |
| `cc_elena` | lei | 988.76 |
| `elena_blocat` | da_nu | da |
| `dep_ion` | lei | 13150.00 |
| `dep_andrei` | lei | 3945.00 |
| `dep_elena` | lei | 3945.00 |
| `depozit_plata_data` | data | 2027-01-03 |
| `platibil_acum` | lei | 4284.61 |

## T6: Ce lipsește, mesajul către moștenitor, documentul 7

| Câmp | Tip | Răspuns corect |
|---|---|---|
| `v_lipseste_acord_elena` | corector: da/nu | lipsește acordul scris al reprezentantului legal pentru ELENA (minoră); suplimentul a venit deja |
| `v_mesaj_cere_acord` | corector: da/nu | mesajul, către IONESCU ION (reprezentantul legal), cere exact acest document și spune cum se trimite |
| `v_mesaj_fara_solduri` | corector: da/nu | mesajul nu dezvăluie solduri sau sumele altor moștenitori (secret bancar) |
| `v_doc7_escaladat` | corector: da/nu | documentul 7 nu se atașează dosarului Mariei (ilizibil, CNP necitibil, alt client): merge la operator |

## De unde vin cifrele

- Dobânda depozitului: 20.000 × 5,20% × 243 zile (03.01→03.09) / 365 = 692,38 lei; la scadență: 20.000 × 5,20% × 365/365 = 1.040,00 lei ⇒ 21.040,00 lei.
- Dobânda creditului: 9.000 × 12% × 9 zile (25.08→03.09) / 365 = 26,63 lei (neacoperită de indemnizație).
- Net cont curent = 3.200,00 + 2.100,00 (pensia din septembrie) − 26,63 = 5.273,37 lei; pensia din octombrie se reține.
- Fracții din bun: Ion ½ + ½ · ¼ = 5/8; Andrei și Elena ½ · 3/8 = 3/16. Cont: 3.295,85 / 988,76 / 988,76 (rămășița cea mai mare).
- Depozit la scadență: 21.040,00 × 5/8 = 13.150,00; × 3/16 = 3.945,00; toate blocate până la 03.01.2027.
- Plătibil acum: 3.295,85 + 988,76 = 4.284,61 lei (Elena blocată, depozitul la scadență).
