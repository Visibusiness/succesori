Sursă: măsurători din 2026-10-28 (`runs/scala/*.json`, scripturile `scripts/scala_*.py`), ținta din `kb/data/estimare-volum-cost.md` și `kb/data/ins-decese.md`, costul din `docs/pitch/cost-per-dosar.md` · Cifrele, pentru ecranul Rezultate: `docs/scalabilitate.json` · Owner: bedrock-scala (083)

# Scalabilitate: ce duce sistemul azi și ce lipsește până la producție

Toate măsurătorile s-au făcut pe o singură mașină virtuală (6 vCPU, 16 GB), aceeași pe care rulează MVP-ul și sesiunile echipei. Modelul a fost Sonnet 5.5 pe Bedrock (us-west-2).

## Ținta (estimare proprie, din INS și cota de clienți)
| Scenariu | Dosare/an | Documente/an (× 7) | Documente/oră lucrătoare (2.000 h/an) | **Vârf × 5** | Lot DGEP pe săptămână (luna de vârf INS, × 5) |
|---|---|---|---|---|---|
| Prudent (7%) | 16.800 | 117.600 | 59 | 294 | 380 (1.902) |
| Central (10%) | 24.000 | 168.000 | 84 | 420 | 543 (2.717) |
| Optimist (14%) | 33.600 | 235.200 | 118 | **588** | 761 (**3.804**) |

Semnalul DGEP vine ca fișier structurat și nu trece prin LLM. Ținta pentru AI e deci **504 documente/oră** (6 documente pe dosar, scenariul optimist, × 5).

## Ce am măsurat
**1. Logica, fără LLM** (`scala_logic.py`). Pipeline-ul rulează în proces, cu N clienți clonați după Maria Ionescu și câte 7 documente pre-extrase pe dosar, trimise pe pași, ca un lot DGEP urmat de poștă. Fiecare dosar ajunge la `PAYMENT_PENDING_APPROVAL`, cu escaladarea `minor_heir` ca în demo. Nu a apărut nicio eroare.

| Dosare | Documente | Timp total | Dosare/s | µs/document | RSS |
|---|---|---|---|---|---|
| 1.000 | 7.000 | 0,76 s | 1.321 | 108 | 58 MB |
| 10.000 | 70.000 | 46 s | 217 | 658 | 409 MB (≈ 40 KB/dosar) |

Timpul per document **crește liniar cu numărul de dosare deschise**, deci costul total crește cu pătratul lor. Profilul arată de ce: 64% din timp se duce în căutări liniare (`Pipeline._case_for` și `Bank.find_customer` parcurg toți clienții și toate dosarele). Cu 33.600 de dosare deschise ar fi ≈ 2 ms/document, adică lotul DGEP de vârf × 5 în ≈ 8 s. Ține, dar e efectul mock-ului, nu un design de producție: o bază de date cu index îl elimină.

**2. API-ul, fără LLM** (`scala_api.py`). Cererile au fost `POST /documents` pe o instanță de test (:8060, cu autopilotul oprit), câte 1.400 de cereri pe nivel și un reset la fiecare 70 de cereri, ca dosarul să rămână de mărime reală.

| Clienți simultani | Cereri/s | p50 | p95 | p99 | Erori |
|---|---|---|---|---|---|
| 1 | 205 | 4,5 ms | 7,9 ms | 9,0 ms | 0 |
| 10 | 152 | 53 ms | 146 ms | 282 ms | 0 |
| 50 | 140 | 271 ms | 616 ms | 709 ms | 0 |

Concurența nu crește debitul: un singur proces uvicorn și GIL-ul serializează cererile, iar latența crește doar din coadă. Un dosar cu 700 de documente coboară debitul la 32 cereri/s (p50 de la 5 la 62 ms), pentru că tot dosarul e rescris pe disc la fiecare document. **Fără lock, starea se strică** (`scala_race.py`): două fire care primesc documentele a 10.000 de clienți noi au pierdut **1.419 din 20.000 de documente (7%)**, cu 1.409 excepții `dictionary changed size during iteration`. API-ul rulează endpoint-ul sincron într-un pool de fire fără lock, deci aceeași cursă poate apărea la documente simultane pentru clienți noi. În testul HTTP nu a apărut: toate documentele mergeau la același dosar, deja existent.

**3. AI-ul, extracție pe Bedrock** (`scala_ai.py`). Am folosit 20 de documente (7 din demo, 10 grele, 3 PDF citite vizual) și am setat `EXTRACT_RETRIES=0`, ca orice eșec să fie numărat. Testul a rulat o singură dată.

| Concurență | Documente/oră | Latență p50 (max) | Erori / throttling | Tip corect | $/document |
|---|---|---|---|---|---|
| 1 | 471 | 7,0 s (10,9) | 0 / 0 | 20/20 | 0,050 |
| 5 | 2.284 | 7,0 s (13,7) | 0 / 0 | 20/20 | 0,046 |
| 10 | 2.928 | 9,1 s (17,0) | 0 / 0 | 20/20 | 0,051 |
| 20 | **4.357** | 11,0 s (16,5) | 0 / 0 | 20/20 | 0,050 |

Rezerva: la concurența 20 sunt 20 de documente într-un singur val, deci debitul e măsurat pe un eșantion mic. O rulare lungă poate lovi cota de tokeni/minut a contului Bedrock, pe care nu am atins-o. Fiecare apel pornește acum un proces `claude -p` de ≈ 250 MB.

## Concluzie
**Logica duce 217–1.321 de dosare/s, iar API-ul 140–205 documente/s. AI-ul duce 4.357 de documente/oră la concurența 20 (2.284 la concurența 5). Ținta e 504 documente/oră cu LLM la vârf × 5 (optimist), deci rezerva e de ≈ 8,6×**. Un singur apel odată (471/oră) aproape atinge ținta, iar la concurența 5 rezerva e deja de 4,5×. Ce limitează nu e calculul, ci agenții: ≈ 8 minute de model pe dosar (`cost-per-dosar.md`) × 84 de dosare/oră la vârf înseamnă ≈ 11 apeluri de agent simultane. Concurența 20 a mers fără throttling, dar nu am testat-o pe ore.

## Costul la scară (2,35 $/dosar măsurat; interval 1,4–2,4 $; ≈ 1 $ optimizat; 1 $ = 4,5 lei)
| Scenariu | Dosare/an | Măsurat | Interval | Optimizat |
|---|---|---|---|---|
| Prudent | 16.800 | 39.480 $ ≈ 178k lei | 23,5–40,3k $ | 16.800 $ |
| Central | 24.000 | 56.400 $ ≈ 254k lei | 33,6–57,6k $ | 24.000 $ |
| Optimist | 33.600 | 78.960 $ ≈ 355k lei | 47,0–80,6k $ | 33.600 $ |

## Limitele de azi și drumul spre producție (efort: estimare proprie, persoană-săptămâni)
| Limită azi | Ce se întâmplă | În producție | Efort |
|---|---|---|---|
| Stare în memorie (dosare, mock core, chei de idempotență) | o repornire pierde toate dosarele | Postgres: dosare, evenimente append-only, documente; index pe CNP și pe nr. de dosar (dispar și căutările liniare și rescrierea dosarului pe disc) | 3 |
| Un singur proces API, fără lock | debit plafonat la ≈ 200/s; cursa măsurată pierde documente | imediat: un lock pe `pipeline.receive` (≈ o zi). Apoi API fără stare în spatele unui load balancer, tranzacție cu blocare pe client (CNP) | 2 |
| Autopilot secvențial, un singur inbox, interogare la 5 s | documentele și agenții merg unul după altul | coadă de mesaje pentru documente + worker-pool pentru agenți, cu limită de concurență (20 măsurat) | 2 |
| Eșecul unui apel AI | extracția: 2 reîncercări (4 s, 8 s), apoi documentul devine `unknown` și ajunge la operator ca ilizibil (sigur, dar automatizarea se pierde); agenții: timeout 180 s, artefact cu eroarea | reîncercare din coadă cu backoff și jitter, dead-letter queue; la throttling, documentul se reprogramează, nu se escaladează | 1 |
| Idempotență (cheia tip + referință + data decesului există deja) | reluările sunt sigure, dar numai cât trăiește procesul | aceeași cheie, persistată în Postgres (constrângere unică) | inclus |
| Lotul DGEP | azi câte un document per semnal | procesare incrementală a fișierului SFTP săptămânal, cu checkpoint pe linie (fără LLM) | 1 |
| `claude -p` per apel | ≈ 250 MB pe apel, plus promptul de sistem al Claude Code | apel direct la API (Bedrock), cu caching pentru prompturile agenților | 1 |

**Total ≈ 10 persoană-săptămâni** (2–3 ingineri, ≈ o lună), fără integrarea reală cu core-ul și cu DGEP, care depinde de bancă.
