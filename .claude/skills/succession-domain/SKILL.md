---
name: succession-domain
description: Harta domeniului pentru orice agent al proiectului - unde în kb/ se află fiecare regulă, deciziile luate, valorile fixe ale scenariului demo. De citit înainte de orice raționament juridic sau de calcul.
---
# Domeniul: succesiunea unui client al băncii

- Scenariul și valorile așteptate (sursa de adevăr pentru cifre): `kb/scenariu-demo/maria-ionescu.md`
- Deciziile echipei (ce s-a confirmat/infirmat): `docs/DECISIONS.md`
- Reguli implementate și testate: `agent/rules.py`, `tests/test_rules.py`
- Legi: `kb/legal/cod-civil-succesiuni.md` (art. 972, 975, 1088, 1103, 1114, 2030, 2186–2187), `mostenitor-minor.md`,
  `legea-pensiilor-deces.md` (Legea 360/2023 art. 100, 156), `cod-civil-regim-matrimonial.md`, `secret-bancar.md`
- Banca: `kb/bank-procedures/raiffeisen-cgb-pf-extras.md` (CGB 3.2.5 b/d, 3.8.3, 5.10.4 c, 7.7.1 c), `asigurare-viata-credit.md`,
  `dgep-arb-acord.md`, `cazuri-reale.md`
- Documente-tip: `kb/document-templates/*.md`

## Principii pe care niciun agent nu le încalcă
1. Cotele vin din certificatul de moștenitor, nu din lege. Se verifică doar că însumează 1.
2. Pe semnal DGEP singur: numai acțiuni reversibile.
3. Plata e ireversibilă ⇒ aprobare umană. Partea minorului și depozitul nescadent rămân blocate.
4. Calculele sunt deterministe (`agent/rules.py`); agenții nu calculează bani în cap.
5. Secretul bancar: solduri doar notarului și moștenitorilor cu certificat.
