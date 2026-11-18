"""Tests for calculator domain logic (expression parser)."""

import pytest

from easycash_web.domain.calculator import (
    Calculator,
    CalculatorError,
    calculate_expression,
)


class TestCalculator:
    def test_simple_number(self) -> None:
        calc = Calculator()
        assert calc.evaluate("100") == 10000  # 100.00 in cents
        assert calc.evaluate("0.01") == 1
        assert calc.evaluate("119.00") == 11900

    def test_german_decimal_comma(self) -> None:
        calc = Calculator()
        assert calc.evaluate("119,00") == 11900
        assert calc.evaluate("0,01") == 1

    def test_addition(self) -> None:
        calc = Calculator()
        assert calc.evaluate("100+50") == 15000
        assert calc.evaluate("100 + 50") == 15000

    def test_subtraction(self) -> None:
        calc = Calculator()
        assert calc.evaluate("100-30") == 7000

    def test_multiplication(self) -> None:
        calc = Calculator()
        assert calc.evaluate("100*2") == 20000
        assert calc.evaluate("50*1.19") == 5950

    def test_division(self) -> None:
        calc = Calculator()
        assert calc.evaluate("100/2") == 5000
        assert calc.evaluate("100/4") == 2500

    def test_precedence(self) -> None:
        calc = Calculator()
        # 100 + 50 * 2 = 200
        assert calc.evaluate("100+50*2") == 20000
        # (100 + 50) * 2 = 300
        assert calc.evaluate("(100+50)*2") == 30000

    def test_parentheses(self) -> None:
        calc = Calculator()
        assert calc.evaluate("(100+50)*2") == 30000
        assert calc.evaluate("((100+50)*2)") == 30000
        assert calc.evaluate("100*(2+3)") == 50000

    def test_unary_minus(self) -> None:
        calc = Calculator()
        assert calc.evaluate("-100") == -10000
        assert calc.evaluate("100+-50") == 5000

    def test_whitespace(self) -> None:
        calc = Calculator()
        assert calc.evaluate("  100  +  50  ") == 15000
        assert calc.evaluate("\t100\n+\t50\n") == 15000

    def test_decimal_with_comma(self) -> None:
        calc = Calculator()
        # German style: 100,50 + 50,25
        assert calc.evaluate("100,50+50,25") == 15075

    def test_complex_expression(self) -> None:
        calc = Calculator()
        # (100 + 50) * 1.19 - 20 = 158.50
        assert calc.evaluate("(100+50)*1.19-20") == 15850

    def test_empty_expression(self) -> None:
        calc = Calculator()
        with pytest.raises(CalculatorError, match="empty expression"):
            calc.evaluate("")
        with pytest.raises(CalculatorError, match="empty expression"):
            calc.evaluate("   ")

    def test_invalid_characters(self) -> None:
        calc = Calculator()
        with pytest.raises(CalculatorError):
            calc.evaluate("100abc")
        with pytest.raises(CalculatorError):
            calc.evaluate("100;50")
        with pytest.raises(CalculatorError):
            calc.evaluate("import os")

    def test_unclosed_parenthesis(self) -> None:
        calc = Calculator()
        with pytest.raises(CalculatorError, match="closing parenthesis"):
            calc.evaluate("(100+50")

    def test_unexpected_token(self) -> None:
        calc = Calculator()
        with pytest.raises(CalculatorError, match="unexpected token"):
            calc.evaluate("100 50")

    def test_division_by_zero(self) -> None:
        calc = Calculator()
        with pytest.raises(CalculatorError, match="division by zero"):
            calc.evaluate("100/0")

    def test_consecutive_operators(self) -> None:
        calc = Calculator()
        with pytest.raises(CalculatorError):
            calc.evaluate("100++50")

    def test_convenience_function(self) -> None:
        assert calculate_expression("100+50*1.19") == 15950
        assert calculate_expression("10,50") == 1050

    def test_rounding_half_up(self) -> None:
        calc = Calculator()
        # 1.005 rounds to 1.01 with ROUND_HALF_UP
        assert calc.evaluate("1.005") == 101
        # 0.004 rounds to 0.00
        assert calc.evaluate("0.004") == 0
        # 0.005 rounds to 0.01
        assert calc.evaluate("0.005") == 1
