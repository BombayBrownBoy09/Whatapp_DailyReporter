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


# ── Factory definitions ───────────────────────────────────────────────────────
# Add one entry per factory / production unit.
# key          : short identifier used everywhere in the system
# display_name : human-readable label used in reports and emails
# monthly_plan_pcs : monthly production target in pieces
# off_day      : weekly off-day name — no system target is computed for this day
FACTORIES: dict[str, FactoryConfig] = {
    "plant_a": FactoryConfig(key="plant_a", display_name="Plant A", monthly_plan_pcs=10_000_000, off_day="Sunday"),
    "plant_b": FactoryConfig(key="plant_b", display_name="Plant B", monthly_plan_pcs=6_000_000, off_day="Thursday"),
    # Add more factories as needed:
    # "plant_c": FactoryConfig(key="plant_c", display_name="Plant C", monthly_plan_pcs=5_000_000, off_day="Wednesday"),
}

# ── Sender → factory mapping ──────────────────────────────────────────────────
# Map each factory manager's WhatsApp number (digits only, no +) to a factory key.
# You can also set this at runtime via the SENDER_TO_FACTORY_MAP env variable
# (see README for format details).
_DEFAULT_SENDER_TO_FACTORY: dict[str, str] = {
    # "919900011122": "plant_a",
    # "919900033344": "plant_b",
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
SMTP_RETRY_COUNT = int(os.environ.get("SMTP_RETRY_COUNT", "3"))
SMTP_RETRY_BASE_DELAY = float(os.environ.get("SMTP_RETRY_BASE_DELAY", "2"))
SMTP_RETRY_MAX_DELAY = float(os.environ.get("SMTP_RETRY_MAX_DELAY", "30"))

EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "resend").strip().lower()
EMAIL_FROM = os.environ.get("EMAIL_FROM") or SMTP_USER
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ENABLE_DAILY_REPORT_EMAIL = os.environ.get("ENABLE_DAILY_REPORT_EMAIL", "false").lower() in {"1", "true", "yes"}

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
