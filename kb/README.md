Sursă: generat de noi (BRIEF.md §5.2, completat de master) · Accesat: 2026-10-28 · Owner: LEAD

# KB: ierarhia de documente pentru agentul de succesiune

Fiecare fișier `.md` din KB începe cu linia `Sursă: <URL> · Accesat: <dată> · Owner: <ROL>`.
Prioritate: **P0** = fără el nu merge demo-ul · **P1** = pentru juriu (domeniu, business) · **P2** = completare.
Owner: Nicolas (LEAD) · Visi (DOMAIN) · Ștefan (DOCS) · Marius (TECH). Când owner-ul nu e online, face master-ul.
Sarcina care produce fișierul e în `docs/TASKS.md` (coloana Nr).

```
kb/
├── README.md                              # acest fișier · LEAD · P0
├── glosar.md                              # termeni RO/EN (cod, pitch): succesiune, opțiune succesorală, cotă, supliment… · generat de noi · LEAD · P1
│
├── scenariu-demo/                         # LEAD + DOCS
│   ├── maria-ionescu.md                   # datele fixe ale demo-ului + VALORILE AȘTEPTATE calculate de mână (sold la deces, dobândă,
│   │                                      #   comisioane de stornat, pensie post-deces, net pe moștenitor) → devin teste în Faza 1 · generat de noi · Nicolas · P0
│   └── documente-demo.md                  # cele 7 documente, în ordine: ce conțin, ce trebuie să facă agentul la fiecare, excepția tratată · generat de noi · Ștefan · P0
│
├── legal/                                 # DOMAIN · Visi
│   ├── cod-civil-succesiuni.md            # art. 1100–1163 (deschidere, opțiune 1 an, acceptare), 1114 (datorii, limita activului),
│   │                                      #   2030 (încetarea mandatului la deces), 2187 și urm. (cont curent/co-titulari) · legislatie.just.ro (Legea 287/2009) · Visi · P0
│   ├── mostenitor-minor.md                # minor 14–18 ani: acceptare, încasare sume, autorizarea instanței de tutelă (C.civ. art. 41, 144–146, 501 etc.) · legislatie.just.ro · Visi · P0
│   ├── legea-pensiilor-deces.md           # pensia lunii decesului, sume virate după deces, restituirea către CNPP (Legea 360/2023; 127/2019 abrogată) · legislatie.just.ro, cnpp.ro · Visi · P0
│   ├── testament-mostenire-testamentara.md # testament, rezervă, cotitate disponibilă; varianta B a demo-ului (D1) · legislatie.just.ro · Visi · P0
│   ├── cod-civil-regim-matrimonial.md     # comunitate de bunuri, cont pe numele unui soț, partea soțului supraviețuitor (art. 339 și urm., 970–974) · legislatie.just.ro · Visi · P1
│   ├── procedura-succesorala-notar.md     # Legea 36/1995 + regulament: ce cere notarul de la bancă, certificat, supliment (art. 101 și urm.) · legislatie.just.ro, uniunea notarilor · Visi · P1
│   ├── secret-bancar.md                   # OUG 99/2006 art. 111–113: cui poate răspunde banca (notar, moștenitori) · legislatie.just.ro · Visi · P1
│   ├── gdpr-decedati-mostenitori.md       # GDPR cons. 27 (nu se aplică decedaților), Legea 190/2018, datele moștenitorilor · eur-lex, dataprotection.ro · Visi · P1
│   ├── aml-kyc-mostenitori.md             # Legea 129/2019: identificarea moștenitorilor/împuterniciților la plată · legislatie.just.ro · Visi · P1
│   ├── termene-si-prescriptie.md          # tabel unic al termenelor: opțiune 1 an, răspuns către notar, daună asigurare, prescripție · din fișierele de mai sus · Visi · P1
│   └── outsourcing-bnr-eba-dora.md        # Reg. BNR 5/2013, EBA GL outsourcing, DORA (Reg. UE 2022/2554) pentru slide-ul „hub extern” · bnr.ro, eba.europa.eu · Visi · P2
│
├── bank-procedures/                       # DOMAIN · Visi
│   ├── raiffeisen-cgb-pf-extras.md        # CGB PF feb 2024: 3.2, 5.10.4 c, orice clauză cu deces/împuternicit/moștenitor/inactiv · PDF raiffeisen.ro (BRIEF §8) · Visi · P0
│   ├── raiffeisen-tarife-produse.md       # comision pachet (Premium), depozit la termen (dobândă, lichidare anticipată), credit nevoi personale +
│   │                                      #   asigurare de viață atașată (asigurător, acoperire) · raiffeisen.ro (pagini publice + lista tarife) · Visi · P0
│   ├── raiffeisen-deces-ghid.md           # ce cere Raiffeisen public la deces (pagini, FAQ, call-center) · raiffeisen.ro · Visi · P1
│   ├── asigurare-viata-credit.md          # declanșare daună, documente, termene, excluderi, cine e beneficiar (banca) · site-uri asigurători · Visi · P0
│   ├── dgep-arb-acord.md                  # ce date trimite DGEP băncilor (data decesului), de când, frecvență · brd.ro, ing.ro, arb.ro · Visi · P1
│   ├── alte-banci-deces.md                # BT, BCR, ING, BRD: liste de documente, termene, comparativ · site-urile băncilor · Visi · P1
│   └── cazuri-reale.md                    # Bragadiru 2023, avocatnet, manager.ro, dcbusiness: URL + citat · BRIEF §8 · Visi · P1
│
├── document-templates/                    # DOCS · Ștefan (fără date personale reale; exemple fictive)
│   ├── certificat-deces.md                # câmpuri, aspect, serie/număr, cine emite · Ștefan · P0
│   ├── adresa-notar-catre-banca.md        # formulare tipice, ce cer exact (sold la data decesului, produse, dobândă) · Ștefan · P0
│   ├── raspuns-banca-catre-notar.md       # documentul GENERAT de agent: structură, ce conține, cine semnează · generat de noi pe baza practicii · Ștefan · P0
│   ├── certificat-mostenitor.md           # structură, masa succesorală, cote, supliment (certificat suplimentar) · Ștefan · P0
│   ├── polita-asigurare-viata.md          # câmpurile relevante pentru credit (asigurat, beneficiar, sumă, excluderi) · Ștefan · P0
│   ├── cerere-eliberare-sume.md           # ce semnează moștenitorii la bancă, IBAN, act identitate · Ștefan · P1
│   ├── procura-notariala.md               # obiect, limite, verificare în RNNEPR, revocare · Ștefan · P2
│   └── hotarare-judecatoreasca.md         # când înlocuiește certificatul (partaj, sentință), ce câmpuri · Ștefan · P2
│
├── data/                                  # DOCS · Ștefan
│   ├── ins-decese.md                      # decese lunare 2024–2025 · insse.ro / tempo-online · Ștefan · P1
│   ├── raiffeisen-cifre.md                # clienți, cotă de piață, angajați, rețea · rapoarte anuale raiffeisen.ro · Ștefan · P1
│   └── estimare-volum-cost.md             # dosare/an, interacțiuni, ore, cost; ipoteze explicite, „(estimare proprie)” · generat de noi · Ștefan · P1
│
├── tech/                                  # TECH · Marius
│   ├── api-contract-bank.md               # cele 6 endpoint-uri: freeze, products-at-date, fees/reverse, payment-plan, payments, cases · generat de noi · Marius · P0
│   ├── claude-tool-use-notes.md           # orchestrare cu tool use, schema de extracție cu scor de încredere, prag de escaladare · docs.anthropic.com · Marius · P0
│   ├── document-extraction-approach.md    # PDF text vs scan, OCR, validare pe schemă, document ilizibil → escaladare · Marius · P1
│   ├── dgep-integration.md                # ce știm despre interfața reală (RNEP), ce mock-uim · Marius · P1
│   └── similar-products.md                # UK Death Notification Service, Tell Us Once, Settld, Lightico · Marius · P2
│
└── _downloads/<nume>/                     # originale (PDF/HTML), doar citite, niciodată rulate; nu se șterge nimic
```

## Reguli (din BRIEF §5.3)
- Fără linie de sursă = nu intră în KB. Citate textuale în română, cu articolul/clauza; nu parafrazăm legi.
- Ce nu găsim: secțiunea `## Necunoscut` cu ce am încercat.
- Cifrele proprii se marchează `(estimare proprie)` cu ipotezele.
- Fiecare fișier se termină cu `## Ce înseamnă pentru agent`: regula/decizia concretă care intră în cod.
