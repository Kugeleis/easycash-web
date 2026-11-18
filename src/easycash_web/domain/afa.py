"""AfA (Abschreibung) depreciation domain logic.

Implements German tax law depreciation modes:
- Annual (GANZJAHRES_AFA = 0)
- Half-year (HALBJAHRES_AFA = 1, includes half-year rule)
- Month-precise (MONATSGENAUE_AFA = 2)
- Per settings (ENTSPRECHEND_EINSTELLUNGEN_AFA = 3)

Supports linear and degressive depreciation methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from easycash_web.models import Booking

AfAMode = Literal["annual", "half_year", "month_precise", "per_settings"]
DepreciationMethod = Literal["linear", "degressive"]


@dataclass
class AfAConfig:
    """Configuration for an asset's depreciation."""

    mode: AfAMode
    method: DepreciationMethod
    year: int  # fiscal year of the asset acquisition
    first_year_depreciation_percentage: Decimal  # e.g. 0.5 for half-year rule
    linear_rate_per_year: Decimal  # percent per year (e.g. 0.1 = 10%)
    degressive_rate_percent: Decimal  # percent per year (e.g. 0.25 = 25% per year)
    acquisition_date: date
    residual_value_at_acquisition: int = 0  # cents
    total_depreciated_percentage: Decimal = Decimal("0")  # accumulated

    def depreciate_month(
        self,
        month: int,  # 1-12
        current_year: int,
        accumulated_for_year: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """Calculate depreciation for a given month of a given year.

        Returns (depreciated_amount_percent, accumulated_for_year).
        """
        # Validate month
        if not 1 <= month <= 12:
            raise ValueError(f"Invalid month: {month}")

        # Check if month belongs to the depreciation start year
        is_first_year = current_year == self.year

        if self.mode == "annual":
            # Annual depreciation: 100% in year of acquisition
            if is_first_year and accumulated_for_year == 0:
                dep_percent = Decimal("1")
                new_accum = min(accumulated_for_year + dep_percent, Decimal("1"))
                return dep_percent, new_accum
            return Decimal("0"), accumulated_for_year

        elif self.mode == "half_year":
            # Half-year rule: 50% in first year (regardless of month)
            if is_first_year and accumulated_for_year == 0:
                dep_percent = Decimal("0.5")
                new_accum = min(accumulated_for_year + dep_percent, Decimal("1"))
                return dep_percent, new_accum
            # Subsequent years: regular depreciation
            dep_percent = self.linear_rate_per_year
            new_accum = min(accumulated_for_year + dep_percent, Decimal("1"))
            return dep_percent, new_accum

        elif self.mode == "month_precise":
            # Month-precise: depreciate proportional to months
            months_in_year = 12
            dep_percent = self.linear_rate_per_year * Decimal(month) / Decimal(months_in_year)
            new_accum = min(accumulated_for_year + dep_percent, Decimal("1"))
            return dep_percent, new_accum

        elif self.mode == "per_settings":
            # Use configured monthly or annual schedule (simplified)
            dep_percent = self.linear_rate_per_year
            new_accum = min(accumulated_for_year + dep_percent, Decimal("1"))
            return dep_percent, new_accum

        else:
            raise ValueError(f"Unknown AfA mode: {self.mode}")

    def get_remaining_depreciable_amount(
        self, book_value_at_year_start_cents: int, accumulated_percent: Decimal
    ) -> int:
        """Calculate remaining amount that can still be depreciated.

        Book value after depreciation = book_value * (1 - accumulated_percent)
        Remaining depreciable = book_value - residual_value_at_acquisition
        """
        book_value = book_value_at_year_start_cents
        remaining_percent = Decimal("1") - accumulated_percent
        depreciable_base = Decimal(book_value) * remaining_percent
        remaining_depreciable = depreciable_base - Decimal(self.residual_value_at_acquisition)
        return int(remaining_depreciable.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def compute_depreciation(
        self, month: int, year: int, accumulated: Decimal
    ) -> tuple[int, Decimal]:
        """Compute actual depreciation amount in cents for a given month.

        Returns (depreciated_cents, new_accumulated_percent).
        """
        dep_percent, new_accum = self.depreciate_month(month, year, accumulated)

        # Calculate depreciable base (book value - residual) for this year
        # This is a simplified model; real AfA depends on asset-specific rates
        # and tax regulations. Here we use linear_rate_per_year as the monthly factor.
        base = Decimal(self.residual_value_at_acquisition) + (Decimal(1) - accumulated) * Decimal(
            self.residual_value_at_acquisition
        )

        # Fallback: if we don't have a proper book value, use a default
        if base == 0:
            dep_cents = 0
        else:
            dep_cents = int((base * dep_percent).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        return dep_cents, new_accum


class AfAService:
    """High-level service for managing asset depreciation across bookings."""

    def __init__(self) -> None:
        self.assets: dict[str, AfAConfig] = {}

    def add_asset(self, asset_id: str, config: AfAConfig) -> None:
        self.assets[asset_id] = config

    def apply_af_a_to_booking(self, booking: Booking, asset_id: str, month: int, year: int) -> int:
        """Apply AfA depreciation to a booking.

        Returns the depreciation amount in cents.
        """
        if asset_id not in self.assets:
            return 0

        asset = self.assets[asset_id]

        dep_cents, _ = asset.compute_depreciation(month, year, asset.total_depreciated_percentage)
        return dep_cents


# Re-export common symbols
__all__ = [
    "AfAMode",
    "DepreciationMethod",
    "AfAConfig",
    "AfAService",
]
