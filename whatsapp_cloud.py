from __future__ import annotations

import logging

import requests
from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID


GRAPH_URL = "https://graph.facebook.com/v20.0"
logger = logging.getLogger("whatsapp_report_agent")


def send_whatsapp_message(to_phone: str, text: str) -> None:
    """
    Send a WhatsApp text message using WhatsApp Cloud API.
    'to_phone' should be in international format without '+' e.g. '9198xxxxxxx'
    """
    url = f"{GRAPH_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if not r.ok:
        logger.error(
            "WhatsApp API error %s: %s", r.status_code, r.text[:2000]
        )
    r.raise_for_status()
