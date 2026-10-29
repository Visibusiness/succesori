# registries/documents/scan — documentele demo așa cum ajung la bancă

Scanările documentelor de hârtie din scenariul Mariei Ionescu (02–07, plus 04-B): pagini A4 la 200 dpi, tipărite,
semnate, ștampilate și trecute prin scaner. PDF-urile conțin **doar imaginea** paginilor, fără strat de text: agentul
le citește vizual (`agent/extract.py` `extract_file`), ca un operator la ghișeu.

```bash
.venv/bin/python -m registries.generator.scan_demo     # regenerează 02–06 din ../NN-*.md (determinist), copiază 07 din ../pdf/
```

- Sursa de adevăr rămâne textul `../NN-*.md`; valorile corecte, în `../NN-*.mvp.json` (nu se schimbă).
- 07 e scanarea degradată făcută de `registries/generator/scan.py` (aceeași ca în `../pdf/`).
- 01, semnalul DGEP, e o linie dintr-un lot electronic: nu are hârtie, deci nici scanare.

Unde se folosesc: Demo ghidat, modul „Documente: scanate” (implicit). Pasul trimite scanarea în inbox
(`POST /demo/step/{n}?source=scan`), autopilotul o citește și o predă pipeline-ului, iar pasul afișează ce a citit
extractorul (`GET /demo/received/{fișier}`). Previzualizarea din UI arată scanarea și în modul „pre-extrase”.
