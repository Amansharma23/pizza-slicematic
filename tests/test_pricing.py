"""Pricing engine tests, including the PRD worked-example regression."""

from core import pricing
from core.models import MenuItem


def _items():
    base = MenuItem("B3", "Cheese Burst", 229.0)
    pizza = MenuItem("P7", "BBQ Chicken", 379.0)
    topping = MenuItem("T2", "Extra Cheese", 69.0)
    return base, pizza, topping


def test_worked_example_qty5_exact():
    """PRD reference: 677 unit, qty 5 -> total 3594.87, discount applies."""
    base, pizza, topping = _items()
    bill = pricing.compute_bill(base, pizza, topping, 5)
    assert bill.unit_price == 677.00
    assert bill.subtotal == 3385.00
    assert bill.discount == 338.50
    assert bill.taxable == 3046.50
    assert bill.gst == 548.37
    assert bill.total == 3594.87


def test_no_discount_below_threshold():
    base, pizza, topping = _items()
    bill = pricing.compute_bill(base, pizza, topping, 4)
    assert bill.discount == 0.0
    assert bill.subtotal == 2708.00
    assert bill.taxable == 2708.00
    assert bill.gst == 487.44
    assert bill.total == 3195.44


def test_discount_exactly_at_threshold():
    base, pizza, topping = _items()
    bill = pricing.compute_bill(base, pizza, topping, 5)
    assert bill.discount > 0


def test_single_pizza():
    base, pizza, topping = _items()
    bill = pricing.compute_bill(base, pizza, topping, 1)
    assert bill.unit_price == 677.00
    assert bill.subtotal == 677.00
    assert bill.discount == 0.0
    assert bill.total == round(677.00 * 1.18, 2)


def test_all_money_two_decimals():
    base = MenuItem("B1", "Thin Crust", 149.0)
    pizza = MenuItem("P1", "Margherita", 299.0)
    topping = MenuItem("T5", "Jalapenos", 39.0)
    bill = pricing.compute_bill(base, pizza, topping, 7)
    for value in (
        bill.unit_price,
        bill.subtotal,
        bill.discount,
        bill.taxable,
        bill.gst,
        bill.total,
    ):
        assert round(value, 2) == value


def test_discount_threshold_is_configurable():
    base, pizza, topping = _items()
    original = pricing.get_discount_threshold()
    try:
        pricing.set_discount_threshold(3)
        assert pricing.compute_bill(base, pizza, topping, 3).discount > 0
        assert pricing.compute_bill(base, pizza, topping, 2).discount == 0.0
    finally:
        pricing.set_discount_threshold(original)
