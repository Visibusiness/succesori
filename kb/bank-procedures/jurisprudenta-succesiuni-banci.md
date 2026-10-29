Sursă: legeaz.net (copii locale `-anon.txt` în `kb/_downloads/visi/jurisprudenta/` (doar pe disc: directorul e în .gitignore): text anonimizat de instanță, unde a lăsat nume în clar anonimizat suplimentar de noi; nu e sursa oficială; hotărârile oficiale: portal.just.ro / ReJust) · Accesat: 2026-10-28 · Owner: DOMAIN

# Jurisprudență anonimizată: bancă + succesiune / asigurare de deces la credit (sarcina 055, etapa 1: listare)

**Stare:** **9** hotărâri utilizabile (5 curate + 4 anonimizate de noi); alte 4 deschise n-au legătură cu succesiunea și au fost șterse. Sarcina cere 10–15: **lipsesc ~2–6**, pentru că **ReJust** e aplicație JavaScript (curl primește doar shell-ul HTML, 14 KB; fără API public cunoscut), `portal.just.ro` răspunde **403** la curl, iar `scj.ro` nu a dat căutare utilizabilă din linia de comandă. Căutările de făcut din Chrome sunt la final. Setul „holdout-real” NU e construit (decizie Nicolas: întâi se văd hotărârile).

**Ce înseamnă „document citat”:** în aceste hotărâri instanța **parafrazează** documentele (adrese, certificate, polițe); citate literale apar rar (clauze de poliță, mențiuni din adrese). Un set de test din ele ar conține fragmente narative, nu documente complete; vezi „Ce se poate construi”.

## 1. Hotărâri utilizabile
| # | Instanță, nr., dată | Document care apare | Problema | Soluția | URL / copie |
|---|---|---|---|---|---|
| 1 | **CA București, dec. civ. 1181, 13.05.2014** (dos. 16643/299/2012) | certificatul de moștenitor (depus la un termen); cererea de plată a indemnizației de deces către bancă (RBS România); notificările băncii către asigurat/coasigurat; art. 7 din contractul de asigurare | Asigurătorul refuză indemnizația de deces la credit; discuție: calitatea procesuală (cocontractant în contractul de credit, ulterior moștenitor), asigurătorul trebuia să verifice starea de sănătate sau își asumă riscul pe declarația asiguratului | Recurs al asigurătorului **respins**; asigurătorul datorează indemnizația băncii | https://legeaz.net/spete-drept-comercial-curtea-de-apel-bucuresti-2014/pretentii-decizia-1181-2014-13-05-2014-yux · `cab-1181-2014-anon.txt` |
| 2 | **CA Cluj, dec. civ. 491/2013** (recurs; sent. 5899/27.03.2013 Jud. Cluj-Napoca) | cererea și **certificatul de asigurare** de viață de grup „Asicredit” (clauze citate: pct. 1 lit. a – asigurătorul plătește beneficiarului soldul creditului + dobânda; pct. 2.1 lit. b – excludere pentru condiție preexistentă ascunsă); chestionar medical; certificat constatator al decesului; adresa băncii cu soldul | Asigurătorul invocă excluderea (afecțiune cardiacă); coasiguratul achitase deja banca (10.462,36 lei sold + 2.789,81 lei dobânzi/comisioane) | Recurs al asigurătorului **respins**: excluderea nu operează (nu s-a probat că asiguratul știa) | https://legeaz.net/spete-comercial-litigii-profesionisti-cluj-2013/decizia-civila-491-2013-cluj-zg4 · `cluj-dc-491-2013-anon.txt` · notă: apare „M. Ștefan” (inițială + prenume), anonimizare parțială |
| 3 | **ÎCCJ, Secția a II-a civ., dec. 2291, 06.06.2013** (dos. 702/30/2012) | **certificat de calitate de moștenitor** (BNP, 21.12.2009), certificat de asigurare de grup atașat unui leasing, certificat de deces | Asigurătorul refuză contravaloarea poliței (101.767,07 RON) pentru boală preexistentă; moștenitoarea câștigase în fond | Recursul asigurătorului declarat **nul** (art. 302¹ lit. c C.proc.civ.): rămâne obligația de plată | https://legeaz.net/spete-civil-iccj-2014/decizia-2291-2013 · `iccj-2291-2013-anon.txt` · caz de leasing, nu credit bancar |
| 4 | **CA Cluj, dec. (comercială) 64/2014** (apel; sent. 5149/2013) | **adresa nr. C134/13.07.2012** a asigurătorului: dosarul de daună respins pentru reziliere (rata 2 neplătită, art. 10 lit. b, c) ; adresa băncii nr. 4007/24.12.2013 (creditele rambursate ⇒ cesiunea despăgubirii încetată) | Asigurare de bunuri (incendiu), cu despăgubirea **cesionată băncii**; cine are calitatea procesuală când banca nu mai e creditor | Apel **admis în parte** (art. 297 C.proc.civ.), acțiune respinsă pe lipsa procedurii prealabile la rezoluțiune | https://legeaz.net/spete-comerciale-ca-cluj-2014/contract-asigurare-credit-ipotecar-64-2014 · `cluj-ca-64-2014-anon.txt` · marginal: nu e viață |
| 5 | **Trib. Neamț, hotărâre 103/AC, 19.02.2015** (apel; sent. 2513/22.11.2013 Jud. Roman) | **ordin de plată nr. 1 / 29.12.2008** (142.730 RON), notificare de tutore (26.02.2013) | Fiica defunctei cere să se aducă o sumă în masa succesorală (ieșire din indiviziune, creanță) | Respinsă: calea procesuală greșită | `partaj-103-2015-anon.txt` · marginal: bani în succesiune, nu bancă ca parte |

**Ce arată pentru agent (interpretare proprie, din cele 3 principale):** (a) refuzul asigurătorului pe „boală preexistentă” cade dacă asigurătorul nu a verificat sau clauza de excludere nu e expresă: agentul nu trebuie să trateze un refuz ca definitiv, ci îl escaladează la operator cu motivul citat (`escalation-playbook`); (b) moștenitorul are calitate procesuală față de asigurător pe baza certificatului de moștenitor/calitate: un certificat de calitate (art. 116 L. 36/1995) apare în practică; (c) notificările băncii către defunct sau coasigurat după deces (cazul 1) sunt exact problema pe care o evită blocarea la semnal DGEP.

## 2. Hotărâri cu nume în clar: anonimizate de noi (decizia Nicolas, actualizarea 2 la 055)
Descărcate în /tmp (brut șters), nume → inițiale fictive consecvente, CNP → `[CNP]`, adrese → `[adresă]`/`[localitate]`, notar/BNP → `[notar]`/`[BNP]`; păstrate instanța, nr./data, băncile și asigurătorii, sumele, datele, clauzele. Verificat cu grep pe numele din original, pe CNP (13 cifre), IBAN, e-mail, telefon, „str./bl./ap.”: zero potriviri.
| # | Hotărâre | Ce apare | Problema / soluția | Copie |
|---|---|---|---|---|
| 6 | **Trib. Specializat Cluj, sent. civ. 1739, 17.06.2013** | cererea individuală de asigurare „Optimist” + declarația medicală; contractul de credit (BRD-GSG); notificarea nr. 2 a băncii (48 h, 909,22 euro) trimisă defunctului; alegații asupra transmiterii actelor către asigurător | Indemnizația de deces (sold 52.284,04 euro + dobânzi) neplătită peste 10 luni; asigurătorul invocă declarația medicală netransmisă de bancă; soțul/moștenitoarea vs. calitatea procesuală | **anonimizat de noi (instanța a lăsat nume în clar)** · `cluj-sc-1739-2013-anon.txt` |
| 7 | **CA București, dec. civ. 1252, 17.12.2014** (dos. 19680/3/2013) | 3 contracte de credit + certificate de asigurare de viață; adresa băncii nr. _/18.11.2010 (refuz comunicat moștenitorilor); chestionar medical; condiții generale (art. 8.2) | Asigurătorul nu a acceptat asiguratul și n-a informat banca/moștenitorii; contradicții în date (27.06.2008 vs. 28.10.2009); moștenitorii cer despăgubiri de la asigurător | Apelul și apelul incident **respinse** · **anonimizat de noi** · `cab-1252-2014-anon.txt` |
| 8 | **Trib. Harghita, 29.04.2014** (dos. 1670/268/2010), recurs | certificatul de moștenitor nr. 3/07.01.2010 (BNP), declarație de acceptare a succesiunii, testament, contract de împrumut cu garanție imobiliară | Anularea certificatului de moștenitor eliberat cu încălcarea drepturilor unui moștenitor; efectul asupra ipotecii acordate pe baza lui | Recurs **respins** · **anonimizat de noi** · `tr-harghita-2014-anon.txt` · relevant: banca a ipotecat pe baza unui certificat ulterior anulat |
| 9 | **Trib. Alba, dec. 839/2015** (apel) | pasivul succesoral: credite UniCredit Țiriac și Banca Românească (½ din soldul la data decesului), certificat de moștenitor/acceptare sub beneficiu de inventar | Constatarea calității de moștenitor și a masei succesorale (active + pasiv bancar) | **anonimizat de noi** · `tr-alba-839-2015-anon.txt` |

În KB ca „anonimizat de noi” și cazul 3 și cele marcate mai sus; cazurile 1–5 au fost trecute prin același script (nume reziduale: „M. Ștefan” în #2; stradă în #5).

## 3. Căutările de făcut din Chrome (ReJust, https://rejust.ro) pentru restul de 7–10
Filtre: instanță = toate; perioada 2019–2026 (după noul Cod civil, ca să reflecte certificate de moștenitor actuale).
1. „certificat de moștenitor” ȘI „extras de cont” ȘI „bancă”
2. „certificat de moștenitor” ȘI „sold” ȘI „data decesului”
3. „asigurare de viață” ȘI „credit” ȘI „deces” ȘI „refuz” (și „indemnizație”, „boală preexistentă”)
4. „împuternicit” ȘI „retragere” ȘI „după deces”
5. „comision” ȘI „defunct” (și „cont” ȘI „încetat prin deces”)
6. „secret bancar” ȘI „moștenitor” (cazurile din care a ieșit RIL 9/2024)
7. „adresă” ȘI „notar public” ȘI „bancă” ȘI „art. 81” (răspuns bancă către notar)
8. „certificat de calitate de moștenitor” ȘI „bancă”
Pentru fiecare: salvează textul (PDF/HTML) în `kb/_downloads/visi/jurisprudenta/` sau trimite-mi lista de linkuri; verific anonimizarea (nume în clar ⇒ exclusă) înainte să listez.

## Necunoscut
- Câte hotărâri relevante există pe ReJust: neinterogat; căutările de mai sus nu au rulat.
- Dacă vreo hotărâre reproduce **literal** un certificat de moștenitor sau o adresă a notarului către bancă: în cele 5 citite, nu (doar parafrază și clauze).
- Textul oficial al hotărârilor (portal.just.ro): inaccesibil (403).

## Ce se poate construi (dacă Nicolas confirmă)
Din cele 5: fragmente narative și 2–3 clauze citate (poliță de grup, adresă de respingere C134/13.07.2012). Utile doar ca **teste negative** (extractorul trebuie să dea tip `unknown`/încredere mică pe text care nu e document) și pentru câteva câmpuri (număr adresă, dată, decizie `refused`). Pentru teste pozitive complete trebuie hotărâri din ReJust cu text citat literal.
