from __future__ import annotations

from datetime import date, timedelta
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config import FACTORIES  # noqa: E402
from db import init_db, upsert_daily_update  # noqa: E402
from report import generate_monthly_report_xlsx  # noqa: E402
from emailer import send_email_with_attachment  # noqa: E402


def _month_key(d: date) -> tuple[int, int]:
    return d.year, d.month


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _send_report_email(year: int, month: int, attachment_path: str) -> None:
    send_email_with_attachment(
        subject=f"Daily Factory Report — {year}-{month:02d}",
        body="Attached: daily production/dispatch tracking report (auto-generated).",
        attachment_path=attachment_path,
    )


def simulate_week(start_date: date, days: int = 28, send_email: bool = True) -> list[str]:
    init_db()

    day1_message = {
        "prod_actual": 1000,
        "prod_target": 1500,
        "dispatch_actual": 500,
        "dispatch_target": 800,
        "remarks": "cutter problem",
    }

    for i in range(days):
        d = start_date + timedelta(days=i)
        for factory_key in FACTORIES:
            upsert_daily_update(
                factory_key=factory_key,
                update_date=d,
                prod_actual=day1_message["prod_actual"],
                prod_target=day1_message["prod_target"],
                dispatch_actual=day1_message["dispatch_actual"],
                dispatch_target=day1_message["dispatch_target"],
                remarks=day1_message["remarks"],
                raw_message=(
                    "Daily Production: 1000\n"
                    "Daily Production Target: 1500\n"
                    "Daily Despatch: 500\n"
                    "Daily Despatch Target: 800\n"
                    "Remarks: cutter problem"
                ),
                sender_phone="test",
            )

    start_year, start_month = _month_key(start_date)
    end_date = start_date + timedelta(days=days - 1)
    end_year, end_month = _month_key(end_date)

    reports: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        report_path = generate_monthly_report_xlsx(year, month)
        reports.append(report_path)
        if send_email:
            _send_report_email(year, month, report_path)
        year, month = _next_month(year, month)

    return reports


if __name__ == "__main__":
    load_dotenv()
    start_date_str = os.environ.get("START_DATE")
    days_str = os.environ.get("DAYS", "28")
    if start_date_str:
        year, month, day = map(int, start_date_str.split("-"))
        start_date = date(year, month, day)
    else:
        start_date = date.today()
    send_email = os.environ.get("SEND_EMAIL", "1") not in {"0", "false", "False"}
    report_paths = simulate_week(start_date, days=int(days_str), send_email=send_email)
    for path in report_paths:
        print(path)
