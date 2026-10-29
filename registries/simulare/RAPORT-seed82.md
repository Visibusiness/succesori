# Simularea la scară: seed 82, 200 dosare

Generat de `scripts/impact_simulare.py` la 2026-10-28T22:48:55+00:00. Referința: `registries/simulare/referinta.py` (nu importă agent/).

- 877 documente în 0.13 s (0.65 ms/dosar)
- dosare complet corecte: **200/200**; cu plan de plată: 200; plan corect: 200
- linii de plată exacte la ban: 1080/1080
- plăți executate fără aprobare: **0**
- dosare cu escaladările exacte: 200/200

## Capcane

| Capcană | Dosare | Prinse |
|---|---|---|
| comision după deces stornat | 84 | 84 |
| pensie de returnat la CNPP | 32 | 32 |
| produs omis ⇒ supliment | 45 | 45 |
| minor: parte blocată | 110 | 110 |
| retragere a împuternicitului după deces | 25 | 25 |
| asigurare refuzată | 10 | 10 |
| document ilizibil / suspect | 33 | 33 |

## Bug-uri găsite: cauza, câte dosare, exemplul minim

Codul din agent/ nu e modificat (regula proiectului); fiecare exemplu minim e rulat prin `Pipeline` în proces și comparat cu referința. Cel mai mic dosar din set cu aceeași cauză e în `rezultat-seed*.json` → `exemple_din_set`.

Niciuna.
