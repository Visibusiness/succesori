"""Rules per life insurer attached to loans: notice term, documents asked of the heirs, decision/payment term,
what is covered, typical exclusions. Source of every value: kb/bank-procedures/asiguratori-reguli.md (table with quotes).

Pure data + lookup; no state. A term that is not public stays `None` with status "necunoscut", never a guess.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

CONFIRMED, HYPOTHESIS, UNKNOWN_STATUS = "confirmat", "ipoteză, de confirmat", "necunoscut, de confirmat cu banca"


@dataclass(frozen=True)
class Term:
    days: int | None = None
    working_days: bool = False        # "zile lucrătoare" instead of calendar days
    status: str = UNKNOWN_STATUS
    max_years: int | None = None      # hard outer limit counted from death (Allianz: 2 ani)
    source: str = ""

    @property
    def label(self) -> str:
        if self.days is None:
            return UNKNOWN_STATUS
        unit = "zile lucrătoare" if self.working_days else "zile"
        return f"{self.days} de {unit}" + ("" if self.status == CONFIRMED else f" ({self.status})")


@dataclass(frozen=True)
class ClaimDocument:
    text: str
    cause: str | None = None          # None = always; "boală" / "accident" = only for that cause of death
    from_heirs: bool = True           # False = the bank already holds it (certificat de asigurare, grafic)


@dataclass(frozen=True)
class Insurer:
    key: str
    name: str
    aliases: tuple[str, ...]
    notice: Term                      # term for the heirs to notify the insurer
    notice_from: str                  # "death" | "death_or_learned"
    decision: Term
    payment: Term
    documents: tuple[ClaimDocument, ...]
    covers: str
    exclusions: tuple[str, ...]
    source: str
    contact: str = ""

    def heir_documents(self, cause: str | None = None) -> list[str]:
        """Checklist asked of the heirs; with a known cause only the documents for that cause."""
        return [d.text for d in self.documents if d.from_heirs and (d.cause is None or cause is None or d.cause == cause)]


_DEATH_DOCS = (ClaimDocument("copia certificatului de deces"), ClaimDocument("copia certificatului medical constatator al decesului"))

UNIQA = Insurer(
    key="uniqa", name="UNIQA Asigurări de viață S.A.", aliases=("uniqa",),
    notice=Term(30, status=HYPOTHESIS, source="Condițiile Generale UNIQA nu sunt publice; 30 de zile e pe daune-viata.uniqa.ro "
                                              "(kb/bank-procedures/asigurare-viata-credit.md), neregăsit pe uniqa.ro/daune"),
    notice_from="death_or_learned",
    decision=Term(source="nepublicat"),
    payment=Term(10, working_days=True, status=HYPOTHESIS, source="PID UNIQA carduri de credit 2023; pentru creditul de nevoi personale nepublicat"),
    documents=(
        ClaimDocument("cererea de despăgubire UNIQA (formularul F1), completată de moștenitor"),
        *_DEATH_DOCS,
        ClaimDocument("documentele medicale din istoric (scrisori medicale, bilete de externare, investigații)", cause="boală"),
        ClaimDocument("documentele medico-legale care lămuresc împrejurările accidentului", cause="accident"),
        ClaimDocument("certificatul de asigurare și declarația semnată de asigurat", from_heirs=False),
        ClaimDocument("graficul de rambursare semnat de bancă și asigurat", from_heirs=False),
    ),
    covers="deces din orice cauză și invaliditate permanentă totală: sold principal + max. 3 rate restante, plafon 260.000 lei; beneficiar banca",
    exclusions=("condiție medicală din ultimele 24 de luni, dacă decesul e în primele 12 luni de asigurare",
                "sinucidere în primii 2 ani", "infracțiuni cu intenție, conducere sub influența alcoolului/substanțelor"),
    source="PID/IPID Raiffeisen–UNIQA V4_09.2025; formular UNIQA 'Notificare și cerere de solicitare a despăgubirii' 2024",
    contact="asigurari@uniqa.ro, daune-viata.uniqa.ro")

ALLIANZ = Insurer(
    key="allianz", name="Allianz-Țiriac Asigurări (My Credit Protect)", aliases=("allianz",),
    notice=Term(90, status=CONFIRMED, max_years=2, source="Condiții My Credit Protect, art. 28 lit. a)"),
    notice_from="death",
    decision=Term(15, status=CONFIRMED, source="Condiții My Credit Protect, art. 30 (decizie)"),
    payment=Term(15, status=CONFIRMED, source="Condiții My Credit Protect, art. 40"),
    documents=(
        *_DEATH_DOCS,
        ClaimDocument("procesul-verbal de constatare a accidentului", cause="accident"),
        ClaimDocument("datele bancare necesare plății"),
        ClaimDocument("comunicarea băncii cu debitul rămas la data decesului și graficul de rambursare actualizat", from_heirs=False),
    ),
    covers="deces, sumă descrescătoare; beneficiar banca, surplusul peste soldul creditului revine moștenitorilor legali (art. 38)",
    exclusions=("boli preexistente", "sinucidere în primii 2 ani"),
    source="Condiții contractuale My Credit Protect (CTL26), allianztiriac.ro")

NN = Insurer(
    key="nn", name="NN Asigurări de Viață (ING Credit Protect)", aliases=("nn", "ing credit protect", "ing bank"),
    notice=Term(30, status=CONFIRMED, source="Termeni ING Credit Protect (din 04.10.2023): neîndeplinirea depunerii documentelor în 30 de zile e excludere"),
    notice_from="death",
    decision=Term(source="nepublicat separat de plată"),
    payment=Term(10, working_days=True, status=CONFIRMED, source="Termeni ING Credit Protect: plata în 10 zile lucrătoare de la ultimul document"),
    documents=(
        ClaimDocument("notificarea evenimentului asigurat"),
        ClaimDocument("copia cărții de identitate a moștenitorului"),
        *_DEATH_DOCS,
        ClaimDocument("fișa medicală / adeverință de la medicul de familie", cause="boală"),
        ClaimDocument("ancheta poliției / raportul toxicologic, dacă e cazul", cause="accident"),
        ClaimDocument("contractul de credit și graficul de rambursare", from_heirs=False),
        ClaimDocument("certificatul de asigurare și cererea de aderare", from_heirs=False),
    ),
    covers="deces = 100% din soldul creditului, max. 180.000 lei; beneficiar banca, excedentul la moștenitori",
    exclusions=("afecțiuni preexistente (12 luni pentru ITM/spitalizare)", "suicid", "alcool/droguri",
                "nedepunerea documentelor în 30 de zile"),
    source="Termeni și condiții ING Credit Protect (04.10.2023)",
    contact="021.9464, evenimenteasigurate@nn.ro")

UNRECOGNIZED = Insurer(
    key="necunoscut", name="asigurător nerecunoscut", aliases=(),
    notice=Term(), notice_from="death_or_learned", decision=Term(), payment=Term(),
    documents=(*_DEATH_DOCS, ClaimDocument("actul de identitate al moștenitorului"),
               ClaimDocument("certificatul de asigurare și graficul de rambursare", from_heirs=False)),
    covers="necunoscut, de confirmat cu banca", exclusions=(), source="nicio sursă publică pentru acest asigurător")

INSURERS: dict[str, Insurer] = {i.key: i for i in (UNIQA, ALLIANZ, NN)}
DEFAULT = UNIQA   # Raiffeisen's loan insurer: used while the document does not name one


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def lookup(name: str | None) -> Insurer:
    """Insurer from the name written on the document. No name -> Raiffeisen's (UNIQA); unknown name -> UNRECOGNIZED."""
    if not name or not name.strip():
        return DEFAULT
    n = _norm(name)
    for ins in INSURERS.values():
        if any(re.search(rf"\b{re.escape(_norm(a))}\b", n) for a in ins.aliases):
            return ins
    return UNRECOGNIZED
