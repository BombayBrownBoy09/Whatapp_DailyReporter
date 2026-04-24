from __future__ import annotations

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import TZ
from report import generate_monthly_report_xlsx
from emailer import send_email_with_attachment


def daily_send_job() -> None:
    # “Daily attached report” — generate current month file each day and email it
    now = datetime.now()
    path = generate_monthly_report_xlsx(now.year, now.month)
    send_email_with_attachment(
        subject=f"Daily Factory Report — {now:%Y-%m-%d}",
        body="Attached: daily production/dispatch tracking report (auto-generated).",
        attachment_path=path,
    )


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=TZ)

    # Send every day at 8:00 PM IST (change if you want)
    sched.add_job(daily_send_job, CronTrigger(hour=20, minute=0))
    sched.start()
    return sched
