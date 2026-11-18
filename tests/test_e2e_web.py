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
    for _ in range(100):
        try:
            urllib.request.urlopen("http://127.0.0.1:8123/api/v1/health", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
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


@pytest.mark.e2e
def test_home_page_loads(page, server_url):
    """The root / serves the SPA with correct title and navigation."""
    page.goto(server_url)
    expect(page).to_have_title("EasyCash&Tax Web")
    # Navigation elements should be present (links)
    expect(page.locator("a#nav-client")).to_be_visible()
    expect(page.locator("a#nav-booking")).to_be_visible()
    expect(page.locator("a#nav-calculator")).to_be_visible()


@pytest.mark.e2e
def test_view_switching_without_client_shows_alert(page, server_url):
    """Clicking Buchungen without a client shows alert and stays on clients view."""
    page.goto(server_url)
    # Default view should be clients (since currentClient starts null)
    expect(page.locator("#view-clients")).not_to_be_hidden()
    expect(page.locator("#view-bookings")).to_be_hidden()

    # Click Buchungen nav → should show alert and stay on clients view
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("a#nav-booking")
    expect(page.locator("#view-clients")).not_to_be_hidden()
    expect(page.locator("#view-bookings")).to_be_hidden()


@pytest.mark.e2e
def test_view_switching_with_client(page, server_url, create_test_client):
    """Clicking nav items switches between views when client is selected."""
    page.goto(server_url)
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
    page.goto(server_url)
    # Navigate to clients view where the button is
    page.click("a#nav-client")
    expect(page.locator("button#new-client")).to_be_visible()
    expect(page).to_have_title("EasyCash&Tax Web")


@pytest.mark.e2e
def test_new_client_flow_creates_client(page, server_url):
    """Clicking + Neuer Mandant and entering a name creates a client."""
    page.goto(server_url)
    page.click("a#nav-client")

    # Capture the browser prompt and accept with a name
    dialogs = []

    def handle_dialog(dialog):
        dialogs.append(dialog.message)
        dialog.accept("PlaywrightClient")

    page.on("dialog", handle_dialog)
    page.click("button#new-client")

    # A prompt dialog must have appeared
    assert len(dialogs) == 1, f"Expected 1 prompt dialog, got {len(dialogs)}: {dialogs}"

    # After creating, the client should appear in the list
    expect(page.locator("#client-list")).to_contain_text("PlaywrightClient", timeout=5000)
    # And in the dropdown (select element, not strict-mode options)
    expect(page.locator("#client-select")).to_contain_text("PlaywrightClient")


@pytest.mark.e2e
def test_api_health(page, server_url):
    """The health endpoint returns OK."""
    page.goto(server_url + "/api/v1/health")
    body = page.evaluate("() => document.body.textContent")
    assert "ok" in body
