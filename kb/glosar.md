Sursă: generat de noi (terminologie din Codul civil — Legea 287/2009, Legea 36/1995, CGB Raiffeisen PF) · Accesat: 2026-10-28 · Owner: LEAD

# Glosar RO → EN (nume în cod)

Regula: în cod folosim numele din coloana „cod”; în UI și în documentele generate, termenul românesc.

| Termen RO | Explicație scurtă | EN / cod |
|---|---|---|
| defunct / de cuius | persoana decedată a cărei moștenire se deschide | `deceased` |
| data decesului | momentul deschiderii moștenirii; toate soldurile se calculează la ea | `date_of_death` |
| moștenire / succesiune | transmiterea patrimoniului defunctului | `estate` / `succession_case` |
| dosar de succesiune (la bancă) | dosarul unic deschis de agent | `case` |
| procedură succesorală notarială | procedura la notar care se încheie cu certificatul de moștenitor | `notarial_procedure` |
| masa succesorală | bunurile și datoriile lăsate de defunct | `estate_assets`, `estate_debts` |
| moștenitor | persoana care primește o parte din moștenire | `heir` |
| moștenitor legal / testamentar | după lege / după testament | `heir.kind = legal|testamentary` |
| soț supraviețuitor | soțul defunctului la data decesului | `surviving_spouse` |
| descendent | copil, nepot de copil | `descendant` |
| cotă (parte) | fracțiunea din moștenire cuvenită unui moștenitor (ex. 1/4) | `share` (fracție exactă) |
| opțiune succesorală | dreptul de a accepta sau renunța; termen 1 an de la deschidere | `succession_option`, `option_deadline` |
| acceptare / renunțare | cele două variante ale opțiunii | `accept` / `renounce` |
| certificat de moștenitor | actul notarului care arată moștenitorii, cotele și bunurile | `heir_certificate` |
| certificat suplimentar (supliment) | certificat emis pentru bunuri omise din primul certificat | `supplementary_certificate` |
| certificat de calitate de moștenitor | arată doar calitatea și cota, fără bunuri | `heir_status_certificate` |
| certificat de deces | actul de stare civilă care dovedește decesul | `death_certificate` |
| adresa notarului | cererea notarului către bancă pentru produse și solduri | `notary_request` |
| răspunsul băncii către notar | documentul generat de agent | `notary_reply` |
| împuternicit / mandatar | persoana cu drept de operare pe cont; mandatul încetează la deces | `mandate_holder` / `mandate` |
| procură | actul prin care cineva e împuternicit (ex. moștenitor din străinătate) | `power_of_attorney` |
| comunitate de bunuri | regimul matrimonial legal; jumătate din bunurile comune e a soțului, nu intră în moștenire | `community_property` |
| depozit la termen nescadent | depozit a cărui scadență n-a sosit la data decesului | `term_deposit`, `matured=false` |
| cont comun / cotitular | cont cu mai mulți titulari | `joint_account`, `holders[]` |
| asigurare de viață atașată creditului | polița care stinge creditul la deces | `credit_life_insurance` |
| dosar de daună | cererea de plată către asigurător | `insurance_claim` |
| instanța de tutelă | instanța care autorizează actele pentru minori | `guardianship_court` |
| reprezentant legal | părintele/tutorele minorului | `legal_representative` |
| succesiune vacantă | fără moștenitori; bunurile trec la comună/oraș | `vacant_estate` |
| DGEP / RNEP | Direcția Generală pentru Evidența Persoanelor / Registrul Național | `dgep_signal` |
| CNPP / casa de pensii | plătitorul pensiei; cere retur pentru pensiile după deces | `pension_payer` |
| escaladare | trimiterea dosarului/documentului la un operator uman | `escalate` |

## Tipuri de document (KB RO → cod EN, D-vocabular în DECISIONS)
| KB / registries (RO) | `document_type` în cod |
|---|---|
| semnal_dgep | `dgep_signal` |
| adresa_notar | `notary_request` |
| polita_asigurare / certificat de asigurare | `insurance_certificate` |
| raspuns_asigurator | `insurer_response` |
| certificat_mostenitor | `heir_certificate` |
| certificat_mostenitor_suplimentar / certificat_suplimentar | `supplementary_certificate` |
| certificat_calitate_mostenitor | `heir_status_certificate` |
| certificat_deces | `death_certificate` |
| procura | `power_of_attorney` |
| hotarare_judecatoreasca | `court_decision` |

## Ce înseamnă pentru agent
- Nume stabile pentru câmpurile din schema de extracție (`claude-tool-use-notes.md`) și din API (`api-contract-bank.md`).
- Cotele se țin ca fracții exacte (`Fraction`), nu ca float.
