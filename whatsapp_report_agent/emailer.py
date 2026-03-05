from __future__ import annotations

import base64
import logging
import mimetypes
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

from config import (
    EMAIL_FROM,
    EMAIL_PROVIDER,
    RESEND_API_KEY,
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


def _build_smtp_message(subject: str, body: str, attachment_path: str | None = None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = REPORT_RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path:
        p = Path(attachment_path)
        data = p.read_bytes()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=p.name,
        )

    return msg


def _send_smtp_email(subject: str, body: str, attachment_path: str | None = None) -> None:
    msg = _build_smtp_message(subject, body, attachment_path)
    _send_message(msg)


def _build_resend_attachment(path: str) -> dict[str, Any]:
    p = Path(path)
    content_type = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(p.read_bytes()).decode("utf-8")
    return {
        "filename": p.name,
        "content": encoded,
        "content_type": content_type,
    }


def _send_resend_email(subject: str, body: str, attachment_path: str | None = None) -> None:
    if not RESEND_API_KEY:
        raise ValueError("RESEND_API_KEY is not configured")

    payload: dict[str, Any] = {
        "from": EMAIL_FROM,
        "to": [REPORT_RECIPIENT_EMAIL],
        "subject": subject,
        "text": body,
    }

    if attachment_path:
        payload["attachments"] = [_build_resend_attachment(attachment_path)]

    response = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json=payload,
        timeout=30,
    )

    if response.status_code >= 300:
        raise RuntimeError(f"Resend API error {response.status_code}: {response.text}")


def _send_via_provider(subject: str, body: str, attachment_path: str | None = None) -> None:
    if EMAIL_PROVIDER == "smtp":
        _send_smtp_email(subject, body, attachment_path)
        return

    try:
        _send_resend_email(subject, body, attachment_path)
        logger.info("Email sent via Resend to %s", REPORT_RECIPIENT_EMAIL)
    except Exception as exc:
        logger.warning("Resend send failed, falling back to SMTP: %s", exc)
        _send_smtp_email(subject, body, attachment_path)


def send_email_with_attachment(subject: str, body: str, attachment_path: str) -> None:
    _send_via_provider(subject, body, attachment_path)
    logger.info("Email with attachment sent to %s", REPORT_RECIPIENT_EMAIL)


def send_text_email(subject: str, body: str) -> None:
    _send_via_provider(subject, body)
    logger.info("Text email sent to %s", REPORT_RECIPIENT_EMAIL)
