"""Calculator domain logic — expression parser for amount fields.

Replaces the original VCalcParser from EasyCash&Tax. Supports:
- Basic arithmetic: +, -, *, /
- Parentheses for grouping
- Decimal numbers with both . and , (German locale)
- Results as integer cents
- Safe evaluation (no arbitrary code execution)
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal


class CalculatorError(ValueError):
    """Raised when an expression cannot be parsed or evaluated."""

    pass


class Calculator:
    """Safe arithmetic expression evaluator for amount fields.

    Supports a restricted subset of arithmetic with no function calls,
    no variables, and no attribute access — only numbers and operators.
    """

    # Allowed tokens: numbers, operators, parentheses, whitespace
    _TOKEN_RE = re.compile(
        r"\s*(?:"
        r"(?P<number>\d+([.,]\d+)?)"
        r"|(?P<op>[+\-*/])"
        r"|(?P<lparen>\()"
        r"|(?P<rparen>\))"
        r")"
    )

    _PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}

    def __init__(self) -> None:
        self._pos: int = 0
        self._tokens: list[tuple[str, str]] = []
        self._expr: str = ""

    def evaluate(self, expression: str) -> int:
        """Evaluate an arithmetic expression and return result in integer cents.

        Args:
            expression: Arithmetic expression like "100+50*1.19" or "100+50*1,19"

        Returns:
            Result in integer cents (e.g., 11900 for 119.00)

        Raises:
            CalculatorError: If the expression is invalid or cannot be evaluated.
        """
        if not expression or not expression.strip():
            raise CalculatorError("empty expression")

        self._expr = expression
        self._pos = 0
        self._tokens = self._tokenize(expression)

        if not self._tokens:
            raise CalculatorError("no valid tokens found")

        try:
            result = self._parse_expression()
        except CalculatorError:
            raise
        except Exception as exc:
            raise CalculatorError(f"evaluation error: {exc}") from exc

        if self._pos < len(self._tokens):
            raise CalculatorError(f"unexpected token: {self._tokens[self._pos]}")

        # Convert result Decimal -> integer cents
        cents = int((result * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cents

    # ------------------------------------------------------------------
    # Tokenizer
    # ------------------------------------------------------------------

    def _tokenize(self, expression: str) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        pos = 0
        while pos < len(expression):
            # Skip whitespace explicitly so trailing whitespace is tolerated.
            while pos < len(expression) and expression[pos].isspace():
                pos += 1
            if pos >= len(expression):
                break
            match = self._TOKEN_RE.match(expression, pos)
            if not match or match.end() == pos:
                ch = expression[pos]
                raise CalculatorError(f"invalid character: {ch!r}")
            pos = match.end()
            kind = match.lastgroup
            if kind == "number":
                # Normalize German decimal comma to dot
                value = match.group(kind).replace(",", ".")
                tokens.append(("number", value))
            elif kind == "op":
                tokens.append(("op", match.group(kind)))
            elif kind in ("lparen", "rparen"):
                tokens.append((kind, match.group(kind)))
        return tokens

    # ------------------------------------------------------------------
    # Recursive descent parser (Pratt-style)
    # ------------------------------------------------------------------

    def _peek(self) -> tuple[str, str] | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self) -> tuple[str, str]:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _parse_expression(self) -> Decimal:
        """Parse addition/subtraction (lowest precedence)."""
        left = self._parse_term()
        while True:
            tok = self._peek()
            if tok and tok[0] == "op" and tok[1] in ("+", "-"):
                self._consume()
                right = self._parse_term()
                if tok[1] == "+":
                    left = left + right
                else:
                    left = left - right
            else:
                break
        return left

    def _parse_term(self) -> Decimal:
        """Parse multiplication/division (medium precedence)."""
        left = self._parse_factor()
        while True:
            tok = self._peek()
            if tok and tok[0] == "op" and tok[1] in ("*", "/"):
                self._consume()
                right = self._parse_factor()
                if tok[1] == "*":
                    left = left * right
                else:
                    if right == 0:
                        raise CalculatorError("division by zero")
                    left = left / right
            else:
                break
        return left

    def _parse_factor(self) -> Decimal:
        """Parse a number or parenthesized expression (highest precedence)."""
        tok = self._peek()
        if tok is None:
            raise CalculatorError("unexpected end of expression")

        kind, value = tok

        if kind == "number":
            self._consume()
            return Decimal(value)

        if kind == "lparen":
            self._consume()
            inner = self._parse_expression()
            close = self._peek()
            if close is None or close[0] != "rparen":
                raise CalculatorError("missing closing parenthesis")
            self._consume()
            return inner

        if kind == "op" and value == "-":
            # Unary minus
            self._consume()
            return -self._parse_factor()

        raise CalculatorError(f"unexpected token: {kind!r} {value!r}")


def calculate_expression(expression: str) -> int:
    """Convenience function: evaluate expression -> integer cents."""
    calc = Calculator()
    return calc.evaluate(expression)


__all__ = ["Calculator", "CalculatorError", "calculate_expression"]
