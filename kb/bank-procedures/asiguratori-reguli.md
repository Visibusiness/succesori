Sursă: kb/_downloads/realsurse/asiguratori/ (INDEX.md; raport coordonare/rapoarte/066-bedrock-asiguratori.md) + kb/bank-procedures/asigurare-viata-credit.md · Accesat: 2026-10-28 · Owner: DOMAIN
Codul: `agent/insurers.py` (aceleași valori; testele în `tests/test_rules.py` și `tests/test_pipeline.py`).

# Reguli pe asigurător (asigurări de viață atașate creditelor)

La Raiffeisen asigurătorul creditelor este **UNIQA Asigurări de viață S.A.**; banca este agent afiliat și beneficiar. Asigurătorul se ia din documentul „certificat de asigurare” (câmpul `insurer`); fără nume, se presupune UNIQA. Un asigurător nerecunoscut nu primește niciun termen inventat: „necunoscut, de confirmat cu banca”.

Stare valoare: **confirmat** = text public citat; **ipoteză** = nu e publicat de asigurător, folosit doar ca alertă; **necunoscut** = nu avem sursă.

## Termene
| Asigurător | Avizare de către moștenitori | Decizie | Plată |
|---|---|---|---|
| UNIQA | 30 de zile de la deces/aflare — **ipoteză, de confirmat** | necunoscut, de confirmat cu banca | 10 zile lucrătoare de la ultimul document — **ipoteză** (doar pentru cardurile de credit) |
| Allianz-Țiriac (My Credit Protect) | 90 de zile calendaristice de la producere, dar nu mai târziu de 2 ani de la deces — confirmat | 15 zile — confirmat | 15 zile de la toate documentele — confirmat |
| NN / ING (Credit Protect) | documentele în 30 de zile (altfel excludere) — confirmat | nepublicat separat | 10 zile lucrătoare de la ultimul document — confirmat |

Citate și surse:
- **UNIQA, avizare.** Condițiile Generale UNIQA pentru titularii de credite nu sunt publice (066). Formularul 2024 și pagina uniqa.ro/daune nu conțin termenul. Singura apariție a „30 de zile” este în `asigurare-viata-credit.md` §7, citat de pe daune-viata.uniqa.ro: *„va anunta asiguratorul [...] in termen de maxim 30 (treizeci) de zile calendaristice de la producerea acestuia sau de la data la care au luat la cunostinta”*, plus PID-ul de card: *„în termen de maxim 30 (treizeci) de zile calendaristice de la data producerii Evenimentului asigurat sau de la data la care moștenitorii iau cunoștință”*. Pentru creditul de nevoi personale nu am găsit textul contractual, deci rămâne ipoteză până la confirmarea cu banca. Codul calculează `data_aflării + 30 zile`.
- **UNIQA, plată.** PID carduri de credit 2023: *„Asigurătorul va plăti indemnizația de asigurare în termen de maximum 10 (zece) zile lucrătoare de la primirea ultimului document necesar”*. IPID-ul creditului de nevoi personale nu are termen de plată.
- **Allianz.** Condiții My Credit Protect (cod CTL26), art. 28 lit. a): avizare *„în termen de 90 de zile calendaristice de la producere, dar nu mai târziu de 2 ani de la data decesului”*; art. 40: plata *„în termen de 15 zile de la primirea tuturor documentelor necesare”*; decizia în 15 zile (INDEX 066, art. 30). Codul: `deces + 90 zile`, plafonat la `deces + 2 ani`.
- **NN / ING Credit Protect.** Termeni din 04.10.2023 (INDEX 066, [citit integral]): plata în 10 zile lucrătoare de la ultimul document; excluderea „nedepunerea documentelor în 30 zile”. Începutul celor 30 de zile nu l-am verificat pe text (PDF-ul nu se extrage curat); codul numără conservator de la deces.

## Documente cerute moștenitorilor pentru dosarul de daună
| Asigurător | De la moștenitori | Le are banca |
|---|---|---|
| UNIQA | cererea de despăgubire (formularul F1); copia certificatului de deces; copia certificatului constatator; la deces din boală: documente medicale din istoric; la accident: documente medico-legale | certificatul de asigurare + declarația asiguratului; graficul de rambursare semnat |
| Allianz | copia certificatului de deces; certificatul medical constatator; procesul-verbal al accidentului (dacă e cazul); datele bancare pentru plată | comunicarea băncii cu debitul rămas + grafic actualizat (art. 29 lit. e) |
| NN / ING | notificarea evenimentului; copia CI; certificat de deces; certificat medical constatator; fișa medicală / adeverința medicului de familie (boală); ancheta poliției/toxicologie (accident, dacă e cazul) | contractul de credit + grafic; certificatul de asigurare + cererea de aderare |

Surse: UNIQA — Anexa F1 RAIB V8_04.2024, secțiunea D; Allianz — art. 29; ING — termenii Credit Protect (lista documentelor la deces). Canale: UNIQA asigurari@uniqa.ro / daune-viata.uniqa.ro; NN 021.9464, evenimenteasigurate@nn.ro.

## Ce acoperă și excluderi tipice
| Asigurător | Acoperă | Excluderi tipice |
|---|---|---|
| UNIQA | deces și invaliditate permanentă totală din orice cauză: sold principal + max. 3 rate restante, plafon 260.000 lei (nevoi personale); beneficiar banca | condiție medicală din ultimele 24 de luni dacă decesul e în primele 12 luni de asigurare (la ipotecar: 5 ani / 5 ani); sinucidere în primii 2 ani; infracțiuni cu intenție, alcool/substanțe |
| Allianz | deces, sumă descrescătoare; beneficiar banca, surplusul la moștenitori (art. 38) | boli preexistente; sinucidere în primii 2 ani |
| NN / ING | deces = 100% din soldul creditului, max. 180.000 lei; excedentul la moștenitori | preexistente (12 luni pentru ITM/spitalizare); suicid; alcool/droguri; nedepunerea documentelor în 30 de zile |

## Necunoscut, de confirmat cu banca
- Termenul de avizare UNIQA pentru creditele Raiffeisen (Condițiile Generale nepublicate) și termenul de decizie UNIQA.
- Termenul de plată UNIQA pentru creditul de nevoi personale.
- Dacă banca, ca beneficiar, poate avizea singură dauna.
- Alți asigurători (Groupama, Generali, Asirom): nu au termen de avizare public; `lookup()` îi tratează ca „nerecunoscut”.
