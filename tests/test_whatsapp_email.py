from __future__ import annotations

import json
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Tuple
import smtplib
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config import REPORT_RECIPIENT_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS


SAMPLE_PAYLOAD: dict[str, Any] = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "910394521686644",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15551861991",
                            "phone_number_id": "972424385960588",
                        },
                        "contacts": [
                            {"profile": {"name": "Bhargav JS"}, "wa_id": "19843296624"}
                        ],
                        "messages": [
                            {
                                "from": "19843296624",
                                "id": "wamid.TEST123",
                                "timestamp": "172560793",
                                "text": {
                                    "body": (
                                        "Daily Production: 1000\n"
                                        "Daily Production Target: 1500\n"
                                        "Daily Despatch: 500\n"
                                        "Daily Despatch Target: 800\n"
                                        "Remarks: cutter problem"
                                    )
                                },
                                "type": "text",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


def extract_sender_and_text(payload: dict[str, Any]) -> Tuple[str, str]:
    entry = payload.get("entry", [])[0]
    change = entry.get("changes", [])[0]
    value = change.get("value", {})
    msg = value.get("messages", [])[0]
    sender = msg.get("from", "")
    text = (msg.get("text") or {}).get("body") or ""
    return sender, text


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


def load_payload() -> dict[str, Any]:
    payload_path = os.environ.get("WHATSAPP_PAYLOAD_PATH")
    payload_json = os.environ.get("WHATSAPP_PAYLOAD_JSON")
    default_path = Path(__file__).resolve().parent / "ngrok_payload.json"

    if payload_path:
        return json.loads(Path(payload_path).read_text())
    if payload_json:
        return json.loads(payload_json)
    if default_path.exists():
        return json.loads(default_path.read_text())
    return SAMPLE_PAYLOAD


def main() -> None:
    payload = load_payload()
    sender, text = extract_sender_and_text(payload)

    subject = "WhatsApp payload test"
    body = f"Sender: {sender}\n\nMessage:\n{text}\n"

    if os.environ.get("DRY_RUN", "0") in {"1", "true", "True"}:
        print("DRY_RUN enabled. Email content would be:")
        print(body)
        return

    send_text_email(subject, body)
    print(f"Email sent to {REPORT_RECIPIENT_EMAIL}.")


if __name__ == "__main__":
    main()
