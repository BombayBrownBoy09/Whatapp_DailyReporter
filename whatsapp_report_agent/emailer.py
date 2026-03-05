from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, REPORT_RECIPIENT_EMAIL


def send_email_with_attachment(subject: str, body: str, attachment_path: str) -> None:
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = REPORT_RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)

    p = Path(attachment_path)
    data = p.read_bytes()
    msg.add_attachment(
        data,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=p.name,
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def send_text_email(subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = REPORT_RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
