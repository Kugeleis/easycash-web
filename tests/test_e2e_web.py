"""Real E2E tests with Playwright against the live EasyCash&Tax Web app."""

import threading
import time
import urllib.request

import pytest
import uvicorn
from playwright.sync_api import expect


@pytest.fixture(scope="module")
def server_url(tmp_path_factory):
    """Start uvicorn in background thread with an isolated DATA_DIR."""
    from easycash_web import api

    data_dir = tmp_path_factory.mktemp("e2e-data")
    api.STORAGE_DIR = data_dir

    config = uvicorn.Config(
        api.app,
        host="127.0.0.1",
        port=8123,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until the server accepts requests
    ready = False
    for _ in range(100):
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8123/api/v1/health", timeout=0.5
            ) as response:
                ready = response.status == 200
            break
        except Exception:
            time.sleep(0.1)
    if not ready:
        server.should_exit = True
        thread.join(timeout=10)
        pytest.fail("E2E server did not become ready")
    yield "http://127.0.0.1:8123"

    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def create_test_client(server_url):
    """Create a test client via API and return its name."""
    import httpx

    with httpx.Client(base_url=server_url) as client:
        # Create a client
        resp = client.post(
            "/api/v1/book/TestClient",
            json={
                "format": "easycash-web",
                "format_version": 1,
                "meta": {"client_name": "TestClient"},
            },
        )
        assert resp.status_code == 200
        yield "TestClient"
        # cleanup not needed for temp directory


@pytest.fixture(autouse=True)
def block_external_assets(page):
    """Keep browser tests independent of optional third-party CDN availability."""
    page.route("https://**/*", lambda route: route.abort())


@pytest.mark.e2e
def test_home_page_loads(page, server_url):
    """The root / serves the SPA with correct title and navigation."""
    page.goto(server_url, wait_until="domcontentloaded")
    expect(page).to_have_title("EasyCash&Tax Web")
    # Navigation elements should be present (links)
    expect(page.locator("a#nav-client")).to_be_visible()
    expect(page.locator("a#nav-booking")).to_be_visible()
    expect(page.locator("a#nav-calculator")).to_be_visible()


@pytest.mark.e2e
def test_view_switching_without_client_shows_alert(page, server_url):
    """Clicking Buchungen without a client shows alert and stays on clients view."""
    page.goto(server_url, wait_until="domcontentloaded")
    # Default view should be clients (since currentClient starts null)
    expect(page.locator("#view-clients")).not_to_be_hidden()
    expect(page.locator("#view-bookings")).to_be_hidden()
    expect(page.locator("#client-list")).to_contain_text("Kein Mandant vorhanden.")

    # Click Buchungen nav → should show alert and stay on clients view
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("a#nav-booking")
    expect(page.locator("#view-clients")).not_to_be_hidden()
    expect(page.locator("#view-bookings")).to_be_hidden()


@pytest.mark.e2e
def test_view_switching_with_client(page, server_url, create_test_client):
    """Clicking nav items switches between views when client is selected."""
    page.goto(server_url, wait_until="domcontentloaded")
    # Select the client from dropdown
    page.select_option("#client-select", "TestClient")
    # Wait for view to switch to bookings
    expect(page.locator("#view-bookings")).not_to_be_hidden()
    expect(page.locator("#view-clients")).to_be_hidden()

    # Click Rechner → should show calculator view
    page.click("a#nav-calculator")
    expect(page.locator("#view-calculator")).not_to_be_hidden()
    expect(page.locator("#view-bookings")).to_be_hidden()

    # Click Buchungen → back to bookings
    page.click("a#nav-booking")
    expect(page.locator("#view-bookings")).not_to_be_hidden()
    expect(page.locator("#view-calculator")).to_be_hidden()


@pytest.mark.e2e
def test_new_client_button_is_visible(page, server_url):
    """The + Neuer Mandant button exists on the clients view."""
    page.goto(server_url, wait_until="domcontentloaded")
    # Navigate to clients view where the button is
    page.click("a#nav-client")
    expect(page.locator("button#new-client")).to_be_visible()
    expect(page).to_have_title("EasyCash&Tax Web")


@pytest.mark.e2e
def test_new_client_flow_creates_client(page, server_url):
    """Clicking + Neuer Mandant and entering a name creates a client."""
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(server_url, wait_until="domcontentloaded")
    page.click("a#nav-client")
    page.click("button#new-client")
    expect(page.locator("#new-client-form")).to_be_visible()
    page.get_by_label("Neuer Mandanten-Name").fill("PlaywrightClient")
    page.get_by_role("button", name="Erstellen").click()

    # After creating, the client should appear in the list
    expect(page.locator("#client-list")).to_contain_text("PlaywrightClient", timeout=5000)
    # And in the dropdown (select element, not strict-mode options)
    expect(page.locator("#client-select")).to_contain_text("PlaywrightClient")
    assert not page_errors, f"Browser errors: {page_errors}"


@pytest.mark.e2e
def test_new_booking_flow_saves_booking(page, server_url, create_test_client):
    """The new-booking action saves entered data through the browser UI."""
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.goto(server_url, wait_until="domcontentloaded")
    page.select_option("#client-select", "TestClient")
    page.click("#new-booking")

    expect(page.locator("#new-booking-form")).to_be_visible()
    page.get_by_label("Datum").fill("2026-03-10")
    page.get_by_label("Beschreibung").fill("E2E booking")
    page.get_by_label("Konto").fill("Umsatzerlöse")
    page.get_by_label("Betrag (€)").fill("119,00")
    page.get_by_label("MwSt-Satz (%)").fill("19")
    page.get_by_label("Belegnummer").fill("E2E-1")
    page.get_by_role("button", name="Buchung speichern").click()

    expect(page.locator("#new-booking-form")).to_be_hidden()
    bookings = page.evaluate(
        """async () => {
            const response = await fetch("/api/v1/bookings/TestClient");
            if (!response.ok) throw new Error(`GET bookings failed: ${response.status}`);
            return (await response.json()).bookings;
        }"""
    )
    booking = next(booking for booking in bookings if booking["description"] == "E2E booking")
    assert booking["date"] == "2026-03-10"
    assert booking["account_name"] == "Umsatzerlöse"
    assert booking["gross_cents"] == 11900
    assert booking["vat_rate_promille"] == 19000
    assert booking["receipt_number"] == "E2E-1"
    assert not page_errors, f"Browser errors: {page_errors}"


@pytest.mark.e2e
def test_browser_exercises_every_api_endpoint(page, server_url):
    """The browser can create, edit, report on, upload, download, and delete API data."""
    page.goto(server_url, wait_until="domcontentloaded")
    endpoint_calls = page.evaluate(
        """async () => {
            const calls = [];
            async function request(path, method = "GET", body) {
                const options = { method };
                if (body !== undefined) {
                    options.headers = { "Content-Type": "application/json" };
                    options.body = JSON.stringify(body);
                }
                const response = await fetch(path, options);
                calls.push([method, new URL(path, location.href).pathname]);
                const text = await response.text();
                if (!response.ok) {
                    throw new Error(`${method} ${path}: ${response.status} ${text}`);
                }
                return text ? JSON.parse(text) : null;
            }
            function assert(condition, message) {
                if (!condition) throw new Error(message);
            }

            assert((await request("/api/v1/health")).status === "ok", "health");
            assert((await request("/api/v1/schema")).title, "schema");
            const name = "BrowserEndpointClient";
            const base = {
                format: "easycash-web",
                format_version: 1,
                meta: { client_name: name },
            };
            await request(`/api/v1/book/${name}`, "POST", base);
            assert((await request("/api/v1/clients")).clients.some(c => c.id === name), "clients");
            const book = await request(`/api/v1/book/${name}`);

            const downloadPath = `/api/v1/book/${name}/download`;
            const download = await fetch(downloadPath);
            calls.push(["GET", new URL(downloadPath, location.href).pathname]);
            assert(download.ok && (await download.json()).meta.client_name === name, "download");

            const form = new FormData();
            form.append("file", new File([JSON.stringify(book)], "book.json", {
                type: "application/json",
            }));
            const uploadPath = `/api/v1/book/${name}/upload`;
            const upload = await fetch(uploadPath, { method: "POST", body: form });
            calls.push(["POST", new URL(uploadPath, location.href).pathname]);
            assert(upload.ok && (await upload.json()).saved, "upload");

            const accountPath = `/api/v1/accounts/${name}`;
            const account = { id: "browser-account", name: "Browser Account", type: "income" };
            await request(accountPath);
            await request(accountPath, "POST", account);
            account.name = "Updated Browser Account";
            await request(`${accountPath}/${account.id}`, "PUT", account);
            await request(`${accountPath}/${account.id}`, "DELETE");
            assert((await request(accountPath)).accounts.length === 0, "account delete");

            const bookingPath = `/api/v1/bookings/${name}`;
            const booking = {
                id: "browser-booking", date: "2026-01-15", description: "Browser test",
                account_id: "browser-account", account_name: "Browser Account",
                type: "income", gross_cents: 11900, vat_rate_promille: 19000,
                year: 2026, month: 1,
            };
            await request(bookingPath);
            await request(bookingPath, "POST", booking);
            booking.description = "Updated browser test";
            await request(`${bookingPath}/${booking.id}`, "PUT", booking);

            const taxPath = `/api/v1/tax-rates/${name}`;
            const rate = {
                id: "browser-rate", name: "Browser VAT", promille: 19000,
                valid_from: "2007-01-01",
            };
            await request(taxPath);
            await request(taxPath, "POST", rate);
            rate.name = "Updated Browser VAT";
            await request(`${taxPath}/${rate.id}`, "PUT", rate);
            await request(`${taxPath}/${rate.id}`, "DELETE");
            assert((await request(taxPath)).tax_rates.length === 0, "tax rate delete");

            const recurringPath = `/api/v1/recurring/${name}`;
            await request(recurringPath);
            await request(recurringPath, "POST", {
                id: "browser-recurring", name: "Browser recurring",
                next_due: "2026-02-01", booking,
            });
            await request(`/api/v1/businesses/${name}`);
            await request(`/api/v1/businesses/${name}`, "POST", {
                id: "browser-business", name: "Browser Business",
            });
            await request(`/api/v1/reports/euer/${name}/2026`);
            await request(`/api/v1/reports/guv/${name}/2026`);
            await request(`/api/v1/reports/susa/${name}/2026`);
            await request(`/api/v1/reports/journal/${name}/2026`);
            await request(
                `/api/v1/reports/accounts/${name}/browser-account/balance?year=2026`
            );
            await request(`${bookingPath}/${booking.id}`, "DELETE");
            assert((await request(bookingPath)).bookings.length === 0, "booking delete");
            return calls;
        }"""
    )

    from fastapi.routing import APIRoute
    from starlette.routing import Match

    from easycash_web.api import app

    api_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/")
    ]
    expected_endpoints = set()
    for route in api_routes:
        if route.methods is None:
            continue
        expected_endpoints.update(
            (method, route.path) for method in route.methods & {"GET", "POST", "PUT", "DELETE"}
        )
    exercised_endpoints = set()
    for method, path in endpoint_calls:
        for route in api_routes:
            if route.methods is None:
                continue
            if method not in route.methods:
                continue
            match, _ = route.matches(
                {"type": "http", "method": method, "path": path, "root_path": "", "headers": []}
            )
            if match is Match.FULL:
                exercised_endpoints.add((method, route.path))
                break

    assert exercised_endpoints == expected_endpoints


@pytest.mark.e2e
def test_api_health(page, server_url):
    """The health endpoint returns OK."""
    page.goto(server_url + "/api/v1/health")
    body = page.evaluate("() => document.body.textContent")
    assert "ok" in body
