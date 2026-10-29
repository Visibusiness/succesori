Sursă: https://www.deathnotificationservice.co.uk/ ; https://www.thegazette.co.uk/all-notices/content/101518 ; https://www.which.co.uk/news/article/new-service-notifies-banks-of-a-loved-ones-death-with-a-single-click-abrpG1B3FUrn ; https://dwpdigital.blog.gov.uk/2020/07/17/100-coverage-an-increase-in-online-users-and-award-nominations-for-tell-us-once ; https://www.uktech.news/news/deathtech-startup-settld-scores-500k-to-reduce-end-of-life-admin-stress-for-grieving-families-20210602 ; https://www.empathy.com/blog/empathy-expands-into-banking ; https://www.lightico.com/blog/bereavement-in-banking-how-to-fix-a-highly-sensitive-journey-in-financial-services/ ; https://uokik.gov.pl/en/Download/1971 (copie: kb/_downloads/marius/uokik-banki-spadkobiercy.docx) · Accesat: 2026-10-28 · Owner: TECH

# Produse similare: ce există, ce preluăm, prin ce diferim

Pentru pitch (slide-ul „de ce noi” și slide-ul de Faza 2 „hub extern”). Concluzia pe scurt:
**în lume există servicii care *anunță* decesul (notificare unică) și servicii care *digitalizează formularele*
moștenitorilor. N-am găsit niciunul care să *ducă dosarul în interiorul băncii* până la plată, cu calcul
determinist pe cote și cu excepțiile legale tratate explicit.** Acolo stă originalitatea noastră.

Citatele sunt în engleză, ca în sursă. Cifrele fără sursă primară sunt marcate *(secundar)*.

## 1. UK Death Notification Service (DNS)
- **Ce face:** un singur formular online prin care familia anunță decesul la mai multe bănci deodată. Gazette:
  „a new, free service”. Formularul cere numele, data nașterii, data decesului, ultima adresă și, opțional,
  nr. certificatului de deces. „The notifier will be contacted by the individual institutions regarding next steps
  within 10 days.” Site-ul DNS: dacă defunctul nu are cont la o instituție, aceasta nu răspunde.
- **Cine îl operează / plătește:** e creat de „UK Finance and the major banks” (Gazette), iar site-ul trimite la
  Equiniti. E gratuit pentru familie; costul îl suportă instituțiile membre (modelul exact de taxare nu e public).
- **Volum:** la lansare (Which?, 28 iunie 2018) erau 6 grupuri bancare: Barclays, HSBC UK, RBS, Santander UK,
  Lloyds, Nationwide. Ulterior Gazette scrie de „16 organisations … so far”. *(secundar)* UK Finance ar fi estimat
  la lansare ~85% din piața de conturi curente și ~900.000 de notificări/an; un ghid terț dă >600.000 de notificări
  până în 2024. Pagina UK Finance nu s-a putut citi pe 2026-10-28.
- **Limite:** Which?: „only covers the banks mentioned above”; e nevoie în continuare de probate (echivalentul
  certificatului de moștenitor); instituția răspunde în 10 zile. **Doar notifică; nu calculează, nu plătește, nu
  urmărește dosarul.**
- **Ce preluăm:** modelul de **hub** pentru Faza 2. Un singur punct de intrare pentru familie/notar/DGEP, banca
  primește notificarea, iar datele și calculele rămân în bancă. E exact `DEPLOYMENT_MODE=hub` din BRIEF.
- **Prin ce diferim:** DNS se oprește unde începem noi. Agentul nostru preia notificarea și execută pașii băncii:
  blocare reversibilă, stornare comisioane, răspuns la notar, daună, cote, plan de plată cu aprobare umană.

## 2. Tell Us Once (GOV.UK, DWP)
- **Ce face:** anunță decesul o singură dată la instituțiile statului: HMRC, DVLA, HM Passport Office,
  administrația locală și unele fonduri de pensii publice. DWP: „Up to 30 different services can be notified.”
  Funcționează pe baza referinței primite de la registratura de stare civilă. **Nu** anunță firme private (deci
  nici băncile).
- **Cine plătește:** statul. E gratuit și voluntar pentru familie.
- **Volum / efect:** DWP (iulie 2020): „100% population coverage in March 2020”; folosirea online a crescut
  „from around 40% … to over 80%”; „annual savings of over £20m”.
- **Ce preluăm:** argumentul că **semnalul de stare civilă e sursa cea mai timpurie și mai sigură**. E analogul
  semnalului DGEP din demo (doc 1) și justifică freeze-ul reversibil la primul semnal.
- **Prin ce diferim:** Tell Us Once e pentru stat; noi suntem în bancă. În România nu există un „Tell Us Once”.
  Fluxul DGEP→bănci (vezi `kb/bank-procedures/dgep-arb-acord.md`) e cel mai apropiat, iar agentul nostru îl
  consumă.

## 3. Settld și Life Ledger (UK, „deathtech” pentru familii)
- **Ce fac:** platforme online unde familia introduce o dată datele defunctului și lista furnizorilor, iar
  platforma îi anunță pe toți. Settld (UKTN, 2 iunie 2021): „notifies all identified Service Providers of death in
  one go to close, freeze and transfer accounts”; Settld a fost ulterior preluată de The Estate Registry
  *(secundar)*. Life Ledger acoperă bănci, utilități, pensii și asigurări: *(secundar)* 650 → 750 → „peste 1.000”
  de organizații, după sursă.
- **Cine plătește:** familia nu plătește. Settld: „free to the public”. Life Ledger percepe *(secundar)* doar
  £12/an pentru păstrarea unui „life record”. Venitul vine probabil de la organizațiile receptoare și din
  consultanță, dar **niciun izvor nu confirmă modelul B2B**.
- **Volum:** Settld a strâns £500k seed (SFC Capital, 2021). Nu am găsit cifre publice de dosare.
- **Ce preluăm:** UX-ul pentru moștenitor: o singură listă a ce lipsește, starea vizibilă și fără să repete
  informația. În ops-ui asta e secțiunea „Ce lipsește”; în Faza 2, portalul pentru moștenitor.
- **Prin ce diferim:** ele stau **în afara** băncii și se opresc la notificare; banca rămâne cu munca manuală.
  Noi automatizăm partea grea și repetitivă **din interiorul** băncii, adică exact tema Raiffeisen „Operational
  Efficiency”.

## 4. SUA/Canada: Empathy și Lightico („bereavement” pentru bănci și asigurători)
- **Empathy:**
  - Ce face: aplicație de sprijin după deces, cu ghiduri, ajutor la acte și beneficii, plus suport emoțional.
    Lucrează mai ales cu asigurători (ex. BMO Insurance).
  - Prima bancă: TD (Canada), anunțată pe 12 noiembrie 2025. TD a integrat Empathy „into its estate settlement
    services”; clienții TD Estates primesc „help with paperwork and benefits”.
  - Cine plătește: partenerul (banca/asigurătorul) îl oferă clienților. Postarea nu dă prețul și nici volume.
- **Lightico:**
  - Ce face: platformă SaaS pentru bănci care „digitize[s] the entire bereavement process from notification to
    closure”. Executorul primește un link (SMS/e-mail), își verifică identitatea cu selfie + act, încarcă
    documente, completează formulare precompletate și semnează electronic.
  - Validarea documentelor: „IDP technology” verifică doar că documentele sunt „complete, unexpired, and
    legible”. Operatorul are un „Case Manager” cu cronologia dosarului.
  - Implementare: „typically go live in under six weeks”. Lightico nu publică cifre de rezultat. Durerile pe care
    le citează sunt aceleași ca la noi: „Repeating the same information across multiple departments”, „Unclear
    timelines”, „Delays in paying urgent expenses like funeral costs”.
- **Ce preluăm:**
  - de la Lightico: argumentul că **procesul e rar per bancă, dar scump** („Low volume relative to onboarding”,
    „No clear product owner across departments”). Un agent care închide cap-coadă e mai ieftin decât un proiect
    de digitalizare per departament;
  - cronologia dosarului pentru operator (o avem în ops-ui, cu regula aplicată la fiecare acțiune).
- **Prin ce diferim:**
  - Lightico **colectează** documente și verifică că sunt lizibile. Nu înțelege certificatul de moștenitor, nu
    calculează cote și nu decide pașii;
  - Empathy e sprijin pentru familie, nu operațiune bancară;
  - noi extragem câmpurile cu scor, validăm determinist (CNP, suma cotelor = 1, produse ⊂ produsele clientului),
    calculăm sumele în bani cu funcții pure testate și lăsăm omului doar plata și excepțiile.

## 5. Europa Centrală și de Est
- **Polonia: UOKiK, 15 iunie 2026 (sursă primară, copie în `kb/_downloads/marius/`).** Autoritatea pentru
  protecția consumatorilor a analizat procedurile pentru moștenitori la 11 bănci: Alior, Millennium, Pekao, BNP
  Paribas, Credit Agricole, ING Bank Śląski, mBank, PKO BP, Santander Bank Polska (acum Erste), Santander Consumer,
  VeloBank. Plângerile tipice:
  - „protracted procedures, requests for additional documents, delays in payments, and unfavourable rules regarding
    the inheritance of loan debts”;
  - „requirements for all heirs to appear in person at a single location and time”;
  - credite declarate scadente imediat la aflarea decesului, cu costuri suplimentare.
  Cauza identificată: „the lack of clear and uniform standards for handling inheritance cases, as well as
  insufficient staff training”. UOKiK a emis „soft calls”, adică așteaptă de la bănci procedurile simplificate și
  informarea clară. **E cea mai puternică dovadă din regiune că problema e sistemică și că regulatorul o urmărește.**
  Durerile coincid cu cazurile românești din `kb/bank-procedures/cazuri-reale.md` (Bragadiru 2023, prezența
  simultană a moștenitorilor).
- **Ungaria:** Raiffeisen HU și UniCredit HU publică note de informare pentru cine anunță decesul și liste de
  documente, adică proceduri pe hârtie. N-am găsit automatizare.
- **Estonia (Coop Pank), Slovenia (OTP banka):** pagini de informare și formulare de notificare, fără procesare
  automată a dosarului.
- **România:** n-am găsit niciun produs de tip DNS/Lightico la băncile românești. Ghidurile băncilor sunt liste de
  documente (vezi `kb/bank-procedures/alte-banci-deces.md`).

## Harta poziționării (pentru slide)
| | Notifică | Colectează documente | Înțelege documentul (extracție) | Calculează sume pe cote | Urmărește termene și excepții | În interiorul băncii |
|---|---|---|---|---|---|---|
| UK DNS | ✔ | — | — | — | — | — (hub) |
| Tell Us Once | ✔ (doar stat) | — | — | — | — | — |
| Settld / Life Ledger | ✔ | parțial | — | — | — | — |
| Empathy | — | ghidaj | — | — | parțial (pentru familie) | — |
| Lightico | ✔ | ✔ | doar „lizibil/complet” | — | cronologie | ✔ (SaaS) |
| **Moștenirea (noi)** | ✔ (DGEP, notar, familie) | ✔ | ✔ cu scor + validări deterministe | ✔ funcții pure, în bani | ✔ (opțiune 1 an, daună 30 zile, minor, supliment) | ✔ (Faza 1) + hub (Faza 2) |

## Necunoscut
- Volumul actual al DNS: cifrele de 900k/an și >600k cumulate vin din surse secundare. Pagina UK Finance nu s-a
  putut citi.
- Modelul de taxare B2B la DNS, Settld, Life Ledger, Lightico: nu e public.
- Rezultatul intervenției UOKiK (ce au schimbat băncile poloneze) după iunie 2026.
- Dacă vreo bancă din România sau din grupul Raiffeisen (RBI) are un pilot intern similar. N-am găsit nimic
  public; de întrebat mentorii.

## Ce înseamnă pentru agent
- Diferențiatorul de pitch e „cap-coadă în bancă”: extracție + validare deterministă + calcul + excepții, cu om
  doar la plată. Nimeni din listă nu face calculul pe cote și nici urmărirea termenelor legale.
- Faza 2 (hub) are un precedent real și funcțional: UK DNS (gratuit pentru familie, plătit de bănci, operat de un
  terț). Asta face slide-ul credibil.
- Durerile citate de UOKiK și Lightico sunt cazuri de test pentru noi: documente cerute din nou (dosar unic,
  idempotent), prezența tuturor moștenitorilor (plan per moștenitor, partea minorului blocată separat), credit
  declarat scadent imediat (răspundere în limita activului + dauna de asigurare înainte de orice recuperare).
