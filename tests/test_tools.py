import json

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
    """Stub the DB order write (chat/voice orders are Supabase-only); capture calls."""
    calls = {"create": []}
    monkeypatch.setattr(
        tools.db_orders,
        "create_order",
        lambda **kw: calls["create"].append(kw) or "SM-20260703-0001",
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
        {"items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 2}]},
        s,
    )
    payload = json.loads(out)  # success path returns the bill as JSON
    assert payload["ok"] is True
    assert len(payload["lines"]) == 1
    assert payload["cart"]["total"] == payload["lines"][0]["total"]
    assert s.pricing["n_lines"] == 1
    assert s.pricing["grand_total"] == payload["cart"]["total"]


def test_calculate_applies_discount_at_qty5(ids):
    b, p, t = ids
    out = tools.execute_tool(
        "calculate_order_price",
        {"items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 5}]},
        None,
    )
    payload = json.loads(out)
    assert payload["cart"]["discount"] > 0


def test_calculate_multi_topping_sums_menu_prices(ids):
    """2-3 toppings are fused into one configuration; unit price adds them all."""
    b, p, _ = ids
    m = menu_mod.load_menu("menu_data")
    t1, t2 = m.toppings[0], m.toppings[1]
    out = tools.execute_tool(
        "calculate_order_price",
        {
            "items": [
                {
                    "base_id": b,
                    "pizza_id": p,
                    "topping_ids": [t1.id, t2.id],
                    "quantity": 1,
                }
            ]
        },
        None,
    )
    line = json.loads(out)["lines"][0]
    assert [tp["id"] for tp in line["toppings"]] == [t1.id, t2.id]
    assert line["unit_price"] == round(
        m.bases[0].price + m.pizzas[0].price + t1.price + t2.price, 2
    )


def test_calculate_multi_line(ids):
    b, p, t = ids
    s = Session(id="c2")
    out = tools.execute_tool(
        "calculate_order_price",
        {
            "items": [
                {"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 2},
                {"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 3},
            ]
        },
        s,
    )
    payload = json.loads(out)
    assert s.pricing["n_lines"] == 2
    assert len(payload["lines"]) == 2
    assert payload["cart"]["total"] == round(
        sum(ln["total"] for ln in payload["lines"]), 2
    )


def test_calculate_rejects_bad_id_and_qty(ids):
    b, p, t = ids
    out = tools.execute_tool(
        "calculate_order_price",
        {
            "items": [
                {"base_id": "NOPE", "pizza_id": p, "topping_ids": [t], "quantity": 99}
            ]
        },
        None,
    )
    assert "Could not price" in out


def test_calculate_rejects_empty_toppings(ids):
    b, p, _ = ids
    out = tools.execute_tool(
        "calculate_order_price",
        {"items": [{"base_id": b, "pizza_id": p, "topping_ids": [], "quantity": 1}]},
        None,
    )
    assert "Could not price" in out and "topping" in out.lower()


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
            "items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 2}],
        },
        s,
    )
    payload = json.loads(out)  # success returns JSON for deterministic injection
    assert payload["ok"] is True and payload["order_no"] == "SM-20260703-0001"
    assert s.confirmed is True and s.status == "ordered"
    # DB-only: one order row, stamped with the profile user + source/session
    assert len(no_writes["create"]) == 1
    row = no_writes["create"][0]
    assert row["user_id"] == tools.CUSTOMER_PROFILE["user_id"]
    assert row["source"] == "chat"
    assert row["session_id"] == "cf1"
    assert row["phone"] == "9811122233"  # orders are listed by phone for now


def test_confirm_multi_line_is_one_db_row(ids, no_writes):
    b, p, t = ids
    line = {"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 1}
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
    assert json.loads(out)["ok"] is True
    assert len(no_writes["create"]) == 1  # one row per order
    row = no_writes["create"][0]
    assert len(row["items"]) == 2  # line breakdown in items jsonb
    assert row["total"] == round(sum(ln["line_total"] for ln in row["items"]), 2)


def test_confirm_rejects_bad_customer(ids, no_writes):
    b, p, t = ids
    out = tools.execute_tool(
        "confirm_and_save_order",
        {
            "customer_name": "A",  # too short
            "customer_phone": "12345",  # invalid
            "payment_mode": "Bitcoin",  # invalid
            "items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 2}],
        },
        Session(id="cf3"),
    )
    assert "Cannot place the order" in out
    assert no_writes["create"] == []  # nothing saved


def test_confirm_surfaces_db_failure(ids, monkeypatch):
    """DB is the source of truth — a failed write must be reported, not saved."""
    b, p, t = ids

    def boom(**kw):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(tools.db_orders, "create_order", boom)
    s = Session(id="cf4")
    out = tools.execute_tool(
        "confirm_and_save_order",
        {
            "customer_name": "Aman Sharma",
            "customer_phone": "9811122233",
            "payment_mode": "UPI",
            "items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 1}],
        },
        s,
    )
    assert "Could not save the order" in out and "NOT" in out
    assert s.confirmed is False  # the gate stays open for a retry


def test_get_customer_profile_sets_session():
    s = Session(id="pf1")
    out = tools.execute_tool("get_customer_profile", {}, s)
    assert tools.CUSTOMER_PROFILE["name"] in out
    assert s.name == tools.CUSTOMER_PROFILE["name"]
    assert s.phone == tools.CUSTOMER_PROFILE["phone"]


def test_confirm_falls_back_to_session_profile(ids, no_writes):
    """confirm without name/phone args uses the profile primed on the session."""
    b, p, t = ids
    s = Session(id="pf2")
    tools.execute_tool("get_customer_profile", {}, s)
    out = tools.execute_tool(
        "confirm_and_save_order",
        {
            "payment_mode": "UPI",
            "items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 1}],
        },
        s,
    )
    assert json.loads(out)["ok"] is True
    assert no_writes["create"][0]["name"] == tools.CUSTOMER_PROFILE["name"]
    assert no_writes["create"][0]["phone"] == tools.CUSTOMER_PROFILE["phone"]


def test_tools_for_gates_save_on_pricing(ids):
    """confirm_and_save_order is only exposed once a bill is priced (and hidden
    again after saving); get_menu/validate_customer are never exposed."""
    b, p, t = ids
    s = Session(id="gate1")
    names = {d["function"]["name"] for d in tools.tools_for(s)}
    assert "confirm_and_save_order" not in names
    assert "get_menu" not in names and "validate_customer" not in names
    assert {
        "get_customer_profile",
        "calculate_order_price",
        "escalate_to_human",
    } <= names

    tools.execute_tool(
        "calculate_order_price",
        {"items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 1}]},
        s,
    )
    names = {d["function"]["name"] for d in tools.tools_for(s)}
    assert "confirm_and_save_order" in names

    s.confirmed = True  # saved — the gate closes until the next repricing
    names = {d["function"]["name"] for d in tools.tools_for(s)}
    assert "confirm_and_save_order" not in names


def test_calculate_reopens_confirmed_session(ids):
    """Repricing after a saved order must re-enable saving (new order flow)."""
    b, p, t = ids
    s = Session(id="gate2", confirmed=True)
    tools.execute_tool(
        "calculate_order_price",
        {"items": [{"base_id": b, "pizza_id": p, "topping_ids": [t], "quantity": 1}]},
        s,
    )
    assert s.confirmed is False


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
