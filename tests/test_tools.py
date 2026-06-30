import pytest

import ai.tools as tools
from ai.session import Session
from core import menu as menu_mod


@pytest.fixture
def ids():
    m = menu_mod.load_menu("menu_data")
    return m.bases[0].id, m.pizzas[0].id, m.toppings[0].id


@pytest.fixture
def no_writes(monkeypatch):
    """Stop tools from touching orders_log.txt or Supabase; capture calls."""
    calls = {"append": [], "mirror": []}
    monkeypatch.setattr(
        tools.persistence,
        "append_order",
        lambda **kw: calls["append"].append(kw) or "ts",
    )
    monkeypatch.setattr(
        tools.db_orders, "mirror_order", lambda **kw: calls["mirror"].append(kw)
    )
    return calls


def test_get_menu_lists_ids_and_prices():
    out = tools.execute_tool("get_menu", {}, None)
    assert "Bases:" in out and "Pizzas:" in out and "Toppings:" in out
    assert "INR" in out


def test_calculate_single_line(ids):
    b, p, t = ids
    s = Session(id="c1")
    out = tools.execute_tool(
        "calculate_order_price",
        {"items": [{"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 2}]},
        s,
    )
    assert "Grand total payable: INR" in out
    assert s.pricing["n_lines"] == 1


def test_calculate_applies_discount_at_qty5(ids):
    b, p, t = ids
    out = tools.execute_tool(
        "calculate_order_price",
        {"items": [{"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 5}]},
        None,
    )
    assert "discount" in out.lower()


def test_calculate_multi_line(ids):
    b, p, t = ids
    s = Session(id="c2")
    out = tools.execute_tool(
        "calculate_order_price",
        {
            "items": [
                {"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 2},
                {"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 3},
            ]
        },
        s,
    )
    assert s.pricing["n_lines"] == 2
    assert out.count("line total") == 2


def test_calculate_rejects_bad_id_and_qty(ids):
    b, p, t = ids
    out = tools.execute_tool(
        "calculate_order_price",
        {
            "items": [
                {"base_id": "NOPE", "pizza_id": p, "topping_id": t, "quantity": 99}
            ]
        },
        None,
    )
    assert "Could not price" in out


def test_calculate_empty_items():
    out = tools.execute_tool("calculate_order_price", {"items": []}, None)
    assert "no items" in out.lower()


def test_confirm_saves_and_returns_order_no(ids, no_writes):
    b, p, t = ids
    s = Session(id="cf1", channel="chat", language="en")
    out = tools.execute_tool(
        "confirm_and_save_order",
        {
            "customer_name": "Aman Sharma",
            "customer_phone": "9811122233",
            "payment_mode": "UPI",
            "items": [{"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 2}],
        },
        s,
    )
    assert "Order confirmed" in out and "SM-" in out
    assert len(no_writes["append"]) == 1
    assert len(no_writes["mirror"]) == 1
    assert s.confirmed is True and s.status == "ordered"
    # all lines share one order number + source/session propagated
    assert no_writes["mirror"][0]["source"] == "chat"
    assert no_writes["mirror"][0]["session_id"] == "cf1"


def test_confirm_multi_line_one_order_no(ids, no_writes):
    b, p, t = ids
    line = {"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 1}
    out = tools.execute_tool(
        "confirm_and_save_order",
        {
            "customer_name": "Priya Verma",
            "customer_phone": "7700088899",
            "payment_mode": "1",  # Cash by number
            "items": [line, line],
        },
        Session(id="cf2"),
    )
    assert "Order confirmed" in out
    assert len(no_writes["append"]) == 2
    order_nos = {m["order_no"] for m in no_writes["mirror"]}
    assert len(order_nos) == 1  # both lines, one order number


def test_confirm_rejects_bad_customer(ids, no_writes):
    b, p, t = ids
    out = tools.execute_tool(
        "confirm_and_save_order",
        {
            "customer_name": "A",  # too short
            "customer_phone": "12345",  # invalid
            "payment_mode": "Bitcoin",  # invalid
            "items": [{"base_id": b, "pizza_id": p, "topping_id": t, "quantity": 2}],
        },
        Session(id="cf3"),
    )
    assert "Cannot place the order" in out
    assert no_writes["append"] == []  # nothing saved


def test_validate_customer_all_valid_sets_session():
    s = Session(id="vc1")
    out = tools.execute_tool(
        "validate_customer",
        {"customer_name": "Aman Sharma", "customer_phone": "9811122233"},
        s,
    )
    assert "Valid" in out
    assert s.name == "Aman Sharma" and s.phone == "9811122233"


def test_validate_customer_reports_bad_field():
    s = Session(id="vc2")
    out = tools.execute_tool(
        "validate_customer",
        {"customer_name": "Aman123", "customer_phone": "9811122233"},
        s,
    )
    assert "need fixing" in out and "name:" in out
    # phone was valid -> stored; name was not
    assert s.phone == "9811122233" and s.name is None


def test_validate_customer_partial_only_name():
    s = Session(id="vc3")
    out = tools.execute_tool("validate_customer", {"customer_name": "Priya"}, s)
    assert "Valid" in out and s.name == "Priya"


def test_validate_customer_nothing_provided():
    out = tools.execute_tool("validate_customer", {}, Session(id="vc4"))
    assert "No customer details" in out


def test_escalate_sets_flags_and_records(monkeypatch):
    captured = {}
    monkeypatch.setattr(tools.db_sessions, "upsert_session", lambda sid, **kw: True)
    monkeypatch.setattr(
        tools.db_escalations,
        "add_escalation",
        lambda **kw: captured.__setitem__("esc", kw) or "esc-id",
    )
    s = Session(id="e1", channel="chat", language="en")
    out = tools.execute_tool("escalate_to_human", {"reason": "wants a human"}, s)
    assert s.human_escalated is True and s.status == "escalated"
    assert "team member" in out.lower()
    assert captured["esc"]["reason"] == "wants a human"
    assert captured["esc"]["session_id"] == "e1"
    assert captured["esc"]["langfuse_session_id"] == "e1"


def test_unknown_tool():
    assert "Unknown tool" in tools.execute_tool("frobnicate", {}, None)
