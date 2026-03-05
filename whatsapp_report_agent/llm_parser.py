from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Optional
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


@dataclass
class ParsedUpdate:
    prod_actual: Optional[int]
    prod_target: Optional[int]
    dispatch_actual: Optional[int]
    dispatch_target: Optional[int]
    remarks: Optional[str]


SYSTEM = """
You extract structured daily factory updates from WhatsApp messages.

Return ONLY valid JSON with keys:
- prod_actual (integer or null)
- prod_target (integer or null)
- dispatch_actual (integer or null)
- dispatch_target (integer or null)
- remarks (string or null)

Rules:
- If message contains a number with commas, parse as integer.
- If units like "k" or "lac" appear, convert to integer pieces (k=1,000; lakh=100,000; lac=100,000; cr=10,000,000).
- If a field is missing, return null for that field.
- remarks: short free-text summary if any issue stated (breakdown, holiday, cutter problem, etc). If no remarks, null.
"""


def parse_whatsapp_message(text: str) -> ParsedUpdate:
    fallback = _parse_structured_text(text)
    if fallback is not None:
        return fallback

    try:
        resp = client.responses.create(
            model="gpt-5",
            input=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        data = resp.output[0].content[0].json  # type: ignore[attr-defined]
    except TypeError:
        chat_resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        content = chat_resp.choices[0].message.content or "{}"
        data = json.loads(content)

    return ParsedUpdate(
        prod_actual=data.get("prod_actual"),
        prod_target=data.get("prod_target"),
        dispatch_actual=data.get("dispatch_actual"),
        dispatch_target=data.get("dispatch_target"),
        remarks=data.get("remarks"),
    )


def _parse_structured_text(text: str) -> Optional[ParsedUpdate]:
    normalized = " ".join(text.split())

    def extract_number(label_patterns: list[str]) -> Optional[int]:
        for pattern in label_patterns:
            matches = list(re.finditer(pattern, normalized, flags=re.IGNORECASE))
            if not matches:
                continue
            raw = matches[-1].group("value")
            if raw is None:
                continue
            parsed = _parse_number(raw)
            if parsed is not None:
                return parsed
        return None

    prod_actual = extract_number(
        [
            r"daily\s+production\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"production\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
        ]
    )
    prod_target = extract_number(
        [
            r"daily\s+production\s+target\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"production\s+target\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
        ]
    )
    dispatch_actual = extract_number(
        [
            r"daily\s+despatch\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"daily\s+dispatch\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"despatch\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"dispatch\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
        ]
    )
    dispatch_target = extract_number(
        [
            r"daily\s+despatch\s+target\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"daily\s+dispatch\s+target\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"despatch\s+target\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
            r"dispatch\s+target\s*:\s*(?P<value>[\d,\.]+\s*(?:k|lac|lakh|cr|crore)?)",
        ]
    )

    remarks_matches = re.findall(
        r"^\s*remarks\s*:\s*(?P<value>.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    remarks = remarks_matches[-1].strip() if remarks_matches else None

    if all(
        value is None
        for value in (prod_actual, prod_target, dispatch_actual, dispatch_target, remarks)
    ):
        return None

    return ParsedUpdate(
        prod_actual=prod_actual,
        prod_target=prod_target,
        dispatch_actual=dispatch_actual,
        dispatch_target=dispatch_target,
        remarks=remarks,
    )


def _parse_number(raw: str) -> Optional[int]:
    cleaned = raw.strip().lower().replace(",", "")
    multiplier = 1
    for suffix, mult in (("k", 1_000), ("lac", 100_000), ("lakh", 100_000), ("cr", 10_000_000), ("crore", 10_000_000)):
        if cleaned.endswith(suffix):
            multiplier = mult
            cleaned = cleaned[: -len(suffix)].strip()
            break
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return int(value * multiplier)
