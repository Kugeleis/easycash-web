"""Reports domain logic: EÜR, GuV, SuSa, Journal."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from easycash_web.models import BookFile, BookingType


class ReportsError(ValueError):
    """Raised for report-related errors."""

    pass


class EuerLine(BaseModel):
    """Single EÜR (Anlage EÜR) line."""

    line_number: str
    description: str = ""
    amount_cents: int = 0


class EuerReport(BaseModel):
    """EÜR report for a year."""

    year: int
    kleinunternehmer: bool
    lines: list[EuerLine] = []
    total_income_cents: int = 0
    total_expenses_cents: int = 0
    profit_loss_cents: int = 0


class GuVSection(BaseModel):
    """GuV section (Einnahmen/Ausgaben)."""

    name: str
    total_cents: int = 0
    accounts: list[str] = []


class GuVReport(BaseModel):
    """GuV (Gewinn- und Verlustrechnung) report."""

    year: int
    sections: list[GuVSection] = []
    profit_loss_cents: int = 0


class SuSaAccount(BaseModel):
    """Account with balance for SuSa report."""

    account_id: str
    balance_cents: int = 0


class SuSaReport(BaseModel):
    """SuSa (Summen- und Saldenliste) report."""

    year: int
    accounts: list[SuSaAccount] = []


class JournalEntry(BaseModel):
    """Single journal entry."""

    booking_id: str
    date: date
    description: str
    account_name: str
    gross_cents: int
    net_cents: int
    vat_cents: int
    tax_rate_promille: int
    account_type: str = ""


class JournalReport(BaseModel):
    """Journal report."""

    year: int
    entries: list[JournalEntry] = []


# ---------------------------------------------------------------------------
# EÜR line mapping helpers
# ---------------------------------------------------------------------------

# Income lines: (line_number, description, vat_rate_promille)
# Kleinunternehmer line 12 has no VAT rate (None)
_EUER_INCOME_LINES: list[tuple[str, str, int | None]] = [
    ("12", "Betriebseinnahmen (brutto)", None),  # Kleinunternehmer only
    ("15", "Einnahmen 19% USt", 19000),
    ("16", "Einnahmen 7% USt", 7000),
    ("17", "Einnahmen 0% USt", 0),
]

# Expense lines: (line_number, description)
_EUER_EXPENSE_LINES: list[tuple[str, str]] = [
    ("24", "Bürobedarf"),
    ("30", "Miete"),
    ("34", "Fahrtkosten"),
    ("50", "Abschreibungen"),
]


def _map_expense_to_euer_line(account_name: str) -> str:
    """Map an expense account name to an EÜR line number.

    Returns the line number as string, e.g. "24" for Bürobedarf.
    Falls back to "34" (sonstige Ausgaben) for unknown accounts.
    """
    name = account_name.lower()
    if "bürobedarf" in name or "buero" in name or "büro" in name:
        return "24"
    if "miete" in name:
        return "30"
    if "fahrtkosten" in name or "auto" in name or "fahrzeug" in name:
        return "34"
    if "afa" in name or "abschreibung" in name:
        return "50"
    if "versicherung" in name:
        return "41"
    if "werbungskosten" in name:
        return "55"
    return "34"


# ---------------------------------------------------------------------------
# Account balance helper
# ---------------------------------------------------------------------------


def calculate_account_balance(book: BookFile, account_id: str, year: int) -> int:
    """Calculate account balance for a given year.

    Sums gross amounts of bookings for the specified account in the given year.
    """
    balance = 0
    for booking in book.bookings:
        if booking.account_id == account_id and booking.year == year:
            balance += booking.gross_cents
    return balance


# ---------------------------------------------------------------------------
# EÜR (Anlage EÜR)
# ---------------------------------------------------------------------------


def calculate_euer_report(
    book: BookFile,
    year: int,
    kleinunternehmer: bool,
) -> EuerReport:
    """Calculate EÜR (Anlage EÜR) report for a year.

    Args:
        book: BookFile containing clients, accounts, and bookings.
        year: Fiscal year to calculate report for.
        kleinunternehmer: If True, Kleinunternehmer mode (line 12, brutto).
                         If False, normal taxpayer mode (lines 15-17, netto).

    Returns:
        EuerReport with lines for EÜR format.
    """
    year_bookings = [b for b in book.bookings if b.year == year]

    # Pre-compute income and expense totals
    income_by_vat_rate: dict[int, int] = {}
    income_gross_total = 0
    expense_by_line: dict[str, int] = {}
    total_expenses = 0

    for b in year_bookings:
        if b.type == BookingType.INCOME:
            income_gross_total += b.gross_cents
            income_by_vat_rate[b.vat_rate_promille] = (
                income_by_vat_rate.get(b.vat_rate_promille, 0) + b.net_cents
            )
        else:
            line = _map_expense_to_euer_line(b.account_name)
            expense_by_line[line] = expense_by_line.get(line, 0) + b.net_cents

    # Build lines in canonical order
    lines: list[EuerLine] = []

    # Income lines
    if kleinunternehmer:
        # Line 12: Betriebseinnahmen (brutto)
        lines.append(
            EuerLine(
                line_number="12",
                description="Betriebseinnahmen (brutto)",
                amount_cents=income_gross_total,
            )
        )
        # Lines 15-17 are 0 for Kleinunternehmer
        for line_num, desc, _ in _EUER_INCOME_LINES[1:]:
            lines.append(EuerLine(line_number=line_num, description=desc, amount_cents=0))
        total_income = income_gross_total
    else:
        # Line 12 is 0 for normal taxpayer
        lines.append(
            EuerLine(
                line_number="12",
                description="Betriebseinnahmen (brutto)",
                amount_cents=0,
            )
        )
        # Lines 15-17: netto income by VAT rate
        for line_num, desc, promille in _EUER_INCOME_LINES[1:]:
            amount = income_by_vat_rate.get(promille, 0)
            lines.append(EuerLine(line_number=line_num, description=desc, amount_cents=amount))
        total_income = sum(income_by_vat_rate.values())

    # Expense lines
    for line_num, desc in _EUER_EXPENSE_LINES:
        amount = expense_by_line.get(line_num, 0)
        lines.append(EuerLine(line_number=line_num, description=desc, amount_cents=amount))
        total_expenses += amount

    profit_loss = total_income - total_expenses

    return EuerReport(
        year=year,
        kleinunternehmer=kleinunternehmer,
        lines=lines,
        total_income_cents=total_income,
        total_expenses_cents=total_expenses,
        profit_loss_cents=profit_loss,
    )


# ---------------------------------------------------------------------------
# GuV (Gewinn- und Verlustrechnung)
# ---------------------------------------------------------------------------


def calculate_guv_report(book: BookFile, year: int) -> GuVReport:
    """Calculate GuV (Gewinn- und Verlustrechnung) report for a year."""
    year_bookings = [b for b in book.bookings if b.year == year]

    income_accounts: set[str] = set()
    expense_accounts: set[str] = set()
    total_income = 0
    total_expenses = 0

    for b in year_bookings:
        if b.type == BookingType.INCOME:
            total_income += b.net_cents
            income_accounts.add(b.account_id)
        else:
            total_expenses += b.net_cents
            expense_accounts.add(b.account_id)

    sections = [
        GuVSection(name="Einnahmen", total_cents=total_income, accounts=sorted(income_accounts)),
        GuVSection(name="Ausgaben", total_cents=total_expenses, accounts=sorted(expense_accounts)),
    ]

    return GuVReport(year=year, sections=sections, profit_loss_cents=total_income - total_expenses)


# ---------------------------------------------------------------------------
# SuSa (Summen- und Saldenliste)
# ---------------------------------------------------------------------------


def calculate_susa_report(book: BookFile, year: int) -> SuSaReport:
    """Calculate SuSa (Summen- und Saldenliste) report for a year.

    Includes all accounts defined in the book, even those with zero balance.
    """
    year_bookings = [b for b in book.bookings if b.year == year]

    # Start with all accounts from the book (zero balance default)
    balances: dict[str, int] = {acc.id: 0 for acc in book.accounts}

    for b in year_bookings:
        if b.account_id not in balances:
            balances[b.account_id] = 0
        balances[b.account_id] += b.gross_cents

    accounts = [
        SuSaAccount(account_id=acc_id, balance_cents=balance)
        for acc_id, balance in balances.items()
    ]

    return SuSaReport(year=year, accounts=accounts)


# ---------------------------------------------------------------------------
# Journal (Buchungsjournal)
# ---------------------------------------------------------------------------


def calculate_journal_report(book: BookFile, year: int) -> JournalReport:
    """Calculate Journal (Buchungsjournal) report for a year.

    Entries are sorted by date ascending.
    """
    year_bookings = sorted(
        [b for b in book.bookings if b.year == year],
        key=lambda b: b.date,
    )

    entries: list[JournalEntry] = []
    for booking in year_bookings:
        entries.append(
            JournalEntry(
                booking_id=booking.id,
                date=booking.date,
                description=booking.description,
                account_name=booking.account_name,
                gross_cents=booking.gross_cents,
                net_cents=booking.net_cents,
                vat_cents=booking.vat_cents,
                tax_rate_promille=booking.vat_rate_promille,
                account_type=booking.type,
            )
        )

    return JournalReport(year=year, entries=entries)
