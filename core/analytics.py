import os
from datetime import datetime

import pandas as pd

from core.persistence import LOG_FILE

# The fields matching persistence.FIELD_ORDER
COLUMNS = [
    "order_id",
    "timestamp",
    "name",
    "phone",
    "base",
    "pizza",
    "topping",
    "unit_price",
    "quantity",
    "subtotal",
    "discount",
    "gst",
    "total",
    "payment_mode",
]


def load_orders_df() -> pd.DataFrame:
    """Load the local orders log into a pandas DataFrame."""
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        return pd.DataFrame(columns=COLUMNS)

    # Read the file line by line to skip blank lines
    lines = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.lstrip("\ufeff").split(" | ")
                if len(parts) == len(COLUMNS) - 1:
                    parts = [""] + parts
                if len(parts) == len(COLUMNS):
                    lines.append(parts)

    df = pd.DataFrame(lines, columns=COLUMNS)
    if df.empty:
        return df

    # Convert numeric columns
    for col in ["unit_price", "subtotal", "discount", "gst", "total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["quantity"] = (
        pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    )

    # Parse timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
    )

    # Add a 'combo' column for analytics
    df["combo"] = df["base"] + " + " + df["pizza"] + " + " + df["topping"]

    return df


def get_analytics(
    filter_type: str, filter_date: str = None, end_date: str = None
) -> dict:
    """
    Returns analytics based on the date filter:
    filter_type: "Date Range", "Specific Date", "This Month", "This Year", "All Time"
    """
    df = load_orders_df()

    empty_res = {
        "total_orders": 0,
        "total_qty": 0,
        "revenue": 0.0,
        "gst": 0.0,
        "discount": 0.0,
        "top_bases": pd.DataFrame(columns=["base", "quantity"]),
        "top_pizzas": pd.DataFrame(columns=["pizza", "quantity"]),
        "top_toppings": pd.DataFrame(columns=["topping", "quantity"]),
        "top_combos": pd.DataFrame(columns=["combo", "quantity"]),
        "orders_df": pd.DataFrame(columns=COLUMNS),
    }

    if df.empty:
        return empty_res

    now = datetime.now()
    if filter_type == "Date Range" and (filter_date or end_date):
        try:
            start = pd.to_datetime(filter_date).date() if filter_date else None
            end = pd.to_datetime(end_date).date() if end_date else None
            if start and end and start > end:
                start, end = end, start
            if start:
                df = df[df["timestamp"].dt.date >= start]
            if end:
                df = df[df["timestamp"].dt.date <= end]
        except Exception:
            pass  # fallback to no filter if parsing fails
    elif filter_type == "Specific Date" and filter_date:
        try:
            if isinstance(filter_date, (int, float)):
                target_date = datetime.fromtimestamp(filter_date).date()
            else:
                target_date = pd.to_datetime(filter_date).date()
            df = df[df["timestamp"].dt.date == target_date]
        except Exception:
            pass  # fallback to no filter if parsing fails
    elif filter_type == "This Month":
        df = df[
            (df["timestamp"].dt.year == now.year)
            & (df["timestamp"].dt.month == now.month)
        ]
    elif filter_type == "This Year":
        df = df[df["timestamp"].dt.year == now.year]

    if df.empty:
        return empty_res

    # KPIs
    total_orders = len(df)
    total_qty = int(df["quantity"].sum())
    revenue = float(df["total"].sum())
    gst = float(df["gst"].sum())
    discount = float(df["discount"].sum())

    # Top Sellers
    top_bases = (
        df.groupby("base")["quantity"]
        .sum()
        .reset_index()
        .sort_values(by="quantity", ascending=False)
    )
    top_pizzas = (
        df.groupby("pizza")["quantity"]
        .sum()
        .reset_index()
        .sort_values(by="quantity", ascending=False)
    )
    top_toppings = (
        df.groupby("topping")["quantity"]
        .sum()
        .reset_index()
        .sort_values(by="quantity", ascending=False)
    )
    top_combos = (
        df.groupby("combo")["quantity"]
        .sum()
        .reset_index()
        .sort_values(by="quantity", ascending=False)
    )

    # Raw orders to display
    # Drop 'combo' and reorder to newest first
    orders_df = df.drop(columns=["combo"]).sort_values(by="timestamp", ascending=False)
    # Format timestamp back to string for clean display
    orders_df["timestamp"] = orders_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "total_orders": total_orders,
        "total_qty": total_qty,
        "revenue": revenue,
        "gst": gst,
        "discount": discount,
        "top_bases": top_bases,
        "top_pizzas": top_pizzas,
        "top_toppings": top_toppings,
        "top_combos": top_combos,
        "orders_df": orders_df,
    }
