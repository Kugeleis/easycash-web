"""API integration tests for reports endpoints using FastAPI TestClient."""

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_book(tmp_path: Path):
    """Create and save a test book in a temporary directory."""
    from easycash_web.models import (
        Account,
        BookFile,
        Booking,
        Business,
        Client,
        TaxRate,
    )
    from easycash_web.storage import save_book

    book = BookFile(
        format="easycash-web",
        format_version=1,
        meta={"client_name": "TestClient"},
    )
    client = Client(name="TestClient")
    business = Business(name="TestBusiness", tax_id="12345")
    client.businesses.append(business)
    book.clients.append(client)

    book.tax_rates.extend(
        [
            TaxRate(name="Regel 19%", valid_from=date(2007, 1, 1), promille=19000),
            TaxRate(name="Ermäßigt 7%", valid_from=date(2007, 1, 1), promille=7000),
            TaxRate(name="Kleinunternehmer 0%", valid_from=date(2024, 1, 1), promille=0),
        ]
    )

    book.accounts.extend(
        [
            Account(id="acc-einnahmen-19", name="Einnahmen 19% USt", type="income"),
            Account(id="acc-einnahmen-7", name="Einnahmen 7% USt", type="income"),
            Account(id="acc-einnahmen-0", name="Einnahmen 0% USt (Klein)", type="income"),
            Account(id="acc-buero", name="Bürobedarf", type="expense"),
            Account(id="acc-miete", name="Miete", type="expense"),
            Account(id="acc-fahrtkosten", name="Fahrtkosten", type="expense"),
            Account(id="acc-afa", name="AfA (Abschreibung)", type="expense"),
        ]
    )

    book.bookings.extend(
        [
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

    save_book(tmp_path, "TestClient", book)
    return book


@pytest.fixture
def client(test_book: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """FastAPI test client with STORAGE_DIR pointed at the temp directory."""
    from easycash_web import api

    monkeypatch.setattr(api, "STORAGE_DIR", tmp_path)
    return TestClient(api.app)


class TestAPIReports:
    """Test reports API endpoints."""

    def test_euer_endpoint(self, client):
        """GET /api/v1/reports/euer/{client}/{year}"""
        resp = client.get("/api/v1/reports/euer/TestClient/2026?kleinunternehmer=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert data["kleinunternehmer"] is False
        assert data["total_income_cents"] > 0
        assert data["total_expenses_cents"] > 0
        assert data["profit_loss_cents"] != 0

    def test_euer_kleinunternehmer(self, client):
        """GET /api/v1/reports/euer/{client}/{year}?kleinunternehmer=true"""
        resp = client.get("/api/v1/reports/euer/TestClient/2026?kleinunternehmer=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["kleinunternehmer"] is True
        # Line 12 should have income; lines 15-17 should be 0
        line_numbers = {line["line_number"] for line in data["lines"]}
        assert "12" in line_numbers
        line12 = next(row for row in data["lines"] if row["line_number"] == "12")
        assert line12["amount_cents"] > 0

    def test_euer_not_found(self, client):
        """EÜR for missing client returns 404."""
        resp = client.get("/api/v1/reports/euer/Missing/2026")
        assert resp.status_code == 404

    def test_guv_endpoint(self, client):
        """GET /api/v1/reports/guv/{client}/{year}"""
        resp = client.get("/api/v1/reports/guv/TestClient/2026")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        section_names = {section["name"] for section in data["sections"]}
        assert "Einnahmen" in section_names
        assert "Ausgaben" in section_names
        assert data["profit_loss_cents"] != 0

    def test_susa_endpoint(self, client):
        """GET /api/v1/reports/susa/{client}/{year}"""
        resp = client.get("/api/v1/reports/susa/TestClient/2026")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert len(data["accounts"]) > 0
        # acc-buero should have a positive balance
        buero = next(a for a in data["accounts"] if a["account_id"] == "acc-buero")
        assert buero["balance_cents"] == 238000

    def test_journal_endpoint(self, client):
        """GET /api/v1/reports/journal/{client}/{year}"""
        resp = client.get("/api/v1/reports/journal/TestClient/2026")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert len(data["entries"]) > 0
        # Entries should be sorted by date
        dates = [entry["date"] for entry in data["entries"]]
        assert dates == sorted(dates)

    def test_account_balance_endpoint(self, client):
        """GET /api/v1/reports/accounts/{client}/{account_id}/balance?year=2026"""
        resp = client.get("/api/v1/reports/accounts/TestClient/acc-einnahmen-19/balance?year=2026")
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_id"] == "acc-einnahmen-19"
        assert data["balance_cents"] == 1190000
