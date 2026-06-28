"""Validation tests covering the 8 graded edge cases and the rules table."""

import pytest

from core import validation as v


# --- Name -------------------------------------------------------------------

def test_name_only_spaces_rejected():            # edge case 1
    ok, msg = v.validate_name("     ")
    assert ok is False and "blank" in msg.lower()


def test_name_empty_rejected():                  # edge case 6 (empty)
    assert v.validate_name("")[0] is False


def test_name_with_digits_rejected():
    assert v.validate_name("Rajan99")[0] is False


def test_name_too_short_rejected():
    assert v.validate_name("A")[0] is False


def test_name_too_long_rejected():
    assert v.validate_name("A" * 41)[0] is False


@pytest.mark.parametrize("name", ["Rajan", "Rajan Sharma", "Mary Jane Watson"])
def test_valid_names_accepted_and_trimmed(name):
    ok, value = v.validate_name(f"  {name}  ")
    assert ok is True and value == name


# --- Phone ------------------------------------------------------------------

def test_phone_starts_with_1_rejected():         # edge case 2
    ok, msg = v.validate_phone("1234567890")
    assert ok is False and "6, 7, 8" in msg


def test_phone_wrong_length_rejected():
    assert v.validate_phone("98765")[0] is False
    assert v.validate_phone("98765432100")[0] is False


def test_phone_non_digit_rejected():
    assert v.validate_phone("98765abcd0")[0] is False


def test_phone_empty_rejected():                 # edge case 6
    assert v.validate_phone("")[0] is False


@pytest.mark.parametrize("phone", ["9876543210", "6000000000", "7111111111", "8123456789"])
def test_valid_phones_accepted(phone):
    assert v.validate_phone(f" {phone} ") == (True, phone)


# --- Quantity ---------------------------------------------------------------

@pytest.mark.parametrize("bad", ["0", "11", "-1", "2.5", "three", "", "  "])
def test_quantity_invalid_rejected(bad):         # edge cases 3, 6, 7
    assert v.validate_quantity(bad)[0] is False


def test_quantity_above_cap_message():
    ok, msg = v.validate_quantity("11")
    assert ok is False and "capacity" in msg.lower()


@pytest.mark.parametrize("good,expected", [("1", 1), ("5", 5), ("10", 10)])
def test_quantity_valid_accepted(good, expected):
    assert v.validate_quantity(good) == (True, expected)


# --- Selection --------------------------------------------------------------

def test_selection_zero_rejected():              # edge case 4
    assert v.validate_selection("0", 8)[0] is False


def test_selection_above_menu_length_rejected():  # edge case 4
    assert v.validate_selection("9", 8)[0] is False


def test_selection_price_typed_instead_of_number():  # edge case 5
    # A price like '229' against an 8-item menu is out of range -> rejected.
    assert v.validate_selection("229", 8)[0] is False


def test_selection_letters_and_empty_rejected():  # edge case 6
    assert v.validate_selection("abc", 8)[0] is False
    assert v.validate_selection("", 8)[0] is False


@pytest.mark.parametrize("good", ["1", "8"])
def test_selection_valid_accepted(good):
    ok, value = v.validate_selection(good, 8)
    assert ok is True and value == int(good)


# --- Payment ----------------------------------------------------------------

@pytest.mark.parametrize("raw,mode", [("1", "Cash"), ("2", "Card"), ("3", "UPI"),
                                      ("cash", "Cash"), ("UPI", "UPI")])
def test_payment_valid(raw, mode):
    assert v.validate_payment(raw) == (True, mode)


@pytest.mark.parametrize("bad", ["0", "4", "paypal", ""])
def test_payment_invalid_rejected(bad):
    assert v.validate_payment(bad)[0] is False
