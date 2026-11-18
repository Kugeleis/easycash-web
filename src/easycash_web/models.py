"""Domain models — single source of truth for data format.

Pydantic v2 models define the JSON file format and the REST API payloads.
Money is stored as integer cents internally; JSON/API payloads use a decimal
string with exactly 2 fraction digits (e.g. "119.00").
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Literal
from uuid import uuid7

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Money helpers (int cents internally; fixed-point string in JSON/API)
# ---------------------------------------------------------------------------


def cents_to_str(cents: int) -> str:
    """Convert cents to a fixed-point string with exactly 2 decimals."""
    sign: Literal["-", ""] = "-" if cents < 0 else ""
    a: int = abs(cents)
    return f"{sign}{a // 100}.{a % 100:02d}"


def str_to_cents(s: str | Decimal | float | int) -> int:
    """Parse a money value into integer cents."""
    if isinstance(s, int):
        return s
    if isinstance(s, float):
        s = str(s)

    decimal_val: Decimal = s if isinstance(s, Decimal) else Decimal(s)
    return int((decimal_val * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Common primitives
# ---------------------------------------------------------------------------


def new_uid() -> str:
    return str(uuid7())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AccountType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class BusinessType(StrEnum):
    FREELANCER = "freiberufler"  # Freiberufler
    SMALL_BUSINESS = "kleinunternehmer"  # Kleingewerbe


class AfAMode(StrEnum):
    ANNUAL = "annual"
    HALF_YEAR = "half_year"
    MONTH_PRECISE = "month_precise"
    PER_SETTINGS = "per_settings"


class DepreciationMethod(StrEnum):
    LINEAR = "linear"
    DEGRESSIVE = "degressive"


class BookingType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


# ---------------------------------------------------------------------------
# TaxRate with validity dates
# ---------------------------------------------------------------------------


class TaxRate(BaseModel):
    """VAT rate applicable to a booking/account/period."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_uid)
    code: str = Field(default="DE", description="Country code, e.g. DE")
    name: str = Field(..., description="Human-readable label, e.g. 'Regelsteuersatz'")
    promille: int = Field(19000, description="Percent * 1000, e.g. 19000 for 19%")
    valid_from: date
    valid_to: date | None = None
    description: str = ""

    @model_validator(mode="after")
    def _valid_range(self) -> TaxRate:
        if self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be <= valid_to")
        return self


# ---------------------------------------------------------------------------
# Account (Konto)
# ---------------------------------------------------------------------------


class Account(BaseModel):
    """Account — income or expense account."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_uid)
    name: str = Field(..., description="Account name")
    type: AccountType = AccountType.EXPENSE
    currency: str = "EUR"
    client_id: str = ""
    business_id: str = ""


# ---------------------------------------------------------------------------
# Booking (Einnahme/Ausgabe line)
# ---------------------------------------------------------------------------


class Booking(BaseModel):
    """Booking line."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_uid)
    booking_number: str = Field(default="", description="User-visible booking number")
    receipt_number: str = Field(default="", description="User-visible receipt number")
    date: date
    description: str = Field(default="", max_length=256)
    account_id: str = ""
    account_name: str = Field(default="")
    type: BookingType = BookingType.EXPENSE
    gross_cents: int = Field(0, description="Gross amount in integer cents")
    vat_rate_promille: int = Field(0, description="Percent*1000, e.g. 19000 for 19%")
    vat_rate_percent: int = Field(0, description="Percent, e.g. 19 for 19%")
    af_a_mode: AfAMode = AfAMode.PER_SETTINGS
    af_a_method: DepreciationMethod = DepreciationMethod.LINEAR
    af_a_jahre: int = Field(0, description="Depreciation years")
    af_a_satz_promille: int = Field(0, description="Depreciation rate percent*1000")
    af_a_restwert_cents: int = Field(0, description="Residual value in cents")
    client_id: str = ""
    business_id: str = ""
    year: int = Field(default=0)
    month: int = Field(default=0)

    @property
    def net_cents(self) -> int:
        return self.gross_cents - self.vat_cents

    @property
    def vat_cents(self) -> int:
        if self.vat_rate_promille <= 0:
            return 0
        # promille = percent * 1000, so percent = promille / 1000
        # VAT = gross * percent / (100 + percent)
        #     = gross * (promille/1000) / (100 + promille/1000)
        #     = gross * promille / (100000 + promille)
        return (self.gross_cents * self.vat_rate_promille) // (100000 + self.vat_rate_promille)


# ---------------------------------------------------------------------------
# Recurring booking (Dauerbuchung)
# ---------------------------------------------------------------------------


class RecurringBooking(BaseModel):
    """Recurring booking template."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_uid)
    name: str = Field(..., description="Template name")
    interval_months: int = Field(1, ge=1, description="1=monthly, 3=quarterly, etc.")
    next_due: date
    booking: Booking


# ---------------------------------------------------------------------------
# Business (Betrieb)
# ---------------------------------------------------------------------------


class Business(BaseModel):
    """Business (Betrieb) under a client."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_uid)
    name: str = Field(..., description="Business name")
    business_type: BusinessType = BusinessType.FREELANCER
    tax_id: str = Field(default="", description="Steuernummer")
    vat_id: str = Field(default="", description="Umsatzsteuer-IdNr.")
    kleinunternehmer: bool = Field(False, description="§19 UStG Kleinunternehmerregelung")


# ---------------------------------------------------------------------------
# Client (Mandant)
# ---------------------------------------------------------------------------


class Client(BaseModel):
    """Client (Mandant) — top-level entity containing one JSON book file."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_uid)
    name: str = Field(..., description="Mandant name")
    businesses: list[Business] = []
    accounts: list[Account] = []
    tax_rates: list[TaxRate] = []
    bookings: list[Booking] = []
    recurring: list[RecurringBooking] = []
    settings: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level book file (JSON) — product artifact
# ---------------------------------------------------------------------------


class BookFile(BaseModel):
    """One JSON file per client (Mandant)."""

    model_config = ConfigDict(populate_by_name=True)

    format: str = Field(default="easycash-web", description="Format identifier")
    format_version: int = Field(default=1, description="Schema version")
    revision: int = Field(default=0, description="Incremented on every save")
    meta: dict = Field(default_factory=dict, description="client name, business type, timestamps")
    settings: dict = Field(default_factory=dict)
    accounts: list[Account] = Field(default_factory=list)
    tax_rates: list[TaxRate] = Field(default_factory=list)
    bookings: list[Booking] = Field(default_factory=list)
    recurring: list[RecurringBooking] = Field(default_factory=list)
    clients: list[Client] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_version(self) -> BookFile:
        if self.format_version < 1:
            raise ValueError("format_version must be >= 1")
        return self


# ---------------------------------------------------------------------------
# Migration chain registry: version → migration callable
# ---------------------------------------------------------------------------


def migrate_v1_to_v2(data: dict) -> dict:
    """Placeholder migration from format_version 1 to 2."""
    data["format_version"] = 2
    data["revision"] = data.get("revision", 0) + 1
    return data


MIGRATIONS: dict[int, Callable[[dict], dict]] = {
    2: migrate_v1_to_v2,
}


def apply_migrations(data: dict) -> dict:
    """Apply all migrations from data['format_version'] up to current."""
    current = data.get("format_version", 1)
    target = BookFile.model_fields["format_version"].default
    for v in range(current + 1, target + 1):
        if v in MIGRATIONS:
            data = MIGRATIONS[v](data)
    return data
