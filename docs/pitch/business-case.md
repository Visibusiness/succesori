Sursă: `kb/data/estimare-volum-cost.md` și `raiffeisen-cifre.md` (volum, clienți), `kb/bank-procedures/cazuri-reale.md` (Bragadiru), `docs/DECISIONS.md`, `kb/legal/outsourcing-bnr-eba-dora.md`, `kb/legal/secret-bancar.md`; prețuri Claude din documentația Anthropic (cache 2026-10-06) · Accesat: 2026-10-28 · Owner: DOMAIN

# Business case: Agentul de succesiune (2 slide-uri)
Tot ce nu are sursă e **(estimare proprie)**; ipotezele sunt la vedere ca mentorii să le poată schimba.

## Slide 1 — Problema și valoarea

**Problema.** Când moare un client, banca află târziu și prin canale fragmentate (familie, notar, asigurător). Cazul-cheie, Raiffeisen, Bragadiru (presă, 22.02.2023): cont Premium cu comision de **60 lei/lună**; familia spune că a depus certificatul pe 4.03.2021, banca răspunde că „nu există dovezi că banca ar fi fost înștiințată”. Rezultat: 490,66 lei necontestați, plus **2.331,45 lei** în comisioane și penalități (martie 2021–decembrie 2022), transformate într-o „linie de credit” pentru recuperare. Nu există recipisă, deci nu există adevăr comun. Decesul era însă în evidența statului (DGEP trimite data decesului săptămânal; contract cu Raiffeisen din iun. 2025).

**Volum** (estimare proprie, `estimare-volum-cost.md`): decese/an ≈ 240.000 (INS); probabilitatea ca un decedat să fie client 7%–14% (I4).

| Scenariu | Dosare/an | Ore manuale/dosar | Ore/an | FTE (1.700 h) |
|---|---|---|---|---|
| Prudent | 16.800 | 1,5 (3 × 30 min) | 25.200 | ≈ 15 |
| Central | 24.000 | 3 (4 × 45 min) | 72.000 | ≈ 42 |
| Optimist | 33.600 | 6 (6 × 60 min) | 201.600 | ≈ 119 |

**Valoare (cost evitat), pe categorii.**

| Categorie | Cum se evită | Cifră |
|---|---|---|
| Ore back-office | agentul extrage, verifică, redactează; omul aprobă (ținta: din 3–6 interacțiuni rămân 1–2) | calcul mai jos (estimare proprie) |
| Comisioane stornate corect | semnal DGEP ⇒ blocare debit + `fees_to_reverse(data_decesului)` (3.8.3 CGB: blocarea parțială nu oprește comisionul, deci se cere explicit) | formulă: dosare afectate × luni × 60 lei; Bragadiru = 22 luni ≈ 2.331 lei per caz extrem. **Nr. real de cazuri: necunoscut** |
| Reclamații / CSALB / reputație | recipisă la fiecare document primit; dosar unic | nicio decizie publică CSALB găsită pe deces; cost per reclamație: necunoscut |
| Pensii returnate manual | pensia lunii următoare decesului primește flag „posibil de restituit” (Legea 360/2023 art. 100, 156) | cost per caz: necunoscut |
| Retrageri ale împuterniciților după deces | revocare la semnal DGEP (CGB 3.2.5 b: împuterniciții doar „pe timpul vieții titularului”) | frecvență: necunoscută (caz în presă, 29.08.2026) |
| Termenul de 30 de zile UNIQA | termen urmărit automat (avizare în 30 de zile de la deces/aflare; plafon 260.000 lei per credit) | expunere maximă per caz ≤ 260.000 lei; frecvență necunoscută |

## Slide 2 — Cost, economie, adopție

**Cost per dosar, măsurat** (`cost-per-dosar.md`, `scripts/cost_dosar.py`): o rulare completă a dosarului demo, Sonnet 5.5, costă **2,35 $** (interval 1,4–2,4 $; auditorul 45%), deci peste estimarea de mai jos; optimizat (auditor la închidere, extracție pe Haiku) ≈ 1 $. Tabelul de mai jos rămâne estimarea inițială pe tokeni.

**Cost per dosar (Claude).** Prețuri (USD/1M tokeni, intrare/ieșire): **Opus 5.5 $4/$20** (cache citit $0.20), Sonnet 5.5 $2/$10. Ipoteze (estimare proprie): 7 documente × (3.000 tokeni intrare + 800 ieșire) pentru extracție + orchestrare/investigare/scrisori ≈ 80.000 intrare + 6.000 ieșire. Curs 1 USD = 4,5 lei (estimare proprie, de înlocuit).

| Scenariu | Ipoteză | $/dosar | Dosare | Total/an |
|---|---|---|---|---|
| Prudent | consum ×2, fără cache | ≈ 1,3 | 16.800 | ≈ 22k $ ≈ 98k lei |
| Central | Opus 5.5 peste tot | ≈ 0,64 | 24.000 | ≈ 15k $ ≈ 69k lei |
| Optimist | extracție pe Sonnet 5.5 + cache | ≈ 0,33 | 33.600 | ≈ 11k $ ≈ 50k lei |

Plus infrastructură internă (găzduire, integrare DGEP/core, monitorizare, echipă): **necunoscut**, parametru de la bancă.

**Economie de ore** = ore/an × % automatizat × cost orar încărcat. Costul orar real al unui operator Raiffeisen nu e public: 60/90/120 lei/oră (estimare proprie, de înlocuit cu salariu mediu bancar brut + contribuții).

| Scenariu | Ore/an × automat. | Ore economisite | Cost orar | Economie/an | vs. cost tokeni |
|---|---|---|---|---|---|
| Prudent | 25.200 × 50% | 12.600 | 60 lei | ≈ 0,76 mil. lei | ≈ 8× |
| Central | 72.000 × 65% | 46.800 | 90 lei | ≈ 4,2 mil. lei | ≈ 60× |
| Optimist | 201.600 × 75% | 151.200 | 120 lei | ≈ 18 mil. lei | ≈ 360× |

Nu includ comisioane, litigii sau pensii (necunoscute). Moștenitorii câștigă și ei timp (mai puține drumuri la agenție, un singur dosar cu recipise), dar nu îl monetizăm.

**Adopție.**
- **Faza 1 — serviciu intern în bancă.** Agentul pregătește, omul decide (GDPR art. 22; pe semnal DGEP doar măsuri reversibile). Dacă LLM-ul e furnizor extern, rămân obligații **DORA art. 28/30** (registru de informații, clauze minime: locație date, audit, ieșire); se evită notificarea BNR prealabilă de 2 luni (Reg. 5/2013 art. 230^11) numai dacă funcția e evaluată ca necritică. Mesaj corect: „obligații minime, standard pentru orice furnizor cloud”, nu „fără obligații”.
- **Faza 2 — hub extern** între bănci/notari: probabil funcție critică ⇒ notificare BNR, acord complet cu drepturi de audit, strategie de ieșire, raportare semestrială.
- **Ce cere un pilot:** feed DGEP deja contractat (iun. 2025); acces read-only la core pentru produse/solduri/comisioane; un operator back-office care aprobă; un set de dosare istorice pentru evaluare; avizul compliance/DPO.

## Pentru oameni (moștenitorii)
Nu monetizăm, dar e partea pe care o simte familia. Surse: `raiffeisen-deces-ghid.md`, `alte-banci-deces.md`, `cazuri-reale.md`; restul **(estimare proprie)**.

| Câștig | Azi | Cu agentul | Sursă / ipoteză |
|---|---|---|---|
| **Drumuri la agenție** | 3–5 per moștenitor: notificare deces, depunere acte, 1–2 completări (ex. banca cere certificatul să menționeze expres disponibilitățile, cazul CEC), semnare | 0–1 (doar dacă KYC cere prezență; actele se încarcă prin link) | Raiffeisen: cerere „în orice agenție” sau scrisă; CEC din forum; numărul de drumuri e estimare proprie |
| **Drumuri evitate/an** | – | ≈ 3 drumuri × 2,5 moștenitori × 24.000 dosare ≈ **180.000** (central) | estimare proprie; 2,5 moștenitori/dosar presupus |
| **Zile de așteptare** | banca află când anunță familia: în Bragadiru, decesul din feb. 2020, „înștiințare” spusă de familie la 4.03.2021 ≈ 13 luni | DGEP săptămânal ⇒ banca știe în ≤ 7 zile; lista documentelor lipsă ajunge în aceeași zi, nu după vizite repetate (≈ 5–15 zile câștigate, estimare proprie) | `cazuri-reale.md`, `dgep-arb-acord.md`. Termenul notarului (4–8 săptămâni, presă) **nu** se schimbă |
| **Comisioane nedatorate evitate** | Premium 60 lei/lună curge până află banca; Bragadiru: 490,66 lei până în martie 2021 + 2.331,45 lei (comisioane/penalități, martie 2021–dec. 2022) | blocare debit + `fees_to_reverse(data_decesului)` în ≤ 1 săptămână de la semnal | formula per caz: (luni între deces și blocare − 1) × 60 lei; ex. familie care anunță după 6 luni ⇒ ≈ 300 lei evitați. Câte conturi au comision: necunoscut |

Un singur dosar cu recipisă pentru fiecare document elimină și litigiul „nu există dovezi că banca ar fi fost înștiințată”.

## Calitatea agentului
Extractorul de documente se îmbunătățește singur din erori: **95,6% → 100%** pe câmpuri după un ciclu de învățare (19 documente de test, 8 principale + 11 grele; ±1 punct de zgomot între rulări, deoarece extracția folosește un LLM). Schimbările se păstrează doar dacă scorul nu scade; codul nu e modificat de buclă (raportul 039, `runs/retro-*.md`).

## Întrebări pentru mentorii Raiffeisen
1. Câți clienți decedați/an (și câți conturi cu rulaj sub pragul comisionului) are portofoliul? Înlocuiește intervalul 7%–14%.
2. Costul orar încărcat al unui operator back-office și timpul real per dosar de succesiune (interacțiuni × minute).
3. Compliance: sunteți de acord cu regula RIL ÎCCJ 9/2024 (moștenitorul primește informații despre perioada dinainte de deces dacă justifică scopul, fără certificat în dispozitiv)? Ce dovadă a calității cereți înainte de certificat?
4. Un LLM găzduit extern, în UE, în Faza 1: ce evaluare de criticitate și ce clauze cere politica voastră de externalizare/DORA?
5. Câte stornări de comisioane, reclamații/CSALB și restituiri de pensii legate de deces aveți pe an?
