Sursă: https://www.raiffeisen.ro/ro/persoane-fizice/in-sprijinul-tau/informatii-utile/colaborarea-raiffeisen-bank-cu-directia-generala-pentru-evidenta-persoanelor-dgep.html ; https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/actionari/formulare/20181026-Emitere-extras-de-cont.pdf.coredownload.inline.pdf ; https://www.raiffeisen.ro/ro/persoane-fizice/in-sprijinul-tau/urgente.html ; https://ziardebragadiru.ro/caz-complicat-la-raiffeisen-bank-cum-s-au-strans-comisioanele-luna-dupa-luna-pentru-o-persoana-decedata/ · Accesat: 2026-10-28 · Owner: DOMAIN

# Ce comunică public Raiffeisen Bank despre decesul unui client

Originale: `kb/_downloads/nicolas/raiffeisen/`, `kb/_downloads/nicolas/dgep/raiffeisen-*`.

## 1. Concluzia (a noastră)
Raiffeisen **nu are o pagină publică dedicată** decesului unui client sau succesiunii. Nu există pagină de tip „ce face familia”, listă de documente pentru moștenitori pe conturi, depozite sau credite, termene sau canal dedicat. Am căutat pe raiffeisen.ro (WebSearch cu `allowed_domains: raiffeisen.ro`, interogări „deces”, „moștenitori”, „certificat de moștenitor”, „succesiune”, „întrebări frecvente”). Ce există public:

| Ce | Unde | Ce spune despre deces |
|---|---|---|
| CGB PF | PDF CGB (vezi `raiffeisen-cgb-pf-extras.md`) | împuterniciți „numai pe timpul vietii titularului”; moștenitori cu certificat de moștenitor sau hotărâre; cardul încetează la deces; debitarea directă încetează la deces; data decesului se poate obține din surse externe |
| Pagina DGEP | raiffeisen.ro (link mai sus) | banca primește de la DGEP „data decesului (după caz)” |
| Formular „Emiterea extrasului de cont” | PDF 2018, secțiunea **acționari** | documente pentru moștenitorii unui **acționar** decedat (nu pentru contul bancar) |
| Pagina „Urgențe” | raiffeisen.ro | documente pentru o daună de **asigurare** (deces din accident/îmbolnăvire), nu pentru cont |

## 2. Citate

### 2.1 Formularul de extras pentru acționari (Registrul Acționarilor), PDF 2018
(Text extras automat. Diacriticele lipsesc și în original. E vorba de „extras de cont” de **acțiuni Raiffeisen**, nu de contul curent.)
> „Extrasul de cont reprezinta o dovada a dreptului de proprietate asupra unui anumit numar de actiuni si se elibereaza numai titularului de cont, imputernicitului acestuia sau unui potential mostenitor.”
> „In cazul decesului titularului de cont, mostenitorii pot obtine extras de cont pentru defunct in baza urmatoarelor acte: · Certificatul de deces al titularului de cont, fotocopie · BI/CI al unui dintre potentialii mostenitori, fotocopie · Cerere privind eliberarea extrasului de cont”

### 2.2 Pagina „Urgențe”, asigurare, „Deces din accident sau îmbolnăvire”
> „• Certificatul de deces (copie); • Certificatul constatator al decesului; [...] • Raportul poliției (dacă este cazul);• Documente medicale referitoare la cauza decesului (conform certificatului de asigurare).”

(Lista aparține unui produs de asigurare distribuit de bancă. Detalii pentru asigurarea de credit: `asigurare-viata-credit.md`.)

### 2.3 Pagina DGEP: canal de contact (protecția datelor)
> „Solicitările pot fi adresate în cadrul oricărei agenții Raiffeisen Bank, precum și prin intermediul unei cereri scrise, datate și semnate, depusă la sediul Raiffeisen Bank din Calea Floreasca nr. 246D, Clădirea de birouri FCC, Sector 1, București, cod poștal 014476, prin fax la numărul +40 21 230 0700, prin telefon la numărul *2000 sau 004 021 306 3002 [...] sau prin e-mail la adresa dpo@raiffeisen.ro.”
Nota DGEP mai indică pentru cereri: „centrala@raiffeisen.ro”.

(Sunt canale generale sau DPO. Nu sunt un canal dedicat decesului.)

### 2.4 Poziția publică a băncii într-un caz real (Ziar de Bragadiru, 2023)
> „Întrucât banca nu a fost informată despre decesul clientului, iar rulajul lunar minim necesar nu a mai fost efectuat, contul a înregistrat comisioane lunare datorate băncii, în conformitate cu condițiile contractuale.”

(Explicația noastră: banca leagă blocarea și oprirea comisioanelor de „informarea” despre deces, dar nu publică *cum* se face informarea.)

## Necunoscut
- **Nu există pagină publică dedicată decesului sau succesiunii** la Raiffeisen România. Nu am găsit FAQ, listă de documente pentru moștenitori pe conturi, depozite sau credite, termen de răspuns către notar sau formular de notificare a decesului.
- Nu știm dacă notificarea se poate face online (Smart Mobile / Raiffeisen Online), telefonic (*2000) sau doar în agenție.
- Nu știm dacă Raiffeisen cere prezența simultană a tuturor moștenitorilor sau plătește separat pe cote.
- Procedura internă (norme interne) nu e publică. CGB nu are o secțiune „deces” (vezi `raiffeisen-cgb-pf-extras.md`, „Ce lipsește din CGB”).
- Am încercat: WebSearch pe raiffeisen.ro cu termenii de mai sus; pagina „Informații utile”; pagina „Urgențe”; pagina DGEP; formularele pentru acționari. Nu am verificat telefonic (fără contact cu banca, conform regulilor).

## Ce înseamnă pentru agent
1. **Golul e argument de pitch.** Raiffeisen primește data decesului de la DGEP (contract din 2025, API în T1 2026), dar nu publică nicio procedură pentru familie. Agentul e chiar „procedura” care lipsește.
2. Canalele de intake în mock: agenție (document scanat), e-mail (`centrala@`), telefon (*2000, transcris de operator) și DGEP. Toate deschid același dosar.
3. **Documente minime pe care le cere agentul**, derivate din CGB și din practica altor bănci, nu dintr-o listă publică Raiffeisen: certificat de deces (copie), act de identitate al solicitantului, certificat de moștenitor sau hotărâre judecătorească pentru plată, IBAN-ul moștenitorului, cerere semnată. Le marcăm în cod ca `source: practice`, nu `source: raiffeisen_public`.
4. **Notificarea familiei primește recipisă** (ID dosar + dată). Previne cazul „nu există dovezi că banca ar fi fost înștiințată”.
5. Agentul generează pentru familie un mesaj cu pașii următori (ce documente, unde). Textul e marcat „generat de noi”, pentru că banca nu are unul public.
