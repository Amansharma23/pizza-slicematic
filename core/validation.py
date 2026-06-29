"""Input validation. Every function returns ``(ok, value_or_message)``.

On success: ``(True, cleaned_value)``. On failure: ``(False, error_message)``
where the message says what was wrong and what is expected (NFR-2). Nothing here
raises on bad input — callers re-prompt using the message.
"""

from __future__ import annotations

NAME_MIN = 2
NAME_MAX = 40
QTY_MIN = 1
QTY_MAX = 10

PAYMENT_MODES = {"1": "Cash", "2": "Card", "3": "UPI"}


def validate_name(raw: str) -> tuple[bool, str]:
    """Alphabets and spaces only, 2–40 chars, not blank/whitespace-only."""
    if raw is None:
        return False, "Please enter a name."
    name = raw.strip()
    if not name:
        return (
            False,
            "Name cannot be blank. Use letters and spaces only (2–40 characters).",
        )
    if not all(ch.isalpha() or ch == " " for ch in name):
        return False, "Name may contain letters and spaces only — no digits or symbols."
    if len(name) < NAME_MIN:
        return False, f"Name is too short. Use at least {NAME_MIN} characters."
    if len(name) > NAME_MAX:
        return False, f"Name is too long. Use at most {NAME_MAX} characters."
    return True, name


def validate_phone(raw: str) -> tuple[bool, str]:
    """Exactly 10 digits, first digit one of 6, 7, 8, 9 (Indian mobile)."""
    if raw is None:
        return False, "Please enter a phone number."
    phone = raw.strip()
    if not phone:
        return (
            False,
            "Phone number cannot be blank. Enter 10 digits starting with 6, 7, 8 or 9.",
        )
    if not phone.isdigit():
        return False, "Phone must be digits only (no spaces, +, or letters)."
    if len(phone) != 10:
        return False, "Phone must be exactly 10 digits."
    if phone[0] not in "6789":
        return False, "Phone must start with 6, 7, 8 or 9. Please re-enter."
    return True, phone


def validate_quantity(raw) -> tuple[bool, int | str]:
    """Integer 1–10 only. Reject floats, strings, zero, negatives, > 10, empty."""
    if raw is None:
        return False, f"Please enter a quantity ({QTY_MIN}–{QTY_MAX})."
    text = str(raw).strip()
    if not text:
        return (
            False,
            f"Quantity cannot be blank. Enter a whole number {QTY_MIN}–{QTY_MAX}.",
        )
    # Pure integer only: optional sign then digits. '2.5' and 'three' are rejected here.
    candidate = text[1:] if text[0] in "+-" else text
    if not candidate.isdigit():
        return (
            False,
            f"Quantity must be a whole number {QTY_MIN}–{QTY_MAX} (no decimals or words).",
        )
    qty = int(text)
    if qty < QTY_MIN:
        return False, f"Quantity must be at least {QTY_MIN}."
    if qty > QTY_MAX:
        return (
            False,
            f"Maximum capacity is {QTY_MAX} pizzas per order. Please enter {QTY_MIN}–{QTY_MAX}.",
        )
    return True, qty


def validate_selection(raw, n_items: int) -> tuple[bool, int | str]:
    """A list number in 1..n_items. Reject letters, blank, 0, out-of-range."""
    if raw is None:
        return False, f"Please pick a number from 1 to {n_items}."
    text = str(raw).strip()
    if not text:
        return False, f"Selection cannot be blank. Enter a number from 1 to {n_items}."
    candidate = text[1:] if text[0] in "+-" else text
    if not candidate.isdigit():
        return False, f"Enter the item number (1 to {n_items}), not text or a price."
    choice = int(text)
    if choice < 1 or choice > n_items:
        return False, f"That number is out of range. Choose from 1 to {n_items}."
    return True, choice


def validate_payment(raw) -> tuple[bool, str]:
    """One of 1=Cash, 2=Card, 3=UPI. Also accepts the mode name itself."""
    if raw is None:
        return False, "Please choose a payment mode: 1 Cash, 2 Card, 3 UPI."
    text = str(raw).strip()
    if text in PAYMENT_MODES:
        return True, PAYMENT_MODES[text]
    for mode in PAYMENT_MODES.values():
        if text.lower() == mode.lower():
            return True, mode
    return False, "Invalid payment mode. Choose 1 Cash, 2 Card or 3 UPI."
