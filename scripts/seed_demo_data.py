"""Seed repeatable local demo data for Admin and AI judging.

This script targets local Postgres through DATABASE_URL. It deletes only records
with deterministic demo markers, then recreates a rich dataset for dashboards,
AI forecasts, recommendation tracking, refunds, notifications, and inventory.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.postgres import get_database_url


DEMO_PHONE_PREFIX = "900000"
DEMO_ORDER_PREFIX = "SM-DEMO-"
DEMO_SESSION_PREFIX = "demo-session-"


def main() -> None:
    import psycopg

    with psycopg.connect(get_database_url()) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                admin_id = _admin_id(cur)
                _clean_demo(cur)
                _seed_inventory(cur, admin_id)
                orders = _seed_orders(cur, admin_id)
                _seed_refunds(cur, admin_id, orders)
                _seed_customer_feedback(cur, admin_id, orders)
                _seed_notifications(cur, admin_id, orders)
                _seed_price_history(cur, admin_id)
                _seed_recommendations(cur, admin_id)
        conn.commit()
    print("Seeded demo data: 28 orders, payments, refunds, feedback sentiment, AI recommendations, notifications, and inventory.")


def _admin_id(cur) -> str:
    cur.execute(
        """
        select id
        from public.app_users
        where email = 'admin@slicematic.local'
        limit 1
        """
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("Admin user admin@slicematic.local is not seeded.")
    return str(row[0])


def _clean_demo(cur) -> None:
    cur.execute(
        """
        delete from public.customer_feedback
        where source_metadata->>'seed' = 'demo'
           or source_metadata->>'smoke' = 'sentiment'
        """
    )
    cur.execute(
        """
        delete from public.ai_recommendation_events
        where recommendation_key like 'demo:%'
           or recommendation_key = 'upsell:smoke:test'
        """
    )
    cur.execute(
        """
        delete from public.notification_logs
        where related_entity_type = 'demo_seed'
           or recipient like %s
        """,
        (f"{DEMO_PHONE_PREFIX}%",),
    )
    cur.execute(
        """
        delete from public.stock_transactions
        where reason like 'Demo seed%%'
        """
    )
    cur.execute(
        """
        delete from public.price_history
        where reason like 'Demo seed%%'
        """
    )
    cur.execute(
        """
        delete from public.orders
        where order_no like %s
           or customer_phone like %s
           or session_id like %s
        """,
        (f"{DEMO_ORDER_PREFIX}%", f"{DEMO_PHONE_PREFIX}%", f"{DEMO_SESSION_PREFIX}%"),
    )
    cur.execute(
        """
        delete from public.sessions
        where id like %s
        """,
        (f"{DEMO_SESSION_PREFIX}%",),
    )


def _seed_inventory(cur, admin_id: str) -> None:
    targets = {
        "Mozzarella Cheese": 5.2,
        "Pizza Sauce": 3.6,
        "Thin Crust Base": 12,
        "Paneer Cubes": 2.4,
        "Chicken Tikka": 1.7,
        "Sweet Corn": 4.1,
    }
    for name, new_qty in targets.items():
        cur.execute(
            """
            select id, stock_quantity
            from public.ingredients
            where name = %s
            """,
            (name,),
        )
        row = cur.fetchone()
        if not row:
            continue
        ingredient_id, old_qty = row
        cur.execute(
            """
            update public.ingredients
            set stock_quantity = %s, updated_at = now()
            where id = %s
            """,
            (new_qty, ingredient_id),
        )
        delta = abs(float(new_qty) - float(old_qty))
        if not delta:
            continue
        cur.execute(
            """
            insert into public.stock_transactions (
                ingredient_id, transaction_type, quantity, old_quantity,
                new_quantity, reason, performed_by, performed_at
            )
            values (%s, 'StockIn', %s, %s, %s, 'Demo seed inventory baseline', %s, now())
            """,
            (ingredient_id, delta, old_qty, new_qty, admin_id),
        )


def _seed_orders(cur, admin_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    pizzas = [
        ("Margherita", "Thin Crust", ["Extra Cheese"], 249),
        ("Farmhouse", "Cheese Burst", ["Sweet Corn", "Olives"], 349),
        ("Paneer Tikka", "Thin Crust", ["Paneer", "Onion"], 389),
        ("Chicken Tikka", "Classic", ["Chicken", "Jalapeno"], 429),
        ("Veggie Supreme", "Multigrain", ["Capsicum", "Sweet Corn"], 329),
        ("Pepperoni", "Classic", ["Extra Cheese"], 449),
    ]
    customers = [
        ("Aarav Sharma", "9000001001"),
        ("Meera Iyer", "9000001002"),
        ("Kabir Khan", "9000001003"),
        ("Nisha Verma", "9000001004"),
        ("Rohan Gupta", "9000001005"),
        ("Priya Nair", "9000001006"),
        ("Dev Patel", "9000001007"),
        ("Isha Mehta", "9000001008"),
    ]
    statuses = [
        "Completed",
        "Delivered",
        "Preparing",
        "Ready",
        "Confirmed",
        "Cancelled",
        "RefundRequested",
    ]
    sources = ["api", "staff_pos", "ai", "voice", "app"]
    payment_modes = ["UPI", "Card", "Cash"]
    orders: list[dict] = []

    for idx in range(28):
        pizza, base, toppings, unit_price = pizzas[idx % len(pizzas)]
        customer, phone = customers[idx % len(customers)]
        quantity = 1 + (idx % 3 == 0)
        subtotal = unit_price * quantity
        discount = round(subtotal * (0.1 if quantity >= 2 else 0), 2)
        gst = round((subtotal - discount) * 0.18, 2)
        total = round(subtotal - discount + gst, 2)
        status = statuses[idx % len(statuses)]
        created_at = now - timedelta(days=idx % 21, hours=(idx * 3) % 14)
        order_no = f"{DEMO_ORDER_PREFIX}{idx + 1:03d}"
        session_id = f"{DEMO_SESSION_PREFIX}{idx + 1:03d}"
        items = [
            {
                "pizza": pizza,
                "base": base,
                "toppings": toppings,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": subtotal,
            }
        ]
        cur.execute(
            """
            insert into public.sessions (
                id, channel, language, customer_name, customer_phone,
                status, metadata, started_at, last_activity_at, ended_at
            )
            values (%s, %s, 'en', %s, %s, 'ordered', %s::jsonb, %s, %s, %s)
            """,
            (
                session_id,
                "voice" if sources[idx % len(sources)] == "voice" else "chat",
                customer,
                phone,
                json.dumps({"seed": "demo"}),
                created_at - timedelta(minutes=12),
                created_at,
                created_at + timedelta(minutes=15),
            ),
        )
        cur.execute(
            """
            insert into public.orders (
                order_no, session_id, source, customer_name, customer_phone,
                base_name, pizza_name, topping_name, unit_price, quantity,
                items, subtotal, discount, gst, total, payment_mode, language,
                status, logged_at, created_at
            )
            values (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s::jsonb, %s, %s, %s, %s, %s, %s,
                %s, %s, %s
            )
            returning id
            """,
            (
                order_no,
                session_id,
                sources[idx % len(sources)],
                customer,
                phone,
                base,
                pizza,
                ", ".join(toppings),
                unit_price,
                quantity,
                json.dumps(items),
                subtotal,
                discount,
                gst,
                total,
                payment_modes[idx % len(payment_modes)],
                "en",
                status,
                created_at.isoformat(),
                created_at,
            ),
        )
        order_id = cur.fetchone()[0]
        payment_status = "Pending" if status == "Confirmed" and idx % 2 else "Paid"
        cur.execute(
            """
            insert into public.payments (
                order_id, payment_mode, payment_status, amount_paid,
                transaction_reference, paid_at, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order_id,
                payment_modes[idx % len(payment_modes)],
                payment_status,
                0 if payment_status == "Pending" else total,
                f"DEMO-PAY-{idx + 1:03d}",
                None if payment_status == "Pending" else created_at + timedelta(minutes=2),
                created_at + timedelta(minutes=1),
            ),
        )
        cur.execute(
            """
            insert into public.order_status_history (
                order_id, old_status, new_status, changed_by, changed_at, reason
            )
            values
                (%s, null, 'Created', %s, %s, 'Demo seed order created'),
                (%s, 'Created', %s, %s, %s, 'Demo seed lifecycle')
            """,
            (
                order_id,
                admin_id,
                created_at,
                order_id,
                status,
                admin_id,
                created_at + timedelta(minutes=5),
            ),
        )
        orders.append({"id": order_id, "total": total, "created_at": created_at})
    return orders


def _seed_refunds(cur, admin_id: str, orders: list[dict]) -> None:
    for idx, status in [(5, "Approved"), (12, "Rejected"), (19, "Paid")]:
        order = orders[idx]
        cur.execute(
            """
            select id
            from public.payments
            where order_id = %s
            limit 1
            """,
            (order["id"],),
        )
        payment_id = cur.fetchone()[0]
        decided_at = order["created_at"] + timedelta(hours=2)
        cur.execute(
            """
            insert into public.refunds (
                order_id, payment_id, amount, reason, status,
                requested_by, approved_by, requested_at, decided_at
            )
            values (%s, %s, %s, 'Demo seed refund case', %s, %s, %s, %s, %s)
            """,
            (
                order["id"],
                payment_id,
                round(order["total"] * 0.4, 2),
                status,
                admin_id,
                admin_id,
                order["created_at"] + timedelta(hours=1),
                decided_at,
            ),
        )


def _seed_customer_feedback(cur, admin_id: str, orders: list[dict]) -> None:
    feedback_rows = [
        (0, "google", 5, "Hot, fresh and delicious pizza. Delivery was quick.", "positive", 0.92, ["taste", "temperature", "delivery", "quality"]),
        (1, "app", 4, "Loved the crispy base and extra cheese recommendation.", "positive", 0.74, ["taste", "quality"]),
        (2, "whatsapp", 2, "Delivery was late and the pizza arrived cold.", "negative", -0.82, ["delivery", "temperature"]),
        (3, "voice", 5, "Staff was friendly and order was perfect.", "positive", 0.88, ["service", "accuracy"]),
        (4, "zomato", 3, "Taste was good but one topping was missing.", "neutral", 0.05, ["taste", "accuracy"]),
        (5, "swiggy", 1, "Wrong order and very slow support.", "negative", -0.95, ["accuracy", "service"]),
        (6, "web", 4, "Fresh toppings and good value for money.", "positive", 0.7, ["quality"]),
        (7, "app", 5, "Best paneer pizza, arrived hot and fast.", "positive", 0.96, ["taste", "temperature", "delivery"]),
    ]
    for idx, channel, rating, text, label, score, topics in feedback_rows:
        order = orders[idx]
        cur.execute(
            """
            select customer_name, customer_phone
            from public.orders
            where id = %s
            """,
            (order["id"],),
        )
        customer_name, customer_phone = cur.fetchone()
        cur.execute(
            """
            insert into public.customer_feedback (
                order_id, customer_name, customer_phone, channel, rating,
                feedback_text, sentiment_label, sentiment_score, topics,
                source_metadata, created_by, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s, %s)
            """,
            (
                order["id"],
                customer_name,
                customer_phone,
                channel,
                rating,
                text,
                label,
                score,
                json.dumps(topics),
                json.dumps({"seed": "demo"}),
                admin_id,
                order["created_at"] + timedelta(minutes=30),
            ),
        )


def _seed_notifications(cur, admin_id: str, orders: list[dict]) -> None:
    for idx, order in enumerate(orders[:8]):
        channel = "whatsapp" if idx % 2 == 0 else "email"
        recipient = f"{DEMO_PHONE_PREFIX}{2000 + idx}" if channel == "whatsapp" else f"demo{idx}@slicematic.local"
        cur.execute(
            """
            insert into public.notification_logs (
                channel, provider, recipient, template_name, payload, status,
                related_entity_type, related_entity_id, created_by, sent_at, created_at
            )
            values (%s, 'mock', %s, 'demo_order_update', %s::jsonb, 'mocked',
                    'demo_seed', %s, %s, %s, %s)
            """,
            (
                channel,
                recipient,
                json.dumps({"message": "Demo SliceMatic order update"}),
                str(order["id"]),
                admin_id,
                order["created_at"] + timedelta(minutes=10),
                order["created_at"] + timedelta(minutes=9),
            ),
        )


def _seed_price_history(cur, admin_id: str) -> None:
    changes = [("P1", 229, 249), ("P4", 369, 389), ("T2", 49, 59)]
    for code, old_price, new_price in changes:
        cur.execute("select id from public.menu_items where item_code = %s", (code,))
        row = cur.fetchone()
        if not row:
            continue
        cur.execute(
            """
            insert into public.price_history (
                menu_item_id, old_price, new_price, changed_by, changed_at, reason
            )
            values (%s, %s, %s, %s, now(), 'Demo seed price movement')
            """,
            (row[0], old_price, new_price, admin_id),
        )


def _seed_recommendations(cur, admin_id: str) -> None:
    events = [
        ("upsell", "demo:upsell:margherita-cheese", "Suggest Extra Cheese", "accepted", 42),
        ("upsell", "demo:upsell:farmhouse-corn", "Suggest Sweet Corn", "rejected", 35),
        ("coupon", "demo:coupon:aov-booster", "BOOSTAOV coupon", "accepted", 58),
        ("coupon", "demo:coupon:hour-15", "Hour 15 Rush Builder", "presented", 25),
        ("churn", "demo:churn:winback", "Win-back coupon", "accepted", 75),
    ]
    for rec_type, key, title, status, value in events:
        cur.execute(
            """
            insert into public.ai_recommendation_events (
                recommendation_type, recommendation_key, title, detail, status,
                estimated_value, source_metrics, related_entity_type,
                related_entity_id, created_by, created_at
            )
            values (%s, %s, %s, 'Demo seed recommendation', %s, %s,
                    %s::jsonb, 'demo_seed', %s, %s, now())
            """,
            (
                rec_type,
                key,
                title,
                status,
                value,
                json.dumps({"seed": "demo", "estimated_value": value}),
                key,
                admin_id,
            ),
        )


if __name__ == "__main__":
    main()
