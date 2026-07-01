"""orders_log.txt format tests — parseable, pipe-separated, blank line between."""

from core import persistence, pricing
from core.models import MenuItem


def _bill():
    base = MenuItem("B3", "Cheese Burst", 229.0)
    pizza = MenuItem("P7", "BBQ Chicken", 379.0)
    topping = MenuItem("T2", "Extra Cheese", 69.0)
    return pricing.compute_bill(base, pizza, topping, 5)


def test_line_has_all_fields_in_order():
    line = persistence.format_order_line(
        order_id="SM-000001",
        timestamp="2026-06-27 12:00:00",
        name="Rajan",
        phone="9876543210",
        bill=_bill(),
        payment_mode="UPI",
    )
    parts = line.split(" | ")
    assert len(parts) == len(persistence.FIELD_ORDER)
    assert parts[0] == "SM-000001"
    assert parts[1] == "2026-06-27 12:00:00"
    assert parts[2] == "Rajan"
    assert parts[3] == "9876543210"
    assert parts[4] == "Cheese Burst"
    assert parts[7] == "677.00"  # unit_price
    assert parts[8] == "5"  # quantity
    assert parts[12] == "3594.87"  # total
    assert parts[13] == "UPI"


def test_blank_line_between_orders(tmp_path):
    path = str(tmp_path / "orders_log.txt")
    for _ in range(3):
        persistence.append_order(
            name="Rajan",
            phone="9876543210",
            bill=_bill(),
            payment_mode="Cash",
            timestamp="2026-06-27 12:00:00",
            path=path,
        )
    content = open(path, encoding="utf-8").read()
    blocks = [b for b in content.split("\n\n") if b.strip()]
    assert len(blocks) == 3
    # No leading blank line before the very first record.
    assert not content.startswith("\n")


def test_separator_in_field_is_sanitised():
    line = persistence.format_order_line(
        order_id="SM-000001",
        timestamp="2026-06-27 12:00:00",
        name="Raj|an",
        phone="9876543210",
        bill=_bill(),
        payment_mode="UPI",
    )
    assert line.split(" | ")[2] == "Raj/an"


def test_next_order_id_accounts_for_legacy_rows(tmp_path):
    path = tmp_path / "orders_log.txt"
    path.write_text(
        "2026-06-27 12:00:00 | Rajan | 9876543210 | Cheese Burst | BBQ Chicken | Extra Cheese | 677.00 | 5 | 3385.00 | 338.50 | 548.37 | 3594.87 | UPI\n\n",
        encoding="utf-8",
    )
    assert persistence.next_order_id(str(path)) == "SM-000002"
