# WhatsApp Production Reporting Agent

A self-hosted WhatsApp bot that receives daily factory production updates from workers via WhatsApp, parses them with an LLM, persists them to an XLSX datastore, and automatically emails a formatted monthly report — triggered on every incoming message and/or on a daily schedule.

```
Worker → WhatsApp Cloud API → this server → OpenAI parser → XLSX store → email report
```

## Features

- **Webhook ingestion** — receives and verifies WhatsApp Cloud API webhooks (Meta-spec compliant)
- **LLM parsing** — uses OpenAI (GPT-4.1-mini / GPT-5) to extract structured fields from free-text messages; falls back to a regex parser for common formats
- **Multi-factory support** — maps WhatsApp sender phone numbers to named factories, each with its own monthly plan and weekly off-day
- **XLSX data store** — appends/upserts daily rows into an `.xlsx` file; no database required
- **Email reports** — sends a formatted multi-sheet monthly report via [Resend](https://resend.com) (default) or SMTP, with automatic retry and deduplication
- **Scheduled reports** — optional APScheduler job fires the report email at a configurable time each day
- **Guided replies** — bot replies to the sender when a message is incomplete or unrecognised

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  WhatsApp Cloud API (Meta)                           │
│   POST /webhook  (production update message)         │
└────────────────────┬─────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │   FastAPI app.py    │
          │  (webhook handler)  │
          └────┬───────────┬────┘
               │           │
    ┌──────────▼───┐  ┌────▼──────────────┐
    │ llm_parser   │  │  whatsapp_cloud   │
    │ (OpenAI +    │  │  (reply to sender)│
    │  regex fall- │  └───────────────────┘
    │  back)       │
    └──────┬───────┘
           │
    ┌──────▼───────┐       ┌──────────────────┐
    │   db.py      │       │   scheduler.py   │
    │ (XLSX store) │       │ (APScheduler,    │
    └──────┬───────┘       │  daily cron job) │
           │               └────────┬─────────┘
    ┌──────▼──────────────────────▼─┐
    │       report.py               │
    │  (generate monthly XLSX)      │
    └──────────────┬────────────────┘
                   │
            ┌──────▼──────┐
            │  emailer.py │
            │  (Resend /  │
            │   SMTP)     │
            └─────────────┘
```

---

## Prerequisites

- Python 3.10+
- A **[Meta WhatsApp Business](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)** app with a phone number and access token
- An **[OpenAI](https://platform.openai.com/api-keys)** API key
- An email delivery credential — either a **[Resend](https://resend.com)** API key (recommended) or SMTP credentials
- A publicly reachable HTTPS URL for the webhook (use [ngrok](https://ngrok.com) for local development)

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/your-org/whatsapp-report-agent.git
cd whatsapp-report-agent/whatsapp_report_agent

# 2. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and fill in your credentials (see Environment variables below)

# 5. Start the server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Local development with ngrok

```bash
ngrok http 8000
# Copy the https:// URL, e.g. https://abc123.ngrok.io
```

Set the webhook URL in your Meta app dashboard:
- **Callback URL**: `https://abc123.ngrok.io/webhook_meta`
- **Verify token**: value of `WHATSAPP_VERIFY_TOKEN` in your `.env`

---

## Factory configuration

Factories are defined in `config.py`. Edit the `FACTORIES` dict to match your setup:

```python
FACTORIES: dict[str, FactoryConfig] = {
    "plant_a": FactoryConfig(
        key="plant_a",
        display_name="Plant A",
        monthly_plan_pcs=10_000_000,   # monthly production target (pieces)
        off_day="Sunday",              # weekly off-day (no target computed)
    ),
    "plant_b": FactoryConfig(
        key="plant_b",
        display_name="Plant B",
        monthly_plan_pcs=6_000_000,
        off_day="Thursday",
    ),
    # add more factories as needed
}
```

Map WhatsApp sender phone numbers to factory keys. You can do this two ways:

**Option A — hardcode in `config.py`** (for a fixed setup):
```python
_DEFAULT_SENDER_TO_FACTORY: dict[str, str] = {
    "919900011122": "plant_a",
    "919900033344": "plant_b",
}
```

**Option B — environment variable** (for runtime configuration):
```
SENDER_TO_FACTORY_MAP=919900011122=plant_a,919900033344=plant_b
# or JSON:
SENDER_TO_FACTORY_MAP={"919900011122":"plant_a","919900033344":"plant_b"}
```

Phone numbers are normalised to digits-only before matching, so `+91-99000-11122`, `919900011122`, and `91 9900011122` all resolve to the same key.

---

## Message format

The bot accepts free-text messages. It first tries a structured regex parser, then falls back to an OpenAI LLM. Both support units like `k`, `lac`, `lakh`, and `cr`.

Example messages the bot understands:

```
Daily Production: 48,500
Daily Production Target: 50,000
Daily Despatch: 42,000
Remarks: cutter problem on line 2
```

```
production 48k dispatch 42k target 50k
```

If a required field is missing, the bot replies to the sender asking for it.

### System-computed target

If the sender does not include a production target, the bot computes one automatically:

```
system_target = monthly_plan_pcs / ASSUMED_WORKING_DAYS   (rounded)
                0                                          (on off_day)
```

`ASSUMED_WORKING_DAYS` defaults to `24` and can be changed in `config.py`.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | yes | — | OpenAI API key |
| `WHATSAPP_VERIFY_TOKEN` | yes | — | Token you set in the Meta webhook config |
| `WHATSAPP_ACCESS_TOKEN` | yes | — | Meta permanent / temporary access token |
| `WHATSAPP_PHONE_NUMBER_ID` | yes | — | Phone number ID from Meta app dashboard |
| `REPORT_RECIPIENT_EMAIL` | yes | — | Address(es) to send daily reports to |
| `EMAIL_PROVIDER` | no | `resend` | `resend` or `smtp` |
| `RESEND_API_KEY` | if Resend | — | Resend API key |
| `EMAIL_FROM` | no | `SMTP_USER` | Sender address shown in emails |
| `SMTP_HOST` | if SMTP | — | SMTP server hostname |
| `SMTP_PORT` | no | `587` | SMTP port (587 = STARTTLS, 465 = SSL) |
| `SMTP_USER` | if SMTP | — | SMTP login username |
| `SMTP_PASS` | if SMTP | — | SMTP login password |
| `SMTP_RETRY_COUNT` | no | `3` | Number of send attempts before giving up |
| `SMTP_RETRY_BASE_DELAY` | no | `2` | Initial retry delay in seconds |
| `SMTP_RETRY_MAX_DELAY` | no | `30` | Maximum retry delay in seconds |
| `ENABLE_DAILY_REPORT_EMAIL` | no | `false` | Set `true` to enable scheduled 8 PM IST email |
| `SENDER_TO_FACTORY_MAP` | no | — | Phone→factory mappings (see above) |
| `DEFAULT_FACTORY_KEY` | no | — | Fallback factory for unmapped senders |
| `TZ` | no | `Asia/Kolkata` | Server timezone (affects scheduler) |
| `DATA_XLSX_PATH` | no | `out/test_data.xlsx` | Path to the XLSX data file |
| `OUTPUT_DIR` | no | `out` | Directory for generated report files |
| `LOG_DIR` | no | `logs/` | Log file directory |
| `LOG_FILE` | no | `whatsapp_report_agent.log` | Log file name |
| `LOG_LEVEL` | no | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, …) |

---

## Running tests

```bash
cd whatsapp_report_agent
pytest tests/
```

To simulate a week of production data and generate a sample report + email:

```bash
python tests/simulate_week.py
```

---

## Deployment

The app is a standard ASGI app. Any platform that can run Python works.

**Render / Railway / Fly.io (recommended for beginners)**

1. Set all environment variables in the platform dashboard.
2. Set the start command to:
   ```
   uvicorn whatsapp_report_agent.app:app --host 0.0.0.0 --port $PORT
   ```
3. Point the Meta webhook URL at your deployed `https://your-app.example.com/webhook_meta`.

**Docker**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY whatsapp_report_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY whatsapp_report_agent/ .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Project structure

```
whatsapp_report_agent/
├── app.py              — FastAPI app, webhook endpoints, orchestration
├── config.py           — Env var loading, factory definitions, sender mapping
├── db.py               — XLSX-backed data store (upsert, fetch, deduplication)
├── llm_parser.py       — OpenAI + regex parser for WhatsApp messages
├── report.py           — Monthly XLSX report generator (formatted, multi-sheet)
├── emailer.py          — Email delivery via Resend or SMTP with retry
├── scheduler.py        — APScheduler cron job for daily email
├── whatsapp_cloud.py   — WhatsApp Cloud API client (send messages)
├── requirements.txt    — Python dependencies
└── tests/
    ├── simulate_week.py            — Populate DB with sample data and send report
    ├── test_email_dedupe.py        — Email deduplication logic
    ├── test_email_provider.py      — Resend / SMTP provider selection
    ├── test_email_retry.py         — SMTP retry behaviour
    ├── test_sender_mapping.py      — Phone number normalisation and factory lookup
    ├── test_whatsapp_email.py      — End-to-end webhook → email flow
    └── test_workflow_truewow.py    — Full workflow integration test
```

---

## License

MIT
