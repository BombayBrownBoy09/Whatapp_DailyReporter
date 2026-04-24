from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import db


class TestEmailDedupe(unittest.TestCase):
    def test_mark_and_check_email_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / "data.xlsx"
            db.DATA_XLSX_PATH = str(temp_path)

            db.init_db()
            db.upsert_daily_update(
                factory_key="devcap",
                update_date=date(2026, 3, 6),
                prod_actual=100,
                prod_target=200,
                dispatch_actual=50,
                dispatch_target=100,
                remarks="ok",
                raw_message="hi",
                sender_phone="123",
            )

            self.assertFalse(db.is_email_up_to_date("devcap", date(2026, 3, 6), "hash-a"))
            db.mark_email_sent("devcap", date(2026, 3, 6), sent_at="2026-03-06", payload_hash="hash-a")
            self.assertTrue(db.is_email_up_to_date("devcap", date(2026, 3, 6), "hash-a"))
            self.assertFalse(db.is_email_up_to_date("devcap", date(2026, 3, 6), "hash-b"))


if __name__ == "__main__":
    unittest.main()
