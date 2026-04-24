from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from emailer import _send_with_retry


class TestEmailRetry(unittest.TestCase):
    def test_retries_then_succeeds(self) -> None:
        attempts = {"count": 0}
        sleeps: list[float] = []

        def send_fn() -> None:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("temporary failure")

        def sleep_fn(delay: float) -> None:
            sleeps.append(delay)

        _send_with_retry(send_fn, retries=3, base_delay=1, max_delay=5, sleep_fn=sleep_fn)
        self.assertEqual(attempts["count"], 3)
        self.assertEqual(sleeps, [1, 2])

    def test_retries_exhausted(self) -> None:
        attempts = {"count": 0}

        def send_fn() -> None:
            attempts["count"] += 1
            raise RuntimeError("fail")

        with self.assertRaises(RuntimeError):
            _send_with_retry(send_fn, retries=2, base_delay=1, max_delay=5, sleep_fn=lambda _: None)

        self.assertEqual(attempts["count"], 2)


if __name__ == "__main__":
    unittest.main()
