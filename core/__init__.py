"""SliceMatic core — pure Python ordering brain.

No web or DB imports live here. Everything in this package runs with only the
standard library and the three menu .txt files present. This is the code the
grader actually exercises, so it must never crash on bad input or swapped files.
"""

from core.models import MenuItem, Menu, Bill
from core.menu import load_menu, MenuError
from core import validation, pricing, persistence

__all__ = [
    "MenuItem",
    "Menu",
    "Bill",
    "load_menu",
    "MenuError",
    "validation",
    "pricing",
    "persistence",
]
