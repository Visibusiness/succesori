Sursă: generat de noi, din kb/data/ins-decese.md și kb/data/raiffeisen-cifre.md · Accesat: 2026-10-28 · Owner: DOCS

# Estimare volum și cost (estimare proprie)

Toate cifrele de aici sunt **(estimare proprie)**; ipotezele sunt explicite ca să poată fi schimbate în pitch.

## Ipoteze
| # | Ipoteză | Valoare | De unde |
|---|---|---|---|
| I1 | Decese/an în România | 240.000 | INS, medie lunară ≈ 20.000 (`ins-decese.md`) |
| I2 | Populație adultă (18+) | ≈ 15,5–16 mil. | estimare; de verificat INS |
| I3 | Clienți Raiffeisen | 2,33 mil. (final 2025) | `raiffeisen-cifre.md` |
| I4 | Probabilitatea ca un decedat să fie client Raiffeisen | 7%–14% | 14% = cota de clienți din adulți; 7% = corecție pentru vârstă (decedații sunt preponderent vârstnici, mai puțin digitali/clienți Raiffeisen). De confirmat cu banca |
| I5 | Interacțiuni manuale per dosar | 3–6 | BRIEF §2 (notar, familie, asigurător, plată…) |
| I6 | Minute per interacțiune | 30–60 | BRIEF §2 |
| I7 | Ore lucrate/an per FTE | 1.700 | convenție |

## Calcul
| Scenariu | Dosare/an (I1×I4) | Ore/dosar (I5×I6) | Ore/an | FTE |
|---|---|---|---|---|
| Prudent | 240.000 × 7% = **16.800** | 3 × 0,5 = 1,5 | 25.200 | ≈ 15 |
| Central | 240.000 × 10% = **24.000** | 4 × 0,75 = 3 | 72.000 | ≈ 42 |
| Maxim | 240.000 × 14% = **33.600** | 6 × 1 = 6 | 201.600 | ≈ 119 |

**Corecție față de BRIEF:** brieful spune 25–30k dosare/an și 40–90k ore/an. Scenariul central (24k dosare, ~72k ore)
e în interval; formularea sigură pentru pitch: **„~17–34 mii dosare/an, ordinul zecilor de mii de ore de lucru manual”**.

## Costuri evitate (de completat după 001/003/010)
- Comisioane încasate după deces și restituite ulterior (caz Bragadiru: 2.331 lei pe un singur dosar) — risc reputațional/CSALB.
- Pensii virate după deces și returnate manual către CNPP.
- Retrageri ale împuterniciților după deces (litigii).

## Necunoscut
- Costul orar intern al unui operator back-office Raiffeisen (nu e public) — în pitch îl lăsăm parametru.
- Rata reală de clienți decedați/an (doar banca o are) — întrebare pentru mentorii Raiffeisen.

## Ce înseamnă pentru agent
- Ținta de automatizare: din 3–6 interacțiuni manuale per dosar rămân 1–2 (aprobarea plății, escaladări).
- Demo-ul trebuie să arate timpul: „7 documente procesate în X minute” vs. ore de lucru manual.
