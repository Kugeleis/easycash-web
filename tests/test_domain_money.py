"""Tests for money domain logic."""

import pytest

from easycash_web.domain.money import (
    cents_to_decimal,
    cents_to_str,
    decimal_to_cents,
    gross_from_net,
    money_add,
    money_mul,
    money_sub,
    net_amount,
    str_to_cents,
    vat_amount,
)


class TestCentsToStr:
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


class TestStrToCents:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("0.00", 0),
            ("1.00", 100),
            ("1.19", 119),
            ("119.00", 11900),
            ("-1.19", -119),
            ("-5.50", -550),
            ("0.01", 1),
            (100, 100),
            (-500, -500),
        ],
    )
    def test_str_to_cents(self, value, expected: int) -> None:
        assert str_to_cents(value) == expected


class TestMoneyOperations:
    def test_add(self) -> None:
        assert money_add(100, 200) == 300
        assert money_add(-100, 200) == 100

    def test_sub(self) -> None:
        assert money_sub(300, 100) == 200
        assert money_sub(100, 200) == -100

    def test_mul(self) -> None:
        assert money_mul(100, 5) == 500


class TestVatCalculation:
    def test_vat_19_percent(self) -> None:
        # 119.00 gross, 19% VAT → 100.00 net, 19.00 VAT
        assert vat_amount(11900, 19000) == 1900
        assert net_amount(11900, 19000) == 10000

    def test_vat_7_percent(self) -> None:
        # 107.00 gross, 7% VAT → 100.00 net, 7.00 VAT
        assert vat_amount(10700, 7000) == 700
        assert net_amount(10700, 7000) == 10000

    def test_vat_0_percent(self) -> None:
        assert vat_amount(10000, 0) == 0
        assert net_amount(10000, 0) == 10000

    def test_gross_from_net(self) -> None:
        # 100.00 net + 19% VAT = 119.00 gross
        assert gross_from_net(10000, 19000) == 11900
        # 100.00 net + 7% VAT = 107.00 gross
        assert gross_from_net(10000, 7000) == 10700
        # 0% VAT
        assert gross_from_net(10000, 0) == 10000


class TestRounding:
    def test_decimal_roundtrip(self) -> None:
        d = cents_to_decimal(11900)
        assert decimal_to_cents(d) == 11900

    def test_cents_to_decimal(self) -> None:
        assert cents_to_decimal(11900) == 119.00  # Decimal comparison
        assert cents_to_decimal(-550) == -5.50
