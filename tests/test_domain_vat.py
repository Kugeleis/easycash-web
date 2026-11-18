"""Tests for VAT domain logic."""

from datetime import date

import pytest

from easycash_web.domain.vat import (
    TaxRateRepository,
    VatError,
    calculate_vat,
    effective_rate_for_booking,
    validate_tax_rate,
)
from easycash_web.models import TaxRate


@pytest.fixture
def repository() -> TaxRateRepository:
    return TaxRateRepository(
        [
            TaxRate(name="Regel 19%", valid_from=date(2007, 1, 1), promille=19000),
            TaxRate(name="Ermäßigt 7%", valid_from=date(2007, 1, 1), promille=7000),
            TaxRate(name="Kleinunternehmer 0%", valid_from=date(2024, 1, 1), promille=0),
        ]
    )


class TestTaxRateRepository:
    def test_rate_for_modern_date(self, repository: TaxRateRepository) -> None:
        # 0% starts 2024-01-01, so for 2026 the 0% rate applies
        rate = repository.rate_for_date(date(2026, 6, 15))
        assert rate is not None
        assert rate.promille == 0
        assert rate.name == "Kleinunternehmer 0%"

    def test_rate_for_old_date(self, repository: TaxRateRepository) -> None:
        # 2007-01-01 to 2023-12-31: 19% and 7% (both valid from 2007)
        rate = repository.rate_for_date(date(2010, 1, 1))
        assert rate is not None
        assert rate.promille in (19000, 7000)

    def test_rate_by_promille(self, repository: TaxRateRepository) -> None:
        rate = repository.rate_by_promille(7000)
        assert rate is not None
        assert rate.name == "Ermäßigt 7%"

    def test_rate_not_found(self, repository: TaxRateRepository) -> None:
        assert repository.rate_by_promille(16000) is None

    def test_empty_repository(self) -> None:
        repo = TaxRateRepository([])
        assert repo.rate_for_date(date(2026, 1, 1)) is None


class TestCalculateVat:
    def test_19_roundtrip(self) -> None:
        gross, net, vat = calculate_vat(11900, 19000)
        assert gross == 11900
        assert net == 10000
        assert vat == 1900

    def test_7_roundtrip(self) -> None:
        gross, net, vat = calculate_vat(10700, 7000)
        assert gross == 10700
        assert net == 10000
        assert vat == 700

    def test_0_rate(self) -> None:
        gross, net, vat = calculate_vat(10000, 0)
        assert gross == 10000
        assert net == 10000
        assert vat == 0


class TestEffectiveRate:
    def test_override_wins(self, repository: TaxRateRepository) -> None:
        rate = effective_rate_for_booking(date(2026, 1, 1), repository, override_promille=7000)
        assert rate == 7000

    def test_lookup_by_date(self, repository: TaxRateRepository) -> None:
        rate = effective_rate_for_booking(date(2010, 1, 1), repository)
        assert rate in (19000, 7000)  # 19% or 7% both valid from 2007

    def test_no_rate(self) -> None:
        repo = TaxRateRepository([])
        assert effective_rate_for_booking(date(2026, 1, 1), repo) == 0


class TestValidateTaxRate:
    def test_valid(self) -> None:
        validate_tax_rate(TaxRate(name="OK", valid_from=date(2020, 1, 1), promille=19000))

    def test_negative_rate(self) -> None:
        with pytest.raises(VatError, match="negative VAT rate"):
            validate_tax_rate(TaxRate(name="Neg", valid_from=date(2020, 1, 1), promille=-100))

    def test_reversed_dates(self) -> None:
        # Pydantic model already rejects reversed dates at construction
        # We expect ValueError from model_validator
        with pytest.raises(ValueError, match="valid_from must be <= valid_to"):
            TaxRate(
                name="Bad",
                valid_from=date(2025, 1, 1),
                valid_to=date(2020, 1, 1),
            )
