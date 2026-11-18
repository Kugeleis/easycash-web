"""Tests for money helpers and Pydantic models."""

from datetime import date

import pytest

from easycash_web.models import (
    Account,
    AccountType,
    AfAMode,
    BookFile,
    Booking,
    Business,
    BusinessType,
    Client,
    DepreciationMethod,
    RecurringBooking,
    TaxRate,
    cents_to_str,
    str_to_cents,
)

# ---------------------------------------------------------------------------
# Money helpers
# ---------------------------------------------------------------------------


class TestMoneyHelpers:
    @pytest.mark.parametrize(
        "cents,expected",
        [
            (0, "0.00"),
            (1, "0.01"),
            (5, "0.05"),
            (10, "0.10"),
            (100, "1.00"),
            (119, "1.19"),
            (11900, "119.00"),
            (-5, "-0.05"),
            (-11900, "-119.00"),
        ],
    )
    def test_cents_to_str(self, cents: int, expected: str) -> None:
        assert cents_to_str(cents) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("0.00", 0),
            ("1.00", 100),
            ("1.19", 119),
            ("119.00", 11900),
            ("-1.19", -119),
            (100, 100),
        ],
    )
    def test_str_to_cents(self, value, expected: int) -> None:
        assert str_to_cents(value) == expected


# ---------------------------------------------------------------------------
# TaxRate
# ---------------------------------------------------------------------------


class TestTaxRate:
    def test_defaults(self) -> None:
        rate = TaxRate(name="Regelsteuersatz", valid_from=date(2007, 1, 1))
        assert rate.code == "DE"
        assert rate.promille == 19000
        assert rate.valid_to is None

    def test_valid_range_ok(self) -> None:
        rate = TaxRate(
            name="Reduced",
            valid_from=date(2020, 1, 1),
            valid_to=date(2025, 12, 31),
        )
        assert rate.valid_to is not None
        assert rate.valid_from < rate.valid_to

    def test_valid_range_reversed(self) -> None:
        with pytest.raises(ValueError, match="valid_from must be <= valid_to"):
            TaxRate(
                name="Bad",
                valid_from=date(2025, 1, 1),
                valid_to=date(2020, 1, 1),
            )


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------


class TestBooking:
    @pytest.fixture()
    def booking(self) -> Booking:
        return Booking(
            date=date(2026, 1, 15),
            gross_cents=11900,
            vat_rate_promille=19000,
            vat_rate_percent=19,
        )

    def test_net_cents(self, booking: Booking) -> None:
        assert booking.net_cents == 10000

    def test_vat_cents(self, booking: Booking) -> None:
        assert booking.vat_cents == 1900

    def test_zero_vat(self) -> None:
        b = Booking(date=date(2026, 1, 1), gross_cents=10000, vat_rate_promille=0)
        assert b.vat_cents == 0
        assert b.net_cents == 10000

    def test_af_a_defaults(self) -> None:
        b = Booking(date=date(2026, 1, 1), gross_cents=1000)
        assert b.af_a_mode == AfAMode.PER_SETTINGS
        assert b.af_a_method == DepreciationMethod.LINEAR
        assert b.af_a_jahre == 0
        assert b.af_a_restwert_cents == 0


# ---------------------------------------------------------------------------
# Account / Business / Client
# ---------------------------------------------------------------------------


class TestEntities:
    def test_account(self) -> None:
        a = Account(name="Bürobedarf", type=AccountType.EXPENSE)
        assert a.type == AccountType.EXPENSE
        assert a.currency == "EUR"

    def test_business(self) -> None:
        b = Business(name="Consulting", business_type=BusinessType.FREELANCER)
        assert b.kleinunternehmer is False

    def test_client(self) -> None:
        c = Client(name="Max Mustermann")
        assert c.businesses == []
        assert c.accounts == []


# ---------------------------------------------------------------------------
# RecurringBooking
# ---------------------------------------------------------------------------


class TestRecurringBooking:
    def test_minimal(self) -> None:
        rb = RecurringBooking(
            name="Rent",
            next_due=date(2026, 2, 1),
            booking=Booking(date=date(2026, 1, 1), gross_cents=1000),
        )
        assert rb.interval_months == 1


# ---------------------------------------------------------------------------
# BookFile
# ---------------------------------------------------------------------------


class TestBookFile:
    def test_defaults(self) -> None:
        bf = BookFile()
        assert bf.format == "easycash-web"
        assert bf.format_version == 1
        assert bf.revision == 0

    def test_rejects_old_version(self) -> None:
        with pytest.raises(ValueError, match="format_version must be >= 1"):
            BookFile(format_version=0)

    def test_serialization_roundtrip(self) -> None:
        booking = Booking(
            date=date(2026, 1, 15),
            gross_cents=11900,
            vat_rate_promille=19000,
            vat_rate_percent=19,
        )
        bf = BookFile(
            bookings=[booking],
            accounts=[Account(name="Office", type=AccountType.EXPENSE)],
            tax_rates=[
                TaxRate(name="Standard", valid_from=date(2007, 1, 1)),
            ],
        )
        data = bf.model_dump()
        restored = BookFile.model_validate(data)
        assert restored == bf
