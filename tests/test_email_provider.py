from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import emailer


class TestEmailProviderRouting(unittest.TestCase):
    def test_smtp_provider_uses_smtp(self) -> None:
        with mock.patch.object(emailer, "EMAIL_PROVIDER", "smtp"), \
            mock.patch.object(emailer, "_send_smtp_email") as smtp_send, \
            mock.patch.object(emailer, "_send_resend_email") as resend_send:
            emailer.send_text_email("Hello", "Body")

        smtp_send.assert_called_once()
        resend_send.assert_not_called()

    def test_resend_provider_uses_resend(self) -> None:
        with mock.patch.object(emailer, "EMAIL_PROVIDER", "resend"), \
            mock.patch.object(emailer, "_send_smtp_email") as smtp_send, \
            mock.patch.object(emailer, "_send_resend_email") as resend_send:
            emailer.send_text_email("Hello", "Body")

        resend_send.assert_called_once()
        smtp_send.assert_not_called()

    def test_resend_fallbacks_to_smtp(self) -> None:
        with mock.patch.object(emailer, "EMAIL_PROVIDER", "resend"), \
            mock.patch.object(emailer, "_send_smtp_email") as smtp_send, \
            mock.patch.object(emailer, "_send_resend_email", side_effect=RuntimeError("boom")):
            emailer.send_text_email("Hello", "Body")

        smtp_send.assert_called_once()

    def test_resend_attachment_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "sample.xlsx"
            file_path.write_bytes(b"hello")

            attachment = emailer._build_resend_attachment(str(file_path))

        self.assertEqual(attachment["filename"], "sample.xlsx")
        self.assertEqual(attachment["content"], "aGVsbG8=")
        self.assertIn("content_type", attachment)


if __name__ == "__main__":
    unittest.main()
