# Regulile pe care le aplicați (aceleași pe care le aplică agentul)

Sursă: `kb/legal/*`, `kb/bank-procedures/*`, `docs/DECISIONS.md`, rezumate în `agent/rules.py` · Accesat: 2026-10-28 ·
Owner: LEAD. Fără valori calculate: doar regula și temeiul.

1. **Soldul la data decesului (D)** e ce cere notarul (Legea 36/1995 art. 81), nu soldul de azi.
2. **Dobânda**: simplă, convenția Act/365 (zile efective / 365), rotunjită la ban (jumătatea în sus). La depozit, de la
   constituire la D; la credit, de la ultima rată plătită la D.
3. **Comisioanele de administrare debitate după D** se stornează (relația contractuală nu continuă după deces; cazul
   Bragadiru 2023). Cele dinainte de D rămân.
4. **Pensia**: pensia lunii decesului se cuvine și intră în masă, chiar dacă e virată după D; pensiile lunilor următoare
   sunt necuvenite și se rețin pentru retur la CNPP (Legea 360/2023 art. 100 alin. 1 lit. a, art. 156 alin. 8).
5. **Credit cu asigurare**: indemnizația aprobată stinge principalul; ce nu acoperă (dobânda curentă la D) e datorie a
   masei și se scade din contul curent înainte de împărțire (C.civ. art. 1114).
6. **Bun comun**: din contul curent și din depozit, 1/2 revine soțului supraviețuitor ca proprietar; cealaltă 1/2 intră
   în masă și se împarte după cotele din certificat (C.civ. art. 339, 343). Cotele se iau din certificat, nu din lege,
   și trebuie să dea suma 1.
7. **Rotunjirea pe moștenitori**: cea mai mare rămășiță (fiecare primește partea întreagă în bani, banii rămași merg la
   cele mai mari rămășițe); la egalitate, în ordinea din certificat. Suma liniilor = suma de împărțit, exact.
8. **Depozitul nescadent**: se plătește la scadență, cu dobânda integrală (lichidarea anticipată ar cere acordul tuturor
   moștenitorilor, C.civ. art. 2187, și pierde dobânda).
9. **Minorul**: partea lui se calculează, dar se blochează până la acordul scris al reprezentantului legal (C.civ.
   art. 41, 144–146).
10. **Plata** pleacă doar cu aprobarea unui operator. **Un document care nu se poate citi** sau nu se potrivește cu niciun
    client nu se atașează la niciun dosar: merge la operator.
11. **Secretul bancar** (OUG 99/2006 art. 113): moștenitorului îi spuneți ce documente lipsesc și pașii următori, nu
    soldurile altor persoane.
