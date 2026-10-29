# real-text: set de test din text real (064: 01–11, 074: 12–40)

Pasaje copiate din surse reale, publice, descărcate în `kb/_downloads/` (în afara git; vezi `kb/_downloads/realsurse/INDEX.md`).
Nimic nu e inventat. Câmpurile necompletate („..........”, „CNP...”) și inițialele puse la anonimizare (de sursă sau de
noi) au rămas cum erau. Ground truth-ul din `.mvp.json` are forma din `agent/demo_documents.py`: fiecare câmp care nu
apare literal în text e `null`.

**Setul nu face parte din `train`.** retro-learner nu îl vede: `scripts/retro.py` îi interzice explicit
`registries/documents/real-text/` și `runs/eval-real-text*.json`. Rulare:
`.venv/bin/python scripts/eval_extract.py --set real-text`. Rezultatul se scrie în `runs/eval-real-text-latest.json`.

Ce măsoară setul. Pe documentele noastre sintetice, toate câmpurile sunt completate. Aici, în schimb, documentele sunt
reale, dar parțiale sau necompletate. Extractorul trebuie să recunoască tipul, să lase `null` ce nu scrie în text
(nu are voie să ghicească) și să rămână sub pragul de 0,80, pentru că lipsesc câmpurile obligatorii. Așteptăm deci
`confidence` 0,5. Testele negative sunt texte care vorbesc despre documente, dar nu sunt documente. Pentru ele
așteptăm `unknown`, sub prag (0,3), și niciun câmp scos din conversație.

## Documente (text real de document)

| Fișier | Tip | Sursa exactă | Observații |
|---|---|---|---|
| `01-adresa-notar-extras-cont` | notary_request | `realsurse/forum/notaripro-supliment-mostenire.txt`, răspunsul oficial al Notariatului Professio din 07-06-2014 (https://notari.pro/forum-notarial/succesiune-mostenire/1972-supliment-mostenire) | Modelul real de adresă a notarului către bancă (extras de cont pentru netitular), cu datele lăsate „...”. Am păstrat doar adresa, de la „CĂTRE,” la „NOTAR PUBLIC,”. Nu are CNP, nr. de dosar sau termen, deci e sub prag. |
| `02-certificat-mostenitor-anexa17-necompletat` | heir_certificate | `realsurse/forme/anexa17-certificat-mostenitor.txt`: Anexa 17 la Regulamentul Legii 36/1995 (Ordin MJ 2333/C/2013), https://notari.pro/docs/regulament-legea-36-ordin-2333-2013.pdf | Modelul oficial necompletat, textul integral. Câmpurile sunt toate goale (`heirs`, `testament`, `ibans` sunt `null`). |
| `03-formular-groupama-anunt-eveniment` | unknown | `realsurse/forme/Groupama-formular-anuntare-eveniment-funeral.pdf` (https://www.groupama.ro/wp-content/uploads/2026/03/Formular_anuntare_eveniment_asigurat_-_funeral_martie_2023.pdf) | Formular real de avizare a daunei, necompletat. Pe mașină nu există pdftotext, așa că textul a fost decodat cu hărțile ToUnicode din PDF (script stdlib, în afara repo-ului). Ce n-a putut fi decodat e marcat `[…]`. Am oprit textul înainte de secțiunea F (GDPR). Tipul e `unknown` pentru că avizarea daunei (cerere către asigurător) nu e în vocabular: nu e `insurer_response`. |
| `04-certificat-persoana-asigurata-citat` | insurance_certificate | `visi/jurisprudenta/cab-1252-2014-anon.txt`: CA București, Decizia 1252/2014, citat între ghilimele din „Certificatul pentru persoana asigurată” | Doar citatul, fără ghilimele. Asigurătorul apare anonimizat de sursă („A. –Ț. Asigurări S.A.”). Nu are CNP și nici nr. de poliție. |
| `05-contract-asigurare-credit-art4-deces` | insurance_certificate | `realsurse/jurisprudenta/CACluj-sent1739-2013-refuz-plata-asigurare-deces-credit.txt`: Trib. Specializat Cluj, Sentința 1739/2013, citatul din art. 4 al contractului de asigurare | Clauza de deces a asigurării de viață atașate creditului, cu greșelile din original („plătii”, „anunnțe”). Am ales tipul `insurance_certificate` pentru că e cel mai apropiat din vocabular: e textul poliței, nu o decizie. Pe acest punct se poate discuta. |
| `06-refuz-asigurator-motivare-citat` | insurer_response (refused) | idem, citatul cu motivarea refuzului asigurătorului („refuză să plătească indemnizația de deces, motivând că …”) | Fragment din poziția asigurătorului. Din hotărâre nu reiese clar dacă vine din scrisoarea de refuz sau din întâmpinare. `decision` = `refused`, restul câmpurilor `null`. |

## Teste negative (text real, dar nu document) → `unknown`

| Fișier | Sursa exactă | De ce e greu |
|---|---|---|
| `07-negativ-forum-intrebare-refuz-asigurare` | `realsurse/forum/avocatnet-asigurare-de-viata-pentru-credit.txt`, primul mesaj (https://www.avocatnet.ro/forum/discutie_355467/ASIGURARE-DE-VIATA-pentru-credit.html) | Autorul povestește un refuz al asigurătorului. Nu trebuie să iasă `insurer_response`/`refused`. |
| `08-negativ-forum-intrebare-sold-fara-certificat` | `realsurse/forum/notaripro-cont-bancar-pentru-succesiune.txt`, întrebarea (https://notari.pro/forum-notarial/succesiune-mostenire/5112-cont-bancar-pentru-succesiune) | Pomenește certificatul de moștenitor, contul și depozitul. |
| `09-negativ-forum-raspuns-supliment-prin-notar` | `realsurse/forum/avocatnet-mostenire-bani.txt`, întrebarea și răspunsul (https://www.avocatnet.ro/forum/discutie_873659/mostenire-bani.html) | Descrie adresa notarului și certificatul suplimentar. Am scos interfața forumului și pseudonimele utilizatorilor. |
| `10-negativ-hotarare-iccj-refuz-dosar-dauna` | `realsurse/jurisprudenta/ICCJ-dec853-2015-asigurare-viata-credit-mostenitori.txt`, un paragraf din considerente (https://legeaz.net/spete-civil-iccj-2015/decizia-853-2015-r54) | Instanța parafrazează o adresă de refuz (nr. 270/2012). E o hotărâre, nu răspunsul asigurătorului. |
| `11-negativ-hotarare-tr-alba-mostenitori-cote` | `visi/jurisprudenta/tr-alba-839-2015-anon.txt`: Tribunalul Alba, Decizia 839/2015, dispozitivul sentinței de fond redat în decizie | Seamănă cu un certificat de moștenitor: moștenitori, calități, cote (¼, 3/8). Dar e o hotărâre de partaj. |

## Ce nu a intrat
- (064) Restul formularelor PDF (NN, UNIQA, Grawe, Allianz, MetLife, Formularul V UE): decodarea a dat text fragmentat
  sau glife lipsă. În 074 au intrat, extrase cu PyMuPDF (vezi mai jos).
- Celelalte adrese din hotărâri (C134/13.07.2012, 4169/07.09.2010, adresa 1535): sunt doar parafrazate, nu citate.
- Certificatul de moștenitor nr. 3/07.01.2010 din `tr-harghita-2014-anon.txt` e descris de instanță, nu citat.

# 074: 29 de pasaje noi (12–40)

Surse noi din `kb/_downloads/realsurse/`: `notari/`, `asiguratori/`, `banci/`, plus formularele PDF din `forme/` pe care
064 nu le-a putut decoda. Textul PDF-urilor e scos cu PyMuPDF (`fitz`, din `.venv`), printr-un script ținut în afara
repo-ului, iar textul HTML vine din `*.txt`-ul deja extras de sursă. Ce am curățat: rândurile goale repetate (păstrez
unul), indentarea de un spațiu de la începutul rândului, marcajele de pagină („N/23”, „Generated by the European
e-Justice Portal”, „=== p.N ===”, antetul ING „G-04 /2026.07.30”). Listele lungi de state și de județe le-am înlocuit
cu `[…]` sau `[… lista județelor …]`. Ordinea rândurilor e cea din PDF, chiar și acolo unde PyMuPDF o amestecă (17
Generali). Restul textului e literal, inclusiv greșelile din original („Inidividual”, „subsemnatului****”). Toate
pasajele se opresc înainte de secțiunea de prelucrare a datelor personale (GDPR).

**Convenția pentru `unknown`.** Vocabularul extractorului are 7 tipuri. Formularele de avizare a daunei, declarațiile
notariale, citațiile, încheierile și clauzele contractuale nu sunt printre ele, așa că ground truth-ul lor e `unknown`,
cu `confidence` 0,3. Câmpurile punctate sunt cele pe care un extractor ar fi tentat să le umple. Toate sunt `null`,
pentru că formularele sunt necompletate, iar pentru tipul `unknown` nu există schemă din care să copiem câmpuri. Două
capcane:
- 13 conține IBAN-ul real al UNIQA din antet, deci `ibans` trebuie să rămână `null`: nu e contul defunctului.
- 23 conține o dată reală de deces („25.07.2001”). Nu am punctat `date_of_death`.

Clauzele contractuale (30–34) sunt etichetate `unknown`. La 05 (064), clauza a fost etichetată `insurance_certificate`.
Diferența e semnalată masterului în raportul 074.

## Documente în vocabular

| Fișier | Tip | Sursa exactă | Observații |
|---|---|---|---|
| `12-certificat-european-mostenitor-formular-v` | heir_certificate | `realsurse/forme/UE-formular-V-certificat-european-mostenitor-ro.pdf` (https://online-forms.e-justice.europa.eu/download-blank-pdf/ecs_e_ro): Formularul V, Regulamentul (UE) 650/2012 | Necompletat. Am păstrat antetul, secțiunile 2–3 și 6–7 (autoritatea, dosarul, defunctul, succesiunea legală sau testamentară) și Anexa IV (moștenitorii). Pentru o bancă din România, certificatul european ține loc de certificat de moștenitor. Tipul se poate discuta. |

## Documente reale în afara vocabularului → `unknown`

| Fișier | Sursa exactă | De ce e greu |
|---|---|---|
| `13-uniqa-notificare-cerere-despagubire` | `realsurse/asiguratori/uniqa-notificare-cerere-despagubire-viata-2024.pdf` (https://www.uniqa.ro/sites/default/files/2024/NOTIFICARE_ȘI_CERERE_DE_SOLICITARE_A_DESPĂGUBIRII_Vmartie_2024.pdf) | Are poliță, CNP, „Moștenitor legal”, IBAN (al asigurătorului). Seamănă cu `insurer_response`. |
| `14-uniqa-anexa-f1-cerere-despagubire-deces` | `realsurse/forme/UNIQA-anexaF1-cerere-despagubire-deces-RAIB-2024.pdf` (https://www.uniqa.ro/sites/default/files/2024/Anexa%20F1%20-%20Cerere%20de%20despagubire%20%C3%AEn%20caz%20de%20daun%C4%83%20RAIB_Vmartie%202024.pdf) | Pomenește de mai multe ori „Certificatul de asigurare”. Seamănă cu `insurance_certificate`. |
| `15-nn-ing-formular-f01-anunt-eveniment` | `realsurse/asiguratori/ing-notificare-eveniment-asigurat.pdf` (https://www.ing.ro/dam/ingro/doc/notificare-eveniment.pdf) | Formularul F01 NN/ING: cont de credit, contract de asigurare, persoană de contact la deces. |
| `16-allianz-chestionar-deces` | `realsurse/asiguratori/allianz-chestionar-2-dauna-deces.pdf` (https://www.allianztiriac.ro/content/dam/onemarketing/cee/azro/documente/b)-daune/viata/Chestionar_2_Dauna_de_tip_Deces.pdf) | Întrebările despre deces (autopsie, alcoolemie) seamănă cu un certificat de deces. |
| `17-generali-declaratie-eveniment` | `realsurse/asiguratori/generali-declaratie-eveniment-life-pf-2025-09.pdf` (https://www.generali.ro/wp-content/uploads/2025/10/DECLARATIE-EVENIMENT_LIFE_PF_-GDPR-Consimtamant_Sept-2025.pdf) | Polița, beneficiarul, „Moștenitor”, plata indemnizației. Ordinea rândurilor e amestecată de PDF. |
| `18-nn-formular-anunt-deces` | `realsurse/forme/NN-formular-anunt-deces.pdf` (https://www.nn.ro/sites/default/files/2021-12/AV_Formular%20anunt%20deces.pdf) | Data decesului, beneficiari, FATCA. |
| `19-grawe-avizare-dauna-deces` | `realsurse/forme/Grawe-avizare-dauna-deces.pdf` (https://www.grawe.ro/fileadmin/grawe_ro/Downloads/formulare/Avizare_dauna_deces.pdf) | „Număr dosar daună” e gol, deci `claim_number` trebuie să rămână `null`. Beneficiari cu „cotele conform procedurii succesorale”. |
| `20-bcr-cerere-transfer-actiuni-succesiune` | `realsurse/banci/bcr-cerere-transfer-actiuni-succesiune.txt` (https://www.bcr.ro/content/dam/ro/bcr/www_bcr_ro/Investitori/Structur%C4%83%20ac%C5%A3ionariat/Documente%20utile%20actionari/Cerere_transfer_actiuni_urmare_succesiune.pdf) | Cerere a moștenitorilor către bancă, cu lista de acte (certificat de moștenitor, certificat de deces). |
| `21-cec-formular-solicitari-succesiune` | `realsurse/banci/cec-succesiune.txt` (https://www.cec.ro/solicitari-informatii-pentru-succesiune) | Formular web pentru moștenitori și notari. Alternativa „Notar / Denumire Birou Notarial” seamănă cu `notary_request`. |
| `22-cnp-cluj-cerere-verificare-evidente-succesorale` | `realsurse/notari/cluj-cerere-verificare-succesiune.pdf` (https://www.cnpcluj.ro/wp-content/uploads/2026/10/Model-cerere-verificare-succesiune-2026.pdf) | Cerere către Camera Notarilor (nu către bancă), cu „Certificatul de mostenitor nr. ____”. |
| `23-notar-declaratie-acceptare-tacita-model` | `realsurse/notari/notaripro-art-acceptare-tacita-termen.txt` (https://notari.pro/declaratie/acceptare-tacita-peste-termen-succesiune) | Declarație notarială model, cu data reală a decesului (25.07.2001) și calitatea de soț supraviețuitor. |
| `24-notar-declaratie-renuntare-model` | `realsurse/notari/notaripro-model-declaratie-renuntare.txt` (https://notari.pro/declaratie/declaratie-de-renuntare-succesiune-mostenire) | Renunțarea la moștenire. Numele notarului apare în clar, așa cum e în sursă. |
| `25-notar-procura-speciala-succesiune-model` | `realsurse/notari/notaripro-model-procura-succesiune.txt`, exemplul nr. 1 (https://notari.pro/procura/procura-reprezentare-succesiune) | Procură pentru dezbaterea succesiunii („va ridica certificatele de moștenitor”). |
| `26-anexa15-incheiere-finala-necompletata` | `realsurse/forme/regulament-legea36-ordin2333-2013.pdf`, Anexa 15 (https://notari.pro/docs/regulament-legea-36-ordin-2333-2013.pdf) | Încheierea finală: moștenitori, cote, masă succesorală. E cel mai aproape de `heir_certificate`, dar nu e certificat. |
| `27-anexa16-certificat-succesoral-lichidare` | idem, Anexa 16 | „Certificat … Moştenitori/Legatari … cu o cotă de”. Certificatul de lichidare nu e certificat de moștenitor. |
| `28-anexa31-incheiere-verificare-evidente-succesorale` | idem, Anexa 31 | Încheierea de verificare a registrelor succesorale (RNNEOS etc.). |
| `29-anexa37-citatie-succesorala` | idem, Anexa 37 | Citația are dosar succesoral, termen, oră și defunct. Seamănă cu `notary_request`, dar e trimisă unui succesibil. |
| `30-clauza-brd-cgb-2-39-2-decesul-clientului` | `realsurse/banci/brd-cgb-pf.txt`, art. 2.39.2 (https://www.brd.ro/sites/default/files/_files/CGB/CGB%20PF_RO.pdf) | Clauză despre deces: blocarea conturilor, moștenitorii, „adresă emisă de un birou notarial”. |
| `31-clauza-ing-cga-mosteniri-2-53-2-59` | `realsurse/banci/ing-cga.txt`, art. 2.53–2.59 (https://ing.ro/dam/jcr:2263627d-9a51-42e1-910d-4d0951a23803/Conditii%20generale%20de%20afaceri.pdf) | Secțiunea „Moșteniri”. Antetul de pagină e scos, numărul paginii („7”) a rămas. |
| `32-clauza-raiffeisen-cgb-3-2-5` | `realsurse/banci/rbro-cgb-pf.txt`, art. 3.2.5 (https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/conditii-general-bancare-pf/20262602-Conditii-general-bancare-Persoane-Fizice.pdf.coredownload.inline.pdf) | Cine dispune de sume după deces (certificat de moștenitor sau hotărâre). |
| `33-clauza-allianz-my-credit-protect-art27-29` | `realsurse/asiguratori/allianz-my-credit-protect-conditii-contractuale.pdf`, art. 27–29 (https://www.allianztiriac.ro/content/dam/onemarketing/cee/azro/documente/ipid/Conditii_contractuale_My_Credit_Protect.pdf) | Avizarea de către moștenitori în 90 de zile și actele cerute la deces. |
| `34-clauza-ing-credit-protect-notificare-documente-deces` | `realsurse/asiguratori/ing-credit-protect-termeni-din-2023-10.pdf`, cap. 5.1–5.2 (https://www.ing.ro/dam/ingro/doc/Termenii-si-Conditiile-asigurarii-ING-Credit-Protect-incepand-cu-04.10.2023.pdf) | Notificarea evenimentului și documentele pentru deces. Am oprit textul la invaliditate. |

## Teste negative 074 (text real, dar nu document) → `unknown`

| Fișier | Sursa exactă | De ce e greu |
|---|---|---|
| `35-negativ-unnpr-intrebare-supliment` | `realsurse/notari/unnpr-intrebari-frecvente.txt` (https://uniuneanotarilor.ro/intrebari-frecvente/) | Explică certificatul de moștenitor suplimentar. Nu trebuie să iasă `supplementary_certificate`. |
| `36-negativ-notaripro-dex-certificat-mostenitor` | `realsurse/notari/notaripro-dex-certificat-mostenitor.txt` (https://notari.pro/dictionar-juridic-dex/certificat-mostenitor) | Definiția certificatului de moștenitor, a suplimentului și a certificatului de calitate. |
| `37-negativ-forum-avocatnet-a-doua-casatorie` | `realsurse/notari/avocatnet-succesiune-conturi-banci-a-doua-casatorie.txt`, primul mesaj (https://www.avocatnet.ro/forum/discutie_878705/) | Povestea unei succesiuni: certificat de moștenitor, cote de „circa 25 %”, testament, bani în bănci. Am scos pseudonimul și interfața forumului, iar rândurile goale dintre rândurile rupte le-am lipit. |
| `38-negativ-raiffeisen-pagina-colaborare-dgep` | `realsurse/banci/rbro-dgep-colaborare.txt`, corpul paginii (https://www.raiffeisen.ro/ro/persoane-fizice/in-sprijinul-tau/informatii-utile/colaborarea-raiffeisen-bank-cu-directia-generala-pentru-evidenta-persoanelor-dgep.html) | Descrie fluxul DGEP („codul numeric personal”, actualizare periodică). Nu trebuie să iasă `dgep_signal`. |
| `39-negativ-ing-pagina-mostenitor-2012` | `realsurse/banci/ing-mostenitor-2012-wayback.txt` (http://www.ing.ro/ing/ro/info/mostenitor.html, Wayback 2012-07-05) | Pașii pentru moștenitori: certificat de deces, certificat de moștenitor/supliment, asigurare de viață. |
| `40-negativ-metlife-kit-despagubire` | `realsurse/forme/MetLife-kit-despagubire-asigurari-prin-banca.pdf` (https://www.metropolitanlife.ro/content/dam/metlifecom/ro/PDFs/Despagubiri/asigurari-incheiate-prin-banca/Claims_Kit_Banca.pdf) | Broșură: pașii unei despăgubiri și actele cerute la deces. |

## Ce nu a intrat (074)
- `jurisprudenta2/` și `rejust/`: la momentul lucrului directoarele erau goale (doar `original/`, fără fișiere).
- Adrese reale ale notarilor către bănci: în sursele noi nu apare niciun text citat literal (forumurile le descriu,
  nu le reproduc). Modelul de la 01 rămâne singurul.
- Duplicate: `asiguratori/allianz-formular-avizare-eveniment-viata.pdf` are același conținut ca
  `allianz-formular-plata-indemnizatii.pdf` (ambele sunt „Formular plata indemnizatii”). Am exclus formularul de plată,
  pentru că e mai puțin relevant decât chestionarul de deces. `asiguratori/groupama-formular-eveniment-funeral.pdf` e deja 03.
- PID-urile Raiffeisen/UNIQA și condițiile NN (NNAV 100/147/159): text de produs lung, fără nimic peste ce acoperă
  deja 33–34.
- `ing-crr-plata-cota-decedat-2011-wayback`: PDF-ul e imagine, nu are text.
