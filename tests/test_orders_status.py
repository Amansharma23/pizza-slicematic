"""Tests for the order status pipeline (db/orders.py:update_order_status,
get_delivery_stats). Run without keys/DB: db.orders.get_client is replaced by a
tiny fake Supabase client/query-builder (execute_query itself is untouched —
it just calls query.execute(), which the fake implements), so the state
machine and stats math are exercised without a live database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from db import orders as db_orders


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Minimal stand-in for a supabase-py PostgREST query builder: enough
    chaining (select/eq/gte/order/limit/update) for db/orders.py's calls."""

    def __init__(self, rows: list[dict]):
        self._filtered = list(rows)
        self._mode = "select"
        self._update_fields: dict | None = None

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._filtered = [r for r in self._filtered if r.get(field) == value]
        return self

    def gte(self, field, value):
        self._filtered = [r for r in self._filtered if (r.get(field) or "") >= value]
        return self

    def order(self, field, desc=False):
        self._filtered.sort(key=lambda r: r.get(field) or "", reverse=desc)
        return self

    def limit(self, n):
        self._filtered = self._filtered[:n]
        return self

    def update(self, fields):
        self._mode = "update"
        self._update_fields = fields
        return self

    def execute(self):
        if self._mode == "update":
            for row in self._filtered:
                row.update(self._update_fields)
        return _FakeResult(list(self._filtered))


class FakeOrdersClient:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def table(self, name: str):
        assert name == "orders"
        return _FakeQuery(self.rows)


@pytest.fixture
def fake_rows():
    return [
        {"order_no": "SM-1", "status": "received"},
        {"order_no": "SM-2", "status": "preparing"},
        {"order_no": "SM-3", "status": "ready_for_pickup"},
    ]


@pytest.fixture
def fake_client(monkeypatch, fake_rows):
    client = FakeOrdersClient(fake_rows)
    monkeypatch.setattr(db_orders, "get_client", lambda: client)
    return client


def test_legal_transition_advances_status_and_stamps_timestamp(fake_client, fake_rows):
    updated = db_orders.update_order_status("SM-1", "preparing")
    assert updated["status"] == "preparing"
    assert updated.get("preparing_at")
    # the underlying row was actually mutated, not just the returned copy
    assert fake_rows[0]["status"] == "preparing"


def test_skipping_a_step_is_rejected(fake_client):
    with pytest.raises(ValueError, match="ready_for_pickup"):
        db_orders.update_order_status("SM-1", "ready_for_pickup")


def test_repeating_the_same_status_is_rejected(fake_client):
    with pytest.raises(ValueError):
        db_orders.update_order_status("SM-2", "preparing")


def test_going_backward_is_rejected(fake_client):
    with pytest.raises(ValueError):
        db_orders.update_order_status("SM-3", "preparing")


def test_unknown_status_is_rejected(fake_client):
    with pytest.raises(ValueError, match="Unknown status"):
        db_orders.update_order_status("SM-2", "cancelled")


def test_unknown_order_is_rejected(fake_client):
    with pytest.raises(ValueError, match="not found"):
        db_orders.update_order_status("SM-999", "preparing")


def _today_at(hour: int, minute: int = 0) -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


def test_delivery_stats_computes_pickup_to_delivered_minutes(monkeypatch):
    sm10_start = datetime.fromisoformat(_today_at(10, 0))
    rows = [
        {
            "order_no": "SM-10",
            "status": "delivered",
            "out_for_delivery_at": sm10_start.isoformat(),
            # 22.5 minutes exactly (seconds needed, hence not using _today_at).
            "delivered_at": (
                sm10_start + timedelta(minutes=22, seconds=30)
            ).isoformat(),
        },
        {
            "order_no": "SM-11",
            "status": "delivered",
            "out_for_delivery_at": _today_at(11, 0),
            "delivered_at": _today_at(11, 15),
        },
    ]
    monkeypatch.setattr(db_orders, "get_client", lambda: FakeOrdersClient(rows))
    stats = db_orders.get_delivery_stats()
    assert stats["delivered_today"] == 2
    by_no = {o["order_no"]: o["pickup_to_delivered_minutes"] for o in stats["orders"]}
    assert by_no["SM-10"] == 22.5
    assert by_no["SM-11"] == 15.0


def test_delivery_stats_handles_missing_pickup_timestamp(monkeypatch):
    rows = [
        {
            "order_no": "SM-12",
            "status": "delivered",
            "out_for_delivery_at": None,
            "delivered_at": _today_at(9, 0),
        }
    ]
    monkeypatch.setattr(db_orders, "get_client", lambda: FakeOrdersClient(rows))
    stats = db_orders.get_delivery_stats()
    assert stats["delivered_today"] == 1
    assert stats["orders"][0]["pickup_to_delivered_minutes"] is None
