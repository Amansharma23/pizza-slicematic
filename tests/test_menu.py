"""Defensive menu-parsing tests — the grader swaps these files."""

import pytest

from core import menu
from core.menu import MenuError


def test_parses_well_formed_lines():
    items = menu.parse_menu_lines(["B1;Thin Crust;149", "B2;Thick Crust;179"])
    assert [i.name for i in items] == ["Thin Crust", "Thick Crust"]
    assert items[0].price == 149.0


def test_strips_whitespace_and_blank_lines():
    items = menu.parse_menu_lines(["  B1 ; Thin Crust ; 149 ", "", "   ", "\n"])
    assert len(items) == 1
    assert items[0].id == "B1" and items[0].name == "Thin Crust"


def test_skips_missing_price_field():            # edge case 8
    items = menu.parse_menu_lines(["B1;Thin Crust", "B2;Thick Crust;179"])
    assert [i.name for i in items] == ["Thick Crust"]


def test_skips_non_numeric_price():
    items = menu.parse_menu_lines(["B1;Thin Crust;free", "B2;Thick Crust;179"])
    assert [i.name for i in items] == ["Thick Crust"]


def test_skips_negative_price():
    items = menu.parse_menu_lines(["B1;Thin Crust;-5", "B2;Thick Crust;179"])
    assert [i.name for i in items] == ["Thick Crust"]


def test_ignores_duplicate_ids():
    items = menu.parse_menu_lines(["B1;Thin Crust;149", "B1;Other;200"])
    assert len(items) == 1


def test_load_category_missing_file_raises(tmp_path):
    with pytest.raises(MenuError):
        menu.load_category(str(tmp_path / "nope.txt"), "Base")


def test_load_category_all_malformed_raises(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("garbage\nno;price\n", encoding="utf-8")
    with pytest.raises(MenuError):
        menu.load_category(str(bad), "Base")


def test_load_menu_from_repo_files():
    """The shipped menu_data/ must load cleanly."""
    m = menu.load_menu("menu_data")
    assert len(m.bases) == 5
    assert len(m.pizzas) == 8
    assert len(m.toppings) == 10


def test_load_menu_missing_dir_raises(tmp_path):
    with pytest.raises(MenuError):
        menu.load_menu(str(tmp_path / "missing"))
