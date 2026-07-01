"""Tests for the additive POST /api/cart/price endpoint (multi-topping cart).

These run without keys/DB: we mount only the api router and pin the menu to the
bundled menu_data/ so results don't depend on any admin-uploaded menu state.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import routes
from core import menu as menu_mod
from core import pricing
from core.models import MenuItem


@pytest.fixture
def client(monkeypatch):
    # Deterministic menu — ignore database/menu_source.txt.
    m = menu_mod.load_menu("menu_data")
    monkeypatch.setattr(routes, "_load_active_menu", lambda: m)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app), m


def _expected_total(base, pizza, toppings, qty):
    combined = MenuItem(
        id="+".join(t.id for t in toppings),
        name=" + ".join(t.name for t in toppings),
        price=round(sum(t.price for t in toppings), 2),
    )
    return pricing.compute_bill(base, pizza, combined, qty)


def test_single_line_three_toppings_matches_core(client):
    c, m = client
    base, pizza = m.bases[0], m.pizzas[0]
    tops = m.toppings[:3]
    payload = {
        "lines": [
            {
                "base_id": base.id,
                "pizza_id": pizza.id,
                "topping_ids": [t.id for t in tops],
                "quantity": 2,
            }
        ]
    }
    res = c.post("/api/cart/price", json=payload).json()
    assert res["ok"] is True
    line = res["lines"][0]
    exp = _expected_total(base, pizza, tops, 2)
    assert line["unit_price"] == exp.unit_price
    assert line["total"] == exp.total
    assert len(line["toppings"]) == 3
    assert res["cart"]["total"] == exp.total


def test_qty_five_applies_discount(client):
    c, m = client
    base, pizza, top = m.bases[0], m.pizzas[0], m.toppings[0]
    payload = {
        "lines": [
            {
                "base_id": base.id,
                "pizza_id": pizza.id,
                "topping_ids": [top.id],
                "quantity": 5,
            }
        ]
    }
    line = c.post("/api/cart/price", json=payload).json()["lines"][0]
    assert line["discount"] > 0


def test_qty_four_no_discount(client):
    c, m = client
    base, pizza, top = m.bases[0], m.pizzas[0], m.toppings[0]
    payload = {
        "lines": [
            {
                "base_id": base.id,
                "pizza_id": pizza.id,
                "topping_ids": [top.id],
                "quantity": 4,
            }
        ]
    }
    line = c.post("/api/cart/price", json=payload).json()["lines"][0]
    assert line["discount"] == 0


def test_multi_line_cart_total_is_sum(client):
    c, m = client
    lines = [
        {
            "base_id": m.bases[0].id,
            "pizza_id": m.pizzas[0].id,
            "topping_ids": [m.toppings[0].id],
            "quantity": 1,
        },
        {
            "base_id": m.bases[1].id,
            "pizza_id": m.pizzas[1].id,
            "topping_ids": [m.toppings[0].id, m.toppings[1].id],
            "quantity": 3,
        },
    ]
    res = c.post("/api/cart/price", json={"lines": lines}).json()
    assert res["ok"] is True
    summed = round(sum(ln["total"] for ln in res["lines"]), 2)
    assert res["cart"]["total"] == summed


def test_rejects_more_than_three_toppings(client):
    c, m = client
    payload = {
        "lines": [
            {
                "base_id": m.bases[0].id,
                "pizza_id": m.pizzas[0].id,
                "topping_ids": [t.id for t in m.toppings[:4]],
                "quantity": 1,
            }
        ]
    }
    res = c.post("/api/cart/price", json=payload).json()
    assert res["ok"] is False
    assert "toppings" in res["errors"]


def test_rejects_no_toppings(client):
    c, m = client
    payload = {
        "lines": [
            {
                "base_id": m.bases[0].id,
                "pizza_id": m.pizzas[0].id,
                "topping_ids": [],
                "quantity": 1,
            }
        ]
    }
    res = c.post("/api/cart/price", json=payload).json()
    assert res["ok"] is False
    assert "toppings" in res["errors"]


def test_rejects_bad_quantity(client):
    c, m = client
    payload = {
        "lines": [
            {
                "base_id": m.bases[0].id,
                "pizza_id": m.pizzas[0].id,
                "topping_ids": [m.toppings[0].id],
                "quantity": 0,
            }
        ]
    }
    res = c.post("/api/cart/price", json=payload).json()
    assert res["ok"] is False
    assert "quantity" in res["errors"]


def test_empty_cart_rejected(client):
    c, _ = client
    res = c.post("/api/cart/price", json={"lines": []}).json()
    assert res["ok"] is False


def test_unknown_topping_rejected(client):
    c, m = client
    payload = {
        "lines": [
            {
                "base_id": m.bases[0].id,
                "pizza_id": m.pizzas[0].id,
                "topping_ids": ["NOPE"],
                "quantity": 1,
            }
        ]
    }
    res = c.post("/api/cart/price", json=payload).json()
    assert res["ok"] is False
    assert "toppings" in res["errors"]


# --------------------------------------------------------------------------- #
# Checkout — API orders write to the DB ONLY (not orders_log.txt). db_orders is
# stubbed so tests run without Supabase/keys and never write anything real.
# --------------------------------------------------------------------------- #


@pytest.fixture
def fake_db(monkeypatch):
    """Stub db_orders.create_order; capture calls, return a DB-style order_no."""
    calls = []

    class _DB:
        def create_order(self, **kw):
            calls.append(kw)
            return "SM-20260702-0001"

    monkeypatch.setattr(routes, "db_orders", _DB())
    return calls


def _good_lines(m):
    return [
        {
            "base_id": m.bases[0].id,
            "pizza_id": m.pizzas[0].id,
            "topping_ids": [m.toppings[0].id],
            "quantity": 1,
        },
        {
            "base_id": m.bases[1].id,
            "pizza_id": m.pizzas[1].id,
            "topping_ids": [m.toppings[0].id, m.toppings[1].id],
            "quantity": 3,
        },
    ]


def test_checkout_creates_one_order_with_all_items(client, fake_db):
    c, m = client
    payload = {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "name": "Aarav Sharma",
        "phone": "9876543210",
        "payment_mode": "UPI",
        "lines": _good_lines(m),
    }
    res = c.post("/api/cart/checkout", json=payload).json()
    assert res["ok"] is True
    assert res["order_no"] == "SM-20260702-0001"
    assert res["line_count"] == 2
    assert res["payment_mode"] == "UPI"
    # One DB row per cart, holding both items and the user_id.
    assert len(fake_db) == 1
    assert len(fake_db[0]["items"]) == 2
    assert fake_db[0]["user_id"] == "11111111-1111-1111-1111-111111111111"


def test_checkout_cash_mode_number_resolves_to_cash(client, fake_db):
    c, m = client
    payload = {
        "name": "Aarav Sharma",
        "phone": "9876543210",
        "payment_mode": "1",  # COD / Cash both send the Cash mode
        "lines": _good_lines(m)[:1],
    }
    res = c.post("/api/cart/checkout", json=payload).json()
    assert res["ok"] is True
    assert res["payment_mode"] == "Cash"
    assert fake_db[0]["payment_mode"] == "Cash"


def test_checkout_bad_phone_writes_nothing(client, fake_db):
    c, m = client
    payload = {
        "name": "Aarav Sharma",
        "phone": "12345",
        "payment_mode": "UPI",
        "lines": _good_lines(m),
    }
    res = c.post("/api/cart/checkout", json=payload).json()
    assert res["ok"] is False
    assert "phone" in res["errors"]
    assert fake_db == []  # nothing written on validation failure


def test_checkout_bad_payment_rejected(client, fake_db):
    c, m = client
    payload = {
        "name": "Aarav Sharma",
        "phone": "9876543210",
        "payment_mode": "7",
        "lines": _good_lines(m),
    }
    res = c.post("/api/cart/checkout", json=payload).json()
    assert res["ok"] is False
    assert "payment_mode" in res["errors"]
    assert fake_db == []


def test_checkout_bad_line_writes_nothing(client, fake_db):
    c, m = client
    payload = {
        "name": "Aarav Sharma",
        "phone": "9876543210",
        "payment_mode": "UPI",
        "lines": [
            {
                "base_id": m.bases[0].id,
                "pizza_id": m.pizzas[0].id,
                "topping_ids": [t.id for t in m.toppings[:4]],  # >3 toppings
                "quantity": 1,
            }
        ],
    }
    res = c.post("/api/cart/checkout", json=payload).json()
    assert res["ok"] is False
    assert res["line_index"] == 0
    assert fake_db == []


def test_checkout_db_unavailable_surfaces_error(client, monkeypatch):
    c, m = client
    monkeypatch.setattr(routes, "db_orders", None)  # DB not configured
    payload = {
        "name": "Aarav Sharma",
        "phone": "9876543210",
        "payment_mode": "UPI",
        "lines": _good_lines(m)[:1],
    }
    res = c.post("/api/cart/checkout", json=payload).json()
    assert res["ok"] is False
    assert "db" in res["errors"]


def test_list_orders_requires_user_id(client):
    c, _ = client
    res = c.get("/api/orders").json()
    assert res["ok"] is False
    assert "user_id" in res["errors"]


def test_list_orders_returns_user_rows(client, monkeypatch):
    c, _ = client

    class _DB:
        def list_orders_by_user(self, user_id, limit=50):
            return [{"order_no": "SM-20260702-0001", "user_id": user_id}]

    monkeypatch.setattr(routes, "db_orders", _DB())
    res = c.get("/api/orders", params={"user_id": "u-1"}).json()
    assert res["ok"] is True
    assert res["orders"][0]["order_no"] == "SM-20260702-0001"
