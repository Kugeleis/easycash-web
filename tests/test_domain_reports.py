"""Tests for reports domain logic: EÜR mapping, GuV, SuSa, Journal."""

from datetime import date

import pytest

from easycash_web.domain.reports import (
    EuerReport,
    GuVReport,
    JournalReport,
    SuSaReport,
    calculate_account_balance,
    calculate_euer_report,
    calculate_guv_report,
    calculate_journal_report,
    calculate_susa_report,
)
from easycash_web.models import Account, BookFile, Booking, Business, Client, TaxRate


@pytest.fixture
def sample_book() -> BookFile:
    """Create a sample book file with accounts and bookings for testing."""
    book = BookFile(
        format="easycash-web",
        format_version=1,
        meta={"client_name": "TestClient"},
    )
    # Add client with business
    client = Client(name="TestClient")
    business = Business(name="TestBusiness", tax_id="12345")
    client.businesses.append(business)
    book.clients.append(client)

    # Add tax rates
    book.tax_rates.extend(
        [
            TaxRate(name="Regel 19%", valid_from=date(2007, 1, 1), promille=19000),
            TaxRate(name="Ermäßigt 7%", valid_from=date(2007, 1, 1), promille=7000),
            TaxRate(name="Kleinunternehmer 0%", valid_from=date(2024, 1, 1), promille=0),
        ]
    )

    # Add accounts
    # Income accounts (Einnahmen)
    book.accounts.extend(
        [
            Account(id="acc-einnahmen-19", name="Einnahmen 19% USt", type="income"),
            Account(id="acc-einnahmen-7", name="Einnahmen 7% USt", type="income"),
            Account(id="acc-einnahmen-0", name="Einnahmen 0% USt (Klein)", type="income"),
            # Expense accounts (Ausgaben)
            Account(id="acc-buero", name="Bürobedarf", type="expense"),
            Account(id="acc-miete", name="Miete", type="expense"),
            Account(id="acc-fahrtkosten", name="Fahrtkosten", type="expense"),
            Account(id="acc-afa", name="AfA (Abschreibung)", type="expense"),
            # Asset accounts
            Account(id="acc-kasse", name="Kasse", type="expense"),
            Account(id="acc-bank", name="Bank", type="expense"),
        ]
    )

    # Add bookings for 2026
    book.bookings.extend(
        [
            # Income: 11,900.00 gross at 19% VAT
            Booking(
                id="b1",
                date="2026-01-15",
                description="Rechnung 1",
                account_id="acc-einnahmen-19",
                account_name="Einnahmen 19% USt",
                type="income",
                gross_cents=1190000,
                vat_rate_promille=19000,
                year=2026,
            ),
            # Income: 5,350.00 gross at 7% VAT
            Booking(
                id="b2",
                date="2026-02-20",
                description="Rechnung 2",
                account_id="acc-einnahmen-7",
                account_name="Einnahmen 7% USt",
                type="income",
                gross_cents=535000,
                vat_rate_promille=7000,
                year=2026,
            ),
            # Income: 3,000.00 gross at 0% VAT (Kleinunternehmer)
            Booking(
                id="b3",
                date="2026-03-10",
                description="Rechnung 3",
                account_id="acc-einnahmen-0",
                account_name="Einnahmen 0% USt",
                type="income",
                gross_cents=300000,
                vat_rate_promille=0,
                year=2026,
            ),
            # Expense: 2,380.00 gross at 19% VAT (Bürobedarf)
            Booking(
                id="b4",
                date="2026-01-20",
                description="Büromaterial",
                account_id="acc-buero",
                account_name="Bürobedarf",
                type="expense",
                gross_cents=238000,
                vat_rate_promille=19000,
                year=2026,
            ),
            # Expense: 14,280.00 gross at 19% VAT (Miete)
            Booking(
                id="b5",
                date="2026-02-01",
                description="Büromiete Jan",
                account_id="acc-miete",
                account_name="Miete",
                type="expense",
                gross_cents=1428000,
                vat_rate_promille=19000,
                year=2026,
            ),
            # Expense: 595.00 gross at 19% VAT (Fahrtkosten)
            Booking(
                id="b6",
                date="2026-03-15",
                description="Taxi",
                account_id="acc-fahrtkosten",
                account_name="Fahrtkosten",
                type="expense",
                gross_cents=59500,
                vat_rate_promille=19000,
                year=2026,
            ),
            # AfA: 1,000.00 gross (no VAT)
            Booking(
                id="b7",
                date="2026-06-30",
                description="AfA 1. Halbjahr",
                account_id="acc-afa",
                account_name="AfA (Abschreibung)",
                type="expense",
                gross_cents=100000,
                vat_rate_promille=0,
                year=2026,
            ),
        ]
    )

    return book


class TestCalculateAccountBalance:
    """Tests for the calculate_account_balance helper."""

    def test_income_account_balance(self, sample_book: BookFile) -> None:
        """Income accounts should show positive balance (credit)."""
        balance = calculate_account_balance(sample_book, "acc-einnahmen-19", 2026)
        # 11,900.00 gross = 10,000.00 net + 1,900.00 VAT
        assert balance == 1190000  # positive for income

    def test_expense_account_balance(self, sample_book: BookFile) -> None:
        """Expense accounts should show positive balance (debit)."""
        balance = calculate_account_balance(sample_book, "acc-buero", 2026)
        # 2,380.00 gross
        assert balance == 238000  # positive for expense

    def test_unknown_account(self, sample_book: BookFile) -> None:
        balance = calculate_account_balance(sample_book, "unknown", 2026)
        assert balance == 0

    def test_year_filter(self, sample_book: BookFile) -> None:
        """Balance should only include bookings from the given year."""
        balance = calculate_account_balance(sample_book, "acc-einnahmen-19", 2025)
        assert balance == 0


class TestCalculateEuerReport:
    """Tests for EÜR (Einnahmen-Überschuss-Rechnung) report."""

    def test_euer_basic_structure(self, sample_book: BookFile) -> None:
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=False)
        assert isinstance(report, EuerReport)
        assert report.year == 2026
        assert report.kleinunternehmer is False

    def test_euer_income_lines_19_percent(self, sample_book: BookFile) -> None:
        """Normal taxpayer: 19% income goes to lines 15-17 (split by VAT rate)."""
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=False)

        # Line 15: Einnahmen 19% USt (netto)
        line_15 = next((line for line in report.lines if line.line_number == "15"), None)
        assert line_15 is not None
        # 11,900.00 gross at 19% = 10,000.00 net
        assert line_15.amount_cents == 1000000

        # Line 16: Einnahmen 7% USt (netto)
        line_16 = next((line for line in report.lines if line.line_number == "16"), None)
        assert line_16 is not None
        # 5,350.00 gross at 7% = 5,000.00 net
        assert line_16.amount_cents == 500000

    def test_euer_income_lines_kleinunternehmer(self, sample_book: BookFile) -> None:
        """Kleinunternehmer: all income goes to line 12 (brutto)."""
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=True)

        # Line 12: Betriebseinnahmen (brutto) - all income
        line_12 = next((line for line in report.lines if line.line_number == "12"), None)
        assert line_12 is not None
        # 11,900 + 5,350 + 3,000 = 20,250.00 brutto
        assert line_12.amount_cents == 2025000

        # Lines 15, 16 should exist but be 0 for Kleinunternehmer
        line_15 = next((line for line in report.lines if line.line_number == "15"), None)
        assert line_15 is not None
        assert line_15.amount_cents == 0
        line_16 = next((line for line in report.lines if line.line_number == "16"), None)
        assert line_16 is not None
        assert line_16.amount_cents == 0

    def test_euer_expense_lines(self, sample_book: BookFile) -> None:
        """Expense lines for normal taxpayer (Ausgaben netto)."""
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=False)

        # Line 24: Bürobedarf (netto) - 2,380 / 1.19 = 2,000.00
        line_24 = next((line for line in report.lines if line.line_number == "24"), None)
        assert line_24 is not None
        assert line_24.amount_cents == 200000

        # Line 30: Miete (netto) - 14,280 / 1.19 = 12,000.00
        line_30 = next((line for line in report.lines if line.line_number == "30"), None)
        assert line_30 is not None
        assert line_30.amount_cents == 1200000

        # Line 34: Fahrtkosten (netto) - 595 / 1.19 = 500.00
        line_34 = next((line for line in report.lines if line.line_number == "34"), None)
        assert line_34 is not None
        assert line_34.amount_cents == 50000

    def test_euer_afa_line(self, sample_book: BookFile) -> None:
        """AfA goes to line 50 (Abschreibungen)."""
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=False)

        line_50 = next((line for line in report.lines if line.line_number == "50"), None)
        assert line_50 is not None
        # AfA is 1,000.00 (no VAT)
        assert line_50.amount_cents == 100000

    def test_euer_total_income_and_expenses(self, sample_book: BookFile) -> None:
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=False)

        # Total income (netto): 10,000 (19%) + 5,000 (7%) + 3,000 (0%) = 18,000
        assert report.total_income_cents == 1800000

        # Total expenses (netto): 2,000 + 12,000 + 500 + 1,000 = 15,500
        assert report.total_expenses_cents == 1550000

        # Profit/loss: 18,000 - 15,500 = 2,500
        assert report.profit_loss_cents == 250000


class TestCalculateGuVReport:
    """Tests for GuV (Gewinn- und Verlustrechnung) report."""

    def test_guv_basic_structure(self, sample_book: BookFile) -> None:
        report = calculate_guv_report(sample_book, 2026)
        assert isinstance(report, GuVReport)
        assert report.year == 2026

    def test_guv_groups_by_account_type(self, sample_book: BookFile) -> None:
        report = calculate_guv_report(sample_book, 2026)

        # Should have income section
        income_section = next((s for s in report.sections if s.name == "Einnahmen"), None)
        assert income_section is not None
        assert income_section.total_cents == 1800000  # netto: 10,000 + 5,000 + 3,000

        # Should have expense section
        expense_section = next((s for s in report.sections if s.name == "Ausgaben"), None)
        assert expense_section is not None
        assert expense_section.total_cents == 1550000  # netto

    def test_guv_profit_loss(self, sample_book: BookFile) -> None:
        report = calculate_guv_report(sample_book, 2026)
        assert report.profit_loss_cents == 250000


class TestCalculateSuSaReport:
    """Tests for SuSa (Summen- und Saldenliste) report."""

    def test_susa_basic_structure(self, sample_book: BookFile) -> None:
        report = calculate_susa_report(sample_book, 2026)
        assert isinstance(report, SuSaReport)
        assert report.year == 2026

    def test_susa_all_accounts(self, sample_book: BookFile) -> None:
        report = calculate_susa_report(sample_book, 2026)

        # Should have all accounts with non-zero balances
        accounts_by_id = {a.account_id: a for a in report.accounts}
        assert "acc-einnahmen-19" in accounts_by_id
        assert "acc-buero" in accounts_by_id
        # Asset accounts should be present (zero balance if no bookings)
        assert "acc-kasse" in accounts_by_id
        assert "acc-bank" in accounts_by_id

    def test_susa_balance_types(self, sample_book: BookFile) -> None:
        report = calculate_susa_report(sample_book, 2026)

        accounts_by_id = {a.account_id: a for a in report.accounts}

        # Income accounts: positive balance
        assert accounts_by_id["acc-einnahmen-19"].balance_cents == 1190000

        # Expense accounts: positive balance
        assert accounts_by_id["acc-buero"].balance_cents == 238000

        # Asset accounts: 0 (no bookings to them in this test)
        assert accounts_by_id["acc-kasse"].balance_cents == 0


class TestCalculateJournalReport:
    """Tests for Journal (Buchungsjournal) report."""

    def test_journal_basic_structure(self, sample_book: BookFile) -> None:
        report = calculate_journal_report(sample_book, 2026)
        assert isinstance(report, JournalReport)
        assert report.year == 2026

    def test_journal_sorted_by_date(self, sample_book: BookFile) -> None:
        report = calculate_journal_report(sample_book, 2026)

        dates = [entry.date for entry in report.entries]
        assert dates == sorted(dates)

    def test_journal_entries_have_details(self, sample_book: BookFile) -> None:
        report = calculate_journal_report(sample_book, 2026)

        entry = report.entries[0]
        assert entry.booking_id == "b1"
        assert entry.date == date(2026, 1, 15)
        assert entry.description == "Rechnung 1"
        assert entry.account_name == "Einnahmen 19% USt"
        assert entry.gross_cents == 1190000
        assert entry.net_cents == 1000000
        assert entry.vat_cents == 190000
        assert entry.tax_rate_promille == 19000


class TestEuerLineMapping:
    """Tests for specific EÜR line number mappings per §4(3) EStG."""

    def test_line_numbers_exist(self, sample_book: BookFile) -> None:
        report = calculate_euer_report(sample_book, 2026, kleinunternehmer=False)

        line_numbers = {line.line_number for line in report.lines}
        # All EÜR lines should exist: 12 (brutto), 15-17 (netto), 24, 30, 34, 50
        expected_lines = {"12", "15", "16", "17", "24", "30", "34", "50"}
        missing = expected_lines - line_numbers
        assert not missing, f"Missing lines: {missing}"
        assert "15" in line_numbers  # Einnahmen 19% USt
        assert "16" in line_numbers  # Einnahmen 7% USt
        assert "17" in line_numbers  # Einnahmen sonstige (0% USt)
        # Expense lines
        assert "24" in line_numbers  # Bürobedarf
        assert "30" in line_numbers  # Miete
        assert "34" in line_numbers  # Fahrtkosten
        assert "50" in line_numbers  # Abschreibungen (AfA)


class TestEdgeCases:
    """Edge cases for reports."""

    def test_empty_book(self) -> None:
        book = BookFile(format="easycash-web", format_version=1, meta={"client_name": "Empty"})
        client = Client(name="Empty")
        book.clients.append(client)

        report = calculate_euer_report(book, 2026, kleinunternehmer=False)
        assert report.total_income_cents == 0
        assert report.total_expenses_cents == 0
        assert report.profit_loss_cents == 0

    def test_no_bookings_for_year(self, sample_book: BookFile) -> None:
        report = calculate_euer_report(sample_book, 2020, kleinunternehmer=False)
        assert report.total_income_cents == 0
        assert report.total_expenses_cents == 0
