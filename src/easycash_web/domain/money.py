"""Money handling — integer cents internally, fixed-point string in API/JSON."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


class MoneyError(ValueError):
    """Raised for invalid money operations."""

    pass


def cents_to_str(cents: int) -> str:
    """Convert integer cents to a two‑decimal string (no leading sign)."""
    sign = "-" if cents < 0 else ""
    a = abs(cents)
    return f"{sign}{a // 100}.{a % 100:02d}"


def str_to_cents(s: str | Decimal | float | int) -> int:
    """Parse a money string like "119.00" or "-5.5" into integer cents.

    Rules:
    - Decimal strings are interpreted with the exact number of digits.
    - Floating point values are converted via str() to avoid binary rounding.
    - Integers are returned as‑is.
    """
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        s = str(s)

    decimal_val = s if isinstance(s, Decimal) else Decimal(s)
    return int((decimal_val * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_decimal(cents: int) -> Decimal:
    """Return a Decimal for precise arithmetic (cents/100)."""
    return Decimal(cents) / Decimal(100)


def decimal_to_cents(d: Decimal) -> int:
    """Round a Decimal (e.g. 119.00) to integer cents."""
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money_add(a: int, b: int) -> int:
    """Add two cent amounts, preserving sign."""
    return a + b


def money_sub(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b


def money_mul(cents: int, factor: int) -> int:
    """Multiply cents by an integer factor (e.g. for VAT)."""
    return cents * factor


def vat_amount(gross_cents: int, rate_promille: int) -> int:
    """Calculate VAT amount from a gross amount (including VAT).

    If gross includes tax: gross = net + vat, where vat = gross * rate/1000
    and net = gross * 1000 / (1000 + rate). Because gross is cents and we need
    integer arithmetic, we keep everything in cents.
    Formula: vat = gross * rate_promille // (100_000 + rate_promille)
    where rate_promille = percent * 1000.
    """
    if rate_promille <= 0:
        return 0
    return (gross_cents * rate_promille) // (100_000 + rate_promille)


def net_amount(gross_cents: int, rate_promille: int) -> int:
    """Calculate net amount (without VAT) from gross (including VAT)."""
    if rate_promille <= 0:
        return gross_cents
    return gross_cents - vat_amount(gross_cents, rate_promille)


def gross_from_net(net_cents: int, rate_promille: int) -> int:
    """Calculate gross amount (including VAT) from net amount."""
    if rate_promille <= 0:
        return net_cents
    return (net_cents * (100_000 + rate_promille)) // 100_000
