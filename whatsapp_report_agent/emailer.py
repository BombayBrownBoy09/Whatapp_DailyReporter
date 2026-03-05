from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SMTP_RETRY_COUNT,
    SMTP_RETRY_BASE_DELAY,
    SMTP_RETRY_MAX_DELAY,
    REPORT_RECIPIENT_EMAIL,
)

logger = logging.getLogger("whatsapp_report_agent.emailer")


def _send_message_once(msg: EmailMessage) -> None:
    logger.info("Connecting to SMTP host %s:%s", SMTP_HOST, SMTP_PORT)
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def _send_with_retry(
    send_fn,
    *,
    retries: int = SMTP_RETRY_COUNT,
    base_delay: float = SMTP_RETRY_BASE_DELAY,
    max_delay: float = SMTP_RETRY_MAX_DELAY,
    sleep_fn=time.sleep,
) -> None:
    for attempt in range(1, retries + 1):
        try:
            send_fn()
            return
        except Exception as exc:  # pragma: no cover - logs are environment dependent
            if attempt >= retries:
                logger.exception("SMTP send failed after %s attempts", attempt)
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning("SMTP send failed on attempt %s: %s; retrying in %.1fs", attempt, exc, delay)
            sleep_fn(delay)


def _send_message(msg: EmailMessage) -> None:
    _send_with_retry(lambda: _send_message_once(msg))


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

    _send_message(msg)
    logger.info("Email with attachment sent to %s", REPORT_RECIPIENT_EMAIL)


def send_text_email(subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = REPORT_RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)

    _send_message(msg)
    logger.info("Text email sent to %s", REPORT_RECIPIENT_EMAIL)
