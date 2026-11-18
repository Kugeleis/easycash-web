// EasyCash&Tax Web — frontend entry point (plain ES modules, no build step)
// i18n: all strings loaded from /static/i18n/de.json

const API = "/api/v1";

// ── i18n ────────────────────────────────────────────────────────────────────

let i18n = {};

async function loadI18n() {
  const res = await fetch("/static/i18n/de.json");
  i18n = await res.json();
}

function t(key) {
  return i18n[key] || key;
}

// ── State ───────────────────────────────────────────────────────────────────

let currentClient = null;
let currentBook = null;

// ── API helpers ─────────────────────────────────────────────────────────────

async function apiGet(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.json();
}

async function apiPost(path, payload) {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`POST ${path}: ${res.status}`);
  return res.json();
}

// ── Views ───────────────────────────────────────────────────────────────────

async function showClients() {
  const main = document.getElementById("main");
  main.innerHTML = `
    <div class="card">
      <h2>${t("client_list")}</h2>
      <div id="client-list"></div>
      <button class="btn primary" onclick="showNewClient()">${t("new_client")}</button>
    </div>
  `;
  // TODO: fetch /api/v1/clients
}

async function showNewClient() {
  const main = document.getElementById("main");
  main.innerHTML = `
    <div class="card">
      <h2>${t("new_client")}</h2>
      <form onsubmit="saveClient(event)">
        <label>Name<br/><input name="name" required /></label><br/><br/>
        <label>Betriebsart<br/>
          <select name="business_type">
            <option value="freiberufler">Freiberufler</option>
            <option value="kleinunternehmer">Kleinunternehmer</option>
          </select>
        </label><br/><br/>
        <button class="btn primary" type="submit">${t("save")}</button>
        <button class="btn" type="button" onclick="showClients()">${t("cancel")}</button>
      </form>
    </div>
  `;
}

async function saveClient(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const name = fd.get("name");
  await apiPost(`/book/${encodeURIComponent(name)}`, {});
  showClients();
}

async function showBookings() {
  const main = document.getElementById("main");
  main.innerHTML = `
    <div class="card">
      <h2>${t("bookings")}</h2>
      <div class="toolbar">
        <button class="btn primary" onclick="addBooking()">${t("add")}</button>
        <button class="btn" onclick="window.print()">${t("print")}</button>
      </div>
      <div id="booking-grid"></div>
    </div>
  `;
  // TODO: fetch bookings + render Tabulator grid
}

async function showAccounts() {
  const main = document.getElementById("main");
  main.innerHTML = `
    <div class="card">
      <h2>${t("accounts")}</h2>
      <div id="account-list"></div>
    </div>
  `;
  // TODO
}

async function showTaxRates() {
  const main = document.getElementById("main");
  main.innerHTML = `
    <div class="card">
      <h2>${t("tax_rates")}</h2>
      <div id="tax-rate-list"></div>
    </div>
  `;
  // TODO
}

async function showEUR() {
  const main = document.getElementById("main");
  main.innerHTML = `<div class="card"><h2>EÜR</h2><p>Formular wird geladen...</p></div>`;
  // TODO
}

async function showUSTVA() {
  const main = document.getElementById("main");
  main.innerHTML = `<div class="card"><h2>USt-Voranmeldung</h2><p>Formular wird geladen...</p></div>`;
  // TODO
}

async function showUSTJA() {
  const main = document.getElementById("main");
  main.innerHTML = `<div class="card"><h2>Umsatzsteuererklärung</h2><p>Formular wird geladen...</p></div>`;
  // TODO
}

async function showReports() {
  const main = document.getElementById("main");
  main.innerHTML = `<div class="card"><h2>${t("reports")}</h2><p>Auswertungen werden geladen...</p></div>`;
  // TODO
}

async function showSettings() {
  const main = document.getElementById("main");
  main.innerHTML = `<div class="card"><h2>${t("settings")}</h2><p>Einstellungen werden geladen...</p></div>`;
  // TODO
}

// ── Router ──────────────────────────────────────────────────────────────────

const routes = {
  clients: showClients,
  "new-client": showNewClient,
  bookings: showBookings,
  accounts: showAccounts,
  "tax-rates": showTaxRates,
  eur: showEUR,
  ustva: showUSTVA,
  ustja: showUSTJA,
  reports: showReports,
  settings: showSettings,
};

function navigate(hash) {
  const key = hash.replace("#", "");
  const fn = routes[key];
  if (fn) fn();
  document.querySelectorAll("nav a").forEach(a => a.classList.toggle("active", a.getAttribute("href") === hash));
}

window.addEventListener("hashchange", () => navigate(location.hash));

// ── Init ────────────────────────────────────────────────────────────────────

async function init() {
  await loadI18n();
  navigate(location.hash || "#clients");
}

init();
