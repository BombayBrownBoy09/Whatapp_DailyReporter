# WhatsApp Production Reporting Agent

This service ingests WhatsApp Cloud API webhooks, extracts daily production updates, stores them in an XLSX-backed data store, and emails a consolidated report.

## Key environment variables

- `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
- `SMTP_RETRY_COUNT`, `SMTP_RETRY_BASE_DELAY`, `SMTP_RETRY_MAX_DELAY` (optional)
- `REPORT_RECIPIENT_EMAIL`
- `SENDER_TO_FACTORY_MAP` (optional): map senders to factories.
	- Format: `919900011122=truewow,919900033344=solace`
	- Or JSON: `{ "919900011122": "truewow" }`
- `DEFAULT_FACTORY_KEY` (optional): fallback factory when sender isn’t mapped.
- `LOG_DIR`, `LOG_FILE`, `LOG_LEVEL` (optional): logging output controls.

## Notes

- Sender phone numbers are normalized to digits-only before matching.
- Webhook logs are written to both stdout and `LOG_DIR/LOG_FILE`.
