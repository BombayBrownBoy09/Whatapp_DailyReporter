from __future__ import annotations

from datetime import date
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request, HTTPException
from config import (
    WHATSAPP_VERIFY_TOKEN,
    SENDER_TO_FACTORY,
    FACTORIES,
    DEFAULT_FACTORY_KEY,
    LOG_LEVEL,
    LOG_DIR,
    LOG_FILE,
    ENABLE_DAILY_REPORT_EMAIL,
    normalize_phone,
)
from db import init_db, upsert_daily_update, fetch_daily_update, mark_email_sent, is_email_up_to_date
from llm_parser import parse_whatsapp_message
from whatsapp_cloud import send_whatsapp_message
from scheduler import start_scheduler
from emailer import send_email_with_attachment
from report import generate_monthly_report_xlsx, computed_system_target

logger = logging.getLogger("whatsapp_report_agent")

app = FastAPI()


def _configure_logging() -> None:
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    if not root.handlers:
        root.addHandler(stream_handler)
        root.addHandler(file_handler)
    else:
        root.addHandler(file_handler)

    logger.info("Logging initialized at %s", log_path)


def _is_relevant_message(text: str) -> bool:
    normalized = " ".join(text.lower().strip().split())
    if not normalized:
        return False

    keywords = [
        "production",
        "prod",
        "dispatch",
        "despatch",
        "target",
        "remarks",
    ]
    if any(k in normalized for k in keywords):
        return True
    return any(ch.isdigit() for ch in normalized)


@app.on_event("startup")
def on_startup() -> None:
    _configure_logging()
    init_db()
    if ENABLE_DAILY_REPORT_EMAIL:
        start_scheduler()


@app.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
    hub_challenge: Optional[str] = None,
):
    # Meta uses query params named: hub.mode, hub.verify_token, hub.challenge
    # FastAPI maps them if you pass exact names; easier: read raw below if needed.
    # We'll also support direct param names if your gateway rewrites them.
    if hub_verify_token != WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Verification token mismatch")
    return int(hub_challenge) if hub_challenge else 0


@app.get("/webhook_meta")
async def verify_webhook_meta(request: Request):
    # Robust version reading exact Meta params
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN and challenge:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def whatsapp_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()
    logger.info("Webhook received")

    payload_path = Path(__file__).resolve().parent / "tests" / "ngrok_payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, indent=2))

    # WhatsApp Cloud payload nesting:
    # entry[0].changes[0].value.messages[0].from + text.body
    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            logger.info("Webhook ignored (no messages field)")
            return {"ok": True}  # delivery receipts etc.
        msg = messages[0]
        sender = msg.get("from")  # phone number string without '+'
        contacts = value.get("contacts", [])
        wa_id = contacts[0].get("wa_id") if contacts else None
        text = (msg.get("text") or {}).get("body") or ""
    except Exception:
        logger.exception("Malformed webhook payload")
        raise HTTPException(status_code=400, detail="Malformed webhook payload")

    logger.info("Message from %s: %s", sender, text.replace("\n", " | ")[:500])

    # Identify factory by sender phone number
    sender_candidates = [normalize_phone(sender), normalize_phone(wa_id)]
    sender_candidates = [s for s in sender_candidates if s]
    factory_key = next(
        (SENDER_TO_FACTORY.get(candidate) for candidate in sender_candidates if candidate in SENDER_TO_FACTORY),
        None,
    )
    if not factory_key and DEFAULT_FACTORY_KEY in FACTORIES:
        factory_key = DEFAULT_FACTORY_KEY
        logger.warning(
            "Sender %s not mapped; using DEFAULT_FACTORY_KEY=%s",
            sender,
            DEFAULT_FACTORY_KEY,
        )

    if not factory_key or factory_key not in FACTORIES:
        logger.warning(
            "Unregistered sender %s (candidates: %s); no factory mapping",
            sender,
            sender_candidates,
        )
        # Optionally reply asking them to register
        # send_whatsapp_message(sender, "Please ask admin to register your number to a factory.")
        return {"ok": True}

    logger.info("Resolved factory %s for sender %s", factory_key, sender)

    if not _is_relevant_message(text):
        today = date.today()
        system_target = computed_system_target(factory_key, today)
        guidance = (
            "I'm Skippy, Smilepad's production reporting agent. "
            "I only log daily production entries. "
            "Please send your daily update in this format:\n"
            "Daily Production: <value>\n"
            f"Daily Production Target: {system_target}\n"
            "Daily Despatch: <value>\n"
            "Remarks: <optional>"
        )
        try:
            send_whatsapp_message(sender, guidance)
        except Exception as exc:
            logger.exception("Failed to send guidance reply to %s: %s", sender, exc)
        return {"ok": True, "ignored": True}

    # Update date: assume message corresponds to "today" (server local date)
    today = date.today()

    existing = fetch_daily_update(factory_key, today)
    existing_raw = existing.get("raw_message") if existing else None
    combined_raw = text if not existing_raw else f"{existing_raw}\n\n---\n\n{text}"

    # Parse the combined daily payload so one entry is based on all messages for the day
    parsed = parse_whatsapp_message(combined_raw)

    system_target = computed_system_target(factory_key, today)
    prod_target = parsed.prod_target if parsed.prod_target is not None else system_target
    dispatch_target = parsed.dispatch_target if parsed.dispatch_target is not None else system_target

    upsert_daily_update(
        factory_key=factory_key,
        update_date=today,
        prod_actual=parsed.prod_actual,
        prod_target=prod_target,
        dispatch_actual=parsed.dispatch_actual,
        dispatch_target=dispatch_target,
        remarks=parsed.remarks,
        raw_message=combined_raw,
        sender_phone=sender,
    )

    missing_fields = []
    if parsed.prod_actual is None:
        missing_fields.append("Daily Production")
    if parsed.dispatch_actual is None:
        missing_fields.append("Daily Despatch")

    if missing_fields:
        follow_up = (
            "I'm Skippy, Smilepad's production reporting agent. "
            "I accept one daily production entry per factory based on all messages received that day and "
            "email the compiled report at end of day.\n\n"
            "To complete today's entry, please share: "
            + ", ".join(missing_fields)
            + "."
        )
        try:
            send_whatsapp_message(sender, follow_up)
        except Exception as exc:
            logger.exception("Failed to send follow-up to %s: %s", sender, exc)
        return {"ok": True, "missing": missing_fields}

    report_path = generate_monthly_report_xlsx(today.year, today.month)

    subject = (
        f"Skippy payload — {FACTORIES[factory_key].display_name} — {today.isoformat()}"
    )
    body = (
        "Latest factory report attached. This attachment is regenerated on every message and "
        "overwrites the same-day XLSX file on disk.\n\n"
        f"Sender: {sender}\n"
        f"Factory: {FACTORIES[factory_key].display_name}\n\n"
        f"Message:\n{combined_raw}\n"
    )
    payload_hash = str(hash(combined_raw))
    if is_email_up_to_date(factory_key, today, payload_hash):
        logger.info("Report email already sent for current payload %s on %s; skipping.", factory_key, today)
    else:
        try:
            logger.info("Sending report email to %s", report_path)
            send_email_with_attachment(subject, body, report_path)
            mark_email_sent(factory_key, today, payload_hash=payload_hash)
            logger.info("Report email sent")
        except Exception as exc:
            logger.exception("Failed to send notification email: %s", exc)

    confirmation = (
        f"Logged for {today.isoformat()} ✅\n"
        f"Prod: {parsed.prod_actual} / target {prod_target}\n"
        f"Dispatch: {parsed.dispatch_actual} / target {dispatch_target}\n"
        f"Remarks: {parsed.remarks or '-'}"
    )
    try:
        send_whatsapp_message(sender, confirmation)
    except Exception as exc:
        logger.exception("Failed to send confirmation to %s: %s", sender, exc)

    return {"ok": True}
