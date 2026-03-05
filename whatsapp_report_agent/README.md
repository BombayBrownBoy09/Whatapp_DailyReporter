# WhatsApp Factory Report Agent

A FastAPI webhook that ingests WhatsApp Business Cloud messages, parses daily production/dispatch updates with an LLM, stores them in SQLite, generates Excel reports, and emails them daily.

## Features

- WhatsApp Cloud API webhook ingestion
- LLM parsing into structured fields
- SQLite storage with daily upserts
- Monthly Excel report with daily + cumulative totals
- Daily auto-email job (APS Scheduler)

## Prerequisites

- Python 3.10+
- WhatsApp Business Cloud API credentials
- OpenAI API key
- SMTP credentials (Gmail App Password recommended)

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env` and fill in values.
4. Map sender phone numbers to factory keys in `config.py`.

## Run locally

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Use a tunnel like ngrok to expose the webhook:

```bash
ngrok http 8000
```

Set the Meta webhook URLs to:

- Verification: `https://<ngrok-domain>/webhook_meta`
- Messages: `https://<ngrok-domain>/webhook`

## Using the WhatsApp Cloud API test number (dev mode)

You can test the full webhook → parse → report flow with Meta’s **test phone number**.
Only **test recipient** numbers can message the test number.

1. In **Meta → WhatsApp → Getting Started**, add your personal number as a **test recipient**.
2. Send the “join <code>” opt-in message to the test number.
3. In **WhatsApp → Configuration**, set:
	- Callback URL: `https://<your-domain>/webhook`
	- Verify token: value of `WHATSAPP_VERIFY_TOKEN`
	- Subscribe to: `messages`
4. Send a WhatsApp message to the test number (from your approved test recipient).

Limitations:

- Test number only works with approved test recipients.
- Not suitable for production; switch to your real Business number when ready.

## Message format (recommended)

```
Daily Production: 1000
Daily Production Target: 1500
Daily Despatch: 500
Daily Despatch Target: 800
Remarks: cutter problem
```

## Notes

- WhatsApp Cloud API only delivers messages sent to your Business number configured with a webhook.
- System target/day is computed from monthly plan and a 30-day working assumption (adjust in `config.py`).
- Daily updates are stored in an Excel file (default: `out/test_data.xlsx`). Set `DATA_XLSX_PATH` in `.env` to change location.
