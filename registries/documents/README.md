# registries/documents — cele 7 documente ale demo-ului (fictive)

Specificația și explicațiile sunt în `kb/scenariu-demo/documente-demo.md`; cifrele vin din `kb/scenariu-demo/maria-ionescu.md`.
Textele `.md` sunt extrase automat din blocurile de cod din `documente-demo.md`. Dacă schimbi un text, îl schimbi acolo
și regenerezi fișierele aici.

| Fișier | Ce e |
|---|---|
| `01-dgep-semnal.json` | linia din lotul DGEP (input structurat, format mock din `kb/tech/dgep-integration.md`) |
| `NN-*.md` | textul integral al documentului, din care generatorul face PDF-ul (doc 7 iese imagine scanată, degradată după `degradation`) |
| `NN-*.mvp.json` | același ground truth în forma din `agent/demo_documents.py` (`id, raw_name, document_type, received_on, confidence, fields`), vocabular EN; `raw_name` → `pdf/` |
| `NN-*.json` | ground truth: `fields` = ce trebuie extras; `expected_agent` = acțiuni + starea dosarului după |

Variantele 04-A (moștenire legală) și 04-B (testament) se exclud reciproc într-o rulare. Documentul 06 e comun și ia
cotele din 04.

Convenții:
- sume în **bani** (întregi, sufix `_bani`);
- cote ca fracții string `"a/b"`;
- date ISO;
- CNP-uri mascate `X` și IBAN-uri cu cifra de control `00` (invalide intenționat).

Valorile ascunse ale documentului 07 sunt în `registries/generator/test_only/07-hidden-truth.json`, nu aici, ca să nu ajungă la agent.

PDF-urile: `pdf/` se regenerează determinist cu `python -m registries.generator` (vezi `registries/generator/README.md`).

Cazurile de test grele (§4 din scenariu) sunt în `hard/`.
