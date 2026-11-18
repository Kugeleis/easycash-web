/**
 * EasyCash&Tax Web – Frontend ES module.
 * Handles client selection, booking grid (Tabulator), and calculator.
 */

const API_BASE = "/api/v1";

let currentClient = null;
let grid = null;

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

async function apiDelete(path) {
    const resp = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`DELETE ${path} failed: ${resp.status}`);
    return resp.json();
}

// ── Client management ─────────────────────────────────────────────────────

async function loadClients() {
    const data = await apiGet("/clients");
    const select = document.getElementById("client-select");
    select.innerHTML = "<option value=\"\">Select client...</option>";
    for (const c of data.clients) {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = `${c.name} (rev ${c.revision})`;
        select.appendChild(opt);
    }
    select.addEventListener("change", async (e) => {
        currentClient = e.target.value || null;
        if (currentClient) {
            await loadBook();
        } else {
            clearGrid();
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
            // Convert gross_cents from input string back to int if edited
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

// ── New booking dialog ────────────────────────────────────────────────────

function showNewBookingDialog() {
    if (!currentClient) {
        alert(i18n.select_client_first || "Bitte wählen Sie zuerst einen Mandanten aus.");
        return;
    }
    const date = prompt("Datum (YYYY-MM-DD):", new Date().toISOString().slice(0, 10));
    if (!date) return;
    const description = prompt("Beschreibung:", "");
    const accountName = prompt("Konto:", "");
    const grossStr = prompt("Betrag (€):", "0.00");
    const vatStr = prompt("MwSt-Satz (%):", "19");
    const receipt = prompt("Belegnummer:", "");

    const gross = parseFloat(grossStr?.replace(",", "."));
    const vat = parseFloat(vatStr?.replace(",", "."));
    if (isNaN(gross) || isNaN(vat)) {
        alert("Ungültiger Betrag oder MwSt-Satz.");
        return;
    }

    const payload = {
        date,
        description: description || "",
        account_name: accountName || "",
        gross_cents: Math.round(gross * 100),
        vat_rate_percent: vat,
        vat_rate_promille: Math.round(vat * 1000),
        receipt_number: receipt || "",
        year: parseInt(date.slice(0, 4), 10),
        month: parseInt(date.slice(5, 7), 10),
    };

    apiPost(`/bookings/${encodeURIComponent(currentClient)}`, payload)
        .then(() => loadBook())
        .catch((e) => console.error("Failed to create booking:", e));
}

// ── Calculator ────────────────────────────────────────────────────────────

function evaluateExpression(expr) {
    // Safe evaluation: allow only digits, operators, parentheses, decimal separators
    const sanitized = expr.replace(/,/g, ".");
    if (!/^[\d+\-*/().\s]+$/.test(sanitized)) {
        throw new Error("Invalid characters in expression");
    }
    // eslint-disable-next-line no-new-func
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
        } catch (e) {
            alert(`Fehler: ${e.message}`);
        }
    });

    clearBtn.addEventListener("click", () => {
        input.value = "";
    });
}

// ── Navigation ────────────────────────────────────────────────────────────

function setupNavigation() {
    document.getElementById("nav-client").addEventListener("click", (e) => {
        e.preventDefault();
        // Client management would be a separate view; for now, focus the select.
        document.getElementById("client-select").focus();
    });
}

// ── Init ──────────────────────────────────────────────────────────────────

async function init() {
    i18n = await loadI18n();
    await loadClients();
    setupCalculator();
    setupNavigation();
    document.getElementById("new-booking").addEventListener("click", showNewBookingDialog);
}

document.addEventListener("DOMContentLoaded", init);
