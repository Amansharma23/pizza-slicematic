"""Tests for protected Staff kitchen API routes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import staff_routes
from db import admin as admin_db


def _user(permissions=None):
    return {
        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "email": "kitchen@slicematic.local",
        "full_name": "Kitchen Staff",
        "status": "active",
        "roles": ["Backstage Staff"],
        "permissions": permissions
        or [
            "staff.kitchen.access",
            "orders.read",
            "orders.update_status",
            "inventory.request",
        ],
    }


def _client(monkeypatch, user=None):
    monkeypatch.setenv("STAFF_DEV_TOKEN", "staff-token")
    monkeypatch.setenv("STAFF_DEV_EMAIL", "kitchen@slicematic.local")
    monkeypatch.setattr(staff_routes.admin_db, "get_user_by_email", lambda _: user)
    monkeypatch.setattr(
        staff_routes.admin_db,
        "list_staff_orders",
        lambda: [{"id": "order-1", "order_no": "SM-1", "status": "Confirmed"}],
    )
    monkeypatch.setattr(
        staff_routes.admin_db,
        "advance_staff_order",
        lambda order_id, **_: {
            "id": order_id,
            "order_no": "SM-1",
            "status": "Preparing",
        },
    )
    monkeypatch.setattr(
        staff_routes.admin_db,
        "list_inventory",
        lambda: {
            "ingredients": [{"id": "ingredient-1", "name": "Cheese"}],
            "transactions": [],
            "requests": [],
        },
    )
    monkeypatch.setattr(
        staff_routes.admin_db,
        "create_inventory_request",
        lambda **_: {"id": "request-1", "status": "Requested"},
    )
    monkeypatch.setattr(
        staff_routes.admin_db,
        "create_staff_order",
        lambda **_: {
            "id": "order-1",
            "order_no": "SM-STAFF-1",
            "status": "Confirmed",
            "total": 399,
        },
    )
    monkeypatch.setattr(
        staff_routes.public_routes,
        "_load_active_menu",
        lambda: object(),
    )

    class _Bill:
        quantity = 1
        unit_price = 399
        subtotal = 399
        discount = 0
        gst = 0
        total = 399

        class pizza:
            name = "Margherita"

        class base:
            name = "Thin Crust"

    class _Topping:
        name = "Extra Cheese"

    monkeypatch.setattr(
        staff_routes.public_routes,
        "_resolve_cart_line",
        lambda _menu, _line: (_Bill(), [_Topping()], None),
    )
    app = FastAPI()
    app.include_router(staff_routes.router)
    return TestClient(app)


def test_staff_me_requires_token(monkeypatch):
    client = _client(monkeypatch, _user())
    res = client.get("/staff/me")
    assert res.status_code == 401


def test_staff_me_returns_seeded_staff(monkeypatch):
    client = _client(monkeypatch, _user())
    res = client.get("/staff/me", headers={"Authorization": "Bearer staff-token"})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "kitchen@slicematic.local"


def test_staff_orders_require_permission(monkeypatch):
    client = _client(monkeypatch, _user(["staff.kitchen.access"]))
    res = client.get("/staff/orders", headers={"Authorization": "Bearer staff-token"})
    assert res.status_code == 403


def test_staff_order_queue_and_advance(monkeypatch):
    client = _client(monkeypatch, _user())
    queue = client.get("/staff/orders", headers={"Authorization": "Bearer staff-token"})
    advanced = client.post(
        "/staff/orders/order-1/advance",
        headers={"Authorization": "Bearer staff-token"},
        json={"reason": "test"},
    )
    assert queue.status_code == 200
    assert queue.json()["orders"][0]["status"] == "Confirmed"
    assert advanced.json()["order"]["status"] == "Preparing"


def test_staff_inventory_request(monkeypatch):
    client = _client(monkeypatch, _user())
    inventory = client.get(
        "/staff/inventory", headers={"Authorization": "Bearer staff-token"}
    )
    request = client.post(
        "/staff/inventory/requests",
        headers={"Authorization": "Bearer staff-token"},
        json={
            "ingredient_id": "ingredient-1",
            "requested_quantity": 2,
            "reason": "Low cheese",
        },
    )
    assert inventory.status_code == 200
    assert request.json()["request"]["status"] == "Requested"


def test_staff_checkout_creates_confirmed_order(monkeypatch):
    client = _client(monkeypatch, _user())
    res = client.post(
        "/staff/checkout",
        headers={"Authorization": "Bearer staff-token"},
        json={
            "name": "Aman",
            "phone": "9876543210",
            "payment_mode": "Cash",
            "lines": [
                {
                    "base_id": "B1",
                    "pizza_id": "P1",
                    "topping_ids": ["T1"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert res.status_code == 200
    assert res.json()["order"]["status"] == "Confirmed"


def test_create_staff_order_uses_null_customer_user_id(monkeypatch):
    calls = []

    class _Cursor:
        description = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def execute(self, sql, params=None):
            calls.append((sql, params))
            if "returning id, order_no" in sql:
                self.description = [
                    type("D", (), {"name": name})
                    for name in [
                        "id",
                        "order_no",
                        "customer_name",
                        "customer_phone",
                        "items",
                        "subtotal",
                        "discount",
                        "gst",
                        "total",
                        "payment_mode",
                        "status",
                        "source",
                        "created_at",
                    ]
                ]

        def fetchone(self):
            return (
                "order-uuid",
                "SM-1",
                "Aman",
                "9876543210",
                [],
                1,
                0,
                0,
                1,
                "Cash",
                "Confirmed",
                "staff_pos",
                None,
            )

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(admin_db.postgres, "is_enabled", lambda: True)
    monkeypatch.setattr(admin_db.postgres, "connect", lambda: _Conn())
    order = admin_db.create_staff_order(
        customer_name="Aman",
        customer_phone="9876543210",
        items=[],
        subtotal=1,
        discount=0,
        gst=0,
        total=1,
        payment_mode="Cash",
        performed_by="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    insert_call = next(call for call in calls if "insert into public.orders" in call[0])
    assert insert_call[1][0] is None
    assert order["order_no"] == "SM-1"
