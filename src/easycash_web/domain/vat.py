"""VAT domain logic — rate lookup by date, VAT/nett calculations."""

from __future__ import annotations

from datetime import date

from easycash_web.domain.money import net_amount, vat_amount
from easycash_web.models import TaxRate


class VatError(ValueError):
    """Raised for VAT-related errors."""

    pass


class TaxRateRepository:
    """In-memory lookup of tax rates with date-based resolution."""

    def __init__(self, rates: list[TaxRate]) -> None:
        self._rates = sorted(rates, key=lambda r: r.valid_from)

    def rate_for_date(self, d: date) -> TaxRate | None:
        """Return the first tax rate whose validity range contains *d*.

        Returns None if no rate matches (e.g. very old dates with no configured rate).
        """
        for rate in reversed(self._rates):
            if rate.valid_from <= d and (rate.valid_to is None or d <= rate.valid_to):
                return rate
        return None

    def rate_by_promille(self, promille: int) -> TaxRate | None:
        """Find a rate by its promille value (e.g. 19000 = 19%)."""
        for rate in reversed(self._rates):
            if rate.promille == promille:
                return rate
        return None

    @property
    def all_rates(self) -> list[TaxRate]:
        return list(self._rates)


def calculate_vat(gross_cents: int, rate_promille: int) -> tuple[int, int, int]:
    """Return (gross, net, vat) for a booking.

    All values are integer cents.
    """
    vat = vat_amount(gross_cents, rate_promille)
    net = net_amount(gross_cents, rate_promille)
    return gross_cents, net, vat


def effective_rate_for_booking(
    booking_date: date,
    repository: TaxRateRepository,
    override_promille: int | None = None,
) -> int:
    """Determine the effective VAT rate for a booking.

    If *override_promille* is given (e.g. from the booking), it wins.
    Otherwise the rate is looked up from the repository by date.
    Returns 0 if no rate can be determined.
    """
    if override_promille is not None and override_promille > 0:
        return override_promille
    rate = repository.rate_for_date(booking_date)
    return rate.promille if rate else 0


def validate_tax_rate(rate: TaxRate) -> None:
    """Validate a TaxRate for logical consistency."""
    if rate.promille < 0:
        raise VatError(f"negative VAT rate: {rate.promille} promille")
    if rate.valid_to is not None and rate.valid_from > rate.valid_to:
        raise VatError(f"valid_from ({rate.valid_from}) must be <= valid_to ({rate.valid_to})")
