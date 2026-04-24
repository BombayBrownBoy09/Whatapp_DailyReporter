from __future__ import annotations

import os
import sys
import requests
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config import FACTORIES, SENDER_TO_FACTORY
from db import init_db


MESSAGE_BODY = (
    "Daily Production: 1000\n"
    "Daily Production Target: 1500\n"
    "Daily Despatch: 500\n"
    "Daily Despatch Target: 800\n"
    "Remarks: cutter problem"
)


def main() -> None:
    init_db()

    sender = "19843296624"
    factory_key = SENDER_TO_FACTORY.get(sender, "truewow")
    factory = FACTORIES[factory_key]

    payload = {
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
                                {"profile": {"name": "Bhargav JS"}, "wa_id": sender}
                            ],
                            "messages": [
                                {
                                    "from": sender,
                                    "id": "wamid.TEST_WORKFLOW",
                                    "timestamp": "172560793",
                                    "text": {"body": MESSAGE_BODY},
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

    webhook_url = os.environ.get("WEBHOOK_URL", "http://127.0.0.1:8000/webhook")
    resp = requests.post(webhook_url, json=payload, timeout=30)
    print(f"POST {webhook_url} -> {resp.status_code}")
    print(resp.text)


if __name__ == "__main__":
    main()
