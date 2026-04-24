from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from config import normalize_phone, _parse_sender_map


class TestSenderMapping(unittest.TestCase):
    def test_normalize_phone_digits_only(self) -> None:
        self.assertEqual(normalize_phone("+91 98765-43210"), "919876543210")

    def test_parse_sender_map_kv(self) -> None:
        raw = "919900011122=truewow, 1-984-329-6624:devcap"
        parsed = _parse_sender_map(raw)
        self.assertEqual(parsed["919900011122"], "truewow")
        self.assertEqual(parsed["19843296624"], "devcap")

    def test_parse_sender_map_json(self) -> None:
        raw = '{"+91 99900 11122": "solace"}'
        parsed = _parse_sender_map(raw)
        self.assertEqual(parsed["919990011122"], "solace")


if __name__ == "__main__":
    unittest.main()
