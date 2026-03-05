from __future__ import annotations

import os
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


@dataclass(frozen=True)
class FactoryConfig:
    key: str
    display_name: str
    monthly_plan_pcs: int
    off_day: str  # "Sunday", "Wednesday", etc.


FACTORIES: dict[str, FactoryConfig] = {
    "truewow": FactoryConfig(key="truewow", display_name="Truewow", monthly_plan_pcs=10_000_000, off_day="Sunday"),
    "solace": FactoryConfig(key="solace", display_name="Solace", monthly_plan_pcs=6_000_000, off_day="Thursday"),
    "garg": FactoryConfig(key="garg", display_name="Garg Hygiene", monthly_plan_pcs=6_000_000, off_day="Sunday"),
    "proctus": FactoryConfig(key="proctus", display_name="Proctus", monthly_plan_pcs=5_000_000, off_day="Wednesday"),
    "devcap": FactoryConfig(key="devcap", display_name="Dev & Cap", monthly_plan_pcs=6_000_000, off_day="Sunday"),
}

# Map WhatsApp sender phone numbers -> factory key (YOU MUST FILL THESE)
# Example:
# SENDER_TO_FACTORY = { "9199xxxxxx01": "truewow", ... }
_DEFAULT_SENDER_TO_FACTORY: dict[str, str] = {
    # "19843296624": "truewow",
    # "919940966624": "truewow",
    # "9199xxxxxx02": "solace",
    # "9199xxxxxx03": "garg",
    # "9199xxxxxx04": "proctus",
    "19843296624": "devcap",
}


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isdigit())


def _parse_sender_map(raw: str) -> dict[str, str]:
    raw = raw.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        data = json.loads(raw)
        if isinstance(data, dict):
            return {normalize_phone(str(k)): str(v) for k, v in data.items()}
        return {}

    pairs: Iterable[str] = (p.strip() for p in raw.replace(";", ",").split(","))
    parsed: dict[str, str] = {}
    for pair in pairs:
        if not pair:
            continue
        if "=" in pair:
            phone, factory = pair.split("=", 1)
        elif ":" in pair:
            phone, factory = pair.split(":", 1)
        else:
            continue
        parsed[normalize_phone(phone)] = factory.strip()
    return parsed


def _build_sender_map() -> dict[str, str]:
    env_raw = os.environ.get("SENDER_TO_FACTORY_MAP") or os.environ.get("SENDER_TO_FACTORY_JSON")
    env_map = _parse_sender_map(env_raw) if env_raw else {}
    base = {normalize_phone(k): v for k, v in _DEFAULT_SENDER_TO_FACTORY.items()}
    base.update(env_map)
    return base


SENDER_TO_FACTORY: dict[str, str] = _build_sender_map()

ASSUMED_WORKING_DAYS = 24  # per your instruction

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

WHATSAPP_VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]
WHATSAPP_ACCESS_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]

REPORT_RECIPIENT_EMAIL = os.environ["REPORT_RECIPIENT_EMAIL"]

TZ = os.environ.get("TZ", "Asia/Kolkata")

DEFAULT_FACTORY_KEY = os.environ.get("DEFAULT_FACTORY_KEY")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.environ.get("LOG_DIR", str(BASE_DIR / "logs"))
LOG_FILE = os.environ.get("LOG_FILE", "whatsapp_report_agent.log")

_data_path_raw = os.environ.get("DATA_XLSX_PATH", "out/test_data.xlsx")
_output_dir_raw = os.environ.get("OUTPUT_DIR", "out")

DATA_XLSX_PATH = str(BASE_DIR / _data_path_raw) if not os.path.isabs(_data_path_raw) else _data_path_raw
OUTPUT_DIR = str(BASE_DIR / _output_dir_raw) if not os.path.isabs(_output_dir_raw) else _output_dir_raw
