"""Local Postgres helpers for Stage 0 local development.

Supabase remains supported through db/client.py. This module is used when
DATABASE_PROVIDER=postgres and DATABASE_URL is set.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def is_enabled() -> bool:
    return os.environ.get("DATABASE_PROVIDER", "").lower() == "postgres"


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required when DATABASE_PROVIDER=postgres.")
    return url


@contextmanager
def connect():
    import psycopg

    with psycopg.connect(get_database_url(), autocommit=True) as conn:
        yield conn


def create_order(
    *,
    user_id: str | None,
    name: str,
    phone: str,
    items: list[dict],
    subtotal: float,
    discount: float,
    gst: float,
    total: float,
    payment_mode: str,
    source: str = "api",
    session_id: str | None = None,
    language: str | None = None,
    status: str = "received",
) -> str:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into public.orders (
                    user_id, session_id, source, customer_name, customer_phone,
                    items, subtotal, discount, gst, total, payment_mode,
                    language, status
                )
                values (
                    %s, %s, %s, %s, %s,
                    %s::jsonb, %s, %s, %s, %s, %s,
                    %s, %s
                )
                returning order_no
                """,
                (
                    user_id,
                    session_id,
                    source,
                    name,
                    phone,
                    _json(items),
                    subtotal,
                    discount,
                    gst,
                    total,
                    payment_mode,
                    language,
                    status,
                ),
            )
            row = cur.fetchone()
    if not row:
        raise RuntimeError("Order insert returned no row.")
    return row[0]


def list_orders_by_user(user_id: str, limit: int = 50) -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select order_no, items, subtotal, discount, gst, total,
                       payment_mode, status, created_at, customer_name
                from public.orders
                where user_id = %s
                order by created_at desc
                limit %s
                """,
                (user_id, limit),
            )
            cols = [desc.name for desc in cur.description]
            rows = cur.fetchall()
    return [_serialize(dict(zip(cols, row))) for row in rows]


def _json(value) -> str:
    import json

    return json.dumps(value)


def _serialize(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            out[key] = value.astimezone(timezone.utc).isoformat()
        else:
            out[key] = value
    return out
