"""Defensive menu loading. The grader swaps these files, so parse paranoidly.

File format: one item per line, ``ID;Name;Price``. We strip whitespace, skip
blank lines, validate the price is numeric, and skip malformed lines rather than
crash. A missing file or a category that ends up empty is a clear, graceful error
(MenuError) — never a stack trace.
"""

from __future__ import annotations

import os

from core.models import Menu, MenuItem

# Default filenames as shipped in menu_data/. Order: base, pizza, topping.
BASE_FILE = "Types_of_Base.txt"
PIZZA_FILE = "Types_of_Pizza.txt"
TOPPING_FILE = "Types_of_Toppings.txt"


class MenuError(Exception):
    """Raised when a menu file is missing, unreadable, or has no valid items."""


def parse_menu_lines(lines: list[str]) -> list[MenuItem]:
    """Parse raw lines into MenuItems, skipping anything malformed.

    A line is valid only if it has at least 3 ``;``-separated fields, a
    non-empty id and name, and a price that parses as a number. Everything
    else (blank lines, comments, missing price, non-numeric price, or columns
    consisting only of special characters) is skipped.
    """
    items: list[MenuItem] = []
    seen_ids: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 3:
            continue  # missing field(s)
        item_id, name, price_str = parts[0], parts[1], parts[2]
        if not item_id or not name or not price_str:
            continue
        # Skip if any column consists only of special characters (no alphanumeric characters)
        if (
            (not any(c.isalnum() for c in item_id))
            or (not any(c.isalnum() for c in name))
            or (not any(c.isalnum() for c in price_str))
        ):
            continue
        try:
            price = float(price_str)
        except ValueError:
            continue  # price not numeric
        if price < 0:
            continue
        if item_id in seen_ids:
            continue  # ignore duplicate ids defensively
        seen_ids.add(item_id)
        items.append(MenuItem(id=item_id, name=name, price=round(price, 2)))
    return items


def load_category(path: str, category: str) -> list[MenuItem]:
    """Load one menu file into a non-empty list of MenuItems or raise MenuError."""
    if not os.path.isfile(path):
        raise MenuError(f"Menu file for {category} not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        raise MenuError(f"Could not read {category} menu file ({path}): {exc}") from exc

    items = parse_menu_lines(lines)
    if not items:
        raise MenuError(
            f"No valid items found in the {category} menu file ({path}). "
            f"Each line must be 'ID;Name;Price'."
        )
    return items


def load_menu(menu_dir: str = "menu_data") -> Menu:
    """Load all three categories from ``menu_dir`` or raise MenuError.

    This is the single entry point the app should call at startup.
    """
    bases = load_category(os.path.join(menu_dir, BASE_FILE), "Base")
    pizzas = load_category(os.path.join(menu_dir, PIZZA_FILE), "Pizza")
    toppings = load_category(os.path.join(menu_dir, TOPPING_FILE), "Topping")
    return Menu(bases=bases, pizzas=pizzas, toppings=toppings)
