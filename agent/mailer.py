"""Livrarea mesajelor către moștenitori (078): o interfață, `send(msg) -> msg`, două implementări.

  OutboxMailer (implicit)  scrie mesajul în runs/<run>/outbox.jsonl (mock: nu pleacă nimic; ops-ui și testele îl citesc)
  SmtpMailer               trimite e-mailul prin SMTP (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS din mediu) și îl
                           păstrează și în outbox. OPRIT implicit: se folosește doar cu MAILER=smtp explicit; fără
                           SMTP_HOST, MAILER=smtp e o eroare de configurare, nu o cădere tăcută pe outbox.

`msg` e mesajul validat de API (POST /messages): case_id, to, channel, template_id, body, + `address` (e-mailul
destinatarului, dacă îl știm). SMS / WhatsApp / app nu au încă un adaptor real: și cu SmtpMailer rămân în outbox.
"""
from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable, Protocol


class Mailer(Protocol):
    name: str

    def send(self, msg: dict[str, Any]) -> dict[str, Any]: ...


class OutboxMailer:
    name = "outbox"

    def __init__(self, path: Callable[[], Path] | Path):
        self._path = path

    def path(self) -> Path:
        return self._path() if callable(self._path) else self._path

    def send(self, msg: dict[str, Any]) -> dict[str, Any]:
        p = self.path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return msg


class SmtpMailer:
    name = "smtp"

    def __init__(self, outbox: OutboxMailer, host: str, port: int = 587, user: str | None = None,
                 password: str | None = None, sender: str | None = None, smtp: Callable[..., Any] = smtplib.SMTP):
        self.outbox, self.host, self.port, self.user, self.password = outbox, host, port, user, password
        self.sender = sender or user or "succesiuni@localhost"
        self._smtp = smtp

    def send(self, msg: dict[str, Any]) -> dict[str, Any]:
        if msg.get("channel") != "email" or not msg.get("address"):
            return self.outbox.send({**msg, "status": "queued_mock", "mailer_note": "fără adaptor real pentru canal / adresă"})
        em = EmailMessage()
        em["From"], em["To"] = self.sender, msg["address"]
        em["Subject"] = msg.get("subject") or f"Dosarul de succesiune {msg.get('case_id')}"
        em.set_content(msg.get("body") or "")
        if msg.get("attachment_path"):   # a letter: the PDF the operator approved (agent/ai_jobs.py mail_letter)
            p = Path(msg["attachment_path"])
            em.add_attachment(p.read_bytes(), maintype="application", subtype="pdf", filename=p.name)
        with self._smtp(self.host, self.port, timeout=30) as s:
            s.starttls()
            if self.user:
                s.login(self.user, self.password or "")
            s.send_message(em)
        return self.outbox.send({**msg, "status": "sent_smtp"})


def get_mailer(outbox: Callable[[], Path] | Path, env: dict[str, str] | None = None) -> Mailer:
    """MAILER unset / `outbox` ⇒ OutboxMailer. Only MAILER=smtp turns SMTP on (and then SMTP_HOST is required)."""
    env = os.environ if env is None else env
    ob = OutboxMailer(outbox)
    kind = (env.get("MAILER") or "outbox").strip().lower()
    if kind == "outbox":
        return ob
    if kind != "smtp":
        raise ValueError(f"MAILER necunoscut: {kind!r} (permise: outbox, smtp)")
    if not env.get("SMTP_HOST"):
        raise ValueError("MAILER=smtp fără SMTP_HOST")
    return SmtpMailer(ob, env["SMTP_HOST"], int(env.get("SMTP_PORT") or 587), env.get("SMTP_USER"), env.get("SMTP_PASS"),
                      env.get("SMTP_FROM"))
