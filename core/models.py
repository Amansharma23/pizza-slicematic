"""Plain dataclasses shared across core. No ORM, no web types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuItem:
    """One line of a menu file: ID;Name;Price."""

    id: str
    name: str
    price: float

    def label(self, index: int) -> str:
        """Numbered display label, e.g. '3. Cheese Burst — INR 229.00'."""
        return f"{index}. {self.name} — INR {self.price:.2f}"


@dataclass(frozen=True)
class Menu:
    """The three loaded categories. Each list is guaranteed non-empty."""

    bases: list[MenuItem]
    pizzas: list[MenuItem]
    toppings: list[MenuItem]


@dataclass(frozen=True)
class Bill:
    """Result of the pricing engine. All money values rounded to 2 dp."""

    base: MenuItem
    pizza: MenuItem
    topping: MenuItem
    quantity: int
    unit_price: float
    subtotal: float
    discount: float
    taxable: float
    gst: float
    total: float
