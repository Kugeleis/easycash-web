/**
 * EasyCash&Tax Web – Frontend ES module.
 * Handles client selection, booking grid (Tabulator), calculator, and view navigation.
 */

const API_BASE = "/api/v1";

let currentClient = null;
let clientListDOM = null;
let grid = null;
let currentView = "bookings";

// ── i18n ──────────────────────────────────────────────────────────────────

async function loadI18n() {
    try {
        const resp = await fetch("/static/i18n/de.json");
        return await resp.json();
    } catch {
        return {};
    }
}

let i18n = {};

// ── API helpers ───────────────────────────────────────────────────────────

async function apiGet(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
    return resp.json();
}

async function apiPost(path, body) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`POST ${path} failed: ${resp.status}`);
    return resp.json();
}

async function apiPut(path, body) {
    const resp = await fetch(`${API_BASE}${path}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`PUT ${path} failed: ${resp.status}`);
    return resp.json();
}

// ── View switching ────────────────────────────────────────────────────────

function showView(viewName) {
    // Hide all views
    document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
    // Remove active class from all nav items
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    // Show the selected view
    const view = document.getElementById(`view-${viewName}`);
    if (view) view.classList.remove("hidden");
    // Mark the matching nav item active
    const navId = viewName === "bookings" ? "nav-booking" : `nav-${viewName}`;
    const nav = document.getElementById(navId);
    if (nav) nav.classList.add("active");
    currentView = viewName;
}

// ── Client management ─────────────────────────────────────────────────────

async function loadClients() {
    const data = await apiGet("/clients");
    const clientList = document.getElementById("client-list");
    clientList.innerHTML = "";

    if (data.clients.length === 0) {
        clientList.innerHTML = `<p class="empty-state">Kein Mandant vorhanden.</p>`;
        return;
    }

    const ul = document.createElement("ul");
    for (const c of data.clients) {
        const li = document.createElement("li");
        li.textContent = `${c.name} (rev ${c.revision})`;
        li.dataset.clientId = c.id;
        li.addEventListener("click", () => selectClient(c.id, c.name));
        ul.appendChild(li);
    }
    clientList.appendChild(ul);
}

async function selectClient(clientId, clientName) {
    currentClient = clientId;
    await loadBook();
    showView("bookings");
}

async function createNewClient(event) {
    event.preventDefault();
    const form = document.getElementById("new-client-form");
    const input = document.getElementById("new-client-name");
    const submitButton = form.querySelector('button[type="submit"]');
    const errorMessage = document.getElementById("new-client-error");
    const name = input.value.trim();
    if (!name) {
        input.setCustomValidity("Bitte geben Sie einen Namen ein.");
        input.reportValidity();
        return;
    }

    input.setCustomValidity("");
    submitButton.disabled = true;
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");
    try {
        await apiPost(`/book/${encodeURIComponent(name)}`, {
            format: "easycash-web",
            format_version: 1,
            meta: { client_name: name },
        });
        await loadClientSelect();
        await loadClients();
        form.reset();
        form.classList.add("hidden");
        await selectClient(name, name);
    } catch (e) {
        errorMessage.textContent = `Fehler: ${e.message}`;
        errorMessage.classList.remove("hidden");
    } finally {
        submitButton.disabled = false;
    }
}

// ── Client select dropdown ────────────────────────────────────────────────

async function loadClientSelect() {
    const data = await apiGet("/clients");
    const select = document.getElementById("client-select");
    const selectLabel = i18n.app?.select_client || "Mandant auswählen...";
    select.innerHTML = `<option value="">${selectLabel}</option>`;

    for (const c of data.clients) {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = `${c.name} (rev ${c.revision})`;
        select.appendChild(opt);
    }
    select.addEventListener("change", async (e) => {
        currentClient = e.target.value || null;
        if (currentClient) {
            showView("bookings");
            await loadBook();
        } else {
            showView("clients");
            await loadClients();
        }
    });
}

// ── Book / booking management ─────────────────────────────────────────────

async function loadBook() {
    if (!currentClient) return;
    try {
        const book = await apiGet(`/book/${encodeURIComponent(currentClient)}`);
        initGrid(book.bookings || []);
    } catch (e) {
        console.error("Failed to load book:", e);
        clearGrid();
    }
}

function clearGrid() {
    if (grid) {
        grid.clearData();
    }
}

// ── Grid (Tabulator) ──────────────────────────────────────────────────────

function initGrid(bookings) {
    const tableEl = document.getElementById("booking-grid");
    if (grid) {
        grid.destroy();
    }
    grid = new Tabulator(tableEl, {
        data: bookings,
        layout: "fitColumns",
        reactiveData: true,
        columns: [
            { title: "Nr.", field: "booking_number", width: 80, editor: "input" },
            { title: "Datum", field: "date", width: 120, editor: "input" },
            { title: "Beschreibung", field: "description", minWidth: 200, editor: "input" },
            { title: "Konto", field: "account_name", minWidth: 150, editor: "input" },
            {
                title: "Betrag (€)",
                field: "gross_cents",
                width: 120,
                formatter: (cell) => (cell.getValue() / 100).toFixed(2),
                editor: "input",
                editorParams: { selectContents: true },
            },
            {
                title: "MwSt %",
                field: "vat_rate_percent",
                width: 80,
                editor: "input",
            },
            { title: "Belegnr.", field: "receipt_number", width: 100, editor: "input" },
        ],
        cellEdited: async (cell) => {
            const row = cell.getRow().getData();
            if (cell.getField() === "gross_cents") {
                const val = parseFloat(String(cell.getValue()).replace(",", "."));
                if (!isNaN(val)) {
                    row.gross_cents = Math.round(val * 100);
                }
            }
            try {
                await apiPut(`/bookings/${encodeURIComponent(currentClient)}/${row.id}`, row);
            } catch (e) {
                console.error("Failed to save booking:", e);
            }
        },
    });
}

// ── New booking form ─────────────────────────────────────────────────────

function showNewBookingForm() {
    if (!currentClient) {
        alert(i18n.client?.select_first || "Bitte wählen Sie zuerst einen Mandanten aus.");
        return;
    }
    const form = document.getElementById("new-booking-form");
    form.classList.remove("hidden");
    document.getElementById("booking-date").value = new Date().toISOString().slice(0, 10);
    document.getElementById("booking-date").focus();
}

async function createNewBooking(event) {
    event.preventDefault();
    const form = document.getElementById("new-booking-form");
    const errorMessage = document.getElementById("new-booking-error");
    const submitButton = form.querySelector('button[type="submit"]');
    const amountText = document.getElementById("booking-amount").value.trim();
    const vatText = document.getElementById("booking-vat").value.trim();
    const amount = Number(amountText.replace(",", "."));
    const vat = Number(vatText.replace(",", "."));

    if (!Number.isFinite(amount) || !Number.isFinite(vat)) {
        errorMessage.textContent = "Ungültiger Betrag oder MwSt-Satz.";
        errorMessage.classList.remove("hidden");
        return;
    }

    const date = document.getElementById("booking-date").value;
    const [year, month] = date.split("-").map(Number);
    const payload = {
        date,
        description: document.getElementById("booking-description").value,
        account_name: document.getElementById("booking-account").value,
        gross_cents: Math.round(amount * 100),
        vat_rate_percent: vat,
        vat_rate_promille: Math.round(vat * 1000),
        receipt_number: document.getElementById("booking-receipt").value,
        year,
        month,
    };

    submitButton.disabled = true;
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");
    try {
        await apiPost(`/bookings/${encodeURIComponent(currentClient)}`, payload);
        form.reset();
        form.classList.add("hidden");
        await loadBook();
    } catch (e) {
        errorMessage.textContent = `Fehler: ${e.message}`;
        errorMessage.classList.remove("hidden");
    } finally {
        submitButton.disabled = false;
    }
}

// ── Calculator ────────────────────────────────────────────────────────────

function evaluateExpression(expr) {
    const sanitized = expr.replace(/,/g, ".");
    if (!/^[\d+\-*/().\s]+$/.test(sanitized)) {
        throw new Error("Invalid characters in expression");
    }
    const result = Function(`"use strict"; return (${sanitized});`)();
    if (typeof result !== "number" || !isFinite(result)) {
        throw new Error("Invalid result");
    }
    return Math.round(result * 100) / 100;
}

function setupCalculator() {
    const input = document.getElementById("calc-input");
    const evalBtn = document.getElementById("calc-eval");
    const clearBtn = document.getElementById("calc-clear");

    evalBtn.addEventListener("click", () => {
        try {
            const result = evaluateExpression(input.value);
            input.value = result.toFixed(2);
            document.getElementById("calc-result").textContent = `Ergebnis: €${result.toFixed(2)}`;
        } catch (e) {
            alert(`Fehler: ${e.message}`);
            document.getElementById("calc-result").textContent = "";
        }
    });

    clearBtn.addEventListener("click", () => {
        input.value = "";
        document.getElementById("calc-result").textContent = "";
    });
}

// ── Init ──────────────────────────────────────────────────────────────────

async function init() {
    i18n = await loadI18n();

    // Load client select and populate list
    await loadClientSelect();
    await loadClients();

    setupCalculator();

    // ── Navigation ────────────────────────────────────────────────────
    document.getElementById("nav-client").addEventListener("click", (e) => {
        e.preventDefault();
        showView("clients");
    });

    document.getElementById("nav-booking").addEventListener("click", async (e) => {
        e.preventDefault();
        if (!currentClient) {
            alert(i18n.client?.select_first || "Bitte wählen Sie zuerst einen Mandanten aus.");
            showView("clients");
            return;
        }
        showView("bookings");
        await loadBook();
    });

    document.getElementById("nav-calculator").addEventListener("click", (e) => {
        e.preventDefault();
        showView("calculator");
    });

    // ── New booking button ──────────────────────────────────────────────
    document.getElementById("new-booking").addEventListener("click", showNewBookingForm);

    const newBookingForm = document.getElementById("new-booking-form");
    newBookingForm.addEventListener("submit", createNewBooking);
    document.getElementById("cancel-new-booking").addEventListener("click", () => {
        newBookingForm.reset();
        newBookingForm.classList.add("hidden");
        const errorMessage = document.getElementById("new-booking-error");
        errorMessage.textContent = "";
        errorMessage.classList.add("hidden");
    });

    const newClientForm = document.getElementById("new-client-form");
    document.getElementById("new-client").addEventListener("click", () => {
        newClientForm.classList.remove("hidden");
        document.getElementById("new-client-name").focus();
    });
    document.getElementById("cancel-new-client").addEventListener("click", () => {
        newClientForm.reset();
        newClientForm.classList.add("hidden");
        const errorMessage = document.getElementById("new-client-error");
        errorMessage.textContent = "";
        errorMessage.classList.add("hidden");
    });
    document.getElementById("new-client-name").addEventListener("input", (event) => {
        event.target.setCustomValidity("");
    });
    newClientForm.addEventListener("submit", createNewClient);

    // Initial view: bookings if we have a client, otherwise clients
    if (currentClient) {
        showView("bookings");
        await loadBook();
    } else {
        showView("clients");
    }
}

document.addEventListener("DOMContentLoaded", init);
