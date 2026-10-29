Sursă: https://legeaz.net/legea-506-2004-prelucrare-date-caracter-personal/articolul-12 și /articolul-4 (Legea 506/2004, copie neoficială; forma acolo trimite încă la Legea 677/2001) ; GDPR art. 6 și 14 (gdpr-text.com, copii în `kb/_downloads/visi/gdprtext-art6-ro.html`, `gdprtext-art14-ro.html`) ; `kb/legal/secret-bancar.md` ; `kb/legal/gdpr-decedati-mostenitori.md` · Accesat: 2026-10-28 · Owner: DOMAIN

Copii locale: `kb/_downloads/visi/legeaz-l506-art12.html`, `legeaz-l506-art4.html`, `edlaw-legea506.html`.

# Canale de comunicare cu moștenitorii: reguli da/nu și temeiul lor

## Citate
**Legea 506/2004 art. 12 alin. (1):** „Este interzisă efectuarea de comunicări comerciale prin utilizarea unor sisteme automate de apelare care nu necesită intervenţia unui operator uman, prin fax ori prin poşta electronică sau prin orice altă metodă care foloseşte serviciile de comunicaţii electronice destinate publicului, cu excepţia cazului în care abonatul vizat şi-a exprimat în prealabil consimţământul expres pentru a primi asemenea comunicări.”
**Alin. (2):** adresa de e-mail obținută „cu ocazia vânzării” unui produs sau serviciu poate fi folosită pentru comunicări comerciale despre „produse sau servicii similare”, cu opțiune de opoziție simplă și gratuită la fiecare mesaj.
**Alin. (3):** interzis e-mailul comercial în care „identitatea reală” a expeditorului e ascunsă sau lipsește o adresă validă pentru încetarea comunicărilor.
**Art. 4 alin. (1):** „Confidenţialitatea comunicărilor transmise prin intermediul reţelelor publice de comunicaţii electronice […] sunt garantate” (obligația furnizorilor de rețea, nu a băncii).

**GDPR art. 6 alin. (1):** temeiuri: „(a) persoana vizată și-a dat consimțământul […]”, „(b) executarea unui contract […] sau demersuri la cererea persoanei vizate înainte de încheierea unui contract”, „(c) obligație legală”, „(f) interese legitime […] cu excepția cazului în care prevalează interesele sau drepturile […] persoanei vizate”.
**GDPR art. 14 alin. (1):** când datele „nu au fost obținute de la persoana vizată”, operatorul îi furnizează identitatea și datele de contact ale operatorului, scopurile etc.; **alin. (5) lit. a)** nu se aplică dacă „persoana vizată deține deja informațiile”.

**Secret bancar (OUG 99/2006 art. 111–113, RIL 9/2024):** vezi `secret-bancar.md`. Aici contează: existența relației cu un client, chiar decedat, e informație protejată.

## Distincții de bază
- **Comunicare comercială** (marketing): intră sub Legea 506/2004 art. 12 ⇒ consimțământ expres prealabil pe canal. **Nu** trimitem așa ceva moștenitorilor (nu vindem produse).
- **Comunicare operațională** (cere documente, spune etapa dosarului): art. 12 vizează „comunicări comerciale”; **interpretare proprie:** mesajele pur operaționale, necesare dosarului, nu intră în art. 12 (definiția „comunicare comercială” din legea comerțului electronic nu am citit-o) ⇒ se bazează pe GDPR art. 6 alin. 1 lit. b/c/f, nu pe consimțământ.
- **Moștenitor care nu e client al băncii:** banca primește datele lui de la familie, notar sau din certificat ⇒ **GDPR art. 14** (informare la primul contact, cu datele operatorului și scopul), dacă nu le are deja (alin. 5 lit. a).
- **Secretul bancar bate canalul:** pe orice canal, către o persoană neverificată ca moștenitor, **nu** se confirmă că defunctul a fost client.

## Reguli per canal (propunere; temeiul în coloana a doua)
| Canal | Către cine | Permis | Interzis | Temei |
|---|---|---|---|---|
| **E-mail** | moștenitor/persoană din dosar, adresă obținută direct de la ea sau din certificat | mesaje operaționale: lista documentelor lipsă, etapa, link securizat de încărcare, cum ne contactează | solduri, produse, cine mai e moștenitor, atașamente cu date de cont; marketing | GDPR 6(1)(b)/(c)/(f); secret bancar; Legea 506/2004 art. 12 (doar pt. marketing) |
| **E-mail** | persoană doar „menționată” de altcineva | nimic, sau mesaj generic fără referire la defunct sau la bancă-client | orice detaliu de dosar | art. 111; GDPR art. 14 |
| **SMS** | numărul dat de moștenitor în dosar | max. 300 caractere (regulă internă din `heir-communicator`), fără date de cont, fără atașamente, doar link/instrucțiuni | solduri; nume alți moștenitori; marketing fără consimțământ | secret bancar; Legea 506/2004 art. 12 |
| **WhatsApp** | doar dacă moștenitorul a inițiat contactul sau și-a dat consimțământul pe acest canal | același conținut minim ca SMS | inițierea contactului cu un număr obținut de la terți | consimțământ GDPR art. 6(1)(a) + condițiile platformei (necitite) |
| **Telefon (call center)** | apelant | reguli „ce poate spune agentul la telefon unei rude” din `secret-bancar.md` | orice confirmare de cont | art. 111; RIL 9/2024 |
| **App / portal** | moștenitor autentificat | detalii de dosar după autentificare și verificarea calității | — | art. 113 alin. (2) lit. a); GDPR art. 6(1)(b)/(c) |
| **Scrisoare/notar** | notar | răspuns la adresă, cu cele cerute de art. 81 Legea 36/1995 | — | `procedura-succesorala-notar.md` |

## Necunoscut
- **Ghidurile ANSPDCP** despre comunicări electronice/consimțământ pe canal: nu le-am putut citi (documentul `dataprotection.ro/ViewDocument?id=859` e o imagine). Rămâne de căutat pe dataprotection.ro.
- **Textul oficial consolidat** al Legii 506/2004 (copia de pe legeaz.net trimite la Legea 677/2001, abrogată; modificări prin Legea 235/2015 menționate de surse secundare): de verificat pe legislatie.just.ro.
- **Definiția „comunicare comercială”** (Legea 365/2002) și dacă un mesaj operațional către un neclient poate fi considerat comercial: neverificat.
- **Politica WhatsApp Business** (opt-in, șabloane) și EDPB despre canale: nevăzute.
- **Amenzi ANSPDCP** pe art. 12: sursele din căutare (Vodafone 2009; Artmark; Elefant Online) sunt presă, necitite la sursă.
- Dacă banca are în contractul DGEP sau în CGB o clauză de contactare a moștenitorilor: negăsită.
- Consimțământul pentru canal al unui moștenitor în momentul în care **nu e încă identificat**: nu există temei de consimțământ, deci nu se trimite nimic.

## Ce înseamnă pentru agent (heir-communicator)
Regulile din `.claude/agents/heir-communicator.md` rămân; completări propuse de DOMAIN (fișierul agentului nu se modifică de mine):
1. **Corecție temei:** regula 3 spune „GDPR art. 6 lit. a/b” pentru WhatsApp/SMS. Pentru mesaje operaționale temeiul e lit. b/c/f; **consimțământul (lit. a)** e cerut de Legea 506/2004 art. 12 doar pentru **comunicări comerciale**. Păstrăm totuși politica prudentă: SMS/WhatsApp doar cu `contact_consent[canal]` sau când moștenitorul a contactat banca pe acel canal; altfel e-mail/app.
2. **Fără mesaj comercial** către moștenitori (nici „oferte” de produse) fără consimțământ separat.
3. **Primul mesaj** către cineva nou: informare GDPR art. 14 (cine suntem, de ce avem datele) într-o frază + link; nimic despre cont.
4. **Verifică destinatarul înainte de orice detaliu**: persoană din dosar (certificat, reprezentant legal, persoana care a notificat decesul). Altfel: mesaj generic „contactați agenția cu actul de identitate”.
5. **Secret bancar:** aceleași interdicții pe toate canalele ca la telefon; detalii de cont doar după verificarea calității de moștenitor + justificarea scopului (RIL 9/2024).
6. **E-mail:** adresă validă de răspuns și identitatea clară a băncii (art. 12 alin. 3); fără atașamente cu date personale; linkul securizat expiră.
7. **Un mesaj = o acțiune**, cu lista documentelor; fără promisiuni de termen de plată (nu există termen legal public).
8. **Escaladare la om** dacă destinatarul cere informații despre cont fără dovada calității sau dacă e minor (`mostenitor-minor.md`: comunicăm cu părintele/reprezentantul legal).
