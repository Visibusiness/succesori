Sursă: https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/pf/asigurari/asigurari-de-viata/document-informatii-produs-asigurare-credite-de-nevoi-personale.sv.pdf (IPID UNIQA V4_09.2025) ; https://www.uniqa.ro/sites/default/files/2024/Anexa%20F1%20-%20Cerere%20de%20despagubire%20%C3%AEn%20caz%20de%20daun%C4%83%20RAIB_Vmartie%202024.pdf · Accesat: 2026-10-28 · Owner: DOCS

# Certificatul de asigurare de viață atașat creditului (UNIQA prin Raiffeisen) — câmpuri

Polița propriu-zisă nu e publică; documentul pe care îl are clientul este **Certificatul de asigurare** (menționat în
formularul F1: „Certificatul de asigurare / Termenii și condițiile Pachetului de asigurare și Declarația cu semnătura
Asiguratului”). Schema de mai jos e construită de noi din IPID și formularul F1; textele citate și regulile de acoperire
sunt în `kb/bank-procedures/asigurare-viata-credit.md`.

## Schema de extracție
| Câmp | Tip | Obligatoriu | Observații |
|---|---|---|---|
| `insurer` | text | da | „UNIQA Asigurări de viață S.A.” |
| `product_name` | text | da | „Asigurare de viață pentru titularii de credite de nevoi personale negarantate” |
| `certificate_number` | text | da | nr. certificat de asigurare |
| `insured_name`, `insured_cnp` | text | da | trebuie = defunctul |
| `beneficiary` | text | da | Raiffeisen Bank, în limita datoriei |
| `loan_contract_number` | text | da | legătura cu creditul din core |
| `start_date` | dată | da | pentru excluderi (12 luni boli preexistente, 24 luni sinucidere) |
| `initial_sum_insured` | sumă | da | = valoarea creditului, descrescătoare după grafic |
| `premium_type` | enum `unica|lunara` | da | lunară neplătită ⇒ asigurare suspendată |
| `covered_risks` | listă | da | deces din orice cauză, invaliditate, șomaj/spitalizare |
| `cap` | sumă | nu | 260.000 lei (V4_09.2025) |

## Exemplu fictiv (scenariul demo)
```
UNIQA Asigurări de viață S.A. — Certificat de asigurare nr. UQ-0000000-FICTIV
Asigurat: Maria Ionescu, CNP 2XXXXXXXXXXXX · Beneficiar: Raiffeisen Bank S.A., în limita datoriei
Contract de credit nr. CNP-FICTIV-001 · Data începerii: 2023-05-10 · Primă: lunară
Suma asigurată inițială: 15.000 lei, descrescătoare conform Graficului de rambursare
Riscuri: Deces din orice cauză; Invaliditate permanentă din orice cauză; Spitalizare din orice cauză (pensionar)
```

## Necunoscut
- Machetă reală a Certificatului de asigurare (nu e publică).

## Ce înseamnă pentru agent
- Validări: `insured_cnp` = CNP client; `loan_contract_number` există în core și e creditul cu `insurance_policy_id`.
- `start_date` + data decesului → flaguri de risc (nu decizie); `premium_type=lunara` → verifică în core plata ultimei prime.
- Indemnizația așteptată = principalul rămas la data decesului + max. 3 rate restante (≤ plafon); dobânda de după deces rămâne datorie a masei succesorale.
