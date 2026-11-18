# Task: Reimplement EasyCash&Tax as a web app (FastAPI + plain HTML/JS)

## Goal

Build a self-hostable web app that reproduces the functionality and daily workflow of EasyCash&Tax (EC&T): a German cash-basis bookkeeping tool for freelancers and small businesses (Einnahmenüberschussrechnung / EÜR, §4(3) EStG) including VAT pre-registration (Umsatzsteuer-Voranmeldung).

Reference material (read-only):

- Source: <https://github.com/Thomas-Mielke-Software/EasyCash> (C++/MFC, Windows only, mostly GPL-3.0; check LIZENZ.txt)
- Homepage and docs: <https://www.easyct.de>, and the PDF guides in Doc/PDF-Anleitungen in the repo

This is a clean reimplementation, not a code translation. Do NOT mirror the MFC architecture (Doc/View, message maps, dialogs). Read the original to learn behaviour, workflow and business rules, then design it properly.

## Step 0: Research and spec (no app code yet)

Produce docs/SPEC.md and stop for my review. It must contain:

1. Feature inventory derived from the repo and the user guides. The file names are a useful map (verify, don't assume): AnfangssaldoDlg (opening balances), UstVorauszahlungenDlg and VoranmeldungszeitraumDroplist (VAT prepayments and periods), UnternehmensartDlg (business type), MandantName and IconAuswahl* (clients, businesses, asset accounts), RechnDlg, NeuesFormular, Formularabschnitt and Formularfeld (tax forms), Navigation, QuickEdit and QuickList (fast entry), OutputWnd (reports), VCalcParser (calculator in input fields), PluginManager. The folders EUeR, UST and UVA hold the forms (UVA is likely the Austrian variant, so decide with me whether it is in scope).
2. A description of the daily workflow: what the user sees and does to enter, edit and find bookings, switch periods, and produce reports and tax forms.
3. Business rules: VAT rates and their validity dates, EÜR line mapping, Kleinunternehmer mode, and anything about depreciation (AfA). Cite where each rule comes from (original code, guide, or law). Never invent tax rules. Mark anything uncertain as OPEN QUESTION.
4. How the original organises its data files (one file per client? per year?), so we can decide the file granularity for the new format.
5. A proposed v1 scope vs. later, and the list of open questions for me.

## Stack and hard constraints

- Python: 3.15, managed with uv. uv is the only tool for Python versions, environments and dependencies: pyproject.toml with requires-python = ">=3.15", .python-version pinned to 3.15, uv.lock committed, uv sync and uv run for everything. No pip, no manual venvs, no poetry. Before choosing dependencies, check that each one installs cleanly on 3.15 (wheels available). If one doesn't, tell me and propose an alternative instead of downgrading Python.
- Backend: FastAPI, Pydantic v2, pytest, ruff. No database and no ORM. Pydantic models are the single source of truth for the data format.
- Frontend: plain HTML, CSS and ES modules served by FastAPI as static files. NO build step, no npm, no bundler, no framework. Use an import map. Third-party libraries are vendored under static/vendor with pinned versions via a scripts/vendor script, and served locally (no CDN at runtime).
- Component libraries: Web Awesome Core (free, MIT web components) for form controls, dialogs, tabs, dropdowns, buttons, drawers and tree. Tabulator (MIT, dependency-free) for the booking grid, with inline editing, keyboard navigation and frozen headers. Verify current versions and licenses before pinning, and tell me if either is a problem.
- UI language German, with all strings in one place (static/i18n/de.json). Code, API and docs in English. Locale de-DE: decimal comma, DD.MM.YYYY, Euro.
- Money: integer cents in memory and domain code, never floats. In files and API payloads, money is a decimal string with exactly two fraction digits (for example "119.00").
- Security v1: bind to localhost by default, no auth, no cookies, CORS closed. Document running behind a reverse proxy.
- License: GPL-3.0-or-later. Keep copyright notices wherever logic or form definitions are ported, and list ported pieces in NOTICE.
- Packaging: a Dockerfile that uses uv to install Python 3.15 and the locked dependencies, with DATA_DIR as a volume.

## Data format: plain JSON file (the key design decision)

The user's data is a single plain, human-readable JSON file per client (Mandant), stored server-side in DATA_DIR and downloadable and uploadable 1:1 through the UI. Download gives exactly the file on disk, and uploading creates or replaces a book. The file is the product. There is no database.

- Canonical format is JSON (UTF-8, indent=2, deterministic key and list ordering so git diffs stay small). YAML is out of scope for v1.
- Top level: format ("easycash-web"), format_version (integer), revision (integer, incremented on every save), meta (client name, business type, timestamps), settings, accounts, tax_rates (with validity dates), bookings. Final field list goes into docs/FORMAT.md. Entities have a stable id (stdlib uuid7) plus user-visible numbers where the original has them (booking number, receipt number).
- Generate docs/format.schema.json from the Pydantic models, and serve it at /api/v1/schema.
- Versioning: every load goes through a chain of migration functions from older format_version values. Refuse files with a newer version than
