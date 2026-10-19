"""Pricing calculations, kept separate from order orchestration for independent testing."""

from __future__ import annotations

from src.models.order import OrderItem

# Simplified flat-rate tax by region; production would call a tax service (e.g. Avalara).
TAX_RATES = {
    "US-CA": 0.0725,
    "US-NY": 0.08,
    "US-TX": 0.0625,
    "US-OR": 0.0,  # no state sales tax
}
DEFAULT_TAX_RATE = 0.05


def calculate_subtotal(items: list[OrderItem]) -> float:
    return round(sum(item.quantity * item.unit_price for item in items), 2)


def calculate_tax(subtotal: float, region: str) -> float:
    rate = TAX_RATES.get(region, DEFAULT_TAX_RATE)
    return round(subtotal * rate, 2)


def calculate_total(items: list[OrderItem], region: str) -> tuple[float, float, float]:
    """Returns (subtotal, tax, total)."""
    subtotal = calculate_subtotal(items)
    tax = calculate_tax(subtotal, region)
    total = round(subtotal + tax, 2)
    return subtotal, tax, total
