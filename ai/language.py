"""Lightweight English/Hindi detection, run per turn (users may switch).

Rules (cheap, no model call):
  1. Any Devanagari character  -> Hindi.
  2. Otherwise, a romanized-Hindi (Hinglish) keyword  -> Hindi.
  3. Otherwise  -> English (the default).

Deliberately conservative: short greetings and ambiguous words stay English so
we don't mislabel plain English orders.
"""

from __future__ import annotations

import re

# Distinctly-Hindi romanized tokens. Words that are also common English
# (e.g. "do", "kar") are intentionally excluded to avoid false positives.
HINGLISH_WORDS = {
    "hai",
    "haan",
    "nahi",
    "nahin",
    "kya",
    "kyun",
    "kaise",
    "kaisa",
    "kitna",
    "kitne",
    "mujhe",
    "mera",
    "meri",
    "chahiye",
    "krpya",
    "kripya",
    "theek",
    "thik",
    "accha",
    "acha",
    "bhai",
    "bhaiya",
    "paisa",
    "paise",
    "bahut",
    "zyada",
    "khana",
    "dedo",
    "dijiye",
    "batao",
    "bataye",
    "order",  # kept out below — see note
}
# "order" is English too; remove it so it can't tip detection on its own.
HINGLISH_WORDS.discard("order")

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_WORD = re.compile(r"[a-z]+")


def detect(text: str | None) -> str:
    """Return 'hi' or 'en' for the given text."""
    if not text or not text.strip():
        return "en"
    if _DEVANAGARI.search(text):
        return "hi"
    words = set(_WORD.findall(text.lower()))
    if words & HINGLISH_WORDS:
        return "hi"
    return "en"
